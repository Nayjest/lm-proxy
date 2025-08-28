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

    @staticmethod
    def init(config: Config | str, debug: bool = False):
        env.debug = debug

        if isinstance(config, Config):
            env.config = config
        elif isinstance(config, str):
            env.config = Config.load(config)
        else:
            raise ValueError("config must be a string (file path) or Config instance")

        # initialize connections
        env.connections = dict()
        for conn_name, conn_config in env.config.connections.items():
            logging.info(f"Initializing '{conn_name}' LLM proxy connection...")
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


env = Env()


def bootstrap(config: str | Config = 'config.toml'):
    load_dotenv('.env', override=True)
    debug = '--debug' in sys.argv or get_bool_from_env('LM_PROXY_DEBUG', False)
    setup_logging(logging.DEBUG if debug else logging.INFO)
    mc.logging.LoggingConfig.OUTPUT_METHOD = logging.info
    logging.info(
        f"Bootstrapping {ui.yellow('lm_proxy')} "
        f"using configuration: {'dynamic' if isinstance(config, Config) else ui.blue(config)} "
        f"{'[DEBUG: ON]' if debug else ''}..."
    )
    Env.init(config, debug=debug)
