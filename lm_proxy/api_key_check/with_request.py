"""
API key check implementation using HTTP requests.
"""
from typing import Optional
from dataclasses import dataclass, field
import requests

from ..config import TApiKeyCheckFunc


@dataclass(slots=True)
class CheckAPIKeyWithRequest:  # pylint: disable=too-many-instance-attributes
    """
    Validates a Client API key by making an HTTP request to a specified URL.
    """
    url: str = field()
    method: str = field(default="get")
    headers: dict = field(default_factory=dict)
    response_as_user_info: bool = field(default=False)
    group_field: Optional[str] = field(default=None)
    """
    Field in the JSON response to extract the user group.
    """
    default_group: str = field(default="default")
    """
    User group to assign if group_field is not used.
    """
    key_placeholder: str = field(default="{api_key}")
    use_cache: bool = field(default=False)
    """
    Whether to cache the results of API key checks.
    Requires 'cachetools' package if set to True.
    """
    cache_size: int = field(default=1024 * 16)
    cache_ttl: int = field(default=60 * 5)  # 5 minutes
    timeout: int = field(default=5)  # seconds
    _func: TApiKeyCheckFunc = field(init=False, repr=False)

    def __post_init__(self):
        def check_func(api_key: str) -> Optional[tuple[str, dict]]:
            try:
                url = self.url.replace(self.key_placeholder, api_key)
                headers = {
                    k: str(v).replace(self.key_placeholder, api_key)
                    for k, v in self.headers.items()
                }
                response = requests.request(
                    method=self.method,
                    url=url,
                    headers=headers,
                    timeout=self.timeout
                )
                response.raise_for_status()
                group = self.default_group
                user_info = None
                if self.response_as_user_info:
                    user_info = response.json()
                    if self.group_field:
                        group = user_info.get(self.group_field, self.default_group)
                return group, user_info
            except requests.exceptions.RequestException:
                return None

        if self.use_cache:
            try:
                import cachetools  # pylint: disable=import-outside-toplevel
            except ImportError as e:
                raise ImportError(
                    "Missing optional dependency 'cachetools'. "
                    "Using 'lm_proxy.api_key_check.CheckAPIKeyWithRequest' with 'use_cache = true' "
                    "requires installing 'cachetools' package. "
                    "\nPlease install it with the following command: 'pip install cachetools'"
                ) from e
            cache = cachetools.TTLCache(maxsize=self.cache_size, ttl=self.cache_ttl)
            self._func = cachetools.cached(cache)(check_func)
        else:
            self._func = check_func

    def __call__(self, api_key: str) -> Optional[tuple[str, dict]]:
        return self._func(api_key)
