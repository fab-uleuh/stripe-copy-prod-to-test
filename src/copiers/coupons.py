"""
Coupon Copier - Copies Stripe coupons.
"""

from typing import Any, Optional

from .base import BaseCopier


class CouponCopier(BaseCopier):
    """Copies Coupons from production to test."""

    @property
    def resource_name(self) -> str:
        return "coupons"

    def can_update(self) -> bool:
        """
        Coupons have limited updatable fields.

        Returns:
            True (but only metadata and name can be updated)
        """
        return True

    def get_create_params(self, prod_entity: Any) -> dict[str, Any]:
        """
        Extract parameters to create a coupon.

        Args:
            prod_entity: Production coupon

        Returns:
            Creation parameters
        """
        params: dict[str, Any] = {}

        # Coupon ID (optional, Stripe can auto-generate)
        # We prefix ID with "test_" to avoid conflicts
        if hasattr(prod_entity, "id") and prod_entity.id:
            params["id"] = f"test_{prod_entity.id}"

        # Percentage or fixed amount (mutually exclusive)
        if hasattr(prod_entity, "percent_off") and prod_entity.percent_off is not None:
            params["percent_off"] = prod_entity.percent_off
        elif hasattr(prod_entity, "amount_off") and prod_entity.amount_off is not None:
            params["amount_off"] = prod_entity.amount_off
            if hasattr(prod_entity, "currency"):
                params["currency"] = prod_entity.currency

        # Duration
        if hasattr(prod_entity, "duration"):
            params["duration"] = prod_entity.duration

        if hasattr(prod_entity, "duration_in_months") and prod_entity.duration_in_months:
            params["duration_in_months"] = prod_entity.duration_in_months

        # Name
        if hasattr(prod_entity, "name") and prod_entity.name:
            params["name"] = prod_entity.name

        # Restrictions
        if hasattr(prod_entity, "max_redemptions") and prod_entity.max_redemptions:
            params["max_redemptions"] = prod_entity.max_redemptions

        if hasattr(prod_entity, "redeem_by") and prod_entity.redeem_by:
            params["redeem_by"] = prod_entity.redeem_by

        # Applies_to (specific products)
        if hasattr(prod_entity, "applies_to") and prod_entity.applies_to:
            applies_to = prod_entity.applies_to
            if hasattr(applies_to, "products") and applies_to.products:
                # Map product IDs
                test_product_ids = []
                for prod_product_id in applies_to.products:
                    test_id = self.mapper.get_test_id("products", prod_product_id)
                    if test_id:
                        test_product_ids.append(test_id)
                    else:
                        self.logger.warning(
                            f"Product {prod_product_id} not found in mapping"
                        )

                if test_product_ids:
                    params["applies_to"] = {"products": test_product_ids}

        # Metadata
        if hasattr(prod_entity, "metadata") and prod_entity.metadata:
            params["metadata"] = dict(prod_entity.metadata)

        return params

    def get_update_params(self, prod_entity: Any) -> dict[str, Any]:
        """
        Extract parameters to update a coupon.

        Note: Only metadata and name can be updated.

        Args:
            prod_entity: Production coupon

        Returns:
            Update parameters
        """
        params: dict[str, Any] = {}

        if hasattr(prod_entity, "name"):
            params["name"] = prod_entity.name

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
        Find an existing coupon in test.

        Matching strategy:
        1. By metadata prod_id
        2. By ID (with test_ prefix)
        3. By name

        Args:
            prod_entity: Production coupon
            test_entities: Test coupons

        Returns:
            Corresponding test coupon, or None
        """
        # Strategy 1: Match by metadata prod_id
        for test_entity in test_entities:
            metadata = getattr(test_entity, "metadata", {})
            if metadata and metadata.get("prod_id") == prod_entity.id:
                return test_entity

        # Strategy 2: Match by ID with prefix
        expected_test_id = f"test_{prod_entity.id}"
        for test_entity in test_entities:
            if test_entity.id == expected_test_id:
                return test_entity

        # Strategy 3: Match by name (if defined)
        if hasattr(prod_entity, "name") and prod_entity.name:
            for test_entity in test_entities:
                if (hasattr(test_entity, "name") and
                        test_entity.name == prod_entity.name):
                    # Check it doesn't already have a different prod_id
                    metadata = getattr(test_entity, "metadata", {})
                    existing_prod_id = metadata.get("prod_id") if metadata else None

                    if not existing_prod_id or existing_prod_id == prod_entity.id:
                        return test_entity

        return None
