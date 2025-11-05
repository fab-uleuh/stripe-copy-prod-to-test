"""
Product Copier - Copies Stripe products.
"""

from typing import Any, Optional

from .base import BaseCopier


class ProductCopier(BaseCopier):
    """Copies Products from production to test."""

    @property
    def resource_name(self) -> str:
        return "products"

    def get_create_params(self, prod_entity: Any) -> dict[str, Any]:
        """
        Extract parameters to create a product.

        Args:
            prod_entity: Production product

        Returns:
            Creation parameters
        """
        params: dict[str, Any] = {
            "name": prod_entity.name,
        }

        # Optional fields
        if hasattr(prod_entity, "description") and prod_entity.description:
            params["description"] = prod_entity.description

        if hasattr(prod_entity, "active"):
            params["active"] = prod_entity.active

        if hasattr(prod_entity, "images") and prod_entity.images:
            params["images"] = list(prod_entity.images)

        if hasattr(prod_entity, "statement_descriptor") and prod_entity.statement_descriptor:
            params["statement_descriptor"] = prod_entity.statement_descriptor

        if hasattr(prod_entity, "unit_label") and prod_entity.unit_label:
            params["unit_label"] = prod_entity.unit_label

        if hasattr(prod_entity, "url") and prod_entity.url:
            params["url"] = prod_entity.url

        if hasattr(prod_entity, "shippable"):
            params["shippable"] = prod_entity.shippable

        # Features (list of strings)
        if hasattr(prod_entity, "features") and prod_entity.features:
            params["features"] = [
                {"name": f.name} for f in prod_entity.features
            ]

        # Tax code
        if hasattr(prod_entity, "tax_code") and prod_entity.tax_code:
            # tax_code can be an object or a string
            if isinstance(prod_entity.tax_code, str):
                params["tax_code"] = prod_entity.tax_code
            elif hasattr(prod_entity.tax_code, "id"):
                params["tax_code"] = prod_entity.tax_code.id

        # Copy existing metadata
        if hasattr(prod_entity, "metadata") and prod_entity.metadata:
            params["metadata"] = dict(prod_entity.metadata)

        return params

    def get_update_params(self, prod_entity: Any) -> dict[str, Any]:
        """
        Extract parameters to update a product.

        Args:
            prod_entity: Production product

        Returns:
            Update parameters
        """
        params: dict[str, Any] = {}

        # Most fields can be updated
        if hasattr(prod_entity, "name"):
            params["name"] = prod_entity.name

        if hasattr(prod_entity, "description"):
            params["description"] = prod_entity.description

        if hasattr(prod_entity, "active"):
            params["active"] = prod_entity.active

        if hasattr(prod_entity, "images") and prod_entity.images:
            params["images"] = list(prod_entity.images)

        if hasattr(prod_entity, "statement_descriptor"):
            params["statement_descriptor"] = prod_entity.statement_descriptor

        if hasattr(prod_entity, "unit_label"):
            params["unit_label"] = prod_entity.unit_label

        if hasattr(prod_entity, "url"):
            params["url"] = prod_entity.url

        if hasattr(prod_entity, "shippable"):
            params["shippable"] = prod_entity.shippable

        if hasattr(prod_entity, "features") and prod_entity.features:
            params["features"] = [
                {"name": f.name} for f in prod_entity.features
            ]

        # Metadata
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
        Find an existing product in test.

        Matching strategy:
        1. By metadata prod_id
        2. By exact name (if unique)

        Args:
            prod_entity: Production product
            test_entities: Test products

        Returns:
            Corresponding test product, or None
        """
        # Strategy 1: Match by metadata prod_id
        for test_entity in test_entities:
            metadata = getattr(test_entity, "metadata", {})
            if metadata and metadata.get("prod_id") == prod_entity.id:
                return test_entity

        # Strategy 2: Match by exact name
        # Note: Returns first match if multiple products have same name
        for test_entity in test_entities:
            if test_entity.name == prod_entity.name:
                # Check it doesn't already have a different prod_id
                metadata = getattr(test_entity, "metadata", {})
                existing_prod_id = metadata.get("prod_id") if metadata else None

                if not existing_prod_id or existing_prod_id == prod_entity.id:
                    return test_entity

        return None
