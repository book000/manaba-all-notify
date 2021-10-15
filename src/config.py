import json
import os
from types import SimpleNamespace
from typing import NamedTuple, Optional


class Config(NamedTuple):
    """
    Config class
    """
    discord_token: str
    discord_task_channel: str
    discord_news_channel: str
    discord_content_channel: str
    discord_threads_channel: str
    manaba_base_url: str
    manaba_username: str
    manaba_password: str


class FailedLoadConfigException(Exception):
    """
    Failed to laod config
    """
    pass


def load_config(filepath: str) -> Config:
    """
    Load config file

    Args:
        filepath: config file path

    Returns:
        Optional[Config]: Config object. If load config fails, return None
    """
    if not os.path.exists(filepath):
        raise FailedLoadConfigException("File not found")
    try:
        with open(filepath, encoding="utf-8") as f:
            config: Config = json.load(f, object_hook=lambda d: SimpleNamespace(**d))
            return config
    except TypeError as e:
        print("Error loading config file:", e.args)
        raise FailedLoadConfigException("Error loading config file: %s" % (e.args, ))
