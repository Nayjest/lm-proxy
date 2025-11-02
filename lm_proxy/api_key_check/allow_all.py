"""
Permissive API key validator that accepts any key and assigns it to a default group.

This module provides a simple authentication strategy for development or testing
environments where all API keys should be accepted without validation.
"""
from typing import Optional
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AllowAll:
    """
    A pass-through API key validator that accepts all keys without verification.
    
    This validator is useful for development environments, testing scenarios, or
    applications where authentication is handled elsewhere in the stack.
    
    Attributes:
        group: The group identifier assigned to all validated keys.
        capture_api_key: Whether to include the raw API key in the returned
            metadata. Set to False in production to avoid logging sensitive data.
    """

    group: str = "default"
    capture_api_key: bool = True

    def __call__(
        self,
        api_key: Optional[str]
    ) -> tuple[str, dict[str, Optional[str]]]:
        """
        Validate an API key (accepts all keys without verification).

        Args:
            api_key: The API key to validate. Can be None.

        Returns:
            A tuple containing:
                - The default group identifier (str)
                - user_info dictionary with the API key if capture_api_key
                  is True, otherwise an empty dictionary

        Note:
            This method never raises authentication errors and always returns
            successfully, regardless of the input.
        """
        user_info = {"api_key": api_key} if self.capture_api_key else {}
        return self.group, user_info
