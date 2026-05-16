# Ranger to Unity Catalog Policy Translation Engine

A comprehensive end-to-end solution for migrating Apache Ranger policies to Databricks Unity Catalog. Built entirely on Databricks with a Streamlit-based UI.

## 🎯 Overview

This tool automates the translation and application of Apache Ranger policies to Unity Catalog, supporting:

* **ACL Policies** - Table/schema level access grants (SELECT, MODIFY, CREATE, etc.)
* **Row Filters** - Row-level security policies
* **Column Masking** - Column-level data masking (MASK, HASH, NULLIFY, etc.)
* **Tag-Based Policies** - Governed tags and attribute-based access control (ABAC)

## 🏗️ Architecture

```
Ranger JSON → Parser → Translation Engine → Validation → UC API/SQL → Audit Log
                                    ↓
                            UI Dashboard (monitoring & control)
```

### Components

1. **Parser** (`parser.py`) - Parses and validates Ranger policy JSON
2. **Translator** (`translator.py`) - Maps Ranger constructs to UC equivalents
3. **Applier** (`applier.py`) - Executes UC policies via SQL/SDK
4. **Config** (`config.py`) - Configuration and mapping definitions
5. **Utils** (`utils.py`) - Helper functions
6. **Streamlit UI** (`app.py`) - Interactive web interface
7. **Audit Tables** (`setup.sql`) - Delta tables for logging and tracking
8. **Sample Policies** (`samples/`) - 12 demo files covering all policy types

## 📋 Prerequisites

* Databricks workspace with Unity Catalog enabled
* Catalog for audit tables (default: `main.ranger_migration`)
* User with admin privileges (to create tags, row filters, grants)
* Python 3.10+

## 🚀 Quick Start

### 1. Setup Audit Tables

Run the setup SQL to create audit tables and views:

```sql
-- In Databricks SQL Editor or Notebook
%sql
SOURCE /Users/your_email/ranger-to-uc/setup.sql
```

Or execute via Python:
```python
with open('setup.sql') as f:
    spark.sql(f.read())
```

### 2. Create Databricks App

1. Navigate to **Apps** in your Databricks workspace
2. Click **Create App**
3. Select **From files**
4. Choose the `ranger-to-uc` directory
5. Set entry point: `app.py`
6. Click **Create**

### 3. Test with Sample Policies

Upload sample files from the `samples/` directory:
```
samples/access_simple.json       → Basic ACL translation
samples/rowfilter_medium.json    → Multi-filter translation
samples/masking_complex.json     → Conditional masking
samples/tag_simple.json          → Tag-based access
```

See [samples/README.md](samples/README.md) for detailed sample documentation.

### 4. Access the UI

Once deployed, the app provides 6 pages:

* **📤 Upload** - Upload Ranger policy JSON files
* **⚙️ Configure** - Set up mappings and translation options
* **🔄 Translate** - Convert Ranger policies to UC format
* **👁️ Review** - Preview generated SQL statements
* **✅ Apply** - Execute policies in Unity Catalog (with dry-run)
* **📊 Monitor** - View audit trail and history

## 📁 Project Structure

```
ranger-to-uc/
├── app.py              # Streamlit main application (6 pages)
├── parser.py           # Ranger JSON parser with validation
├── translator.py       # Translation engine (ACL, row filter, column mask, tags)
├── applier.py          # UC policy executor with audit logging
├── config.py           # Configuration and default mappings
├── utils.py            # Helper functions (SQL formatting, validation)
├── setup.sql           # Audit table DDL and views
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── samples/            # Sample policy files (12 files)
    ├── README.md
    ├── access_simple.json
    ├── access_medium.json
    ├── access_complex.json
    ├── rowfilter_simple.json
    ├── rowfilter_medium.json
    ├── rowfilter_complex.json
    ├── masking_simple.json
    ├── masking_medium.json
    ├── masking_complex.json
    ├── tag_simple.json
    ├── tag_medium.json
    └── tag_complex.json
```

## 🔧 Configuration

### Default Settings

Edit `config.py` or use the UI to configure:

```python
DEFAULT_CATALOG = "main"
DEFAULT_SCHEMA = "ranger_migration"
```

### Custom Mappings

Define custom mappings for resources, principals, and privileges:

**Resource Mapping** (Ranger path → UC catalog.schema.table):
```
/hive/database/table → catalog.schema.table
```

**Principal Mapping** (Ranger user/group → UC principal):
```
ranger_user → uc_user@company.com
ranger_group → uc_group_name
```

**Privilege Mapping** (Ranger permission → UC privilege):
```
select → SELECT
update → MODIFY
all → ALL PRIVILEGES
```

### Translation Options

* **Dry Run** - Preview without applying (recommended for first run)
* **Skip Errors** - Continue on individual policy failures
* **Create Tags** - Auto-create governed tags
* **Apply Grants/Filters/Masks** - Enable/disable specific policy types

## 📝 Usage Examples

### Example 1: Simple ACL Translation

**Ranger Policy:**
```json
{
  "id": 1,
  "name": "customer_table_access",
  "resources": {
    "database": {"values": ["sales"]},
    "table": {"values": ["customers"]}
  },
  "policyItems": [{
    "users": ["analyst1"],
    "accesses": [{"type": "select"}]
  }]
}
```

**Translated UC SQL:**
```sql
GRANT SELECT ON main.sales.customers TO `analyst1`;
```

### Example 2: Row Filter Translation

**Ranger Policy:**
```json
{
  "id": 2,
  "name": "regional_filter",
  "resources": {
    "database": {"values": ["sales"]},
    "table": {"values": ["orders"]}
  },
  "rowFilterPolicyItems": [{
    "users": ["regional_manager"],
    "rowFilterInfo": {
      "filterExpr": "region = 'west'"
    }
  }]
}
```

**Translated UC SQL:**
```sql
CREATE OR REPLACE FUNCTION main.sales.rf_orders_2_0(row ROW(orders))
RETURN IF(
  is_account_group_member('regional_manager'),
  region = 'west',
  FALSE
);

ALTER TABLE main.sales.orders SET ROW FILTER rf_orders_2_0 ON (`regional_manager`);
```

### Example 3: Column Masking

**Ranger Policy:**
```json
{
  "id": 3,
  "name": "ssn_masking",
  "resources": {
    "database": {"values": ["hr"]},
    "table": {"values": ["employees"]},
    "column": {"values": ["ssn"]}
  },
  "dataMaskPolicyItems": [{
    "groups": ["hr_staff"],
    "dataMaskInfo": {
      "dataMaskType": "MASK_SHOW_LAST_4"
    }
  }]
}
```

**Translated UC SQL:**
```sql
CREATE OR REPLACE FUNCTION main.hr.mask_employees_ssn_mask_show_last_4(column_value STRING)
RETURN CASE 
  WHEN is_account_group_member('hr_staff') THEN column_value 
  ELSE CONCAT(REPEAT('X', LENGTH(column_value)-4), RIGHT(column_value, 4)) 
END;

ALTER TABLE main.hr.employees ALTER COLUMN ssn SET MASK mask_employees_ssn_mask_show_last_4;
```

### Example 4: Tag-Based Policy

**Ranger Policy:**
```json
{
  "policies": [{
    "resources": {
      "tag": {"values": ["PII"]}
    },
    "policyItems": [{
      "groups": ["data_protection_team"],
      "accesses": [{"type": "select"}]
    }]
  }],
  "tagDefinitions": {
    "PII": {
      "attributeDefs": {"level": "high"}
    }
  },
  "resourceTags": {
    "sales.customers.ssn": ["PII"]
  }
}
```

**Translated UC SQL:**
```sql
CREATE TAG IF NOT EXISTS main.ranger_migration.PII;
ALTER TABLE sales.customers SET TAGS ('main.ranger_migration.PII' = 'true');
```

## 🔍 Monitoring & Audit

The tool creates Delta tables for comprehensive audit trail:

### Audit Tables

1. **ranger_policies_raw** - Raw Ranger policy JSON uploads
2. **translation_log** - Translation attempts and results
3. **uc_policies_applied** - Execution audit trail
4. **mapping_config** - Custom user-defined mappings

### Audit Views

1. **v_translation_summary** - Translation stats by date
2. **v_application_summary** - Applied policies by type and status
3. **v_recent_errors** - Latest errors for troubleshooting

### Query Examples

```sql
-- View recent translations
SELECT * FROM main.ranger_migration.v_translation_summary 
ORDER BY translation_date DESC LIMIT 10;

-- Check success rate
SELECT 
  policy_type,
  status,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY policy_type), 2) as pct
FROM main.ranger_migration.uc_policies_applied
GROUP BY policy_type, status;

-- View failed policies
SELECT * FROM main.ranger_migration.v_recent_errors;
```

## 🧪 Testing Strategy

### Test with Sample Files

1. **Start Simple:** `samples/access_simple.json`
   - Single table, single permission
   - Validate basic translation works

2. **Test Medium Complexity:** `samples/rowfilter_medium.json`
   - Multiple filters
   - Different user groups
   - Verify filter logic

3. **Test Complex Scenarios:** `samples/tag_complex.json`
   - Multiple tags
   - Combined policies
   - Compliance requirements

### Test with Dry Run

1. Upload a sample policy file
2. Configure mappings if needed
3. Enable "Dry Run" mode
4. Review generated SQL in the Review page
5. Validate mappings and translations
6. Disable dry run for actual execution

### Validate Results

After applying policies:
```sql
-- Check grants
SHOW GRANTS ON catalog.schema.table;

-- Check row filters
DESCRIBE TABLE EXTENDED catalog.schema.table;

-- Check column masks
SHOW TBLPROPERTIES catalog.schema.table;

-- Check tags
SELECT * FROM system.information_schema.table_tags 
WHERE catalog_name = 'main' AND schema_name = 'ranger_migration';
```

## ⚠️ Important Notes

### Limitations

* **Resource Mapping** - Complex path patterns may require custom mapping
* **Conditions** - Advanced Ranger conditions may need manual translation
* **Dynamic Policies** - Time-based or context-based policies need adaptation
* **Service Definitions** - Focus is on Hive/HDFS services

### Best Practices

1. **Start Small** - Test with sample files or subset of policies first
2. **Use Dry Run** - Always preview before applying
3. **Backup** - Document existing Ranger policies
4. **Test Permissions** - Verify UC grants work as expected
5. **Monitor Audit** - Review logs after each run
6. **Iterate Mappings** - Refine resource/principal mappings based on results
7. **Validate Results** - Test actual data access after policy application

## 🐛 Troubleshooting

### Common Issues

**Issue: "Could not determine resource"**
* Check resource mapping in config
* Ensure Ranger paths follow expected format
* Add custom mapping for non-standard paths

**Issue: "Permission denied"**
* Verify user has admin privileges in UC
* Check catalog/schema permissions
* Ensure tables exist before applying row filters/masks

**Issue: "Function already exists"**
* Row filter/mask functions may exist from previous runs
* Use "CREATE OR REPLACE" or drop existing functions
* Check function naming conflicts

**Issue: "Invalid tag name"**
* Ensure tag names are valid UC identifiers
* Check tag definition format
* Verify catalog/schema exists for tags

### Debug Mode

Enable verbose logging in the app:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🔄 Extending the Tool

### Add Custom Masking Functions

Edit `config.py`:
```python
MASKING_FUNCTIONS["CUSTOM_MASK"] = "your_sql_expression_here"
```

### Add Custom Policy Types

Extend `translator.py`:
```python
def _translate_custom_policy(self, policy: RangerPolicy) -> Optional[UCPolicy]:
    # Your custom translation logic
    pass
```

### Integrate with Ranger API

Add to `parser.py`:
```python
def fetch_from_ranger_api(self, ranger_url: str, auth_token: str):
    # Fetch policies directly from Ranger REST API
    pass
```

## 📚 References

* [Apache Ranger Documentation](https://ranger.apache.org/)
* [Unity Catalog Documentation](https://docs.databricks.com/data-governance/unity-catalog/index.html)
* [Unity Catalog Row Filters](https://docs.databricks.com/security/privacy/row-and-column-filters.html)
* [Unity Catalog Column Masks](https://docs.databricks.com/security/privacy/column-masks.html)
* [Governed Tags (ABAC)](https://docs.databricks.com/data-governance/unity-catalog/tags.html)
* [Ranger Policy Engine Tests](https://github.com/apache/ranger/tree/master/agents-common/src/test/resources/policyengine)

## 🤝 Contributing

Contributions welcome! Areas for improvement:

* Additional masking function templates
* Support for more Ranger service types (HBase, Kafka, etc.)
* Enhanced error handling and recovery
* Performance optimization for large policy sets
* Integration with Ranger API for direct export
* Support for policy versioning and rollback
* Batch processing with progress tracking

## 📄 License

This tool is provided as-is for migration purposes. Ensure compliance with your organization's security and governance policies.

## 👥 Support

For issues and questions:
1. Check audit tables for error details
2. Review translation logs
3. Validate Ranger JSON format against samples
4. Test with simplified policies
5. Check Unity Catalog permissions

---

**Version:** 1.0.0 (MVP)  
**Last Updated:** 2026-05-16  
**Status:** ✅ Ready for production testing

## 🎉 Getting Started Checklist

- [ ] Run `setup.sql` to create audit tables
- [ ] Create Databricks App from the `ranger-to-uc` directory
- [ ] Test with `samples/access_simple.json`
- [ ] Configure custom mappings for your environment
- [ ] Test translation with dry run enabled
- [ ] Review generated SQL in the Review page
- [ ] Apply policies to a test catalog/schema
- [ ] Validate results with SHOW GRANTS
- [ ] Monitor audit logs
- [ ] Scale to production policies
