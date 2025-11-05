"""
Stripe Client - Secure wrapper for Stripe API.
"""

import stripe
from typing import Any, Iterator
from enum import Enum

from .config import Config
from .logger import get_logger


class Environment(Enum):
    """Stripe environment enumeration."""
    PRODUCTION = "production"
    TEST = "test"


class StripeClientError(Exception):
    """Exception raised for Stripe client errors."""
    pass


class StripeClient:
    """Client wrapper to manage Stripe API calls securely."""

    def __init__(self, config: Config, dry_run: bool = False) -> None:
        """
        Initialize Stripe clients.

        Args:
            config: Configuration containing API keys
            dry_run: If True, simulates operations without modifying data
        """
        self.config = config
        self.dry_run = dry_run
        self.logger = get_logger()

        # Create two distinct instances
        self.prod_key = config.get_prod_key()
        self.test_key = config.get_test_key()

        self.logger.info(
            f"Stripe client initialized (dry_run={dry_run})"
        )

    def _get_client(self, env: Environment) -> str:
        """
        Return API key for specified environment.

        Args:
            env: Target environment

        Returns:
            Stripe API key
        """
        if env == Environment.PRODUCTION:
            return self.prod_key
        else:
            return self.test_key

    def list_all(
        self,
        resource: str,
        env: Environment,
        **params: Any
    ) -> list[Any]:
        """
        List all resources of a given type (handles pagination).

        Args:
            resource: Resource type (e.g. 'products', 'prices', 'coupons')
            env: Environment to query
            **params: Additional parameters for the API

        Returns:
            Complete list of resources

        Raises:
            StripeClientError: On API error
        """
        api_key = self._get_client(env)
        all_items: list[Any] = []

        try:
            # Map resource names to Stripe methods
            resource_map = {
                'products': stripe.Product.list,
                'prices': stripe.Price.list,
                'coupons': stripe.Coupon.list,
                'tax_rates': stripe.TaxRate.list,
            }

            if resource not in resource_map:
                raise StripeClientError(f"Unknown resource: {resource}")

            list_method = resource_map[resource]

            # Automatic pagination
            has_more = True
            starting_after = None

            while has_more:
                list_params = {**params, 'limit': 100}
                if starting_after:
                    list_params['starting_after'] = starting_after

                response = list_method(api_key=api_key, **list_params)
                all_items.extend(response.data)

                has_more = response.has_more
                if has_more and response.data:
                    starting_after = response.data[-1].id

            self.logger.debug(
                f"Listed {len(all_items)} {resource} from {env.value}"
            )
            return all_items

        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe error while listing: {e}")
            raise StripeClientError(f"Error listing {resource}: {e}")

    def create(
        self,
        resource: str,
        env: Environment,
        **params: Any
    ) -> Any:
        """
        Create a resource in the specified environment.

        Args:
            resource: Resource type to create
            env: Target environment
            **params: Creation parameters

        Returns:
            Created resource

        Raises:
            StripeClientError: If write attempt in production or API error
        """
        # CRITICAL PROTECTION: prohibit any write in production
        if env == Environment.PRODUCTION:
            raise StripeClientError(
                "FORBIDDEN: Attempt to write in PRODUCTION. "
                "Only read access is allowed in production."
            )

        if self.dry_run:
            self.logger.info(f"[DRY-RUN] Creating {resource} with params: {params}")
            return {"id": f"dry_run_{resource}_id", **params}

        api_key = self._get_client(env)

        try:
            resource_map = {
                'products': stripe.Product.create,
                'prices': stripe.Price.create,
                'coupons': stripe.Coupon.create,
                'tax_rates': stripe.TaxRate.create,
            }

            if resource not in resource_map:
                raise StripeClientError(f"Unknown resource: {resource}")

            create_method = resource_map[resource]
            result = create_method(api_key=api_key, **params)

            self.logger.debug(f"Created {resource}: {result.id}")
            return result

        except stripe.error.StripeError as e:
            self.logger.error(f"Error during creation: {e}")
            raise StripeClientError(f"Error creating {resource}: {e}")

    def update(
        self,
        resource: str,
        resource_id: str,
        env: Environment,
        **params: Any
    ) -> Any:
        """
        Update an existing resource.

        Args:
            resource: Resource type
            resource_id: ID of the resource to modify
            env: Target environment
            **params: Update parameters

        Returns:
            Updated resource

        Raises:
            StripeClientError: If write attempt in production or API error
        """
        # CRITICAL PROTECTION
        if env == Environment.PRODUCTION:
            raise StripeClientError(
                "FORBIDDEN: Attempt to modify in PRODUCTION"
            )

        if self.dry_run:
            self.logger.info(
                f"[DRY-RUN] Update {resource} {resource_id} with: {params}"
            )
            return {"id": resource_id, **params}

        api_key = self._get_client(env)

        try:
            resource_map = {
                'products': stripe.Product.modify,
                'prices': stripe.Price.modify,
                'coupons': stripe.Coupon.modify,
                'tax_rates': stripe.TaxRate.modify,
            }

            if resource not in resource_map:
                raise StripeClientError(f"Unknown resource: {resource}")

            modify_method = resource_map[resource]
            result = modify_method(resource_id, api_key=api_key, **params)

            self.logger.debug(f"Updated {resource}: {resource_id}")
            return result

        except stripe.error.StripeError as e:
            self.logger.error(f"Error during update: {e}")
            raise StripeClientError(f"Error updating {resource}: {e}")

    def retrieve(
        self,
        resource: str,
        resource_id: str,
        env: Environment
    ) -> Any:
        """
        Retrieve a resource by its ID.

        Args:
            resource: Resource type
            resource_id: Resource ID
            env: Environment

        Returns:
            Retrieved resource

        Raises:
            StripeClientError: On error
        """
        api_key = self._get_client(env)

        try:
            resource_map = {
                'products': stripe.Product.retrieve,
                'prices': stripe.Price.retrieve,
                'coupons': stripe.Coupon.retrieve,
                'tax_rates': stripe.TaxRate.retrieve,
            }

            if resource not in resource_map:
                raise StripeClientError(f"Unknown resource: {resource}")

            retrieve_method = resource_map[resource]
            return retrieve_method(resource_id, api_key=api_key)

        except stripe.error.StripeError as e:
            raise StripeClientError(f"Error retrieving {resource}: {e}")
