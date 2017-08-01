import logging
from slacker_log_handler import SlackerLogHandler, NoStacktraceFormatter

FMT = '*[%(levelname)s]* %(message)s'


def setup_loggers(slack):
    for name in ['default', 'txns', 'cron']:
        username = "{}-{}".format(slack['username'], name)
        handler = SlackerLogHandler(
            slack['key'], slack['channel'],
            username=username, icon_emoji=slack['emojis'].get(name)
        )

        formatter = NoStacktraceFormatter(FMT)
        handler.setFormatter(formatter)
        handler.setLevel(logging.INFO)
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
