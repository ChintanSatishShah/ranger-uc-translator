# App User Guide

> Translate Apache Ranger policies to Databricks Unity Catalog SQL

**Version:** 2.1 | **Updated:** 2026-05-19

---

## Running the App

**Local (translation only):**
```bash
pip install -r requirements.txt
streamlit run app.py --server.port 8501
# http://localhost:8501
```

**Databricks App (full functionality):**
Deploy from `/Workspace/Repos/chintsinfo@gmail.com/ranger-uc-translator` via Databricks Apps UI.

---

## Interface

Three tabs at the top: **Translate**, **Mapping**, **History**

**Translate tab — two-column layout:**
- Left (40%): JSON input via Upload / Paste / Sample
- Right (60%): Validate → Translate → Download SQL

---

## Basic Workflow

1. **Load JSON** — upload a file, paste JSON, or pick a sample from the dropdown
2. **Validate** — click ✅ Validate to check JSON structure
3. **Translate** — click 🔄 Translate to generate UC SQL
4. **Download** — Download All SQL (single file) or expand individual statements
5. **Execute** — paste into Databricks SQL Editor or notebook

---

## Sample Policies

| Sample | Type | Notes |
|--------|------|-------|
| `access_simple.json` | Access | Basic SELECT grant |
| `access_medium.json` | Access | Multiple users/groups |
| `access_complex.json` | Access | Mixed privileges |
| `masking_simple.json` | Column Mask | Single column |
| `masking_medium.json` | Column Mask | Multiple columns |
| `masking_complex.json` | Column Mask | Multiple mask types |
| `rowfilter_simple.json` | Row Filter | Single filter |
| `rowfilter_medium.json` | Row Filter | Multiple filters merged |
| `rowfilter_complex.json` | Row Filter | Complex conditions |
| `tag_simple.json` | Tag | Basic tag + grant |
| `tag_medium.json` | Tag | Multiple tags |
| `tag_complex.json` | Tag | Tags + masking + row filter |

---

## Translation Output Examples

### Access policy
```sql
GRANT SELECT ON TABLE main.sales.customers TO `analyst@company.com`;
```

### Column masking
```sql
CREATE OR REPLACE FUNCTION main.hr.mask_employees_ssn_mask_show_last_4(ssn STRING)
RETURNS STRING
RETURN
  CONCAT(REPEAT('X', LENGTH(ssn)-4), RIGHT(ssn, 4));

ALTER TABLE main.hr.employees
ALTER COLUMN ssn
SET MASK main.hr.mask_employees_ssn_mask_show_last_4;
```

### Row filter (all user logic merged into one function per table)
```sql
CREATE OR REPLACE FUNCTION main.sales.rf_orders_101_0(region STRING)
RETURNS BOOLEAN
RETURN
  CASE
    WHEN is_account_group_member('west_manager@company.com')
    THEN region = 'WEST'
    ELSE TRUE
  END;

ALTER TABLE main.sales.orders
SET ROW FILTER main.sales.rf_orders_101_0
ON (region);
```

### Tag-based policy (with resourceTags metadata — real tables resolved)
```sql
ALTER TABLE main.sales.customers ALTER COLUMN ssn SET TAGS ('pii' = 'true');

GRANT SELECT ON TABLE main.sales.customers TO `data_protection_team`;
```

When `resourceTags` is absent, a `<table_with_TAG>` placeholder is used instead.

---

## Key Behaviours

- **Wildcards (`*`)** in table names fall back to a SCHEMA-level grant automatically
- **Deny policies** are emitted as `-- DENY POLICY` comments (UC is deny-by-default)
- **Row filters**: one function per table — all items merged into a single CASE statement
- **DROP privilege** remaps to `MANAGE` (DROP is not valid in UC)
- **Hyphenated identifiers** are backtick-quoted automatically
- **Tag resolution**: real table names used when `resourceTags` metadata is present in the JSON

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "No JSON provided" | Load JSON first via Upload, Paste, or Sample tab |
| "Invalid JSON format" | Check syntax with a JSON validator (e.g., jsonlint.com) |
| "Validation failed" | Read error details; check required fields: `id`, `name`, `policyType`, `resources` |
| Download button missing | Translation must complete successfully first |
| `<table_with_TAG>` placeholders | Add `resourceTags` to the JSON or replace manually |

---

## Mapping Reference Tab

The **Mapping** tab in the app shows the complete Ranger → UC translation reference including privilege mappings, resource type mappings, masking function types, and limitations. Consult it before executing generated SQL.
