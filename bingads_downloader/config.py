"""
Configures access to BingAds API and where to store results
"""


def data_dir() -> str:
    """The directory where result data is written to"""
    return '/tmp/bingads/'


def data_file() -> str:
    """The name of the file the result is written to"""
    return 'download.csv.gz'


def first_date() -> str:
    """The first day from which on data will be downloaded"""
    return '2015-01-01'

def developer_token() -> str:
    """The developer token that is used to access the BingAds API"""
    return '012A3B3C4D001234'


def environment() -> str:
    """The deployment environment"""
    return 'production'


def oauth2_client_id() -> str:
    """The Oauth client id obtained from the BingAds developer center"""
    return 'a411bc41-12d4-1234-b123-ef120120g387'


def oauth2_client_state() -> str:
    """non guessable client state"""
    return '123456'


def oauth2_client_secret() -> str:
    """The Oauth client secret obtained from the BingAds developer center"""
    return 'a1B2Cde1Fi9g2hIjKLMno5p'


def oauth2_refresh_token() -> str:
    """The Oauth refresh token returned from the adwords-downloader-refresh-oauth2-token script"""
    return 'ABCdeFgHi!hTXYUDAhSRFZtc2b9n1YyZBDc5BBx9ckPit0EVkMJYgMhlz!aeVbqiFMdbwe69QZVKOIpd2Ns8MHrPU1haST2svtx0zOcdhUQe7Sdnl1AgBVe21xm4dTH9CdG9GIPAZlGH!QZQTP97wsb0ROvn2y71b*VBodw9wjiS0GIWyr8jcsQoYUPUSsP*ST*gRnPtM4Sst0XmEswNhk15OI1gL9OLCYwDl89*mSQUJkuV11vgkV9kZy3spqTEK0toBkgYInLf5EBCxUaZkKVDqUpv*xRCqrU3Ae0wyZFDJwq7DjmUQig7pKofqumVwZ3EqYA0U732g2Dlcf8u8LjM$'


def timeout() -> int:
    # The maximum amount of time (in milliseconds) that you want to wait for the report download.
    return 3600000
