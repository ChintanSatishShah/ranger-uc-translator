# Enhanced Streamlit App - User Guide

## 🚀 Running the App

### Method 1: Databricks Apps (Recommended)
1. Deploy as a Databricks App from your workspace
2. The app will be accessible via a shareable URL
3. Team members can use it self-service

### Method 2: Local Testing
```bash
cd /Workspace/Repos/chintsinfo@gmail.com/ranger-uc-translator
streamlit run app.py
```

## 📱 App Navigation

The enhanced app has **6 main pages**:

### 1. 🏠 Home
**Purpose:** Welcome page with overview and quick start guide

**Features:**
* Overview of supported policy types
* Feature highlights
* Quick start instructions
* Available sample policies list

**Actions:** None (informational only)

---

### 2. 📤 Upload & Validate
**Purpose:** Load and validate Ranger policy files

**Features:**
* **Two input methods:**
  * Upload your own JSON file (drag & drop supported)
  * Select from 12 pre-loaded sample policies
* **Automatic validation:**
  * JSON structure validation
  * Required fields checking
  * Data type validation
  * Policy items validation
* **Validation results:**
  * Parse status
  * Valid/invalid policy counts
  * Detailed error messages
  * Warning indicators

**Sample Policies Available:**
* **Access:** simple, medium, complex
* **Masking:** simple, medium, complex  
* **Row Filter:** simple, medium, complex
* **Tag:** simple, medium, complex

**Typical Flow:**
1. Choose "Sample Policies" tab
2. Select "access_simple.json" from dropdown
3. Click "Load Sample"
4. Review validation results (should be green ✅)
5. Proceed to Translation page

---

### 3. 🔄 Translate
**Purpose:** Convert Ranger policies to Unity Catalog SQL

**Features:**
* **Translation configuration:**
  * Target catalog (default: "main")
  * Target schema (default: "ranger_migration")
  * Dry run mode toggle
  * Skip errors option
* **Policy summary:**
  * Total policies by type
  * Visual breakdown
* **Translation execution:**
  * One-click translation
  * Progress indication
  * Success/error metrics
* **Enhanced translation:**
  * Uses `translator_enhanced.py` (supports tag policies)
  * Automatic tag metadata handling
  * Comprehensive error collection

**Typical Flow:**
1. Review policy summary
2. Adjust configuration if needed (optional)
3. Click "🚀 Start Translation"
4. Wait for completion
5. Review metrics (policies, SQL statements, errors)
6. Proceed to Review page

---

### 4. 👁️ Review & Compare
**Purpose:** Side-by-side comparison of original and translated policies

**Features:**
* **Policy selector dropdown:**
  * Browse all translated policies
  * See policy ID and type
* **Side-by-side view:**
  * **Left:** Original Ranger policy (JSON format)
  * **Right:** Generated UC SQL (syntax highlighted)
* **SQL statement management:**
  * Expandable sections for each SQL statement
  * Copy button for each statement
  * Numbered for easy reference
* **SQL validation:**
  * Automatic syntax checking
  * Error and warning detection
  * Validation status indicators

**Typical Flow:**
1. Select policy from dropdown
2. Review original Ranger policy (left side)
3. Review generated SQL statements (right side)
4. Check validation status
5. Copy SQL if needed
6. Repeat for other policies
7. Proceed to Export when satisfied

---

### 5. 💾 Export Results
**Purpose:** Download translated policies in various formats

**Export Formats:**

#### 📄 SQL Script
* **Content:** All SQL statements in executable format
* **Features:**
  * Header with metadata (date, counts)
  * Organized by policy
  * Comments for each section
  * Ready to execute
* **Use Case:** Direct execution in UC

#### 📊 CSV Report
* **Content:** Detailed policy information in tabular format
* **Columns:**
  * policy_id
  * policy_type
  * resource
  * statement_number
  * sql_statement
  * description
  * principals
* **Use Case:** Analysis, auditing, documentation

#### 📋 JSON Export
* **Content:** Complete policy data in structured JSON
* **Use Case:** Programmatic processing, archival

**Typical Flow:**
1. Review export summary (policy count, SQL count)
2. Choose format(s) to download
3. Click download button
4. Save file with timestamped name
5. Review downloaded file before use

---

### 6. 📊 Statistics
**Purpose:** Analytics and visualizations of translation results

**Features:**
* **Overall metrics:**
  * Total policies
  * Total SQL statements
  * Average SQL per policy
  * Total principals
* **Policy type breakdown:**
  * Count by type
  * SQL statements by type
  * Average SQL per type
* **Interactive visualizations:**
  * Bar charts (using Plotly)
  * Filterable data tables
* **Detailed policy list:**
  * All policies in table format
  * Sortable columns
  * Resource paths
  * Statement counts

**Typical Flow:**
1. View overall metrics
2. Examine policy type distribution
3. Interact with charts
4. Review detailed table
5. Use for reporting/documentation

---

## 🎯 Complete Workflow Example

### Scenario: Migrate Access Policies

**Step 1: Upload (2 minutes)**
1. Go to "📤 Upload & Validate"
2. Click "Sample Policies" tab
3. Select "access_complex.json"
4. Observe validation results:
   * Parse Status: ✅ Success
   * Valid Policies: 1/1
   * Errors: 0
   * Warnings: 0

**Step 2: Translate (1 minute)**
1. Go to "🔄 Translate"
2. Review summary: 1 Access policy
3. Click "🚀 Start Translation"
4. Observe results:
   * UC Policies: 1
   * SQL Statements: 13
   * Errors: 0

**Step 3: Review (5 minutes)**
1. Go to "👁️ Review & Compare"
2. Select the policy from dropdown
3. Left side: Original Ranger JSON
4. Right side: 13 SQL GRANT statements
5. Expand each statement
6. Verify:
   * Resources look correct
   * Principals mapped properly
   * Privileges translated correctly
7. Check validation: ✅ All passed

**Step 4: Export (1 minute)**
1. Go to "💾 Export Results"
2. Download SQL Script for execution
3. Download CSV Report for audit
4. Save files to project folder

**Step 5: Execute (manual)**
1. Open downloaded SQL script
2. Review one more time
3. Execute in Unity Catalog (via SQL editor or API)
4. Verify grants were applied

**Total Time: ~10 minutes** (for complex policy)

---

## 🆚 Key Improvements Over Original App

| Feature | Original App | Enhanced App |
|---------|-------------|--------------|
| **Translation Engine** | Basic translator | EnhancedPolicyTranslator with tag support |
| **Validation** | Parse only | Full input + SQL validation |
| **Sample Policies** | ❌ Not available | ✅ 12 samples built-in |
| **Policy Preview** | Limited | Side-by-side comparison |
| **Export Formats** | 1 format | 3 formats (SQL, CSV, JSON) |
| **Statistics** | Basic | Interactive charts & metrics |
| **Tag Policies** | ❌ Not supported | ✅ Fully supported |
| **UI Design** | Basic | Custom CSS, better layout |
| **Error Handling** | Limited | Comprehensive validation |

---

## 🔧 Configuration Options

### Translation Config (Configure page)

```python
TranslationConfig(
    catalog="main",                    # Target UC catalog
    schema="ranger_migration",         # Target UC schema
    dry_run=True,                      # Preview mode
    skip_errors=True,                  # Continue on errors
    create_tags=True,                  # Create tag definitions
    apply_grants=True,                 # Include GRANT statements
    apply_row_filters=True,            # Include row filters
    apply_column_masks=True            # Include column masks
)
```

### Validation Levels

* **STRICT:** Fail on any error or warning
* **NORMAL:** Fail on errors only (default)
* **PERMISSIVE:** Allow all, just log

---

## 📝 Best Practices

### 1. Start Small
* Begin with simple sample policies
* Understand the flow before using real data
* Test translation before applying to production

### 2. Review Everything
* Always review generated SQL
* Check validation results
* Verify resource mappings
* Confirm principal mappings

### 3. Use Dry Run
* Keep dry_run=True during testing
* Only disable for actual execution
* Use separate dev/staging environment first

### 4. Export for Audit
* Download CSV reports
* Keep JSON backups
* Document all migrations

### 5. Incremental Migration
* Start with access policies (highest success rate)
* Then row filters and masking
* Finally tag-based policies
* Test each batch before next

---

## 🐛 Troubleshooting

### Issue: "No policies loaded" error
**Solution:** Go to Upload & Validate page first, load a policy

### Issue: Validation errors
**Solution:** Check the error details in the expandable section, fix JSON structure

### Issue: Translation errors
**Solution:** Review error messages, might be unsupported policy features

### Issue: Download button not working
**Solution:** Ensure browser allows downloads, check file size

### Issue: App crashes
**Solution:** Check that all modules are present (translator_enhanced.py, validator.py)

---

## 📚 Additional Resources

* **Sample Policies:** `/samples` directory (12 files)
* **Test Results:** `[removed - see live test results in app]`
* **Documentation:** `README.md`, `MVP1_SUMMARY.md`
* **Original App:** `app_original_backup.py` (if needed)

---

## 🎉 Success Indicators

Your migration is successful when:
* ✅ All policies parse without errors
* ✅ Translation success rate = 100%
* ✅ SQL validation passes
* ✅ Generated SQL executes in UC
* ✅ Grants are applied correctly
* ✅ Users have expected access

---

**Version:** 2.0 (Enhanced)  
**Last Updated:** 2026-05-16  
**Branch:** mvp1
