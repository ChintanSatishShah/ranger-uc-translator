# Ranger → UC Policy Translator - App User Guide

> Complete guide for using the Streamlit app to translate Apache Ranger policies to Unity Catalog

**Version:** 2.0  
**Last Updated:** 2024-05-16  
**App Type:** Single-page interface with two-column layout

---

## 🚀 Running the App

### Method 1: Databricks Apps (Recommended)
1. Deploy as a Databricks App from your workspace
2. The app will be accessible via a shareable URL
3. Team members can use it self-service
4. Full functionality: Translation + SQL execution + Audit logging

**Deployment:**
```bash
# Navigate to Databricks Apps in workspace
# Create app from: /Workspace/Repos/chintsinfo@gmail.com/ranger-uc-translator
# Access via generated URL
```

### Method 2: Local Development
```bash
cd /Workspace/Repos/chintsinfo@gmail.com/ranger-uc-translator
pip install -r requirements.txt
streamlit run app.py --server.port 8501
# Access at: http://localhost:8501
```

**Note:** Local mode provides translation and SQL generation only. SQL execution requires Databricks workspace.

---

## 📱 App Interface Overview

The app uses a **single-page, two-column layout** optimized for quick policy translation:

```
┌────────────────────────────────────────────────────────────┐
│            🔐 Ranger → UC Policy Translator                │
├──────────────────────┬─────────────────────────────────────┤
│   LEFT COLUMN (40%)  │   RIGHT COLUMN (60%)                │
│                      │                                     │
│   📄 JSON Input      │   📝 SQL Output & Actions           │
│   ┌──────────────┐   │   ┌─────────┐ ┌─────────┐         │
│   │ 📁 Upload    │   │   │✅Validate│ │🔄Translate│        │
│   │ ✏️  Paste    │   │   └─────────┘ └─────────┘         │
│   │ 📋 Sample    │   │                                     │
│   └──────────────┘   │   ⚙️  Validation Results           │
│                      │   📊 Translation Stats             │
│   📝 JSON Editor     │   💾 Download All SQL              │
│   (Pretty-printed)   │   📝 Individual SQL Statements     │
│   (Editable)         │      • Expandable sections         │
│                      │      • Copy & Download buttons     │
└──────────────────────┴─────────────────────────────────────┘
```

---

## 🎯 Quick Start (5 Minutes)

### Step 1: Load a Sample Policy (30 seconds)

1. **Go to the 📋 Sample tab** in the left column
2. **Select a sample** from the dropdown (e.g., "access_simple.json")
3. **JSON auto-loads** in the editor below

**Available samples:**
* `access_simple.json` - Basic SELECT grant (1 policy → 1 SQL statement)
* `access_medium.json` - Multiple users/groups (1 policy → 9 SQL statements)
* `access_complex.json` - Mixed privileges (1 policy → 13 SQL statements)
* `masking_simple.json` - Single column mask (1 policy → 2 SQL statements)
* `rowfilter_simple.json` - Single filter (1 policy → 2 SQL statements)
* `tag_simple.json` - Basic tag policy (1 policy → 2 SQL statements)
* ...and 6 more complex samples

---

### Step 2: Validate the JSON (10 seconds)

1. **Click ✅ Validate** button in the right column
2. **Review validation results:**
   * ✅ "Validation passed! Found X valid policies"
   * JSON structure, required fields, data types checked
   * Any errors or warnings displayed inline

**What validation checks:**
* ✓ Valid JSON syntax
* ✓ Required policy fields (id, name, policyType)
* ✓ Valid policy types (0=access, 1=masking, 2=row filter, 3=tag)
* ✓ Policy items structure
* ✓ Resource definitions

---

### Step 3: Translate to UC SQL (5 seconds)

1. **Click 🔄 Translate** button in the right column
2. **Wait for translation** (usually < 5 seconds)
3. **Review results:**
   * ✅ "Translation complete! Generated X SQL statements from Y policies"
   * 📋 Policies Translated: X
   * 📝 SQL Statements: X

**Translation engine:**
* Uses `EnhancedPolicyTranslator` with support for all 4 policy types
* Automatically detects and handles tag metadata
* Collects and displays any translation warnings

---

### Step 4: Download SQL Statements (30 seconds)

**Two download options:**

1. **📥 Download All SQL** - Full-width button at top
   * Downloads all statements in a single `.sql` file
   * Timestamped filename: `uc_policies_YYYYMMDD_HHMMSS.sql`

2. **Individual SQL Statements** - Expandable sections below
   * **Click to expand** each statement (first one auto-expanded)
   * **Copy SQL:** Select all (Ctrl+A), copy (Ctrl+C) from text area
   * **📥 Download:** Individual file per statement

**Each expandable section shows:**
* Statement number (e.g., "Statement 1 of 13")
* Syntax-highlighted SQL code
* Copy text area
* Individual download button

---

### Step 5: Execute SQL (Manual)

1. **Open Databricks SQL Editor** or **create a notebook**
2. **Paste or import** the downloaded SQL
3. **Review each statement** before execution
4. **Execute** against your Unity Catalog

**Example SQL:**
```sql
-- Statement 1
GRANT SELECT ON main.sales.customers TO `analyst1@company.com`;

-- Statement 2
GRANT MODIFY ON main.sales.orders TO `sales_manager@company.com`;
```

---

## 📖 Detailed Features

### Left Column: JSON Input

#### 📁 Upload Tab
* **Drag & drop** or click to upload JSON files
* Supports `.json` file extension only
* **Auto-loads** and pretty-prints on upload
* Shows filename confirmation

**Usage:**
1. Switch to "📁 Upload" tab
2. Drag JSON file or click "Browse files"
3. File loads automatically
4. JSON appears in editor below

---

#### ✏️ Paste Tab
* **Text area** for direct JSON input
* **"Load Pasted JSON"** button to confirm
* Ideal for quick testing or small policies
* Copy/paste from any source

**Usage:**
1. Switch to "✏️ Paste" tab
2. Paste JSON content in text area
3. Click "Load Pasted JSON" button
4. JSON appears in editor below

---

#### 📋 Sample Tab
* **Dropdown selector** with 12 pre-loaded samples
* **Auto-loads** on selection (no button needed)
* Organized by policy type and complexity
* Perfect for testing and learning

**Usage:**
1. Switch to "📋 Sample" tab
2. Select sample from dropdown
3. JSON loads automatically
4. Ready to validate and translate

**Sample organization:**
```
access_simple.json       → Basic access control
access_medium.json       → Multiple principals
access_complex.json      → Mixed privileges
masking_simple.json      → Single column mask
masking_medium.json      → Multiple columns
masking_complex.json     → Custom mask types
rowfilter_simple.json    → Single filter
rowfilter_medium.json    → Multiple filters
rowfilter_complex.json   → Complex conditions
tag_simple.json          → Basic tag policy
tag_medium.json          → Multiple tags
tag_complex.json         → Tag + masking
```

---

#### 📝 JSON Editor

**Features:**
* **Pretty-printed** JSON display
* **Editable** text area (400px height)
* **Auto-clears** outputs when JSON changes
* **Real-time** validation on edit

**Manual editing:**
1. Click in JSON editor
2. Make changes
3. Outputs auto-clear
4. Re-validate and translate

---

### Right Column: SQL Output & Actions

#### Action Buttons

**✅ Validate Button:**
* **Purpose:** Validates JSON structure and policy format
* **When to use:** After loading JSON, before translation
* **Result:** Validation status, error/warning messages

**🔄 Translate Button:**
* **Purpose:** Translates policies to Unity Catalog SQL
* **When to use:** After successful validation
* **Result:** SQL statements, statistics, download options
* **Primary action** - styled in blue

---

#### Output Displays

**Validation Results:**
* ✅ "Last validation: Passed" (green info box)
* ❌ "Last validation: Failed" (red error box)
* Expandable error details if validation failed
* Policy counts and warning messages

**Translation Results:**
* ✅ Success message with counts
* ⚠️ Translation warnings (expandable)
* Automatic UI refresh (no extra click needed)

**Statistics:**
* 📋 **Policies Translated** - Count of input policies
* 📝 **SQL Statements** - Count of generated SQL statements

**Download All SQL:**
* Full-width button
* Downloads all statements in single file
* Timestamped filename
* Enabled immediately after translation

**Individual SQL Statements:**
* Expandable sections (first auto-expanded)
* **Format:** "📝 Statement X of Y"
* Each contains:
  * Syntax-highlighted SQL code
  * Copy text area (hidden height, use Ctrl+A + Ctrl+C)
  * Individual download button
* Perfect for reviewing/executing one at a time

---

## 💼 Usage Scenarios

### Scenario 1: Translate Access Policies

**Goal:** Convert Ranger access control policies to UC GRANT statements

**Steps:**
1. Load `access_simple.json` from samples
2. Click ✅ Validate → Should pass
3. Click 🔄 Translate
4. Review generated GRANT statements
5. Download and execute in Unity Catalog

**Expected output:**
```sql
GRANT SELECT ON main.sales.customers TO `analyst1@company.com`;
```

---

### Scenario 2: Translate Column Masking Policies

**Goal:** Convert Ranger column masking to UC mask functions

**Steps:**
1. Load `masking_simple.json` from samples
2. Click ✅ Validate
3. Click 🔄 Translate
4. Review mask function creation SQL
5. Download and execute

**Expected output:**
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

### Scenario 3: Translate Row Filter Policies

**Goal:** Convert Ranger row filters to UC row filter functions

**Steps:**
1. Load `rowfilter_simple.json`
2. Validate and translate
3. Review function + ALTER TABLE statements
4. Execute in Unity Catalog

**Expected output:**
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

### Scenario 4: Translate Tag-Based Policies

**Goal:** Convert Ranger tag policies to UC tags + grants

**Steps:**
1. Load `tag_simple.json`
2. Note: "ℹ️ Detected X tag definitions and Y tagged resources"
3. Validate and translate
4. Review:
   * Tag creation statements
   * Tag application (ALTER TABLE...SET TAGS)
   * Access grants on tagged resources

**Expected output:**
```sql
-- Create tag definition
CREATE TAG IF NOT EXISTS main.ranger_migration.PII 
COMMENT 'Tag attributes: level=high, category=sensitive';

-- Apply tag to resources
ALTER TABLE main.sales.customers 
SET TAGS ('main.ranger_migration.PII' = 'true');

-- Grant access on tagged resources
GRANT SELECT ON main.sales.customers TO `data_protection_team`;
```

---

## 🔧 Advanced Features

### Real-Time Output Clearing

**Behavior:**
* Outputs **auto-clear** when new JSON is loaded
* Prevents confusion from stale results
* Clean slate for each policy translation

**Triggers:**
* Switching between Upload/Paste/Sample tabs
* Loading a different sample
* Manually editing JSON in editor
* Uploading a new file

---

### Progress Indicators

**Validation spinner:**
* Shows "Validating JSON..." during validation
* Disappears when complete
* Prevents duplicate clicks

**Translation spinner:**
* Shows "Translating policies..." during translation
* Disappears when complete
* Auto-refreshes UI with results

---

### Error Handling

**JSON syntax errors:**
```
❌ Invalid JSON format: Expecting property name enclosed in double quotes: line 5 column 3 (char 42)
```

**Validation errors:**
```
❌ Validation failed
❌ Missing required field: policyType
❌ Invalid policy type: 99 (must be 0-3)
```

**Translation warnings:**
```
⚠️ Translation completed with 2 warnings
• Tag-based policy detected. Replace placeholder...
• Could not determine resource for policy...
```

---

## 💡 Best Practices

### 1. Start with Samples
* Always test with samples first
* Understand expected output format
* Learn translation patterns
* Then move to production policies

### 2. Validate Before Translate
* Catch errors early
* Fix JSON issues before translation
* Review warnings carefully
* Validation is quick (~1 second)

### 3. Review Generated SQL
* **Don't blindly execute!**
* Check table names are correct
* Verify user/group names
* Confirm privileges match intent
* Test in dev environment first

### 4. Use Individual Downloads
* Review complex policies one statement at a time
* Execute incrementally
* Easier to debug issues
* Better for documentation

### 5. Export for Audit
* Download all SQL for version control
* Keep timestamped copies
* Document what was executed
* Maintain migration history

---

## 🔍 Troubleshooting

### Issue: "No JSON provided" error

**Cause:** Clicked Validate/Translate with empty editor

**Solution:**
1. Load JSON via Upload, Paste, or Sample tab
2. Verify JSON appears in editor
3. Then click Validate/Translate

---

### Issue: "Invalid JSON format" error

**Cause:** JSON syntax error (missing quote, comma, brace, etc.)

**Solution:**
1. Copy JSON to JSON validator (e.g., jsonlint.com)
2. Fix syntax errors
3. Use Paste tab to load corrected JSON
4. Or edit directly in editor

---

### Issue: "Validation failed" errors

**Cause:** Missing required fields or invalid values

**Solution:**
1. Read error messages carefully
2. Check required fields: id, name, policyType, resources
3. Verify policy type is 0-3
4. Ensure proper nesting of policy items
5. Compare with working samples

---

### Issue: Download button not appearing

**Cause:** Translation not completed or failed

**Solution:**
1. Check for translation errors above
2. Fix any issues and re-translate
3. Button appears immediately after successful translation

---

### Issue: Translation warnings

**Cause:** Non-critical issues that don't block translation

**Solution:**
1. Click "View Translation Warnings" expander
2. Read each warning carefully
3. Note any placeholder values
4. Manually fix placeholders in downloaded SQL
5. Common warnings:
   * Tag-based policies needing table names
   * Wildcard resources needing review
   * Custom expressions needing validation

---

## 📚 Additional Resources

### Documentation
* **[README.md](../README.md)** - Main project documentation
* **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Code organization
* **[GIT_INTEGRATION.md](GIT_INTEGRATION.md)** - Git and deployment
* **[DEPLOYMENT.md](../DEPLOYMENT.md)** - Deployment guide

### Sample Files
* **[samples/README.md](../samples/README.md)** - Sample policy descriptions
* **samples/*.json** - 12 test policies

### External Links
* [Databricks Unity Catalog Documentation](https://docs.databricks.com/en/data-governance/unity-catalog/index.html)
* [Apache Ranger Documentation](https://ranger.apache.org/index.html)
* [Streamlit Documentation](https://docs.streamlit.io/)

---

## 🆘 Support

### Getting Help

**Issues:** Open a GitHub issue for bugs or feature requests  
**Questions:** Use GitHub Discussions for questions  
**Documentation:** This guide + README.md for detailed usage

### Common Questions

**Q: Can I edit the JSON in the app?**  
A: Yes! The JSON editor is fully editable. Make changes and click Validate/Translate again.

**Q: How do I upload multiple policies?**  
A: The app processes one JSON file at a time. For multiple policies, combine them in a single JSON array before upload.

**Q: Can I execute SQL directly from the app?**  
A: Not in the current version. Download SQL and execute manually in Databricks SQL Editor or notebook.

**Q: What if translation fails?**  
A: Check error messages, fix the JSON, and retry. Most failures are due to invalid JSON or missing required fields.

**Q: How do I test tag policies?**  
A: Use `tag_simple.json`, `tag_medium.json`, or `tag_complex.json` samples. The app auto-detects tag metadata.

---

**Version 2.0** | Last Updated: 2024-05-16 | Single-Page UI
