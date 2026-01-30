"""Tests for custom headers functionality."""

import pytest
from lm_proxy.utils import (
    filter_sensitive_headers,
    merge_headers,
    SENSITIVE_HEADERS,
)


class TestFilterSensitiveHeaders:
    """Tests for the filter_sensitive_headers utility function."""

    def test_filter_authorization_header(self):
        """Test that Authorization header is filtered out."""
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer secret-token",
            "X-Custom-Header": "value",
        }
        result = filter_sensitive_headers(headers)
        assert "authorization" not in result
        assert "Authorization" not in result
        assert result.get("Accept") == "application/json"
        assert result.get("X-Custom-Header") == "value"

    def test_filter_content_length_header(self):
        """Test that Content-Length header is filtered out."""
        headers = {
            "Content-Length": "123",
            "X-Custom-Header": "value",
        }
        result = filter_sensitive_headers(headers)
        assert "content-length" not in result
        assert result.get("X-Custom-Header") == "value"

    def test_filter_host_header(self):
        """Test that Host header is filtered out."""
        headers = {
            "Host": "api.example.com",
            "X-Custom-Header": "value",
        }
        result = filter_sensitive_headers(headers)
        assert "host" not in result
        assert result.get("X-Custom-Header") == "value"

    def test_case_insensitive_filtering(self):
        """Test that header filtering is case-insensitive."""
        auth_header_varitions = ["AUTHORIZATION", "Authorization", "authorization"]
        for auth_header in auth_header_varitions:
            headers = {
                auth_header: "Bearer token",
                "Content-Type": "application/json",
                "X-Custom-Header": "value",
            }
            result = filter_sensitive_headers(headers)
            assert not any(i in result for i in auth_header_varitions)
            assert "content-type" not in result
            assert "Content-Type" not in result
            assert result.get("X-Custom-Header") == "value"

    def test_allow_custom_headers(self):
        """Test that custom X-* headers are preserved."""
        headers = {
            "X-Custom-Header": "custom-value",
            "X-Request-ID": "req-123",
            "X-Title": "MyApp",
        }
        result = filter_sensitive_headers(headers)
        assert result.get("X-Custom-Header") == "custom-value"
        assert result.get("X-Request-ID") == "req-123"
        assert result.get("X-Title") == "MyApp"

    def test_empty_headers(self):
        """Test filtering empty headers dict."""
        result = filter_sensitive_headers({})
        assert result == {}

    def test_all_sensitive_headers_filtered(self):
        """Test that all known sensitive headers are filtered."""
        # Build a dict with all sensitive headers
        headers = {h: f"value-for-{h}" for h in SENSITIVE_HEADERS}
        # Add some non-sensitive headers
        headers["X-Custom-Header"] = "value"
        headers["X-Another-Custom"] = "another-value"

        result = filter_sensitive_headers(headers)

        # All sensitive headers should be removed
        for sensitive in SENSITIVE_HEADERS:
            assert sensitive not in result

        # Custom headers should be preserved
        assert result.get("X-Custom-Header") == "value"
        assert result.get("X-Another-Custom") == "another-value"


class TestMergeHeaders:
    """Tests for the merge_headers utility function."""

    def test_merge_base_headers_only(self):
        """Test merging with only base headers."""
        base = {"X-Custom": "base-value", "X-Another": "base-another"}
        result = merge_headers(base, None)
        assert result == base

    def test_merge_override_headers_only(self):
        """Test merging with only override headers."""
        override = {"X-Custom": "override-value"}
        result = merge_headers(None, override)
        assert result == override

    def test_merge_override_takes_precedence(self):
        """Test that override headers take precedence over base headers."""
        base = {"X-Custom": "base-value", "X-Preserved": "base-value"}
        override = {"X-Custom": "override-value"}
        result = merge_headers(base, override)
        assert result.get("X-Custom") == "override-value"
        assert result.get("X-Preserved") == "base-value"

    def test_merge_combines_unique_headers(self):
        """Test that unique headers from both are combined."""
        base = {"X-Base-Only": "base"}
        override = {"X-Override-Only": "override"}
        result = merge_headers(base, override)
        assert result.get("X-Base-Only") == "base"
        assert result.get("X-Override-Only") == "override"

    def test_merge_with_filtering(self):
        """Test that sensitive headers are filtered by default."""
        base = {
            "X-Custom": "value",
            "Authorization": "Bearer secret",
        }
        override = {
            "X-Override": "value",
            "Host": "api.example.com",
        }
        result = merge_headers(base, override)
        # Sensitive headers should be filtered
        assert "authorization" not in result
        assert "host" not in result
        # Custom headers should be preserved
        assert result.get("X-Custom") == "value"
        assert result.get("X-Override") == "value"

    def test_merge_without_filtering(self):
        """Test merging without filtering sensitive headers."""
        base = {
            "X-Custom": "value",
            "Authorization": "Bearer secret",
        }
        override = {
            "X-Override": "value",
        }
        result = merge_headers(base, override, filter_sensitive=False)
        # Authorization should be preserved when filtering is disabled
        assert result.get("Authorization") == "Bearer secret"
        assert result.get("X-Custom") == "value"
        assert result.get("X-Override") == "value"

    def test_empty_headers_merge(self):
        """Test merging with empty dicts."""
        result = merge_headers({}, {})
        assert result == {}


class TestCreateLlmWrapper:
    """Tests for the create_llm_wrapper function."""

    @pytest.mark.asyncio
    async def test_wrapper_passes_through_without_headers(self):
        """Test that wrapper passes through when no extra headers."""
        from lm_proxy.bootstrap import create_llm_wrapper

        async def base_llm(prompt, **kwargs):
            return f"response for: {prompt}"

        wrapped = create_llm_wrapper(base_llm)
        result = await wrapped("test prompt")
        assert result == "response for: test prompt"

    @pytest.mark.asyncio
    async def test_wrapper_injects_config_headers(self):
        """Test that wrapper injects config-level headers."""
        from lm_proxy.bootstrap import create_llm_wrapper

        captured_kwargs = {}

        async def base_llm(prompt, **kwargs):
            captured_kwargs.update(kwargs)
            return f"response for: {prompt}"

        extra_headers = {"X-Custom-Header": "custom-value", "X-Title": "MyApp"}
        wrapped = create_llm_wrapper(base_llm, extra_headers)

        await wrapped("test prompt")

        assert "extra_headers" in captured_kwargs
        assert captured_kwargs["extra_headers"]["X-Custom-Header"] == "custom-value"
        assert captured_kwargs["extra_headers"]["X-Title"] == "MyApp"

    @pytest.mark.asyncio
    async def test_wrapper_request_headers_override_config(self):
        """Test that request-level headers override config-level headers."""
        from lm_proxy.bootstrap import create_llm_wrapper

        captured_kwargs = {}

        async def base_llm(prompt, **kwargs):
            captured_kwargs.update(kwargs)
            return f"response for: {prompt}"

        config_headers = {"X-Custom": "config-value", "X-Preserved": "config-only"}
        wrapped = create_llm_wrapper(base_llm, config_headers)

        # Call with request-level headers
        await wrapped("test prompt", extra_headers={"X-Custom": "request-value"})

        assert captured_kwargs["extra_headers"]["X-Custom"] == "request-value"
        assert captured_kwargs["extra_headers"]["X-Preserved"] == "config-only"

    @pytest.mark.asyncio
    async def test_wrapper_filters_sensitive_headers(self):
        """Test that wrapper filters sensitive headers from config."""
        from lm_proxy.bootstrap import create_llm_wrapper

        captured_kwargs = {}

        async def base_llm(prompt, **kwargs):
            captured_kwargs.update(kwargs)
            return f"response for: {prompt}"

        # Config with sensitive header
        config_headers = {
            "X-Custom": "value",
            "Authorization": "Bearer secret-token",
        }
        wrapped = create_llm_wrapper(base_llm, config_headers)

        await wrapped("test prompt")

        # Sensitive headers should be filtered
        assert "authorization" not in captured_kwargs.get("extra_headers", {})
        assert captured_kwargs["extra_headers"]["X-Custom"] == "value"

    @pytest.mark.asyncio
    async def test_wrapper_empty_extra_headers_removed(self):
        """Test that empty extra_headers dict is not passed to LLM."""
        from lm_proxy.bootstrap import create_llm_wrapper

        captured_kwargs = {}

        async def base_llm(prompt, **kwargs):
            captured_kwargs.update(kwargs)
            return f"response for: {prompt}"

        # No extra headers
        wrapped = create_llm_wrapper(base_llm)

        await wrapped("test prompt")

        # extra_headers should not be in kwargs if empty
        assert "extra_headers" not in captured_kwargs

    @pytest.mark.asyncio
    async def test_wrapper_preserves_other_kwargs(self):
        """Test that wrapper preserves other kwargs passed to LLM."""
        from lm_proxy.bootstrap import create_llm_wrapper

        captured_kwargs = {}

        async def base_llm(prompt, **kwargs):
            captured_kwargs.update(kwargs)
            return f"response for: {prompt}"

        extra_headers = {"X-Custom": "value"}
        wrapped = create_llm_wrapper(base_llm, extra_headers)

        await wrapped("test prompt", temperature=0.5, max_tokens=100)

        assert captured_kwargs["extra_headers"]["X-Custom"] == "value"
        assert captured_kwargs["temperature"] == 0.5
        assert captured_kwargs["max_tokens"] == 100
