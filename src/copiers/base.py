"""
Base Copier - Abstract class for copying Stripe entities.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from ..stripe_client import StripeClient, Environment
from ..mapper import IDMapper
from ..logger import get_logger


class BaseCopier(ABC):
    """
    Abstract class for copying Stripe entities (Template Method Pattern).

    Subclasses must implement:
    - resource_name: Stripe resource name
    - get_create_params(): Parameters to create the entity
    - get_update_params(): Parameters to update the entity
    - find_existing(): Logic to find existing entity in test
    """

    def __init__(
        self,
        client: StripeClient,
        mapper: IDMapper
    ) -> None:
        """
        Initialize the copier.

        Args:
            client: Configured Stripe client
            mapper: Mapper to store ID correspondences
        """
        self.client = client
        self.mapper = mapper
        self.logger = get_logger()

    @property
    @abstractmethod
    def resource_name(self) -> str:
        """Resource name (e.g. 'products', 'prices', 'tax_rates')."""
        pass

    @abstractmethod
    def get_create_params(self, prod_entity: Any) -> dict[str, Any]:
        """
        Extract parameters to create the entity in test.

        Args:
            prod_entity: Production entity

        Returns:
            Dictionary of parameters for Stripe API
        """
        pass

    @abstractmethod
    def get_update_params(self, prod_entity: Any) -> dict[str, Any]:
        """
        Extract parameters to update the entity in test.

        Args:
            prod_entity: Production entity

        Returns:
            Dictionary of parameters for Stripe API
        """
        pass

    @abstractmethod
    def find_existing(
        self,
        prod_entity: Any,
        test_entities: list[Any]
    ) -> Optional[Any]:
        """
        Find existing test entity corresponding to prod entity.

        Args:
            prod_entity: Production entity
            test_entities: List of test entities

        Returns:
            Corresponding test entity, or None if not found
        """
        pass

    def can_update(self) -> bool:
        """
        Indicates if entities of this type can be updated.

        Default True. Override for resources like Price that
        don't support updates.

        Returns:
            True if updates are possible, False otherwise
        """
        return True

    def list_from_prod(self, **filters: Any) -> list[Any]:
        """
        List all entities from production.

        Args:
            **filters: Optional filters for Stripe API

        Returns:
            List of production entities
        """
        self.logger.info(f"Fetching {self.resource_name} from production...")
        entities = self.client.list_all(
            self.resource_name,
            Environment.PRODUCTION,
            **filters
        )
        self.logger.info(f"✓ {len(entities)} {self.resource_name} found in production")
        return entities

    def list_from_test(self, **filters: Any) -> list[Any]:
        """
        List all entities from test.

        Args:
            **filters: Optional filters

        Returns:
            List of test entities
        """
        return self.client.list_all(
            self.resource_name,
            Environment.TEST,
            **filters
        )

    def create_in_test(self, prod_entity: Any) -> Any:
        """
        Create a new entity in test.

        Args:
            prod_entity: Production entity to copy

        Returns:
            Created test entity
        """
        params = self.get_create_params(prod_entity)

        # Add metadata to trace origin
        if "metadata" not in params:
            params["metadata"] = {}
        params["metadata"]["prod_id"] = prod_entity.id

        test_entity = self.client.create(
            self.resource_name,
            Environment.TEST,
            **params
        )

        # Record mapping
        self.mapper.add_mapping(self.resource_name, prod_entity.id, test_entity.id)
        self.mapper.increment_stat(self.resource_name, "created")

        return test_entity

    def update_in_test(self, test_entity: Any, prod_entity: Any) -> Any:
        """
        Update existing test entity.

        Args:
            test_entity: Test entity to update
            prod_entity: Source prod entity

        Returns:
            Updated entity
        """
        if not self.can_update():
            self.logger.warning(
                f"{self.resource_name} cannot be updated. "
                f"Consider archiving and recreating."
            )
            return test_entity

        params = self.get_update_params(prod_entity)

        updated = self.client.update(
            self.resource_name,
            test_entity.id,
            Environment.TEST,
            **params
        )

        # Update mapping
        self.mapper.add_mapping(self.resource_name, prod_entity.id, test_entity.id)
        self.mapper.increment_stat(self.resource_name, "updated")

        return updated

    def copy_one(
        self,
        prod_entity: Any,
        test_entities: list[Any]
    ) -> tuple[Any, str]:
        """
        Copy a single entity (create or update).

        Args:
            prod_entity: Production entity
            test_entities: List of existing test entities

        Returns:
            Tuple (result_entity, action) where action is 'created' or 'updated'
        """
        existing = self.find_existing(prod_entity, test_entities)

        if existing:
            self.logger.debug(
                f"Updating {self.resource_name}: {prod_entity.id} → {existing.id}"
            )
            result = self.update_in_test(existing, prod_entity)
            return result, "updated"
        else:
            self.logger.debug(
                f"Creating {self.resource_name}: {prod_entity.id}"
            )
            result = self.create_in_test(prod_entity)
            return result, "created"

    def copy(self, **filters: Any) -> dict[str, int]:
        """
        Copy all entities from prod to test (main method).

        Args:
            **filters: Optional filters

        Returns:
            Dictionary with statistics {created: N, updated: M, errors: K}
        """
        self.logger.section(f"Copying {self.resource_name.upper()}")

        try:
            # List entities
            prod_entities = self.list_from_prod(**filters)
            test_entities = self.list_from_test()

            if not prod_entities:
                self.logger.info(f"No {self.resource_name} to copy")
                return {"created": 0, "updated": 0, "errors": 0}

            # Copy each entity
            with self.logger.create_progress() as progress:
                task = progress.add_task(
                    f"Copying {self.resource_name}...",
                    total=len(prod_entities)
                )

                for prod_entity in prod_entities:
                    try:
                        self.copy_one(prod_entity, test_entities)
                        progress.advance(task)
                    except Exception as e:
                        self.logger.error(
                            f"Error copying {prod_entity.id}: {e}"
                        )
                        self.mapper.increment_stat(self.resource_name, "errors")
                        progress.advance(task)

            # Get stats
            stats = self.mapper.stats[self.resource_name]
            self.logger.success(
                f"{self.resource_name}: {stats['created']} created, "
                f"{stats['updated']} updated, {stats['errors']} errors"
            )

            return stats

        except Exception as e:
            self.logger.error(f"Error copying {self.resource_name}: {e}")
            raise
