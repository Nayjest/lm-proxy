import sys
import logging
import inspect
from datetime import datetime


import microcore as mc
from microcore import ui
from microcore.configuration import get_bool_from_env
from dotenv import load_dotenv

from .config import Config


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


class Env:
    config: Config
    connections: dict[str, mc.types.LLMAsyncFunctionType]
    debug: bool


env = Env()


def bootstrap(config_file: str = 'config.toml'):
    load_dotenv('.env', override=True)
    env.debug = '--debug' in sys.argv or get_bool_from_env('LM_PROXY_DEBUG', False)
    setup_logging(logging.DEBUG if env.debug else logging.INFO)
    logging.info(
        f"Bootstrapping {ui.yellow('lm_proxy')} "
        f"using configuration: {ui.blue(config_file)} "
        f"{'[DEBUG: ON]' if env.debug else ''}..."
    )

    env.config = Config.load(config_file)
    env.connections = dict()

    for conn_name, conn_config in env.config.connections.items():
        logging.info(f"Initializing '{conn_name}' connection...")
        try:
            if inspect.iscoroutinefunction(conn_config):
                env.connections[conn_name] = conn_config
            else:
                mc.configure(
                    **conn_config,
                    EMBEDDING_DB_TYPE=mc.EmbeddingDbType.NONE
                )
                env.connections[conn_name] = mc.env().llm_async_function
        except mc.LLMConfigError as e:
            raise ValueError(f"Error in configuration for connection '{conn_name}': {e}")

    logging.info(f"Done initializing {len(env.connections)} connections.")
    mc.logging.LoggingConfig.OUTPUT_METHOD = logging.info
