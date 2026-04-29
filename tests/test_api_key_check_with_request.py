import requests

from lm_proxy.api_key_check import CheckAPIKeyWithRequest


class _ResponseOk:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_check_api_key_with_request_success(monkeypatch):
    def fake_request(method, url, headers, timeout):
        assert method == "post"
        assert url == "https://auth.local/check?key=token-1"
        assert headers["Authorization"] == "Bearer token-1"
        assert timeout == 3
        return _ResponseOk({"group": "pro", "sub": "u-1"})

    monkeypatch.setattr(requests, "request", fake_request)

    checker = CheckAPIKeyWithRequest(
        url="https://auth.local/check?key={api_key}",
        method="post",
        headers={"Authorization": "Bearer {api_key}"},
        timeout=3,
        response_as_user_info=True,
        group_field="group",
        default_group="default",
    )

    group, user_info = checker("token-1")
    assert group == "pro"
    assert user_info == {"group": "pro", "sub": "u-1"}


def test_check_api_key_with_request_returns_none_on_http_error(monkeypatch):
    def fake_request(*args, **kwargs):
        raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr(requests, "request", fake_request)

    checker = CheckAPIKeyWithRequest(url="https://auth.local/check?key={api_key}")
    assert checker("token-2") is None
