#!/usr/bin/env python3
"""
Main script to copy Stripe data from production to test.

Usage:
    python main.py [--dry-run] [--entities ENTITIES] [--verbose]

Examples:
    python main.py --dry-run
    python main.py --entities products,prices
    python main.py --verbose
"""

import argparse
import sys
from typing import List

from src.config import Config, ConfigError
from src.stripe_client import StripeClient
from src.mapper import IDMapper
from src.logger import get_logger
from src.copiers import (
    TaxRateCopier,
    ProductCopier,
    PriceCopier,
    CouponCopier,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Copy Stripe products and prices from production to test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the operation without modifying data"
    )

    parser.add_argument(
        "--entities",
        type=str,
        default="tax_rates,products,prices,coupons",
        help="Entities to copy (comma-separated). "
             "Options: tax_rates, products, prices, coupons. "
             "Default: all"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logs (DEBUG level)"
    )

    parser.add_argument(
        "--env-file",
        type=str,
        default=None,
        help="Path to .env file (optional)"
    )

    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Automatically accept confirmation (no interaction)"
    )

    return parser.parse_args()


def main() -> int:
    """
    Main entry point.

    Returns:
        Return code (0 = success, 1 = error)
    """
    args = parse_args()

    # Initialize logger
    log_level = "DEBUG" if args.verbose else "INFO"
    logger = get_logger(level=log_level)

    logger.print(
        "\n╔═══════════════════════════════════════════════════════════════╗\n"
        "║       Stripe Copy: Production → Test Environment       ║\n"
        "╚═══════════════════════════════════════════════════════════════╝\n",
        style="bold blue"
    )

    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config(env_file=args.env_file)
        logger.success("Configuration validated")

        # Create Stripe client
        client = StripeClient(config, dry_run=args.dry_run)

        # Create mapper
        mapper = IDMapper()

        # Display mode
        if args.dry_run:
            logger.print(
                "\n⚠️  DRY-RUN MODE: No modifications will be made\n",
                style="bold yellow"
            )

        # Create copiers
        copiers_map = {
            "tax_rates": TaxRateCopier(client, mapper),
            "products": ProductCopier(client, mapper),
            "prices": PriceCopier(client, mapper),
            "coupons": CouponCopier(client, mapper),
        }

        # Parse requested entities
        requested_entities = [e.strip() for e in args.entities.split(",")]
        entities_to_copy: List[str] = []

        for entity in requested_entities:
            if entity in copiers_map:
                entities_to_copy.append(entity)
            else:
                logger.warning(f"Unknown entity ignored: {entity}")

        if not entities_to_copy:
            logger.error("No valid entities to copy")
            return 1

        logger.info(f"Entities to copy: {', '.join(entities_to_copy)}")

        # User confirmation
        if not args.dry_run:
            logger.print(
                "\n⚠️  This operation will modify your TEST environment.\n"
                "   PRODUCTION environment will be used in read-only mode.\n",
                style="bold yellow"
            )

            if not args.yes:
                if not logger.confirm("Do you want to continue?"):
                    logger.print("Operation cancelled", style="red")
                    return 0
            else:
                logger.info("Automatic mode enabled (--yes)")

        # Copy entities in dependency order
        logger.section("COPY START")

        for entity_name in entities_to_copy:
            copier = copiers_map[entity_name]
            try:
                copier.copy()
            except Exception as e:
                logger.error(f"Error copying {entity_name}: {e}")
                if not args.dry_run:
                    logger.error("Some entities were not copied")

        # Save mapping
        if not args.dry_run:
            logger.section("SAVING MAPPING")
            mapping_file = mapper.save()
            logger.success(f"Mapping saved: {mapping_file}")

        # Display final statistics
        logger.section("FINAL STATISTICS")

        stats = mapper.get_stats()
        summary = mapper.get_summary()

        # Detailed table by entity
        stats_data = {}
        for entity_name in entities_to_copy:
            entity_stats = stats.get(entity_name, {})
            stats_data[entity_name] = (
                f"✓ {entity_stats.get('created', 0)} created, "
                f"↻ {entity_stats.get('updated', 0)} updated, "
                f"✗ {entity_stats.get('errors', 0)} errors"
            )

        logger.table("Statistics by entity", stats_data)

        # Global summary
        logger.print(
            f"\n[bold green]TOTAL:[/bold green] "
            f"{summary['created']} created, "
            f"{summary['updated']} updated, "
            f"{summary['errors']} errors\n"
        )

        if summary["errors"] > 0:
            logger.warning("Some entities could not be copied")
            return 1

        logger.success("✓ Copy completed successfully!")
        return 0

    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        logger.print(
            "\nCheck that your .env file contains:\n"
            "  STRIPE_SECRET_KEY=sk_live_...\n"
            "  STRIPE_SECRET_KEY_TEST=sk_test_...\n",
            style="yellow"
        )
        return 1

    except KeyboardInterrupt:
        logger.print("\n\nOperation interrupted by user", style="red")
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
