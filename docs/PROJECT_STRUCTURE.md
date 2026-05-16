# Project Structure

## Directory Organization

```
ranger-uc-translator/
├── app.yaml                    # Databricks App configuration
├── app.py                      # Streamlit application entry point
├── requirements.txt            # Python dependencies
├── README.md                   # Main project documentation
├── .gitignore                  # Git ignore rules
│
├── src/                        # Source code modules
│   ├── __init__.py            # Package initialization
│   ├── parser.py              # Ranger policy JSON parser
│   ├── translator.py          # Basic policy translator
│   ├── translator_enhanced.py # Enhanced translator with tag support
│   ├── validator.py           # Policy and SQL validation
│   ├── applier.py             # SQL execution and application
│   ├── config.py              # Configuration management
│   └── utils.py               # Utility functions
│
├── samples/                    # Sample Ranger policy files
│   ├── README.md              # Sample documentation
│   ├── access_simple.json     # Simple access policy
│   ├── access_medium.json     # Medium complexity access
│   ├── access_complex.json    # Complex access policy
│   ├── masking_simple.json    # Simple masking policy
│   ├── masking_medium.json    # Medium masking policy
│   ├── masking_complex.json   # Complex masking policy
│   ├── rowfilter_simple.json  # Simple row filter
│   ├── rowfilter_medium.json  # Medium row filter
│   ├── rowfilter_complex.json # Complex row filter
│   ├── tag_simple.json        # Simple tag-based policy
│   ├── tag_medium.json        # Medium tag policy
│   └── tag_complex.json       # Complex tag policy
│
├── docs/                       # Documentation files
│   ├── APP_USER_GUIDE.md      # User guide for the Streamlit app
│   ├── DEPLOYMENT_GUIDE.md    # Deployment instructions
│   └── GIT_INTEGRATION.md     # Git workflow guide
│
├── tests/                      # Test files and results
│   ├── setup.sql              # UC setup SQL scripts
│
└── backups/                    # Backup/archive files
    ├── app_enhanced.py        # Previous version
    └── app_original_backup.py # Original version
```

## Module Descriptions

### Core Application
* **app.py** - Main Streamlit UI with multi-page navigation
* **app.yaml** - Databricks Apps V2 configuration

### Source Modules (src/)
* **parser.py** - Parses Ranger policy JSON exports
* **translator.py** - Translates policies to UC SQL
* **translator_enhanced.py** - Enhanced translator with tag-based policies
* **validator.py** - Validates Ranger JSON and UC SQL syntax
* **applier.py** - Applies SQL statements to Unity Catalog
* **config.py** - Configuration classes and defaults
* **utils.py** - Shared utility functions

### Supporting Files
* **samples/** - 12 sample Ranger policies covering all types
* **docs/** - User guides and deployment documentation
* **tests/** - Test scripts and results
* **backups/** - Previous versions of the app

## Import Structure

All modules are now organized under the `src` package:

```python
from src.parser import RangerPolicyParser, PolicyType
from src.translator_enhanced import EnhancedPolicyTranslator
from src.validator import RangerPolicyValidator, UCSQLValidator
from src.config import TranslationConfig, default_config
```

## Running the Application

### Local Development
```bash
streamlit run app.py
```

### Databricks App
The app.yaml configuration allows running as a Databricks App:
```yaml
command: ['streamlit', 'run', 'app.py', '--server.port', '8080', '--server.address', '0.0.0.0']
```

## Version
Current version: 2.0.0
