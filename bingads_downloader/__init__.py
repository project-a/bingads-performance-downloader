from bingads_downloader import cli, config

MARA_CONFIG_MODULES = [config]

MARA_CLICK_COMMANDS = [cli.download_data, cli.refresh_oauth2_token]
