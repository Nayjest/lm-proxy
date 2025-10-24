from typing import Optional
from dataclasses import dataclass, field
import requests


@dataclass(slots=True)
class CheckAPIKeyWithRequest:
    url: str = field()
    method: str = field(default="get")
    headers: dict = field(default_factory=dict)
    response_as_user_info: bool = field(default=False)
    group_field: Optional[str] = field(default=None)
    default_group: str = field(default="default")
    key_placeholder: str = field(default="{api_key}")
    use_cache: bool = field(default=False)
    cache_size: int = field(default=1024 * 16)
    cache_ttl: int = field(default=60 * 5)  # 5 minutes
    timeout: int = field(default=5)  # seconds
    _func: callable = field(init=False, repr=False)

    def __post_init__(self):
        def check_func(api_key: str) -> dict | None:
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
                import cachetools
            except ImportError as e:
                raise ImportError(
                    "Missing optional dependency 'cachetools'. "
                    "Using 'lm_proxy.api_key_check.CheckAPIKeyWithRequest' with 'use_cache = true' "
                    "requires installing 'cachetools' package. "
                    "\nPlease install it with following command: 'pip install cachetools'"
                ) from e
            cache = cachetools.TTLCache(maxsize=self.cache_size, ttl=self.cache_ttl)
            self._func = cachetools.cached(cache)(check_func)
        else:
            self._func = check_func

    def __call__(self, api_key: str) -> dict | None:
        return self._func(api_key)
