import os
import json
from dataclasses import dataclass

from .base_logger import AbstractLogWriter
from ..utils import CustomJsonEncoder


@dataclass
class JsonLogWriter(AbstractLogWriter):

    file_name: str

    def __post_init__(self):
        os.makedirs(os.path.dirname(self.file_name), exist_ok=True)
        # Create the file if it doesn't exist
        with open(self.file_name, "a", encoding="utf-8"):
            pass

    def __call__(self, logged_data: dict):
        with open(self.file_name, "a", encoding="utf-8") as f:
            f.write(json.dumps(logged_data, cls=CustomJsonEncoder) + "\n")
