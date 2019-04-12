"""Make the functionalities of this package auto-discoverable by mara-app"""


def MARA_CONFIG_MODULES():
    from . import config
    return [config]


def MARA_FLASK_BLUEPRINTS():
    return []


def MARA_AUTOMIGRATE_SQLALCHEMY_MODELS():
    return []


def MARA_ACL_RESOURCES():
    return {}


def MARA_CLICK_COMMANDS():
    from . import cli
    return [cli.download_data, cli.refresh_oauth2_token]


def MARA_NAVIGATION_ENTRIES():
    return []
