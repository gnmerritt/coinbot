import logging
from slacker_log_handler import SlackerLogHandler, NoStacktraceFormatter

FMT = '*[%(levelname)s]* <%(name)s> %(message)s'


def setup_loggers(slack):
    for name in ['default', 'txns', 'cron']:
        handler = SlackerLogHandler(
            slack['key'], slack['channel'],
            username=slack['username'], icon_emoji=slack['emoji']
        )

        formatter = NoStacktraceFormatter(FMT)
        handler.setFormatter(formatter)
        handler.setLevel(logging.INFO)
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
