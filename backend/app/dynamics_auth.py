"""
Microsoft Dynamics CRM OAuth Authentication.

This module handles OAuth 2.0 authentication with Microsoft Azure AD
for accessing Dynamics CRM via the Dataverse Web API.
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import msal
from functools import lru_cache

logger = logging.getLogger(__name__)


class DynamicsAuthConfig:
    """Configuration for Dynamics CRM authentication."""

    def __init__(self):
        """Initialize authentication configuration from environment variables."""
        # Azure AD / Entra ID Configuration
        self.tenant_id = os.getenv('DYNAMICS_TENANT_ID')
        self.client_id = os.getenv('DYNAMICS_CLIENT_ID')
        self.client_secret = os.getenv('DYNAMICS_CLIENT_SECRET')

        # Dynamics CRM Configuration
        self.resource_url = os.getenv('DYNAMICS_RESOURCE_URL')  # e.g., https://yourorg.crm.dynamics.com

        # OAuth endpoints
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}" if self.tenant_id else None

        # Scopes for Dataverse API
        # Default scope is {resource}/.default
        self.scope = [f"{self.resource_url}/.default"] if self.resource_url else []

    def is_configured(self) -> bool:
        """Check if all required configuration is present."""
        return all([
            self.tenant_id,
            self.client_id,
            self.client_secret,
            self.resource_url
        ])

    def get_missing_config(self) -> list:
        """Get list of missing configuration items."""
        missing = []
        if not self.tenant_id:
            missing.append('DYNAMICS_TENANT_ID')
        if not self.client_id:
            missing.append('DYNAMICS_CLIENT_ID')
        if not self.client_secret:
            missing.append('DYNAMICS_CLIENT_SECRET')
        if not self.resource_url:
            missing.append('DYNAMICS_RESOURCE_URL')
        return missing


class DynamicsAuthenticator:
    """Handles OAuth authentication for Dynamics CRM."""

    def __init__(self, config: Optional[DynamicsAuthConfig] = None):
        """
        Initialize the authenticator.

        Args:
            config: Authentication configuration. If None, loads from environment.
        """
        self.config = config or DynamicsAuthConfig()
        self._token_cache: Optional[Dict[str, Any]] = None
        self._token_expiry: Optional[datetime] = None

    def _create_msal_app(self) -> msal.ConfidentialClientApplication:
        """Create an MSAL confidential client application."""
        if not self.config.is_configured():
            missing = self.config.get_missing_config()
            raise ValueError(
                f"Dynamics authentication not configured. Missing: {', '.join(missing)}"
            )

        return msal.ConfidentialClientApplication(
            client_id=self.config.client_id,
            client_credential=self.config.client_secret,
            authority=self.config.authority
        )

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid access token for Dynamics CRM.

        Uses cached token if available and not expired.

        Args:
            force_refresh: Force token refresh even if cached token is valid

        Returns:
            Valid access token string

        Raises:
            ValueError: If authentication configuration is incomplete
            Exception: If token acquisition fails
        """
        # Check if we have a valid cached token
        if not force_refresh and self._is_token_valid():
            logger.debug("Using cached access token")
            return self._token_cache['access_token']

        logger.info("Acquiring new access token for Dynamics CRM")

        try:
            app = self._create_msal_app()

            # Acquire token using client credentials flow (service principal)
            result = app.acquire_token_for_client(scopes=self.config.scope)

            if "access_token" in result:
                # Cache the token
                self._token_cache = result

                # Set expiry time (typically tokens expire in 1 hour)
                expires_in = result.get('expires_in', 3600)  # Default to 1 hour
                self._token_expiry = datetime.now() + timedelta(seconds=expires_in - 60)  # Refresh 1 min early

                logger.info("Successfully acquired access token")
                return result['access_token']
            else:
                error = result.get('error', 'Unknown error')
                error_description = result.get('error_description', 'No description')
                logger.error(f"Failed to acquire token: {error} - {error_description}")
                raise Exception(f"Authentication failed: {error} - {error_description}")

        except Exception as e:
            logger.error(f"Error acquiring access token: {str(e)}")
            raise

    def _is_token_valid(self) -> bool:
        """Check if the cached token is still valid."""
        if not self._token_cache or not self._token_expiry:
            return False

        return datetime.now() < self._token_expiry

    def clear_token_cache(self):
        """Clear the cached token."""
        self._token_cache = None
        self._token_expiry = None
        logger.info("Token cache cleared")


# Global authenticator instance
_authenticator: Optional[DynamicsAuthenticator] = None


@lru_cache(maxsize=1)
def get_authenticator() -> DynamicsAuthenticator:
    """
    Get or create the global authenticator instance.

    Returns:
        DynamicsAuthenticator instance
    """
    global _authenticator
    if _authenticator is None:
        _authenticator = DynamicsAuthenticator()
    return _authenticator


def get_access_token() -> str:
    """
    Get a valid access token for Dynamics CRM.

    This is a convenience function that uses the global authenticator.

    Returns:
        Valid access token string

    Raises:
        ValueError: If authentication is not configured
        Exception: If token acquisition fails
    """
    authenticator = get_authenticator()
    return authenticator.get_access_token()
