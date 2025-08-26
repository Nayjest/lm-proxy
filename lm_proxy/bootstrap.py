import logging
from datetime import datetime
import microcore as mc


def setup_logging(log_level: int = logging.INFO):
    class CustomFormatter(logging.Formatter):
        def format(self, record):
            dt = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            message, level_name = record.getMessage(), record.levelname
            if record.levelno == logging.WARNING:
                message = mc.ui.yellow(message)
                level_name = mc.ui.yellow(level_name)
            if record.levelno >= logging.ERROR:
                message = mc.ui.red(message)
                level_name = mc.ui.red(level_name)
            return f"{dt} {level_name}: {message}"

    handler = logging.StreamHandler()
    handler.setFormatter(CustomFormatter())
    logging.basicConfig(level=log_level, handlers=[handler])

def bootstrap():
    setup_logging()
    logging.info("Bootstrapping lm_proxy application...")
    mc.configure(
        DOT_ENV_FILE='.env',
        USE_LOGGING=True,
    )
    mc.logging.LoggingConfig.OUTPUT_METHOD = logging.info