# Project Structure

**Version:** 2.1 | **Updated:** 2026-05-19

---

## Directory Layout

```
ranger-uc-translator/
├── app.yaml                  # Databricks App configuration
├── app.py                    # Streamlit UI (single-page, 3-tab)
├── requirements.txt
├── README.md
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── parser.py             # Ranger JSON parser
│   ├── translator.py         # UC SQL translator (EnhancedPolicyTranslator)
│   ├── validator.py          # Input + SQL validation
│   ├── applier.py            # SQL execution against Unity Catalog
│   ├── config.py             # Privilege/masking mappings, TranslationConfig
│   └── utils.py              # SQL formatting, identifier quoting, name generation
│
├── samples/                  # 12 sample Ranger policy JSON files
│   ├── access_{simple,medium,complex}.json
│   ├── masking_{simple,medium,complex}.json
│   ├── rowfilter_{simple,medium,complex}.json
│   └── tag_{simple,medium,complex}.json
│
├── docs/
│   ├── APP_USER_GUIDE.md     # App usage guide
│   ├── GIT_INTEGRATION.md    # Git setup and deployment
│   └── PROJECT_STRUCTURE.md  # This file
│
└── tests/
    ├── setup.sql             # Audit table DDL for Unity Catalog
    ├── test_suite.py         # Full sample test suite
    └── quick_test.py         # Smoke tests
```

---

## Module Descriptions

### `src/parser.py`
Parses Ranger JSON exports into typed `RangerPolicy` objects.
- Supports formats: standard export, `policyDeltas[]`, `testCases[]`, `aclprovider`, `policyengine`
- Numeric `policyType` always takes precedence over inferred type
- Policy types: ACCESS (0), COLUMN_MASK (1), ROW_FILTER (2), TAG-based

### `src/translator.py`
Core translation engine — `PolicyTranslator` base + `EnhancedPolicyTranslator`.
- **ACCESS**: `GRANT privilege ON resource TO principal`; wildcard tables → SCHEMA-level; `DROP` → `MANAGE`
- **COLUMN_MASK**: `CREATE OR REPLACE FUNCTION` (typed params/returns) + `ALTER TABLE SET MASK`
- **ROW_FILTER**: one merged function per table (all items combined into one CASE) + `ALTER TABLE SET ROW FILTER`
- **TAG-based**: resolves to real tables via `resourceTags` metadata; generates `ALTER TABLE SET TAGS`; falls back to placeholder when metadata absent
- Backtick-quotes hyphenated identifiers automatically

### `src/config.py`
Central configuration:
- `PRIVILEGE_MAPPING`: Ranger → UC privilege names (`drop` → `MANAGE`, etc.)
- `MASKING_FUNCTIONS`: expression templates per mask type
- `MASKING_FUNCTION_TYPES`: SQL param/return types (STRING, DATE, TIMESTAMP) per mask type
- `TranslationConfig`: catalog, schema, dry_run, custom mappings

### `src/validator.py`
- `RangerPolicyValidator`: checks JSON structure, required fields, policy type validity
- `UCSQLValidator`: checks generated SQL for syntax issues

### `src/applier.py`
Executes generated SQL against Unity Catalog. Supports dry-run, batch execution, and audit logging to Delta tables.

### `src/utils.py`
- Identifier quoting (`_quote_id` — adds backticks for hyphens/special chars)
- Function name generation for row filters and column masks
- SQL statement formatting

---

## Import Pattern

```python
from src.parser import RangerPolicyParser
from src.translator import EnhancedPolicyTranslator
from src.config import TranslationConfig

parser = RangerPolicyParser()
parser.parse_file('samples/tag_complex.json')

translator = EnhancedPolicyTranslator(TranslationConfig(catalog="main"))
translator.set_tag_metadata(data.get('tagDefinitions', {}), data.get('resourceTags', {}))

tag_sql = translator.generate_tag_sql()
uc_policies = translator.translate_all(parser.policies)
```

---

## Architecture Flow

```
Ranger JSON
    ↓ parser.py         → RangerPolicy objects
    ↓ validator.py      → JSON structure check
    ↓ translator.py     → UC SQL statements
    ↓ app.py            → display / download
    ↓ applier.py        → execute (optional, Databricks only)
    ↓ Unity Catalog
```

---

## Version History

**v2.1** (2026-05-19)
- Proper UC privilege mapping: `DROP` → `MANAGE`, `CREATE` → `CREATE TABLE ON SCHEMA`
- One row filter function per table (all items merged)
- Tag resolution from `resourceTags` metadata + `ALTER TABLE SET TAGS` generation
- Typed masking function signatures (DATE, TIMESTAMP, BOOLEAN return types)
- Backtick-quoting for hyphenated identifiers
- Deny policies emitted as SQL comments

**v2.0** (2024-05-16)
- Single-page Streamlit UI with 2-column layout
- EnhancedPolicyTranslator with all 4 policy types
- 12 sample policies
