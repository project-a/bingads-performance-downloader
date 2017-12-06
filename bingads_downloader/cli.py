"""Command line interface for adwords downloader"""

import sys

import click
from bingads_downloader import downloader,config
from functools import partial


def config_option(config_function):
    """Helper decorator that turns an option function into a cli option"""
    return lambda function: \
        click.option('--' + config_function.__name__,
                     help=f'{config_function.__doc__}. Default: "{config_function()}"')(function)


def apply_options(kwargs):
    """Applies passed cli parameters to config.py"""
    for key, value in kwargs.items():
        if value: setattr(config, key, partial(lambda v: v, value))


def show_version():
    """Shows the package version in logs, if possible"""
    try:
        import pkg_resources
        version = pkg_resources.require("bingads-performance-downloader")[0].version
        print('Bing ads performance downloader version {}'.format(version))
    except:
        print('Warning: cannot determine module version')
        print(sys.exc_info())


@click.command()
@config_option(config.developer_token)
@config_option(config.oauth2_client_id)
@config_option(config.oauth2_client_secret)
def refresh_oauth2_token(**kwargs):
    """
    Creates a new OAuth2 token.
    When options are not specified, then the defaults from config.py are used.
    """
    apply_options(kwargs)
    show_version()
    downloader.refresh_oauth_token()


@click.command()
@config_option(config.developer_token)
@config_option(config.oauth2_client_id)
@config_option(config.oauth2_client_secret)
@config_option(config.oauth2_refresh_token)
@config_option(config.data_dir)
@config_option(config.ad_performance_data_file)
@config_option(config.keyword_performance_data_file)
@config_option(config.first_date)
@config_option(config.environment)
@config_option(config.timeout)
@config_option(config.total_attempts_for_single_day)
@config_option(config.retry_timeout_interval)
def download_data(**kwargs):
    """
    Downloads data.
    When options are not specified, then the defaults from config.py are used.
    """
    apply_options(kwargs)
    show_version()
    downloader.download_data()