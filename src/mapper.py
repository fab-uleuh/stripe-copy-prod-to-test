"""
Mapper - Manages ID mappings between production and test environments.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .logger import get_logger


class IDMapper:
    """Manages ID correspondences between prod and test environments."""

    def __init__(self, mappings_dir: str = "mappings") -> None:
        """
        Initialize the mapper.

        Args:
            mappings_dir: Directory where to save mappings
        """
        self.mappings_dir = Path(mappings_dir)
        self.mappings_dir.mkdir(exist_ok=True)

        self.logger = get_logger()

        # Structure: {resource_type: {prod_id: test_id}}
        self.mappings: dict[str, dict[str, str]] = {
            "tax_rates": {},
            "products": {},
            "prices": {},
            "coupons": {},
        }

        # Statistics
        self.stats: dict[str, dict[str, int]] = {
            "tax_rates": {"created": 0, "updated": 0, "errors": 0},
            "products": {"created": 0, "updated": 0, "errors": 0},
            "prices": {"created": 0, "updated": 0, "errors": 0},
            "coupons": {"created": 0, "updated": 0, "errors": 0},
        }

    def add_mapping(
        self,
        resource_type: str,
        prod_id: str,
        test_id: str
    ) -> None:
        """
        Add an ID mapping.

        Args:
            resource_type: Resource type (products, prices, etc.)
            prod_id: Production ID
            test_id: Test ID
        """
        if resource_type not in self.mappings:
            raise ValueError(f"Unknown resource type: {resource_type}")

        self.mappings[resource_type][prod_id] = test_id
        self.logger.debug(f"Mapping added: {resource_type} {prod_id} → {test_id}")

    def get_test_id(
        self,
        resource_type: str,
        prod_id: str
    ) -> Optional[str]:
        """
        Get test ID corresponding to a prod ID.

        Args:
            resource_type: Resource type
            prod_id: Production ID

        Returns:
            Test ID, or None if not found
        """
        return self.mappings.get(resource_type, {}).get(prod_id)

    def get_prod_id(
        self,
        resource_type: str,
        test_id: str
    ) -> Optional[str]:
        """
        Get prod ID corresponding to a test ID (reverse lookup).

        Args:
            resource_type: Resource type
            test_id: Test ID

        Returns:
            Production ID, or None if not found
        """
        mappings = self.mappings.get(resource_type, {})
        for prod_id, tid in mappings.items():
            if tid == test_id:
                return prod_id
        return None

    def increment_stat(
        self,
        resource_type: str,
        stat_type: str
    ) -> None:
        """
        Increment a statistic.

        Args:
            resource_type: Resource type
            stat_type: Stat type (created, updated, errors)
        """
        if resource_type in self.stats and stat_type in self.stats[resource_type]:
            self.stats[resource_type][stat_type] += 1

    def get_stats(self) -> dict[str, dict[str, int]]:
        """Return statistics."""
        return self.stats

    def get_summary(self) -> dict[str, int]:
        """
        Calculate global summary of statistics.

        Returns:
            Dictionary with totals created, updated, errors
        """
        summary = {"created": 0, "updated": 0, "errors": 0}
        for resource_stats in self.stats.values():
            for key, value in resource_stats.items():
                summary[key] += value
        return summary

    def save(self, filename: Optional[str] = None) -> Path:
        """
        Save mappings and statistics to a JSON file.

        Args:
            filename: Filename (optional, auto-generated if absent)

        Returns:
            Path of saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mapping_{timestamp}.json"

        filepath = self.mappings_dir / filename

        data = {
            "timestamp": datetime.now().isoformat(),
            "mappings": self.mappings,
            "stats": self.stats,
            "summary": self.get_summary(),
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Mappings saved to: {filepath}")
        return filepath

    def load(self, filepath: str | Path) -> None:
        """
        Load mappings from a JSON file.

        Args:
            filepath: Path to file to load
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Mapping file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.mappings = data.get("mappings", {})
        self.stats = data.get("stats", {})

        self.logger.info(f"Mappings loaded from: {filepath}")

    def get_all_mappings(self) -> dict[str, dict[str, str]]:
        """Return all mappings."""
        return self.mappings

    def __repr__(self) -> str:
        """Mapper representation."""
        total_mappings = sum(len(m) for m in self.mappings.values())
        return f"IDMapper(total_mappings={total_mappings})"
