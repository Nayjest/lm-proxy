import sys
import logging
from datetime import datetime

from dotenv import load_dotenv
import microcore as mc

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

    @staticmethod
    def bootstrap(config_file: str = 'config.toml') -> 'Env':
        setup_logging()
        logging.info("Bootstrapping lm_proxy application...")

        env = Env()
        load_dotenv('.env', override=True)
        env.config = Config.load(config_file)
        env.connections = dict()

        for conn_name, conn_config in env.config.connections.items():
            logging.info(f"Initializing '{conn_name}' connection...")
            try:
                mc.configure(
                    **conn_config,
                    EMBEDDING_DB_TYPE=mc.EmbeddingDbType.NONE
                )
            except mc.LLMConfigError as e:
                raise ValueError(f"Error in configuration for connection '{conn_name}': {e}")

            env.connections[conn_name] = mc.env().llm_async_function
        logging.info(f"Done initializing {len(env.connections)} connections.")
        mc.logging.LoggingConfig.OUTPUT_METHOD = logging.info
        return env