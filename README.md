# Stripe Copy: Production → Test

Python script to automatically copy Stripe products, prices and other entities from your **production** environment to your **test** environment.

## 🎯 Goal

Quickly recreate a test environment from your production data, with:
- ✅ Secure copy (production in **read-only** mode)
- ✅ Smart update (no duplicates)
- ✅ ID mapping (prod ↔ test) saved in JSON
- ✅ Modular and extensible architecture
- ✅ Error protection

## 📋 Features

### Supported Entities
- **Tax Rates**: Tax rates
- **Products**: Products
- **Prices**: Prices (recurring and one-time)
- **Coupons**: Promo codes and discounts

### Copy Strategy
1. **Smart Detection**: Identifies existing entities via metadata or characteristics
2. **Update**: Updates existing entities with production data
3. **Creation**: Creates missing entities
4. **Mapping**: Records ID correspondences in a JSON file

## 🚀 Installation

### Prerequisites
- Python 3.8+
- Stripe API keys (production and test)

### Installing Dependencies

```bash
# Install dependencies
pip install -r requirements.txt

# Or directly with pip
pip install stripe python-dotenv rich
```

## ⚙️ Configuration

### 1. Create `.env` File

Copy `.env.sample` and fill in your API keys:

```bash
cp .env.sample .env
```

Edit `.env`:

```env
STRIPE_SECRET_KEY=sk_live_XXXXXXXXXXXXXXXXXX
STRIPE_SECRET_KEY_TEST=sk_test_XXXXXXXXXXXXXXXXXX
```

### 2. Key Validation

The script automatically validates:
- ✅ Production key starts with `sk_live_`
- ✅ Test key starts with `sk_test_`
- ✅ Both keys are different
- ✅ **Critical protection**: No write operations possible on production

## 📖 Usage

### Basic Command

```bash
python main.py
```

### Available Options

```bash
python main.py [OPTIONS]

Options:
  --dry-run              Simulate operation without modifying data
  --entities ENTITIES    Entities to copy (comma-separated)
                         Default: tax_rates,products,prices,coupons
  --verbose              Enable detailed logs (DEBUG level)
  --env-file PATH        Path to .env file (optional)
  --yes, -y              Automatically accept confirmation (no interaction)
  -h, --help            Show help
```

### Examples

#### 1. Dry-run mode (simulation)
```bash
python main.py --dry-run
```

#### 2. Copy only products and prices
```bash
python main.py --entities products,prices
```

#### 3. Copy everything with detailed logs
```bash
python main.py --verbose
```

#### 4. Combine multiple options
```bash
python main.py --dry-run --entities products --verbose
```

#### 5. Non-interactive mode
```bash
python main.py --yes
```

## 📊 Output

### ID Mapping

The script generates a JSON file in the `mappings/` folder:

```
mappings/mapping_20250105_143022.json
```

File structure:

```json
{
  "timestamp": "2025-01-05T14:30:22.123456",
  "mappings": {
    "tax_rates": {
      "txr_prod_abc123": "txr_test_xyz789"
    },
    "products": {
      "prod_abc123": "prod_xyz789"
    },
    "prices": {
      "price_abc123": "price_xyz789"
    },
    "coupons": {
      "coupon_abc123": "test_coupon_abc123"
    }
  },
  "stats": {
    "tax_rates": {"created": 2, "updated": 1, "errors": 0},
    "products": {"created": 10, "updated": 5, "errors": 0},
    "prices": {"created": 25, "updated": 0, "errors": 0},
    "coupons": {"created": 3, "updated": 1, "errors": 0}
  },
  "summary": {
    "created": 40,
    "updated": 7,
    "errors": 0
  }
}
```

### Console Statistics

The script displays a detailed summary:

```
╔═══════════════════════════════════════════════════════════════╗
║       Statistics by Entity                                ║
╚═══════════════════════════════════════════════════════════════╝

┌─────────────────┬───────────────────────────────────────────┐
│ Metric          │ Value                                     │
├─────────────────┼───────────────────────────────────────────┤
│ tax_rates       │ ✓ 2 created, ↻ 1 updated, ✗ 0 errors     │
│ products        │ ✓ 10 created, ↻ 5 updated, ✗ 0 errors    │
│ prices          │ ✓ 25 created, ↻ 0 updated, ✗ 0 errors    │
│ coupons         │ ✓ 3 created, ↻ 1 updated, ✗ 0 errors     │
└─────────────────┴───────────────────────────────────────────┘

TOTAL: 40 created, 7 updated, 0 errors
```

## 🏗️ Architecture

### Project Structure

```
stripe-copy-prod-to-test/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration and validation
│   ├── stripe_client.py       # Secure Stripe API wrapper
│   ├── mapper.py              # ID mapping management prod↔test
│   ├── logger.py              # Structured logs with Rich
│   └── copiers/               # Copy modules
│       ├── __init__.py
│       ├── base.py            # BaseCopier abstract class
│       ├── tax_rates.py       # Tax rate copying
│       ├── products.py        # Product copying
│       ├── prices.py          # Price copying
│       └── coupons.py         # Coupon copying
├── mappings/                  # Generated mapping files
├── main.py                    # CLI entry point
├── requirements.txt
├── pyproject.toml
├── .env                       # Configuration (to create)
├── .env.sample
└── README.md
```

### Template Method Pattern

The project uses the **Template Method Pattern** for clean and extensible architecture:

```python
# Abstract class
class BaseCopier(ABC):
    def copy(self):
        # Orchestration (template)
        prod_entities = self.list_from_prod()
        test_entities = self.list_from_test()
        for entity in prod_entities:
            existing = self.find_existing(entity, test_entities)
            if existing:
                self.update_in_test(existing, entity)
            else:
                self.create_in_test(entity)

    @abstractmethod
    def get_create_params(self, entity): pass

    @abstractmethod
    def find_existing(self, prod, tests): pass
```

### Security Protections

1. **Key Validation**: Verification `sk_live_*` vs `sk_test_*`
2. **Production Read-Only**: Exception raised if write attempt in prod
3. **User Confirmation**: Confirmation request before modification
4. **Dry-run Mode**: Simulation without modification
5. **Detailed Logs**: Complete operation traceability

## 🔧 Extensibility

### Adding a New Stripe Entity

1. Create a new copier in `src/copiers/`:

```python
# src/copiers/subscriptions.py
from .base import BaseCopier

class SubscriptionCopier(BaseCopier):
    @property
    def resource_name(self):
        return "subscriptions"

    def get_create_params(self, prod_entity):
        return {
            "customer": self.map_customer_id(prod_entity.customer),
            "items": [{"price": self.mapper.get_test_id("prices", item.price)}
                      for item in prod_entity.items],
            # ... other params
        }

    def get_update_params(self, prod_entity):
        # Update params
        pass

    def find_existing(self, prod_entity, test_entities):
        # Matching logic
        pass
```

2. Register in `src/copiers/__init__.py`:

```python
from .subscriptions import SubscriptionCopier

__all__ = [..., "SubscriptionCopier"]
```

3. Add to `main.py`:

```python
copiers_map = {
    ...,
    "subscriptions": SubscriptionCopier(client, mapper),
}
```

## 🧪 Tests (coming soon)

The project is structured to facilitate test addition:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# With coverage
pytest --cov=src tests/
```

## 🐛 Troubleshooting

### Error: "STRIPE_SECRET_KEY must be a PRODUCTION key"

➜ Check that your key starts with `sk_live_` in the `.env` file

### Error: "Cannot find test product"

➜ Entities have dependencies. Copy in order:
1. Tax Rates
2. Products
3. Prices (depend on products)
4. Coupons (may reference products)

### Prices are created but not updated

➜ This is normal! **Stripe Prices** cannot be modified after creation.
The script creates new prices if parameters change.

## 📝 Limitations

- **Immutable Prices**: Prices cannot be updated (Stripe limitation)
- **Customers Not Copied**: Customer data not copied (sensitive data)
- **Active Subscriptions**: Active subscriptions not copied
- **Webhooks**: Webhooks not automatically configured

## 🤝 Contributing

To contribute:
1. Fork the project
2. Create a branch (`git checkout -b feature/new-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Open a Pull Request

## 📄 License

This project is under MIT license. See `LICENSE` file for details.

## ⚠️ Warning

This script modifies your Stripe **test** environment. Make sure to:
- ✅ Test first with `--dry-run`
- ✅ Verify your keys are correct
- ✅ Have a backup if necessary
- ✅ **NEVER swap prod and test**

---

**Made with ❤️ for Stripe developers**
