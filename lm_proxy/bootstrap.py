"""Initialization and bootstrapping."""
import sys
import logging
import inspect
from os import PathLike
from datetime import datetime
from typing import TYPE_CHECKING

import microcore as mc
from microcore import ui
from microcore.configuration import get_bool_from_env
from dotenv import load_dotenv

from .config import Config
from .utils import resolve_instance_or_callable

if TYPE_CHECKING:
    from .loggers import TLogger


def setup_logging(log_level: int = logging.INFO):
    """Setup logging format and level."""
    class CustomFormatter(logging.Formatter):
        """Custom log formatter with colouring."""
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
    """Runtime environment singleton."""
    config: Config
    connections: dict[str, mc.types.LLMAsyncFunctionType]
    debug: bool
    components: dict
    loggers: list["TLogger"]

    def _init_components(self):
        self.components = {}
        for name, component_data in self.config.components.items():
            self.components[name] = resolve_instance_or_callable(component_data)
            logging.info("Component initialized: '%s'.", name)

    @staticmethod
    def init(config: Config | str | PathLike, debug: bool = False):
        """Initializes the LM-Proxy runtime environment singleton."""
        env.debug = debug

        if not isinstance(config, Config):
            if isinstance(config, (str, PathLike)):
                config = Config.load(config)
            else:
                raise ValueError("config must be a string (file path) or Config instance")
        env.config = config

        env._init_components()

        env.loggers = [resolve_instance_or_callable(logger) for logger in env.config.loggers]

        # initialize connections
        env.connections = {}
        for conn_name, conn_config in env.config.connections.items():
            logging.info("Initializing '%s' LLM proxy connection...", conn_name)
            try:
                if inspect.iscoroutinefunction(conn_config):
                    env.connections[conn_name] = conn_config
                elif isinstance(conn_config, str):
                    env.connections[conn_name] = resolve_instance_or_callable(conn_config)
                else:
                    mc.configure(
                        **conn_config, EMBEDDING_DB_TYPE=mc.EmbeddingDbType.NONE
                    )
                    env.connections[conn_name] = mc.env().llm_async_function
            except mc.LLMConfigError as e:
                raise ValueError(
                    f"Error in configuration for connection '{conn_name}': {e}"
                ) from e

        logging.info("Done initializing %d connections.", len(env.connections))


env = Env()


def bootstrap(config: str | Config = "config.toml", env_file: str = ".env", debug=None):
    """Bootstraps the LM-Proxy environment."""
    def log_bootstrap():
        cfg_val = 'dynamic' if isinstance(config, Config) else ui.blue(config)
        cfg_line = f"\n  - Config{ui.gray('......')}[ {cfg_val} ]"
        env_line = f"\n  - Env. File{ui.gray('...')}[ {ui.blue(env_file)} ]" if env_file else ""
        dbg_line = f"\n  - Debug{ui.gray('.......')}[ {ui.yellow('On')} ]" if debug else ""
        message = f"Bootstrapping {ui.magenta('LM-Proxy')}...{cfg_line}{env_line}{dbg_line}"
        logging.info(message)

    if env_file:
        load_dotenv(env_file, override=True)
    if debug is None:
        debug = "--debug" in sys.argv or get_bool_from_env("LM_PROXY_DEBUG", False)
    setup_logging(logging.DEBUG if debug else logging.INFO)
    mc.logging.LoggingConfig.OUTPUT_METHOD = logging.info
    log_bootstrap()
    Env.init(config, debug=debug)
