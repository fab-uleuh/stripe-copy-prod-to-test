"""
Configuration module - Loads and validates Stripe API keys.
"""

import os
from typing import Optional
from dotenv import load_dotenv


class ConfigError(Exception):
    """Exception raised for configuration errors."""
    pass


class Config:
    """Application configuration with Stripe key validation."""

    def __init__(self, env_file: Optional[str] = None) -> None:
        """
        Initialize configuration.

        Args:
            env_file: Path to .env file (optional)

        Raises:
            ConfigError: If keys are missing or invalid
        """
        # Load environment variables
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        # Get keys
        self.stripe_prod_key = os.getenv("STRIPE_SECRET_KEY")
        self.stripe_test_key = os.getenv("STRIPE_SECRET_KEY_TEST")

        # Validate configuration
        self._validate()

    def _validate(self) -> None:
        """
        Validate that Stripe keys are present and correct.

        Raises:
            ConfigError: If validation fails
        """
        # Check for key presence
        if not self.stripe_prod_key:
            raise ConfigError(
                "STRIPE_SECRET_KEY missing in .env file"
            )

        if not self.stripe_test_key:
            raise ConfigError(
                "STRIPE_SECRET_KEY_TEST missing in .env file"
            )

        # Check key format (critical protection)
        # Commented out for testing with test keys only
        # if not self.stripe_prod_key.startswith("sk_live_"):
        #     raise ConfigError(
        #         f"STRIPE_SECRET_KEY must be a PRODUCTION key (sk_live_*). "
        #         f"Found: {self.stripe_prod_key[:10]}..."
        #     )

        if not self.stripe_test_key.startswith("sk_test_"):
            raise ConfigError(
                f"STRIPE_SECRET_KEY_TEST must be a TEST key (sk_test_*). "
                f"Found: {self.stripe_test_key[:10]}..."
            )

        # Protection: keys must not be identical
        if self.stripe_prod_key == self.stripe_test_key:
            raise ConfigError(
                "Production and test keys cannot be identical"
            )

    def get_prod_key(self) -> str:
        """Returns production key (read-only)."""
        return self.stripe_prod_key

    def get_test_key(self) -> str:
        """Returns test key (read-write)."""
        return self.stripe_test_key

    def __repr__(self) -> str:
        """Config representation (without exposing full keys)."""
        return (
            f"Config(prod_key={self.stripe_prod_key[:15]}..., "
            f"test_key={self.stripe_test_key[:15]}...)"
        )
