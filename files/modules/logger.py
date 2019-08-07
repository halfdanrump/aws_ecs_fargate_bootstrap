import enum
import logging
import sys
import traceback
from functools import partial
from logging import StreamHandler
from typing import Dict, List

import progressbar
from slack_logger import SlackFormatter, SlackHandler


class LoggerName(enum.Enum):
    """
    This class will be project dependent, and the enum values must
    match the names specified in config["whitelisted"]
    """

    stdout = "zendishes"
    slack = "zendishes_slack"


def trace():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    logging.debug(
        "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    )


# make sure that progressbar integrates with logging, see https://pypi.org/project/progressbar2/
progressbar.streams.wrap_stderr()
progressbar.streams.flush()


def setup_logger(config):
    logger = logging.getLogger(LoggerName.stdout.value)
    logger.setLevel(config["whitelisted"]["loglevel"])

    log_format = "[%(asctime)s][PID:%(process)d][%(module)s:%(lineno)d:%(funcName)s][%(levelname)s]\t%(message)s"

    formatter = logging.Formatter(log_format)
    stream_handler = StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def setup_slack_logger(config):
    slack_logger = logging.getLogger(LoggerName.slack.value)
    slack_handler = SlackHandler(
        username="logger", icon_emoji=":robot_face:", url=config["slack_webhook"]
    )
    slack_handler.setLevel(config["whitelisted"]["loglevel"])

    log_format = "[%(name)s][%(asctime)s][%(module)s:%(lineno)d:%(funcName)s][%(levelname)s]\t%(message)s"
    slack_formattter = SlackFormatter(log_format)
    slack_handler.setFormatter(slack_formattter)
    slack_logger.addHandler(slack_handler)
    return slack_logger


class Logger:
    def __init__(self, config: dict, default_loggers: List[LoggerName]):
        assert "whitelisted" in config
        assert "blacklisted" in config
        self.config = config
        self.loggers = self.setup_loggers()
        self.default_loggers = default_loggers
        for loglevel in ["debug", "info", "warning", "error", "critical"]:
            f = partial(self.log_all, loglevel)
            setattr(self, loglevel, f)

    def setup_loggers(self) -> Dict[LoggerName, logging.Logger]:
        # setup logger for stdout
        logger = setup_logger(self.config)
        self.set_loglevel(logger)

        # setup logger for slack
        logger_slack = setup_slack_logger(self.config)
        # set verbose=False because we don't want to send info about loglevel
        # tweaking to slack
        self.set_loglevel(logger_slack, verbose=False)
        return {LoggerName.stdout: logger, LoggerName.slack: logger_slack}

    def set_loglevel(self, logger, verbose=True):
        for l in logging.Logger.manager.loggerDict.keys():
            if l.split(".")[0] in self.config["whitelisted"]["whitelist"]:
                logging.getLogger(l).setLevel(self.config["whitelisted"]["loglevel"])
                if not verbose:
                    continue
                logger.info(
                    f"Setting loglevel for {l} to {self.config['whitelisted']['loglevel']}"
                )
            else:
                logging.getLogger(l).setLevel(self.config["blacklisted"]["loglevel"])
                if not verbose:
                    continue
                logger.info(
                    f"Setting loglevel for {l} to {self.config['blacklisted']['loglevel']}"
                )

    def log_all(self, loglevel, msg: str, *include: List[LoggerName]):
        for logger_name in self.default_loggers + list(include):
            logger = self.loggers.get(logger_name)
            getattr(logger, loglevel)(msg)
