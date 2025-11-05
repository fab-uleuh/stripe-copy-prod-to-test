"""
Price Copier - Copies Stripe prices.
"""

from typing import Any, Optional

from .base import BaseCopier


class PriceCopier(BaseCopier):
    """
    Copies Prices from production to test.

    Important note: Stripe Prices cannot be updated after creation.
    This copier checks if a price already exists and doesn't recreate it if identical.
    """

    @property
    def resource_name(self) -> str:
        return "prices"

    def can_update(self) -> bool:
        """
        Prices cannot be updated in Stripe.

        Returns:
            False
        """
        return False

    def get_create_params(self, prod_entity: Any) -> dict[str, Any]:
        """
        Extract parameters to create a price.

        Args:
            prod_entity: Production price

        Returns:
            Creation parameters
        """
        params: dict[str, Any] = {
            "currency": prod_entity.currency,
        }

        # Associate with test product (via mapper)
        prod_product_id = prod_entity.product
        # Can be an object or an ID
        if hasattr(prod_product_id, "id"):
            prod_product_id = prod_product_id.id

        test_product_id = self.mapper.get_test_id("products", prod_product_id)
        if not test_product_id:
            raise ValueError(
                f"Cannot find test product for {prod_product_id}. "
                "Make sure to copy products before prices."
            )

        params["product"] = test_product_id

        # Unit price or tiered
        # IMPORTANT: Stripe only accepts ONE of these two parameters
        if hasattr(prod_entity, "unit_amount_decimal") and prod_entity.unit_amount_decimal:
            # Prefer unit_amount_decimal (more precise)
            params["unit_amount_decimal"] = prod_entity.unit_amount_decimal
        elif hasattr(prod_entity, "unit_amount") and prod_entity.unit_amount is not None:
            params["unit_amount"] = prod_entity.unit_amount

        # Recurring price
        if hasattr(prod_entity, "recurring") and prod_entity.recurring:
            params["recurring"] = {
                "interval": prod_entity.recurring.interval,
            }
            if hasattr(prod_entity.recurring, "interval_count"):
                params["recurring"]["interval_count"] = prod_entity.recurring.interval_count
            if hasattr(prod_entity.recurring, "usage_type"):
                params["recurring"]["usage_type"] = prod_entity.recurring.usage_type
            if hasattr(prod_entity.recurring, "trial_period_days"):
                params["recurring"]["trial_period_days"] = prod_entity.recurring.trial_period_days

        # Billing scheme
        if hasattr(prod_entity, "billing_scheme"):
            params["billing_scheme"] = prod_entity.billing_scheme

        # Tiers (for billing_scheme = tiered)
        if hasattr(prod_entity, "tiers") and prod_entity.tiers:
            params["tiers"] = []
            for tier in prod_entity.tiers:
                tier_dict: dict[str, Any] = {}
                if hasattr(tier, "up_to") and tier.up_to:
                    tier_dict["up_to"] = tier.up_to
                else:
                    tier_dict["up_to"] = "inf"

                if hasattr(tier, "unit_amount") and tier.unit_amount is not None:
                    tier_dict["unit_amount"] = tier.unit_amount

                if hasattr(tier, "flat_amount") and tier.flat_amount is not None:
                    tier_dict["flat_amount"] = tier.flat_amount

                params["tiers"].append(tier_dict)

            if hasattr(prod_entity, "tiers_mode"):
                params["tiers_mode"] = prod_entity.tiers_mode

        # Transform quantity
        if hasattr(prod_entity, "transform_quantity") and prod_entity.transform_quantity:
            params["transform_quantity"] = {
                "divide_by": prod_entity.transform_quantity.divide_by,
                "round": prod_entity.transform_quantity.round,
            }

        # Other fields
        if hasattr(prod_entity, "active"):
            params["active"] = prod_entity.active

        if hasattr(prod_entity, "nickname") and prod_entity.nickname:
            params["nickname"] = prod_entity.nickname

        if hasattr(prod_entity, "lookup_key") and prod_entity.lookup_key:
            params["lookup_key"] = prod_entity.lookup_key

        if hasattr(prod_entity, "tax_behavior"):
            params["tax_behavior"] = prod_entity.tax_behavior

        # Metadata
        if hasattr(prod_entity, "metadata") and prod_entity.metadata:
            params["metadata"] = dict(prod_entity.metadata)

        return params

    def get_update_params(self, prod_entity: Any) -> dict[str, Any]:
        """
        Prices cannot be updated.

        Args:
            prod_entity: Production price

        Returns:
            Empty dictionary (not used)
        """
        # Only certain fields like metadata, nickname, active can be updated
        # but generally prices are not updated
        params: dict[str, Any] = {}

        if hasattr(prod_entity, "active"):
            params["active"] = prod_entity.active

        if hasattr(prod_entity, "nickname"):
            params["nickname"] = prod_entity.nickname

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
        Find an existing price in test.

        Matching strategy:
        1. By metadata prod_id
        2. By lookup_key (if defined and unique)
        3. By combination product + unit_amount + currency + recurring

        Args:
            prod_entity: Production price
            test_entities: Test prices

        Returns:
            Corresponding test price, or None
        """
        # Strategy 1: Match by metadata prod_id
        for test_entity in test_entities:
            metadata = getattr(test_entity, "metadata", {})
            if metadata and metadata.get("prod_id") == prod_entity.id:
                return test_entity

        # Strategy 2: Match by lookup_key
        if hasattr(prod_entity, "lookup_key") and prod_entity.lookup_key:
            for test_entity in test_entities:
                if (hasattr(test_entity, "lookup_key") and
                        test_entity.lookup_key == prod_entity.lookup_key):
                    return test_entity

        # Strategy 3: Match by characteristics
        prod_product_id = prod_entity.product
        if hasattr(prod_product_id, "id"):
            prod_product_id = prod_product_id.id

        test_product_id = self.mapper.get_test_id("products", prod_product_id)

        if not test_product_id:
            return None

        for test_entity in test_entities:
            # Same product
            test_prod = test_entity.product
            if hasattr(test_prod, "id"):
                test_prod = test_prod.id

            if test_prod != test_product_id:
                continue

            # Same currency and amount
            if test_entity.currency != prod_entity.currency:
                continue

            if hasattr(prod_entity, "unit_amount") and prod_entity.unit_amount is not None:
                if test_entity.unit_amount != prod_entity.unit_amount:
                    continue

            # Same recurrence
            prod_recurring = getattr(prod_entity, "recurring", None)
            test_recurring = getattr(test_entity, "recurring", None)

            if bool(prod_recurring) != bool(test_recurring):
                continue

            if prod_recurring and test_recurring:
                if prod_recurring.interval != test_recurring.interval:
                    continue
                if (hasattr(prod_recurring, "interval_count") and
                        prod_recurring.interval_count != test_recurring.interval_count):
                    continue

            # If everything matches, it's probably the same price
            return test_entity

        return None
