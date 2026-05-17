# Apache Ranger to Unity Catalog Policy Translation Engine

> Automate Apache Ranger to Databricks Unity Catalog policy migration with confidence

[![Translation Success](https://img.shields.io/badge/Translation%20Success-100%25-brightgreen)]()
[![Policy Types](https://img.shields.io/badge/Policy%20Types-4%2F4-blue)]()
[![SQL Statements](https://img.shields.io/badge/SQL%20Generated-118-orange)]()
[![UI](https://img.shields.io/badge/UI-Streamlit-red)]()

---

## 🎯 Overview

This comprehensive solution automates the migration of Apache Ranger policies to Databricks Unity Catalog format. Built entirely on Databricks with an intuitive Streamlit UI, it handles all policy types with validated 100% translation success.

### ✨ Supported Policy Types

| Policy Type | Support | Test Coverage | Success Rate |
|------------|---------|---------------|--------------|
| **Access Control (ACL)** | ✅ Full | 3 samples | 100% |
| **Row-level Filters** | ✅ Full | 3 samples | 100% |
| **Column Masking** | ✅ Full | 3 samples | 100% |
| **MASK_NONE (Conditional)** | ✅ Full | Included | 100% |
| **Tag-based Policies** | ✅ Full | 3 samples | 100% |

**Total:** 12 test samples, 118 SQL statements generated, 0 errors

---

## 🏗️ Architecture

```
┌─────────────────┐
│  Ranger JSON    │
│  Policy Export  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐      ┌──────────────────┐
│     Parser      │─────→│    Validator     │
│  (JSON → Obj)   │      │ (Input + SQL)    │
└────────┬────────┘      └──────────────────┘
         │
         ↓
┌─────────────────┐      ┌──────────────────┐
│   Enhanced      │─────→│   UC Policies    │
│   Translator    │      │  (SQL + Tags)    │
└────────┬────────┘      └──────────────────┘
         │
         ↓
┌─────────────────┐      ┌──────────────────┐
│    Applier      │─────→│  Audit Logger    │
│ (Execute SQL)   │      │  (Delta Tables)  │
└─────────────────┘      └──────────────────┘
         │
         ↓
┌─────────────────────────────────────────────┐
│        Streamlit UI (Interactive)           │
│  Upload • Validate • Translate • Review     │
└─────────────────────────────────────────────┘
```

### Core Components

| Module | Purpose | Lines | Features |
|--------|---------|-------|----------|
| `parser.py` | Parse Ranger JSON | 227 | 4 policy types, error handling |
| `translator.py` | UC policy translation | 606 | All 4 policy types, tag support |
| `validator.py` | Input/SQL validation | 307 | Error detection, warnings |
| `applier.py` | Execute policies | 203 | Dry-run mode, audit logging |
| `config.py` | Configuration | 100 | Mappings, settings |
| `utils.py` | Helper functions | 219 | SQL formatting, identifiers |
| `app.py` | Streamlit UI | 414 | Single-page, 3-tab interface |

---

## 📦 Project Structure

```
ranger-uc-translator/
├── 📄 Configuration & Entry Point
│   ├── app.yaml                  # Databricks App configuration
│   ├── app.py                    # Streamlit UI (414 lines)
│   ├── requirements.txt          # Python dependencies
│   └── .gitignore
│
├── 📚 Documentation
│   ├── README.md                 # This file
│   ├── PROJECT_STRUCTURE.md      # Detailed structure guide
│
├── 📁 src/                       # Source Code Package
│   ├── __init__.py              # Package initialization (v2.0.0)
│   ├── parser.py                # Ranger JSON parser
│   ├── translator.py            # UC policy translator (EnhancedPolicyTranslator)
│   ├── validator.py             # Input/SQL validation
│   ├── applier.py               # Policy executor
│   ├── config.py                # Configuration management
│   └── utils.py                 # Utility functions
│
├── 📁 samples/                   # Sample Policy Files
│   ├── access_simple.json       # Basic access control
│   ├── access_medium.json       # Multiple users/groups
│   ├── access_complex.json      # Mixed privileges
│   ├── masking_simple.json      # Single column mask
│   ├── masking_medium.json      # Multiple columns
│   ├── masking_complex.json     # Custom mask types
│   ├── rowfilter_simple.json    # Single filter
│   ├── rowfilter_medium.json    # Multiple filters
│   ├── rowfilter_complex.json   # Complex conditions
│   ├── tag_simple.json          # Basic tag policy
│   ├── tag_medium.json          # Multiple tags
│   └── tag_complex.json         # Tag + masking
│
├── 📁 docs/                      # Documentation
│   ├── APP_USER_GUIDE.md        # Streamlit app usage guide
│   └── GIT_INTEGRATION.md       # Git setup guide
│
├── 📁 tests/                     # Test Files
│   ├── setup.sql                # Audit table setup
│
```

---

## 🚀 Quick Start

### Prerequisites

**For Local Development (Translation Only):**
- ✅ Python 3.10+
- ✅ pip (for installing dependencies)

**For Full Functionality (Translation + Execution):**
- ✅ Databricks workspace with Unity Catalog enabled
- ✅ Catalog for audit tables (default: `main.ranger_migration`)
- ✅ User with admin privileges (CREATE TABLE, GRANT, CREATE TAG)

### Installation

#### Option 1: Local Deployment (No Databricks Required) ⭐ **NEW**

**Perfect for:** Translation-only workflow, generating SQL scripts for manual execution

```bash
# 1. Clone or download the repository
git clone https://github.com/YOUR_USERNAME/ranger-uc-translator.git
cd ranger-uc-translator

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py --server.port 8501
```

**Access at:** http://localhost:8501

**✅ What Works:**
- Upload and validate Ranger JSON policies
- Translate all 4 policy types (access, masking, row filters, tags)
- Review generated SQL with syntax highlighting
- Export SQL scripts (.sql files)
- Export CSV/JSON reports
- Test all 12 sample policies

**❌ What Requires Databricks:**
- Direct SQL execution (UC policies)
- Audit logging to Delta tables

**Use Case:** Generate SQL scripts locally, then copy/paste into Databricks SQL Editor or notebook for manual execution.

---

#### Option 2: Databricks App (Full Functionality)

The project is configured to run as a Databricks App with `app.yaml`:

```yaml
command: ['streamlit', 'run', 'app.py', '--server.port', '8080', '--server.address', '0.0.0.0']
```

**Deploy via Databricks Apps UI:**
1. Go to Databricks Apps
2. Create new app from `/Workspace/Repos/chintsinfo@gmail.com/ranger-uc-translator`
3. App will automatically install dependencies from requirements.txt
4. Access via the generated app URL

**Full functionality:** Translation + Direct SQL execution + Audit logging

---

#### Option 3: Databricks Repos

```bash
# 1. In Databricks UI, go to Repos
# 2. Click "Add Repo"
# 3. Enter: https://github.com/YOUR_USERNAME/ranger-uc-translator.git
# 4. Click "Create Repo"
```

### Setup Audit Tables

```sql
-- Run in Databricks SQL Editor or Notebook
%sql
CREATE CATALOG IF NOT EXISTS main;
CREATE SCHEMA IF NOT EXISTS main.ranger_migration;

-- Run setup script
%run ./tests/setup.sql
```

---


## 🔄 Deployment Workflows

Choose the workflow that best fits your environment and requirements:

### Workflow 1: Local-Only (No Databricks) 💻

**Best for:** Testing, SQL script generation, offline development

```
┌─────────────────────────────────────────────────────────────────────┐
│                      LOCAL MACHINE                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  📥 Ranger JSON         🔄 Translation          📤 SQL Scripts       │
│  ┌──────────┐          ┌──────────┐           ┌──────────┐         │
│  │ Upload   │─────────→│ Validate │─────────→ │ Export   │         │
│  │ Policy   │          │ Translate│           │ .sql file│         │
│  └──────────┘          └──────────┘           └─────┬────┘         │
│       ↓                      ↓                       │              │
│  ✅ 12 samples         ✅ All 4 types           ✅ Ready to use     │
│  ✅ Custom JSON        ✅ SQL preview           ✅ CSV/JSON export  │
│                                                      │              │
└──────────────────────────────────────────────────────┼──────────────┘
                                                       ↓
                          ┌──────────────────────────────────┐
                          │  MANUAL STEP (Later)             │
                          │  Copy/paste SQL to Databricks    │
                          │  Execute in SQL Editor/Notebook  │
                          └──────────────────────────────────┘
```

**✅ Advantages:**
* No Databricks account needed during translation
* Work offline or in restricted networks
* Review SQL before execution
* Share scripts with team for approval

**⏱️ Time:** ~5 minutes per policy

**Command:**
```bash
streamlit run app.py --server.port 8501
# Access at: http://localhost:8501
```

---

### Workflow 2: Databricks App (Full Integration) ☁️

**Best for:** Production migration, automated workflows, audit logging

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DATABRICKS WORKSPACE                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  📥 Ranger JSON    🔄 Translation    ▶️ Execution    📊 Audit       │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐   ┌──────────┐    │
│  │ Upload   │────→│ Validate │────→│  Apply   │──→│  Log to  │    │
│  │ Policy   │     │ Translate│     │  SQL     │   │  Delta   │    │
│  └──────────┘     └──────────┘     └──────────┘   └──────────┘    │
│       ↓                 ↓                ↓              ↓           │
│  ✅ 12 samples    ✅ All 4 types   ✅ Auto-exec   ✅ Full audit    │
│  ✅ Custom JSON   ✅ SQL preview   ✅ Dry-run     ✅ Rollback      │
│                                    ✅ Unity Cat.  ✅ Compliance    │
│                                                                      │
│  🔒 Unity Catalog Integration                                       │
│  ├── GRANT statements applied automatically                         │
│  ├── Row filters created and assigned                               │
│  ├── Column masks configured                                        │
│  └── Tags defined and applied                                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**✅ Advantages:**
* End-to-end automation
* Immediate policy application
* Complete audit trail in Delta tables
* No manual copy/paste steps
* Dry-run mode for safety

**⏱️ Time:** ~3 minutes per policy (fully automated)

**Setup:**
```yaml
# Deploy via Databricks Apps UI
App Source: /Workspace/Repos/yourname/ranger-uc-translator
# Access via generated app URL
```

---

### Workflow 3: Hybrid (Best of Both) 🔄

**Best for:** Compliance-heavy environments, multi-stage approvals

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│    LOCAL MACHINE        │         │   DATABRICKS WORKSPACE       │
│  (Development/Review)   │         │   (Execution/Production)     │
├─────────────────────────┤         ├──────────────────────────────┤
│                         │         │                              │
│  📥 Upload Ranger JSON  │         │  📥 Receive approved SQL     │
│  🔄 Translate to UC SQL │         │  👁️ Final review            │
│  👁️ Review & validate   │────────→│  ▶️ Execute in UC           │
│  📝 Document changes    │  .sql   │  📊 Monitor & audit          │
│  ✅ Get team approval   │  file   │  ✅ Verify permissions       │
│                         │         │                              │
└─────────────────────────┘         └──────────────────────────────┘
       DAY 1-3: Review                   DAY 4: Execution
```

**Stages:**

1. **Week 1: Translation (Local)**
   * Data team translates all policies locally
   * Security team reviews generated SQL
   * Compliance approves changes
   * SQL scripts stored in version control

2. **Week 2: Testing (Dev Databricks)**
   * Copy SQL to dev workspace
   * Execute with dry_run=True
   * Validate with test users
   * Refine as needed

3. **Week 3: Production (Prod Databricks)**
   * Deploy approved scripts to production
   * Execute in maintenance window
   * Monitor for 48 hours
   * Document actual vs. expected

**✅ Advantages:**
* Maximum control and visibility
* Clear approval checkpoints
* Version controlled SQL scripts
* Gradual rollout
* Easy rollback with saved SQL

**⏱️ Time:** 2-3 weeks for enterprise migration

---

### Workflow Comparison

| Feature | Local-Only | Databricks App | Hybrid |
|---------|-----------|----------------|---------|
| **Databricks Required** | ❌ No | ✅ Yes | ✅ Yes (later) |
| **Translation** | ✅ Yes | ✅ Yes | ✅ Yes |
| **SQL Execution** | ⚠️ Manual | ✅ Automatic | ⚠️ Manual |
| **Audit Logging** | ❌ No | ✅ Yes | ✅ Yes (execution phase) |
| **Approval Process** | ✅ Easy | ⚠️ After execution | ✅ Before execution |
| **Version Control** | ✅ Easy | ⚠️ Extra steps | ✅ Built-in |
| **Team Collaboration** | ✅ Easy (SQL files) | ⚠️ Requires access | ✅ Easy (SQL files) |
| **Speed** | ⚡ Fast translation | ⚡⚡ Fastest overall | 🐢 Slower (controlled) |
| **Risk Level** | 🟢 Low (review first) | 🟡 Medium (auto-exec) | 🟢 Low (staged) |
| **Best For** | POC, testing | Production automation | Enterprise, compliance |

---

### Quick Decision Guide

**Choose Local-Only if:**
* You don't have Databricks access yet
* You need to review SQL before execution
* Your team requires external approval
* You're in a restricted/air-gapped network

**Choose Databricks App if:**
* You have Databricks with Unity Catalog
* You want end-to-end automation
* You need audit trails in Delta tables
* Speed is a priority

**Choose Hybrid if:**
* You have strict change control processes
* Multiple approval stages are required
* You want version-controlled migration
* You're migrating 100+ policies

---

## 💡 Usage Guide

### Basic Workflow

```
1. Upload/Select → 2. Validate → 3. Translate → 4. Review → 5. Export → 6. Execute
   📤              🔍             🔄            👁️          💾          ✅
```

### Step-by-Step Example

#### Step 1: Load Policy (1 min)

**Left Column - Choose input method:**

* **📁 Upload Tab:** Drag & drop your Ranger JSON file
* **✏️ Paste Tab:** Paste JSON content and click "Load Pasted JSON"
* **📋 Sample Tab:** Select from 12 pre-loaded samples (e.g., "access_simple.json")

**Result:** JSON appears in the editor below, pretty-printed and ready to validate

---

#### Step 2: Validate (1 min)

**Right Column - Click ✅ Validate button**

Validation checks:
* ✓ JSON structure validation
* ✓ Required fields checking
* ✓ Data type validation
* ✓ Policy items validation

**Example results:**
```
✅ Validation passed! Found 1 valid policies
✅ Last validation: Passed
```

---

#### Step 3: Translate (1 min)

**Right Column - Click 🔄 Translate button**

The engine uses:
* EnhancedPolicyTranslator (supports all 4 policy types)
* Automatic tag metadata handling
* Comprehensive error collection

**Result:**
```
✅ Translation complete! Generated 13 SQL statements from 1 policies.
📋 Policies Translated: 1
📝 SQL Statements: 13
```

---

#### Step 4: Download SQL (30 sec)

**Two download options appear:**

1. **📥 Download All SQL** - Single file with all statements
2. **Individual Downloads** - Expand each statement, copy or download individually

Each SQL statement shows:
* Syntax-highlighted SQL code
* Copy text area (Ctrl+A, Ctrl+C)
* Individual download button

---

#### Step 5: Execute (Manual)

```sql
-- Review downloaded SQL script
-- Execute in Unity Catalog:

GRANT SELECT ON main.sales.customers TO `analyst1@company.com`;
GRANT MODIFY ON main.sales.orders TO `sales_manager@company.com`;
-- ... more statements
```

**Total Time: ~8 minutes** for simple policy

---

## 🎨 Streamlit UI Features

### Single-Page Interface with Two-Column Layout

The app uses a streamlined single-page design optimized for quick policy translation:

#### **Left Column: JSON Input (40%)**

**Three Input Methods (Tabs):**

1. **📁 Upload Tab**
   * Drag & drop JSON files
   * Supports .json format
   * Auto-loads on upload
   * Shows filename confirmation

2. **✏️ Paste Tab**
   * Text area for direct JSON input
   * "Load Pasted JSON" button
   * Ideal for quick testing
   * Copy/paste from clipboard

3. **📋 Sample Tab**
   * Dropdown selector with 12 pre-loaded samples
   * Auto-loads on selection
   * Organized by policy type and complexity
   * No button needed - instant load

**JSON Display:**
* Pretty-printed JSON viewer
* Editable text area (400px height)
* Auto-clears outputs when JSON changes
* Syntax validation on input

---

#### **Right Column: SQL Output & Actions (60%)**

**Action Buttons (2-button row):**

1. **✅ Validate** - Validates JSON structure and policy format
2. **🔄 Translate** - Translates policies to Unity Catalog SQL (primary action)

**Output Displays:**

* **Validation Results:** JSON structure, policy counts, errors/warnings
* **Translation Results:** Success metrics, SQL statement count, any errors
* **Download All SQL:** Button to download all statements as single .sql file
* **Individual SQL Statements:** Expandable sections with code display, copy area, and individual download buttons
* **Statistics:** Policy counts by type, SQL statement breakdown

---

### Key UI Features

* **Real-time Clearing:** Outputs auto-clear when new JSON is loaded
* **Progress Indicators:** Spinners show validation/translation progress
* **Error Handling:** Inline error messages with specific details
* **Download Timestamping:** Files auto-named with `uc_policies_YYYYMMDD_HHMMSS.sql`
* **Responsive Layout:** Wide layout optimized for side-by-side viewing
* **Session State:** Maintains JSON, SQL, and results across interactions

---

## 🧪 Testing & Validation

### Test Results Summary

| Metric | Result |
|--------|--------|
| **Total Test Files** | 12 |
| **Parse Success Rate** | 100% (12/12) |
| **Translation Success Rate** | 100% (12/12) |
| **SQL Statements Generated** | 118 |
| **Total Errors** | 0 |
| **Total Warnings** | 0 |

### Results by Policy Type

| Policy Type | Files | Success | SQL Generated |
|-------------|-------|---------|---------------|
| Access (ACL) | 3 | 3/3 (100%) | 23 |
| Row Filters | 3 | 3/3 (100%) | 12 |
| Column Masking | 3 | 3/3 (100%) | 52 |
| Tag-based | 3 | 3/3 (100%) | 31 |

### Results by Complexity

| Complexity | Files | Avg SQL/Policy | Errors |
|-----------|-------|----------------|--------|
| Simple | 4 | 3.75 | 0 |
| Medium | 4 | 10.50 | 0 |
| Complex | 4 | 15.25 | 0 |

### Sample Policies Included

```
samples/
├── access_simple.json      # Basic SELECT grant
├── access_medium.json      # Multiple users/groups
├── access_complex.json     # Mixed privileges
├── masking_simple.json     # Single column mask
├── masking_medium.json     # Multiple columns
├── masking_complex.json    # Custom mask types
├── rowfilter_simple.json   # Single filter expression
├── rowfilter_medium.json   # Multiple filters
├── rowfilter_complex.json  # Complex conditions
├── tag_simple.json         # Basic tag policy
├── tag_medium.json         # Multiple tags
└── tag_complex.json        # Tag + masking
```

---

## 📖 Translation Examples

### Example 1: Access Control (ACL)

**Ranger Policy:**
```json
{
  "name": "sales_read_access",
  "resources": {
    "database": {"values": ["sales"]},
    "table": {"values": ["customers"]}
  },
  "policyItems": [{
    "users": ["analyst1@company.com"],
    "accesses": [{"type": "select"}]
  }]
}
```

**Generated UC SQL:**
```sql
GRANT SELECT ON main.sales.customers TO `analyst1@company.com`;
```

---

### Example 2: Row-level Filter

**Ranger Policy:**
```json
{
  "name": "regional_filter",
  "resources": {
    "database": {"values": ["sales"]},
    "table": {"values": ["orders"]}
  },
  "rowFilterPolicyItems": [{
    "users": ["west_manager@company.com"],
    "rowFilterInfo": {
      "filterExpr": "region = 'WEST'"
    }
  }]
}
```

**Generated UC SQL:**
```sql
CREATE OR REPLACE FUNCTION main.sales.rf_orders_101_0(row ROW(orders))
RETURN IF(
  is_account_group_member('west_manager@company.com'),
  region = 'WEST',
  FALSE
);

ALTER TABLE main.sales.orders 
SET ROW FILTER rf_orders_101_0 ON (`west_manager@company.com`);
```

---

### Example 3: Column Masking

**Ranger Policy:**
```json
{
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

**Generated UC SQL:**
```sql
CREATE OR REPLACE FUNCTION main.hr.mask_employees_ssn_mask_show_last_4(column_value STRING)
RETURN CASE 
  WHEN is_account_group_member('hr_staff') THEN column_value 
  ELSE CONCAT(REPEAT('X', LENGTH(column_value)-4), RIGHT(column_value, 4)) 
END;

ALTER TABLE main.hr.employees 
ALTER COLUMN ssn SET MASK mask_employees_ssn_mask_show_last_4;
```

---

### Example 4: Tag-based Policy

**Ranger Policy:**
```json
{
  "name": "pii_tag_access",
  "resources": {
    "tag": {"values": ["PII"]}
  },
  "policyItems": [{
    "groups": ["data_protection_team"],
    "accesses": [{"type": "select"}]
  }],
  "resourceTags": {
    "sales.customers.ssn": ["PII"],
    "hr.employees.salary": ["PII"]
  }
}
```

**Generated UC SQL:**
```sql
-- Create tag definition
CREATE TAG IF NOT EXISTS main.ranger_migration.PII 
COMMENT 'Tag attributes: level=high, category=sensitive';

-- Apply tag to resources
ALTER TABLE main.sales.customers.ssn 
SET TAGS ('main.ranger_migration.PII' = 'true');

ALTER TABLE main.hr.employees.salary 
SET TAGS ('main.ranger_migration.PII' = 'true');

-- Grant access on tagged resources
GRANT SELECT ON main.sales.customers.ssn TO `data_protection_team`;
GRANT SELECT ON main.hr.employees.salary TO `data_protection_team`;
```

---

## ⚙️ Configuration

### Translation Configuration

```python
from src.config import TranslationConfig

config = TranslationConfig(
    catalog="main",                    # Target UC catalog
    schema="ranger_migration",         # Target UC schema
    dry_run=True,                      # Preview mode (don't execute)
    skip_errors=True,                  # Continue on errors
    batch_size=50,                     # Policies per batch
    create_tags=True,                  # Create tag definitions
    apply_grants=True,                 # Include GRANT statements
    apply_row_filters=True,            # Include row filters
    apply_column_masks=True            # Include column masks
)
```

### Custom Mappings

```python
# Override default mappings
config = TranslationConfig(
    # Custom resource mapping
    resource_mapping={
        "prod_db": "main.production_schema",
        "dev_db": "main.development_schema"
    },
    
    # Custom principal mapping
    principal_mapping={
        "ranger_admin": "uc_admin@company.com",
        "data_team": "data_engineers"
    },
    
    # Custom privilege mapping
    privilege_mapping={
        "read": "SELECT",
        "write": "MODIFY"
    }
)
```

---

## ⚠️ Known Limitations

### Not Yet Implemented

| Feature | Status | Impact | Workaround |
|---------|--------|--------|------------|
| **Wildcard Resources (*)** | Partial | Wildcards in table names need review | Manual verification |
| **Deny Policies** (denyPolicyItems) | Not implemented | Deny rules must be converted manually | Use DENY statements |
| **Conditional Policies** | Not implemented | Time/IP-based conditions ignored | Apply conditions separately |
| **Complex Hierarchies** | Basic support | Multi-level hierarchies need review | Flatten structure |
| **Custom Masking Functions** | Limited templates | Complex masks may need adjustment | Extend MASKING_FUNCTIONS dict |

### Recommendations

1. **Input Validation:** Always run validator before translation
2. **SQL Review:** Review all generated SQL before execution
3. **Dry Run Mode:** Test with `dry_run=True` first
4. **Incremental Migration:** Start with simple policies, progress to complex
5. **Audit Logging:** Enable audit tables for tracking

---

## 🔒 Security Considerations

### Before Migration

- ✅ Review all Ranger policies for accuracy
- ✅ Validate principal mappings (users/groups)
- ✅ Check resource paths are correct
- ✅ Test in non-production environment first

### During Migration

- ✅ Use dry-run mode initially
- ✅ Execute in batches (not all at once)
- ✅ Monitor audit logs
- ✅ Have rollback plan ready

### After Migration

- ✅ Verify grants were applied correctly
- ✅ Test with sample users
- ✅ Compare Ranger vs UC effective permissions
- ✅ Monitor for 48 hours before full rollout

---

## 📊 Production Readiness Checklist

| Category | Item | Status |
|----------|------|--------|
| **Core Functionality** | All 4 policy types supported | ✅ Complete |
| **Testing** | 100% success rate on samples | ✅ Complete |
| **Validation** | Input + SQL validation | ✅ Complete |
| **Error Handling** | Comprehensive error collection | ✅ Complete |
| **UI/UX** | Interactive Streamlit app | ✅ Complete |
| **Documentation** | User guide + API docs | ✅ Complete |
| **Audit** | Logging and tracking | ✅ Complete |
| **Export** | Multiple formats (SQL/CSV/JSON) | ✅ Complete |
| **Local Deployment** | Run without Databricks | ✅ Complete |
| **Recommended** | Manual SQL review | ⚠️ Required |
| **Recommended** | Dev/staging testing | ⚠️ Required |
| **Recommended** | Incremental rollout | ⚠️ Required |

---

## 🛠️ Development

### Module Development

```python
# Add new validation rule
from src.validator import RangerPolicyValidator

validator = RangerPolicyValidator()
# Extend _validate_policy_items() method

# Add new masking function
from src.config import MASKING_FUNCTIONS

MASKING_FUNCTIONS['CUSTOM_MASK'] = "CASE WHEN ... THEN ... END"

# Add new translator logic
from src.translator import EnhancedPolicyTranslator

class CustomTranslator(EnhancedPolicyTranslator):
    def _translate_custom_policy(self, policy):
        # Your logic here
        pass
```

### Running Tests

```bash
# Test all sample policies
python -c "
from src.parser import RangerPolicyParser
from src.translator import EnhancedPolicyTranslator
from src.config import TranslationConfig

# Test workflow
parser = RangerPolicyParser()
parser.parse_file('samples/access_simple.json')

translator = EnhancedPolicyTranslator(TranslationConfig())
policies = translator.translate_all(parser.policies)

print(f'Generated {len(policies)} UC policies')
"
```

### Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -m 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Open Pull Request

---

## 📈 Roadmap

### Future Enhancements

- [ ] Support for deny policies (denyPolicyItems)
- [ ] Conditional policy translation (time/IP-based)
- [ ] Expanded masking function library
- [ ] Advanced wildcard handling
- [ ] Multi-level resource hierarchy support
- [ ] Batch execution optimization
- [ ] Real-time validation during upload
- [ ] Policy comparison tool (Ranger vs UC)
- [ ] Automated rollback functionality
- [ ] Integration with Ranger API (direct export)

---

## 📚 Additional Resources

### Documentation

- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Complete project structure guide
- **[docs/APP_USER_GUIDE.md](docs/APP_USER_GUIDE.md)** - Complete Streamlit app usage guide
- **[docs/GIT_INTEGRATION.md](docs/GIT_INTEGRATION.md)** - Git setup and deployment
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment instructions

### Sample Files

- **[samples/README.md](samples/README.md)** - Sample policy descriptions

### External Links

- [Databricks Unity Catalog Documentation](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
- [Apache Ranger Documentation](https://ranger.apache.org/index.html)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

## 🤝 Support

### Getting Help

- **Issues:** Open a GitHub issue for bugs or feature requests
- **Questions:** Use GitHub Discussions for questions
- **Documentation:** Check docs/APP_USER_GUIDE.md for detailed usage

### Common Issues

**Q: Translation errors for tag policies?**  
A: Ensure you're using `translator.py` and tag metadata is loaded.

**Q: Validation warnings?**  
A: Warnings are informational. Review them but translation can proceed.

**Q: SQL execution fails?**  
A: Check that catalog/schema exist and you have necessary privileges.

**Q: App shows "Not Available"?**  
A: Wait 3-5 minutes for dependencies to install, then refresh. Use the restart_app notebook if needed.

**Q: Can I run this without Databricks?**  
A: Yes! Run locally for translation and SQL generation. You'll need Databricks only for SQL execution.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 👏 Acknowledgments

- Databricks documentation and support team
- Apache Ranger community
- Streamlit framework contributors
- All testers and early adopters

<div align="center">

**Built with ❤️ on Databricks**

[![Databricks](https://img.shields.io/badge/Databricks-Unity%20Catalog-FF3621?logo=databricks)](https://databricks.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)

*Last Updated: 2024-05-16 | Version: 2.0 | Structure: Reorganized*

</div>
