import datetime
import errno
import sys
import tempfile
import urllib
import webbrowser
from pathlib import Path

from bingads import (AuthorizationData, OAuthAuthorization, OAuthDesktopMobileAuthCodeGrant,
                     OAuthTokenRequestException)
from bingads.v11.reporting.reporting_service_manager import ReportingServiceManager, time
from bingads.service_client import ServiceClient

from bingads_downloader import config


class BingReportClient(ServiceClient):
    """
    A client for downloading data from the Bing Ads API
    """

    def __init__(self):
        authorization_data = AuthorizationData(
            developer_token=config.developer_token(),
            authentication=OAuthAuthorization(client_id=config.oauth2_client_id(),
                                              oauth_tokens=config.developer_token()),
        )

        self.client = super(BingReportClient, self).__init__(service='ReportingService',
                                                             authorization_data=authorization_data,
                                                             environment='production', version='v11')


def download_data():
    """
    Creates an BingApiClient and downloads the data
    """
    api_client = BingReportClient()
    download_data_sets(api_client)


def download_data_sets(api_client: BingReportClient):
    """
    Downloads BingAds performance
        Args:
            api_client: BingAdsApiClient
    """

    authenticate_with_oauth(api_client)
    download_performance_data(api_client)


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

        if not filepath.is_dir() or (last_date - current_date).days < 31:
            report_request_ad = build_ad_performance_request_for_single_day(api_client, current_date)
            report_request_keyword = build_keyword_performance_request_for_single_day(api_client, current_date)

            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_filepath = Path(tmp_dir, relative_filepath)
                tmp_filepath.parent.mkdir(exist_ok=True, parents=True)
                try:
                    start_time = time.time()
                    submit_and_download(report_request_ad, api_client, str(filepath), config.ad_performance_data_file())
                    print('Successfully downloaded ad data for {date:%Y-%m-%d} in {elapsed:.1f} seconds'
                          .format(date=current_date, elapsed=time.time() - start_time))
                    start_time = time.time()
                    submit_and_download(report_request_keyword, api_client, str(filepath), config.keyword_performance_data_file())
                    print('Successfully downloaded keyword data for {date:%Y-%m-%d} in {elapsed:.1f} seconds'
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
        else:
            current_date -= datetime.timedelta(days=1)





def build_ad_performance_request_for_single_day(api_client: BingReportClient,
                                                current_date: datetime):
    """
    Creates an Ad report request object with hard coded parameters for a give date.
    Args:
        api_client: BingApiClient object
        current_date: date for which the report object will be created

    Returns:
        A report request object with our specific hard coded settings for a given date
    """
    report_request = api_client.factory.create('AdPerformanceReportRequest')
    report_request.Format = 'Csv'
    report_request.ReportName = 'My Ad Performance Report'
    report_request.ReturnOnlyCompleteData = False
    report_request.Aggregation = 'Daily'
    report_request.Language = 'English'

    report_time = api_client.factory.create('ReportTime')

    # You may either use a custom date range
    custom_date_range_start = api_client.factory.create('Date')
    custom_date_range_start.Day = current_date.day
    custom_date_range_start.Month = current_date.month
    custom_date_range_start.Year = current_date.year
    report_time.CustomDateRangeStart = custom_date_range_start
    report_time.CustomDateRangeEnd = custom_date_range_start
    report_time.PredefinedTime = None
    report_request.Time = report_time

    report_columns = api_client.factory.create('ArrayOfAdPerformanceReportColumn')
    report_columns.AdPerformanceReportColumn.append([
        "AccountName",
        "AccountNumber",
        "AccountId",
        "TimePeriod",
        "CampaignName",
        "CampaignId",
        "AdGroupName",
        "AdId",
        "AdGroupId",
        "AdTitle",
        "AdDescription",
        "AdType",
        "Impressions",
        "Clicks",
        "Ctr",
        "Spend",
        "AveragePosition",
        "Conversions",
        "ConversionRate",
        "CostPerConversion",
        "DeviceType",
        "AccountStatus",
        "CampaignStatus",
        "AdGroupStatus",
        "AdLabels"
    ])
    report_request.Columns = report_columns

    return report_request


def build_keyword_performance_request_for_single_day(api_client: BingReportClient,
                                                current_date: datetime):
    """
    Creates a Keyword report request object with hard coded parameters for a give date.
    Args:
        api_client: BingApiClient object
        current_date: date for which the report object will be created

    Returns:
        A report request object with our specific hard coded settings for a given date
    """
    report_request = api_client.factory.create('KeywordPerformanceReportRequest')
    report_request.Format = 'Csv'
    report_request.ReportName = 'My Keyword Performance Report'
    report_request.ReturnOnlyCompleteData = False
    report_request.Aggregation = 'Daily'
    report_request.Language = 'English'

    report_time = api_client.factory.create('ReportTime')

    # You may either use a custom date range
    custom_date_range_start = api_client.factory.create('Date')
    custom_date_range_start.Day = current_date.day
    custom_date_range_start.Month = current_date.month
    custom_date_range_start.Year = current_date.year
    report_time.CustomDateRangeStart = custom_date_range_start
    report_time.CustomDateRangeEnd = custom_date_range_start
    report_time.PredefinedTime = None
    report_request.Time = report_time

    report_columns = api_client.factory.create('ArrayOfKeywordPerformanceReportColumn')
    report_columns.KeywordPerformanceReportColumn.append([
        "TimePeriod",
        "AccountId",
        "AccountName",
        "CampaignId",
        "CampaignName",
        "AdGroupId",
        "AdGroupName",
        "AdId",
        "Keyword",
        "KeywordId",
        "DeviceType",
        "BidMatchType",
        "Clicks",
        "Impressions",
        "Ctr",
        "AverageCpc",
        "Spend",
        "QualityScore",
        "Conversions",
        "Revenue",
        "Network"
    ])
    report_request.Columns = report_columns

    report_sorts = api_client.factory.create('ArrayOfKeywordPerformanceReportSort')
    report_sort = api_client.factory.create('KeywordPerformanceReportSort')
    report_sort.SortColumn = 'Clicks'
    report_sort.SortOrder = 'Ascending'
    report_sorts.KeywordPerformanceReportSort.append(report_sort)
    report_request.Sort = report_sorts
    return report_request


def submit_and_download(report_request, api_client, data_dir, data_file):
    """
    Submit the download request and then use the ReportingDownloadOperation result to
    track status until the report is complete.
    Args:
        report_request: report_request object e.g. created by get_ad_performance_for_single_day
        api_client: BingApiClient object
        data_dir: target directory of the files containing the reports
        data_file: the name of the file containing the data
    """

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
        decompress=False,
        overwrite=True,  # Set this value true if you want to overwrite the same file.
        timeout_in_milliseconds=config.timeout()
    )

    print("Download result file: {}".format(result_file_path))
    print("Status: {}\n".format(current_reporting_operation_status.status))


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
        print('Authentication error. Could be necessary to run refresh refresh-bingads-api-oauth2-token', file=sys.stderr)
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


if __name__ == "__main__":
    download_data()
