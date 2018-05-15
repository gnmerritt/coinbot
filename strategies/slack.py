import sys
import logging
from slacker_log_handler import SlackerLogHandler, NoStacktraceFormatter

FMT = '*[%(levelname)s]* %(message)s'
default = logging.getLogger('default')


def setup_loggers(slack):
    for name in ['default', 'txns', 'cron']:
        username = "{}-{}".format(slack['username'], name)
        channel = slack['channel']
        if name == 'txns':
            channel = slack.get('txns-channel', channel)
        handler = SlackerLogHandler(
            slack['key'], channel,
            username=username, icon_emoji=slack['emojis'].get(name)
        )

        formatter = NoStacktraceFormatter(FMT)
        handler.setFormatter(formatter)
        handler.setLevel(logging.INFO)
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

    sys.excepthook = handle_exception


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    default.error("Uncaught exception",
                  exc_info=(exc_type, exc_value, exc_traceback))
