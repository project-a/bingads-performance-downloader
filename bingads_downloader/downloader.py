import csv
import datetime
import errno
import gzip
import json
import os
import re
import shutil
import sys
import tempfile
import urllib
import webbrowser
from pathlib import Path

from bingads import (AuthorizationData, OAuthAuthorization, OAuthDesktopMobileAuthCodeGrant,
                     OAuthTokenRequestException)
from bingads.service_client import ServiceClient
from bingads.v13.reporting.reporting_service_manager import ReportingServiceManager, time
from suds import WebFault

from bingads_downloader import config


class BingReportClient(ServiceClient):
    """
    A client for downloading data from the Bing Ads API
    """

    def __init__(self):
        authorization_data = AuthorizationData(
            developer_token=config.developer_token(),
            customer_id=config.oauth2_customer_id(),
            account_id=config.oauth2_account_id(),
            authentication=OAuthAuthorization(client_id=config.oauth2_client_id(),
                                              oauth_tokens=config.developer_token()
                                             ),
        )

        self.client = super(BingReportClient, self).__init__(service='ReportingService',
                                                             authorization_data=authorization_data,
                                                             environment='production', version='v13')


def download_data():
    """
    Creates an BingApiClient and downloads the data
    """
    try:
        api_client = BingReportClient()
        download_data_sets(api_client)
    except WebFault as e:
        print(e.fault)
        raise


def download_data_sets(api_client: BingReportClient):
    """
    Downloads BingAds performance
        Args:
            api_client: BingAdsApiClient
    """

    authenticate_with_oauth(api_client)
    download_account_structure_data(api_client)
    download_performance_data(api_client)


def download_account_structure_data(api_client: BingReportClient):
    """
    Downloads the marketing structure for all accounts
        Args:
         api_client: BingAdsApiClient
    """

    filename = Path('bing-account-structure_{}.csv.gz'.format(config.output_file_version()))
    filepath = ensure_data_directory(filename)
    print('Start downloading account structure in {}'.format(str(filename)))
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_filepath = Path(tmp_dir, filename)
        with gzip.open(str(tmp_filepath), 'wt') as tmp_campaign_structure_file:
            header = ['AdId', 'AdTitle', 'AdGroupId', 'AdGroupName', 'CampaignId',
                      'CampaignName', 'AccountId', 'AccountName', 'Attributes']
            writer = csv.writer(tmp_campaign_structure_file, delimiter="\t")
            ad_data = get_ad_data(api_client, tmp_dir)
            campaign_attributes = get_campaign_attributes(api_client, tmp_dir)
            writer.writerow(header)
            for ad_id, ad_data_dict in ad_data.items():
                campaign_id = ad_data_dict['CampaignId']
                ad_group_id = ad_data_dict['AdGroupId']
                attributes = {**campaign_attributes.get(campaign_id, {}),
                              **ad_data_dict['attributes']}
                ad = [str(ad_id),
                      ad_data_dict['AdTitle'],
                      str(ad_group_id),
                      ad_data_dict['AdGroupName'],
                      str(campaign_id),
                      ad_data_dict['CampaignName'],
                      ad_data_dict['AccountId'],
                      ad_data_dict['AccountName'],
                      json.dumps(attributes)
                      ]

                writer.writerow(ad)

        shutil.move(str(tmp_filepath), str(filepath))


def get_ad_data(api_client: BingReportClient, tmp_dir: Path) -> {}:
    """Downloads the ad data from the Bing AdWords API
    Args:
        api_client: BingAdsApiClient
        tmp_dir: path to write the temp file in
    Returns:
        A dictionary of the form {ad_id: {key: value}}
    """
    ad_data = {}
    fields = ["TimePeriod",
              "DeviceType",

              "AccountId",
              "AccountName",
              "AccountNumber",
              "AccountStatus",

              "CampaignId",
              "CampaignName",
              "CampaignStatus",

              "AdGroupId",
              "AdGroupName",
              "AdGroupStatus",

              "AdId",
              "AdTitle",
              "AdDescription",
              "AdType",
              "AdLabels",

              "Impressions"]  # need to include impressions, otherwise API call fails??
    report_request_ad = build_ad_performance_request(api_client, current_date=None, fields=fields, all_time=True)

    report_file_location = submit_and_download(report_request_ad, api_client, str(tmp_dir),
                                               'ad_account_structure_{}.csv'.format(config.output_file_version()),
                                               overwrite_if_exists=True, decompress=True)

    with open(report_file_location, 'r') as f:
        for i in range(11):  # skip header lines
            next(f)
        reader = csv.reader(f)
        report_data = list(reader)

    relevant_columns = ['AdId', 'AdTitle', 'AdGroupId', 'AdGroupName', 'CampaignId', 'CampaignName', 'AccountId',
                        'AccountName']
    positions = [fields.index(name) for name in relevant_columns]

    relevant_columns.extend(['attributes'])
    for row in report_data[:-2]:
        attributes = parse_labels(row[fields.index("AdLabels")])
        new_row = [row[i] for i in positions]
        new_row.extend([attributes])
        ad_data[row[fields.index("AdId")]] = {key: value for key, value in zip(relevant_columns, new_row)}

    return ad_data


def get_campaign_attributes(api_client: BingReportClient, tmp_dir: Path) -> {}:
    """Downloads the campaign attributes from the Bing AdWords API
    Args:
        api_client: BingAdsApiClient
        tmp_dir: path to write the temp file in
    Returns:
        A dictionary of the form {campaign_id: {key: value}}
    """
    campaign_labels = {}
    fields = ["TimePeriod",

              "AccountId",
              "AccountName",
              "CampaignId",
              "CampaignName",
              "CampaignLabels",

              "Spend"]  # fails without adding spend
    report_request_campaign = build_campaign_performance_request(api_client, current_date=None,
                                                                 fields=fields, all_time=True)

    report_file_location = submit_and_download(report_request_campaign, api_client, str(tmp_dir),
                                               'campaign_labels_{}.csv'.format(config.output_file_version()),
                                               overwrite_if_exists=True, decompress=True)

    with open(report_file_location, 'r') as f:
        for i in range(11):  # skip header lines
            next(f)
        reader = csv.reader(f)
        report_data = list(reader)

    for row in report_data[:-2]:
        attributes = parse_labels(row[fields.index("CampaignLabels")])
        campaign_labels[row[fields.index("CampaignId")]] = attributes

    return campaign_labels


def download_performance_data(api_client: BingReportClient):
    """
    Downloads BingAds Ads performance reports by creating report objects
    for every day since config.first_date() till today
        Args:
         api_client: BingAdsApiClient
    """
    first_date = datetime.datetime.strptime(config.first_date(), '%Y-%m-%d')
    last_date = datetime.datetime.now() - datetime.timedelta(days=1)
    current_date = last_date
    remaining_attempts = config.total_attempts_for_single_day
    while current_date >= first_date:
        print(current_date)
        relative_filepath = Path('{date:%Y/%m/%d}/bing/'.format(
            date=current_date))
        filepath = ensure_data_directory(relative_filepath)

        overwrite_if_exists = (last_date - current_date).days < 31
        if overwrite_if_exists:
            print('The data for {date:%Y-%m-%d} will be downloaded. Already present files will be overwritten'.format(
                date=current_date))
        report_request_ad = build_ad_performance_request(api_client, current_date)
        report_request_keyword = build_keyword_performance_request(api_client, current_date)
        report_request_campaign = build_campaign_performance_request(api_client, current_date)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_filepath = Path(tmp_dir, relative_filepath)
            tmp_filepath.parent.mkdir(exist_ok=True, parents=True)
            try:
                start_time = time.time()
                print('About to download ad data for {date:%Y-%m-%d}'
                      .format(date=current_date))
                submit_and_download(report_request_ad, api_client, str(filepath),
                                    'ad_performance_{}.csv.gz'.format(config.output_file_version()),
                                    overwrite_if_exists)
                print('Successfully downloaded ad data for {date:%Y-%m-%d} in {elapsed:.1f} seconds'
                      .format(date=current_date, elapsed=time.time() - start_time))
                start_time = time.time()
                print('About to download keyword data for {date:%Y-%m-%d}'
                      .format(date=current_date))
                submit_and_download(report_request_keyword, api_client, str(filepath),
                                    'keyword_performance_{}.csv.gz'.format(config.output_file_version()),
                                    overwrite_if_exists)
                print('Successfully downloaded keyword data for {date:%Y-%m-%d} in {elapsed:.1f} seconds'
                      .format(date=current_date, elapsed=time.time() - start_time))
                print('About to download campaign data for {date:%Y-%m-%d}'
                      .format(date=current_date))
                submit_and_download(report_request_campaign, api_client, str(filepath),
                                    'campaign_performance_{}.csv.gz'.format(config.output_file_version()),
                                    overwrite_if_exists)
                print('Successfully downloaded campaign data for {date:%Y-%m-%d} in {elapsed:.1f} seconds'
                      .format(date=current_date, elapsed=time.time() - start_time))
                # date is decreased only if the download above does not fail
                current_date -= datetime.timedelta(days=1)
                remaining_attempts = config.total_attempts_for_single_day
            except urllib.error.URLError as url_error:
                if remaining_attempts == 0:
                    print('Too many failed attempts while downloading this day, quitting', file=sys.stderr)
                    raise
                print('ERROR WHILE DOWNLOADING REPORT, RETRYING in {} seconds, attempt {}#...'
                      .format(config.retry_timeout_interval, remaining_attempts), file=sys.stderr)
                print(url_error, file=sys.stderr)
                time.sleep(config.retry_timeout_interval)
                remaining_attempts -= 1


def set_report_time(api_client: BingReportClient,
                    current_date: datetime = None, all_time: bool = False):
    """
    Sets the report time for the BingAds API Client
    Args:
        api_client: BingApiClient object
        current_date: date for which the report object will be created
        all_time: include all days from the import start date
    Returns:
        A report time object with a specific date
    """

    report_time = api_client.factory.create('ReportTime')

    custom_date_range_end = api_client.factory.create('Date')

    if current_date is None:
        current_date = datetime.datetime.now()  # for example for downloading current campaign structure
    custom_date_range_end.Day = current_date.day
    custom_date_range_end.Month = current_date.month
    custom_date_range_end.Year = current_date.year

    report_time.CustomDateRangeEnd = custom_date_range_end
    if not all_time:
        report_time.CustomDateRangeStart = custom_date_range_end
    else:
        first_date = datetime.datetime.strptime(config.first_date(), '%Y-%m-%d')
        custom_date_range_start = api_client.factory.create('Date')
        custom_date_range_start.Day = first_date.day
        custom_date_range_start.Month = first_date.month
        custom_date_range_start.Year = first_date.year
        report_time.CustomDateRangeStart = custom_date_range_start
    report_time.PredefinedTime = None
    report_time.ReportTimeZone = None

    return report_time


def build_ad_performance_request(api_client: BingReportClient,
                                 current_date: datetime = None,
                                 fields: [str] = None, all_time=False):
    """
    Creates an Ad report request object with hard coded parameters for a give date.
    Args:
        api_client: BingApiClient object
        current_date: date for which the report object will be created
        fields: a list of columns to download from AdPerformanceReport
        all_time: include all days from the import start date
    Returns:
        A report request object with our specific hard coded settings for a given date
    """
    report_request = api_client.factory.create('AdPerformanceReportRequest')
    report_request.Format = 'Csv'
    report_request.ReportName = 'My Ad Performance Report'
    report_request.ReturnOnlyCompleteData = False
    scope = api_client.factory.create('AccountThroughCampaignReportScope')
    scope.AccountIds={'long': config.oauth2_account_array()}
    scope.Campaigns=None
    report_request.Scope=scope
    if all_time:
        report_request.Aggregation = 'Yearly'
    else:
        report_request.Aggregation = 'Daily'
    #report_request.Language = 'English'
    report_request.Time = set_report_time(api_client, current_date, all_time)

    report_columns = api_client.factory.create('ArrayOfAdPerformanceReportColumn')
    if fields is None:
        report_columns.AdPerformanceReportColumn.append([
            "TimePeriod",
            "DeviceType",

            "AccountId",
            "AccountName",
            "AccountNumber",
            "AccountStatus",

            "CampaignId",
            "CampaignName",
            "CampaignStatus",

            "AdGroupId",
            "AdGroupName",
            "AdGroupStatus",

            "AdId",
            "AdTitle",
            "AdDescription",
            "AdType",
            "AdLabels",

            "Impressions",
            "Clicks",
            "Ctr",
            "Spend",
            "AveragePosition",
            "Conversions",
            "ConversionRate",
            "CostPerConversion"
        ])
    else:
        report_columns.AdPerformanceReportColumn.append(fields)
    report_request.Columns = report_columns

    return report_request


def build_keyword_performance_request(api_client: BingReportClient,
                                      current_date: datetime = None,
                                      fields: [str] = None, all_time=False):
    """
    Creates a Keyword report request object with hard coded parameters for a give date.
    Args:
        api_client: BingApiClient object
        current_date: date for which the report object will be created
        fields: a list of columns to download from AdPerformanceReport
        all_time: include all days from the import start date
    Returns:
        A report request object with our specific hard coded settings for a given date
    """
    report_request = api_client.factory.create('KeywordPerformanceReportRequest')
    report_request.Format = 'Csv'
    report_request.ReportName = 'My Keyword Performance Report'
    report_request.ReturnOnlyCompleteData = False
    scope = api_client.factory.create('AccountThroughCampaignReportScope')
    scope.AccountIds={'long': config.oauth2_account_array()}
    scope.Campaigns=None
    report_request.Scope=scope

    if all_time:
        report_request.Aggregation = 'Yearly'
    else:
        report_request.Aggregation = 'Daily'
    #report_request.Language = 'English'

    report_request.Time = set_report_time(api_client, current_date, all_time)

    report_columns = api_client.factory.create('ArrayOfKeywordPerformanceReportColumn')
    if fields is None:
        report_columns.KeywordPerformanceReportColumn.append([
            "TimePeriod",
            "Network",
            "DeviceType",
            "BidMatchType",

            "AccountId",
            "AccountName",
            "CampaignId",
            "CampaignName",
            "AdGroupId",
            "AdGroupName",
            "AdId",
            "KeywordId",
            "Keyword",

            "Clicks",
            "Impressions",
            "Ctr",
            "AverageCpc",
            "Spend",
            "QualityScore",
            "Conversions",
            "Revenue",
        ])
    else:
        report_columns.KeywordPerformanceReportColumn.append(fields)
    report_request.Columns = report_columns

    report_sorts = api_client.factory.create('ArrayOfKeywordPerformanceReportSort')
    report_sort = api_client.factory.create('KeywordPerformanceReportSort')
    report_sort.SortColumn = 'Clicks'
    report_sort.SortOrder = 'Ascending'
    report_sorts.KeywordPerformanceReportSort.append(report_sort)
    report_request.Sort = report_sorts

    return report_request


def build_campaign_performance_request(api_client: BingReportClient,
                                       current_date: datetime = None,
                                       fields: [str] = None, all_time=False):
    """
    Creates a Campaign report request object with hard coded parameters for a give date.
    Args:
        api_client: BingApiClient object
        current_date: date for which the report object will be created
        fields: a list of columns to download from AdPerformanceReport

    Returns:
        A report request object with our specific hard coded settings for a given date
    """
    report_request = api_client.factory.create('CampaignPerformanceReportRequest')
    report_request.Format = 'Csv'
    report_request.ReportName = 'My Campaign Performance Report'
    report_request.ReturnOnlyCompleteData = False
    scope = api_client.factory.create('AccountThroughCampaignReportScope')
    scope.AccountIds={'long': config.oauth2_account_array()}
    scope.Campaigns=None
    report_request.Scope=scope
    #report_request.Language = 'English'
    if all_time:
        report_request.Aggregation = 'Yearly'
    else:
        report_request.Aggregation = 'Daily'
    report_request.Time = set_report_time(api_client, current_date, all_time)

    report_columns = api_client.factory.create('ArrayOfCampaignPerformanceReportColumn')
    if fields is None:
        report_columns.CampaignPerformanceReportColumn.append([
            "TimePeriod",

            "AccountId",
            "AccountName",
            "CampaignId",
            "CampaignName",
            "CampaignLabels",

            "Spend"
        ])
    else:
        report_columns.CampaignPerformanceReportColumn.append(fields)

    report_request.Columns = report_columns
    return report_request


def parse_labels(labels: str) -> {str: str}:
    """Extracts labels from a string
    Args:
        labels: Labels as an json encoded array of strings '["{key_1=value_1}","{key_2=value_2}]", ..]'
    Returns:
            A dictionary of labels with {key_1 : value_1, ...} format
    """
    matches = re.findall("{([^=]+)=([^=]+)}", labels)
    labels = {x[0].strip().lower().title(): x[1].strip() for x in matches}
    return labels


def submit_and_download(report_request, api_client, data_dir, data_file, overwrite_if_exists, decompress: bool = False):
    """
    Submit the download request and then use the ReportingDownloadOperation result to
    track status until the report is complete.
    Id the file already exists, do nothing
    Args:
        report_request: report_request object e.g. created by get_ad_performance
        api_client: BingApiClient object
        data_dir: target directory of the files containing the reports
        data_file: the name of the file containing the data
        overwrite_if_exists: if True, overwrite the file
        decompress: whether to decompress zip files
    Returns:
        result_file_path: the location of the result file
    """
    target_file = data_dir + '/' + data_file
    if os.path.exists(target_file) and not overwrite_if_exists:
        print('The file {} already exists, skipping it'.format(target_file))
        return

    current_reporting_service_manager = \
        ReportingServiceManager(
            authorization_data=api_client.authorization_data,
            poll_interval_in_milliseconds=5000,
            environment='production',
            working_directory=config.data_dir(),
        )
    reporting_download_operation = current_reporting_service_manager.submit_download(report_request)

    # You may optionally cancel the track() operation after a specified time interval.
    current_reporting_operation_status = reporting_download_operation.track(
        timeout_in_milliseconds=config.timeout())

    # You can use ReportingDownloadOperation.track() to poll until complete as shown above,
    # or use custom polling logic with get_status() as shown below.
    for i in range(10):
        time.sleep(current_reporting_service_manager.poll_interval_in_milliseconds / 1000.0)

        download_status = reporting_download_operation.get_status()

        if download_status.status == 'Success':
            break

    print("Awaiting Download Results . . .")

    result_file_path = reporting_download_operation.download_result_file(
        result_file_directory=data_dir,
        result_file_name=data_file,
        decompress=decompress,
        overwrite=True,  # Set this value true if you want to overwrite the same file.
        timeout_in_milliseconds=config.timeout()
    )

    print("Download result file: {}".format(result_file_path))
    print("Status: {}\n".format(current_reporting_operation_status.status))

    return result_file_path


def authenticate_with_oauth(api_client):
    """
    Sets the authentication with OAuthDesktopMobileAuthCodeGrant.
    Args:
        param api_client: The BingApiClient.
    """

    authentication = OAuthDesktopMobileAuthCodeGrant(
        client_id=config.oauth2_client_id()
    )

    api_client.authorization_data.authentication = authentication

    # load refresh token from config
    refresh_token = config.oauth2_refresh_token()
    try:
        # If we have a refresh token let's refresh it
        if refresh_token is not None:
            api_client.authorization_data.authentication.request_oauth_tokens_by_refresh_token(
                refresh_token)
        else:
            print('No refresh token found. Please run refresh refresh-bingads-api-oauth2-token')
            sys.exit(1)
    except OAuthTokenRequestException as exc:
        print('Authentication error. Could be necessary to run refresh refresh-bingads-api-oauth2-token',
              file=sys.stderr)
        print('Ensure that the registered application type is Native-Application', file=sys.stderr)
        print(' - client id: {}'.format(config.oauth2_client_id()), file=sys.stderr)
        print(' - refresh_token: {}'.format(refresh_token), file=sys.stderr)
        print(exc, file=sys.stderr)
        sys.exit(1)


def refresh_oauth_token():
    """Retrieve and display the access and refresh token."""
    """
    Search for account details by UserId.
    Args:
        param api_client: The BingApiClient.
    Returns:
        List of accounts that the user can manage.
    """
    api_client = BingReportClient()
    authentication = OAuthDesktopMobileAuthCodeGrant(client_id=config.oauth2_client_id())
    api_client.authorization_data.authentication = authentication
    print(
        'Authorization Endpoint: {}'.format(api_client.authorization_data.authentication.get_authorization_endpoint()))
    webbrowser.open(api_client.authorization_data.authentication.get_authorization_endpoint(),
                    new=1)
    response_uri = input(
        "You need to provide consent for the application to access your Bing Ads accounts. "
        "After you have granted consent in the web browser for the application to access your Bing Ads accounts, "
        "please enter the response URI that includes the authorization 'code' parameter: \n"
    )

    # Request access and refresh tokens using the URI that you provided manually during program execution.
    oauth_tokens = api_client.authorization_data.authentication.request_oauth_tokens_by_response_uri(
        response_uri=response_uri)
    print('Below is your oauth refresh token:')
    print(str(oauth_tokens.refresh_token).replace('!', '\!'))  # this is important for bash


def ensure_data_directory(relative_path: Path = None) -> Path:
    """Checks if a directory in the data dir path exists. Creates it if necessary

    Args:
        relative_path: A Path object pointing to a file relative to the data directory

    Returns:
        The absolute path Path object

    """
    if relative_path is None:
        return Path(config.data_dir())
    try:
        current_path = Path(config.data_dir(), relative_path)
        # if path points to a file, create parent directory instead
        if current_path.suffix:
            if not current_path.parent.exists():
                current_path.parent.mkdir(exist_ok=True, parents=True)
        else:
            if not current_path.exists():
                current_path.mkdir(exist_ok=True, parents=True)
        return current_path
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
