# Project Structure

**Version:** 2.0.0  
**Last Updated:** 2024-05-16

## Directory Organization

```
ranger-uc-translator/
├── app.yaml                    # Databricks App configuration
├── app.py                      # Streamlit application (414 lines, single-page UI)
├── requirements.txt            # Python dependencies
├── README.md                   # Main project documentation
├── DEPLOYMENT.md               # Deployment guide
├── .gitignore                  # Git ignore rules
│
├── src/                        # Source code modules
│   ├── __init__.py            # Package initialization (v2.0.0)
│   ├── parser.py              # Ranger policy JSON parser (227 lines)
│   ├── translator.py          # UC policy translator (606 lines, includes EnhancedPolicyTranslator)
│   ├── validator.py           # Policy and SQL validation (307 lines)
│   ├── applier.py             # SQL execution and application (203 lines)
│   ├── config.py              # Configuration management (100 lines)
│   └── utils.py               # Utility functions (219 lines)
│
├── samples/                    # Sample Ranger policy files
│   ├── README.md              # Sample documentation
│   ├── access_simple.json     # Simple access policy (1→1 SQL)
│   ├── access_medium.json     # Medium complexity (1→9 SQL)
│   ├── access_complex.json    # Complex access (1→13 SQL)
│   ├── masking_simple.json    # Simple masking (1→2 SQL)
│   ├── masking_medium.json    # Medium masking (1→6 SQL)
│   ├── masking_complex.json   # Complex masking (1→8 SQL)
│   ├── rowfilter_simple.json  # Simple row filter (1→2 SQL)
│   ├── rowfilter_medium.json  # Medium row filter (1→6 SQL)
│   ├── rowfilter_complex.json # Complex row filter (1→4 SQL)
│   ├── tag_simple.json        # Simple tag-based (1→2 SQL)
│   ├── tag_medium.json        # Medium tag (2→5 SQL)
│   └── tag_complex.json       # Complex tag (2→13 SQL)
│
├── docs/                       # Documentation files
│   ├── APP_USER_GUIDE.md      # Complete user guide (578 lines)
│   ├── GIT_INTEGRATION.md     # Git workflow guide
│   └── PROJECT_STRUCTURE.md   # This file
│
└── tests/                      # Test files and utilities
    ├── setup.sql              # Unity Catalog audit table setup
    ├── test_suite.py          # Comprehensive test suite (268 lines)
    └── quick_test.py          # Quick validation tests (135 lines)
```

## File Statistics

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 414 | Streamlit UI with single-page, 2-column layout |
| `src/parser.py` | 227 | Parse Ranger JSON, extract policies |
| `src/translator.py` | 606 | Translate to UC SQL (all 4 policy types, tag support) |
| `src/validator.py` | 307 | Validate Ranger JSON and UC SQL |
| `src/applier.py` | 203 | Execute SQL against Unity Catalog |
| `src/config.py` | 100 | Configuration classes and mappings |
| `src/utils.py` | 219 | Utility functions (SQL formatting, identifiers) |
| `docs/APP_USER_GUIDE.md` | 578 | Complete app usage guide |
| `tests/test_suite.py` | 268 | Validation and translation tests |
| `tests/quick_test.py` | 135 | Quick smoke tests |

**Total Source Code:** ~2,479 lines

## Module Descriptions

### Core Application

#### app.py (414 lines)
* **Single-page Streamlit UI** with two-column layout
* **Left column (40%):** JSON input with 3 tabs (Upload, Paste, Sample)
* **Right column (60%):** SQL output, validation, translation, download
* **Session state management** for JSON, SQL, results
* **Real-time clearing** when JSON changes
* **Auto-enable download** after translation

### Source Modules (src/)

#### parser.py (227 lines)
* **RangerPolicyParser** class for parsing Ranger JSON exports
* Supports all 4 policy types:
  * Type 0: Access Control (ACL)
  * Type 1: Column Masking
  * Type 2: Row-level Filters
  * Type 3: Tag-based Policies
* Extracts policy items, resources, principals
* Error collection and validation

#### translator.py (606 lines)
* **PolicyTranslator** - Base translator class
* **EnhancedPolicyTranslator** - Full implementation with:
  * Access control → GRANT statements
  * Column masking → CREATE FUNCTION + ALTER COLUMN
  * Row filters → CREATE FUNCTION + ALTER TABLE
  * Tag-based → CREATE TAG + SET TAGS + GRANT
* Handles tag metadata (tagDefinitions, resourceTags)
* Resource mapping and principal translation
* Comprehensive error collection

#### validator.py (307 lines)
* **RangerPolicyValidator** - Validates Ranger JSON structure
  * Required fields checking
  * Policy type validation
  * Data type verification
  * Policy items validation
* **UCSQLValidator** - Validates Unity Catalog SQL
  * Syntax checking
  * Identifier validation
  * Security best practices

#### applier.py (203 lines)
* **PolicyApplier** - Executes SQL against Unity Catalog
* Dry-run mode support
* Batch execution
* Audit logging to Delta tables
* Error handling and rollback

#### config.py (100 lines)
* **TranslationConfig** - Configuration class
  * Catalog and schema settings
  * Dry-run toggle
  * Skip errors option
  * Custom mappings (resources, principals, privileges)
* **MASKING_FUNCTIONS** - Mask type templates
* **PRIVILEGE_MAPPING** - Ranger → UC privilege mapping
* Default configuration object

#### utils.py (219 lines)
* **SQL formatting** functions
* **Identifier validation** and sanitization
* **Function name generation** (row filters, column masks)
* **Tag name handling**
* **Error message formatting**

### Supporting Files

#### samples/ (12 files)
* **12 sample Ranger policies** covering all types and complexities
* **Total:** 15 policies → 118 SQL statements
* **100% translation success rate**
* Each sample includes:
  * Policy JSON in standard Ranger format
  * Comments explaining the policy
  * Expected SQL output count

#### docs/ (3 files)
* **APP_USER_GUIDE.md** (578 lines) - Complete usage guide
  * Quick start (5 minutes)
  * Detailed feature documentation
  * Usage scenarios
  * Troubleshooting
  * Best practices
* **GIT_INTEGRATION.md** - Git workflow and deployment
* **PROJECT_STRUCTURE.md** - This file

#### tests/ (3 files)
* **setup.sql** - Creates audit tables in Unity Catalog
  * `audit_translations` table
  * `audit_executions` table
* **test_suite.py** (268 lines) - Comprehensive test suite
  * Tests all 12 samples
  * Validates translation success
  * Checks SQL statement counts
* **quick_test.py** (135 lines) - Quick validation tests

## Import Structure

All modules are organized under the `src` package:

```python
# Core imports
from src.parser import RangerPolicyParser, PolicyType
from src.translator import EnhancedPolicyTranslator, PolicyTranslator, UCPolicy
from src.validator import RangerPolicyValidator, UCSQLValidator, ValidationLevel
from src.applier import PolicyApplier
from src.config import TranslationConfig, default_config

# Example usage
parser = RangerPolicyParser()
parser.parse_json(policy_data)

translator = EnhancedPolicyTranslator(TranslationConfig(catalog="main"))
uc_policies = translator.translate_all(parser.policies)
```

## Running the Application

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run app locally
streamlit run app.py --server.port 8501

# Access at: http://localhost:8501
```

**Capabilities:**
* ✅ Translation (all 4 policy types)
* ✅ SQL generation and export
* ✅ Validation and error checking
* ❌ SQL execution (requires Databricks)
* ❌ Audit logging (requires Unity Catalog)

### Databricks App
The `app.yaml` configuration allows running as a Databricks App:

```yaml
command: ['streamlit', 'run', 'app.py', '--server.port', '8080', '--server.address', '0.0.0.0']
```

**Deploy:**
1. Navigate to Databricks Apps in workspace
2. Create app from: `/Workspace/Repos/chintsinfo@gmail.com/ranger-uc-translator`
3. App auto-installs dependencies from requirements.txt
4. Access via generated app URL

**Full capabilities:**
* ✅ Translation (all 4 policy types)
* ✅ SQL generation and export
* ✅ Validation and error checking
* ✅ SQL execution (if configured)
* ✅ Audit logging to Delta tables

## Version History

**v2.0.0** (2024-05-16)
* Single-page UI with 2-column layout
* Enhanced download options (Download All + Individual)
* Fixed auto-enable download button
* Complete documentation rewrite
* All 12 samples passing (100% success rate)

**v1.x** (Previous)
* Multi-page UI (deprecated)
* Basic translation functionality

## Architecture Flow

```
User Input (JSON)
       ↓
  parser.py → Parse policies
       ↓
  validator.py → Validate structure
       ↓
  translator.py → Generate UC SQL
       ↓
  validator.py → Validate SQL
       ↓
  app.py → Display results
       ↓
  applier.py → Execute (optional)
       ↓
  Unity Catalog
```

## Testing Strategy

1. **Unit Tests** - Test individual modules
2. **Integration Tests** - Test full workflow
3. **Sample Validation** - All 12 samples must pass
4. **Manual Testing** - UI walkthrough and edge cases

**Current Status:**
* ✅ 12/12 samples passing
* ✅ 118 SQL statements generated
* ✅ 0 critical errors
* ✅ 100% translation success rate

## Development Workflow

1. **Clone repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ranger-uc-translator.git
   cd ranger-uc-translator
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Make changes** to source files in `src/`

4. **Test locally**
   ```bash
   streamlit run app.py
   # Or run test suite:
   python tests/test_suite.py
   ```

5. **Clear Python cache** after code changes
   ```bash
   find . -type d -name __pycache__ -exec rm -rf {} +
   find . -name "*.pyc" -delete
   ```

6. **Commit and push**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin main
   ```

## Production Deployment

See **[DEPLOYMENT.md](../DEPLOYMENT.md)** for complete deployment instructions including:
* Databricks Apps deployment
* Databricks Repos setup
* Unity Catalog configuration
* Audit table setup
* Team permissions

---

**Last Updated:** 2024-05-16 | **Version:** 2.0.0 | **Structure:** Reorganized
