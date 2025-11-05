"""
Tax Rate Copier - Copies Stripe tax rates.
"""

from typing import Any, Optional

from .base import BaseCopier


class TaxRateCopier(BaseCopier):
    """Copies Tax Rates from production to test."""

    @property
    def resource_name(self) -> str:
        return "tax_rates"

    def get_create_params(self, prod_entity: Any) -> dict[str, Any]:
        """
        Extract parameters to create a tax rate.

        Args:
            prod_entity: Production tax rate

        Returns:
            Creation parameters
        """
        params: dict[str, Any] = {
            "display_name": prod_entity.display_name,
            "inclusive": prod_entity.inclusive,
            "percentage": prod_entity.percentage,
        }

        # Optional fields
        if hasattr(prod_entity, "description") and prod_entity.description:
            params["description"] = prod_entity.description

        if hasattr(prod_entity, "jurisdiction") and prod_entity.jurisdiction:
            params["jurisdiction"] = prod_entity.jurisdiction

        if hasattr(prod_entity, "country") and prod_entity.country:
            params["country"] = prod_entity.country

        if hasattr(prod_entity, "state") and prod_entity.state:
            params["state"] = prod_entity.state

        # Copy existing metadata
        if hasattr(prod_entity, "metadata") and prod_entity.metadata:
            params["metadata"] = dict(prod_entity.metadata)

        return params

    def get_update_params(self, prod_entity: Any) -> dict[str, Any]:
        """
        Extract parameters to update a tax rate.

        Note: Tax rates have limited updatable fields.

        Args:
            prod_entity: Production tax rate

        Returns:
            Update parameters
        """
        params: dict[str, Any] = {}

        # Only certain fields can be updated
        if hasattr(prod_entity, "description"):
            params["description"] = prod_entity.description

        if hasattr(prod_entity, "display_name"):
            params["display_name"] = prod_entity.display_name

        # Metadata can be updated
        if hasattr(prod_entity, "metadata") and prod_entity.metadata:
            params["metadata"] = dict(prod_entity.metadata)
            params["metadata"]["prod_id"] = prod_entity.id

        return params

    def find_existing(
        self,
        prod_entity: Any,
        test_entities: list[Any]
    ) -> Optional[Any]:
        """
        Find an existing tax rate in test.

        Matching strategy:
        1. By metadata prod_id
        2. By display_name + percentage + jurisdiction (unique combination)

        Args:
            prod_entity: Production tax rate
            test_entities: Test tax rates

        Returns:
            Corresponding test tax rate, or None
        """
        # Strategy 1: Match by metadata prod_id
        for test_entity in test_entities:
            metadata = getattr(test_entity, "metadata", {})
            if metadata and metadata.get("prod_id") == prod_entity.id:
                return test_entity

        # Strategy 2: Match by unique characteristics
        for test_entity in test_entities:
            # Compare display_name, percentage and jurisdiction
            same_name = test_entity.display_name == prod_entity.display_name
            same_percentage = abs(test_entity.percentage - prod_entity.percentage) < 0.01

            prod_jurisdiction = getattr(prod_entity, "jurisdiction", None)
            test_jurisdiction = getattr(test_entity, "jurisdiction", None)
            same_jurisdiction = prod_jurisdiction == test_jurisdiction

            if same_name and same_percentage and same_jurisdiction:
                return test_entity

        return None
