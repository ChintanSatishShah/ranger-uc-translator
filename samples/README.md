# Sample Ranger Policy Files

This directory contains 12 sample Ranger policy JSON files demonstrating all 4 policy types at 3 complexity levels each.

## 📂 File Structure

```
samples/
├── access_simple.json          # Simple ACL policy
├── access_medium.json          # Medium ACL policy
├── access_complex.json         # Complex ACL policy
├── rowfilter_simple.json       # Simple row filter
├── rowfilter_medium.json       # Medium row filter
├── rowfilter_complex.json      # Complex row filter
├── masking_simple.json         # Simple column masking
├── masking_medium.json         # Medium column masking
├── masking_complex.json        # Complex column masking
├── tag_simple.json             # Simple tag-based policy
├── tag_medium.json             # Medium tag-based policy
└── tag_complex.json            # Complex tag-based policy
```

## 🎯 Policy Types Overview

### 1. Access Policies (ACL)
Grant/revoke table and column level permissions.

**Simple** - Single table, single user, SELECT permission
* Resource: `sales.customers`
* User: `analyst1@company.com`
* Permission: SELECT

**Medium** - Multiple tables, users/groups, CRUD operations
* Resources: `sales.customers`, `sales.orders`, `sales.products`
* Users: `sales_manager@company.com`
* Groups: `sales_team`, `data_analysts`
* Permissions: SELECT, UPDATE, CREATE (deny DROP)

**Complex** - Wildcards, exclusions, delegation, deny policies
* Resources: `sales.*`, `marketing.*`, `finance.*` (recursive)
* Multiple policy items with different access levels
* Delegate admin capabilities
* Deny policies for external vendors
* Allow exceptions for compliance team

### 2. Row Filter Policies
Restrict rows visible to users based on SQL expressions.

**Simple** - Single region filter
* Table: `sales.orders`
* Filter: `region = 'WEST'`
* User: `west_manager@company.com`

**Medium** - Multiple filters for different groups
* Table: `sales.transactions`
* Filters:
  - Regional managers: `region IN ('WEST', 'CENTRAL') AND order_date >= '2024-01-01'`
  - Sales analysts: `department = 'SALES' AND status = 'ACTIVE'`
  - Executives: `TRUE` (see all data)

**Complex** - Dynamic filters with user context
* Table: `customer_360.customer_details`
* Filters:
  - VIP account managers: Multi-condition with consent and tier checks
  - Account managers: User context `CURRENT_USER()` with subquery
  - IP range conditions for sensitive data

### 3. Column Masking Policies
Mask sensitive column data based on user/group access.

**Simple** - Basic SSN masking
* Table: `hr.employees`
* Column: `ssn`
* Mask Type: `MASK_SHOW_LAST_4`
* Group: `hr_staff`

**Medium** - Multiple columns with different masks
* Table: `customer_360.customers`
* Columns: `email`, `phone`, `credit_card`
* Mask Types:
  - Support team: `MASK_SHOW_FIRST_4`
  - Analytics: `MASK_HASH`
  - Contractors: `MASK_NULL`

**Complex** - Conditional masks with custom expressions
* Tables: `finance.transactions`, `finance.accounts`
* Columns: `account_number`, `transaction_amount`, `customer_id`, `birth_date`
* Mask Types:
  - Custom CASE expressions for amount thresholds
  - Date masking (show year only)
  - Conditional masking based on age
  - Full access for finance leadership

### 4. Tag-Based Policies (ABAC)
Apply policies based on data classification tags.

**Simple** - Basic PII tag
* Tag: `PII`
* Access: `data_protection_team`, `legal`
* Resources: 3 columns tagged with PII

**Medium** - Multi-level classification
* Tags: `CONFIDENTIAL`, `INTERNAL`, `PUBLIC`
* Different access levels per classification
* Resources tagged by sensitivity level

**Complex** - GDPR/SOX/PCI compliance
* Tags: `PII`, `PII_EU`, `FINANCIAL`, `SENSITIVE`, `SOX`, `PCI_DSS`
* Combines ACL, row filters, and column masking
* Geography-based controls (EU data)
* Regulatory compliance (SOX, PCI-DSS)
* IP range restrictions
* Deny policies for contractors

## 🚀 Usage

### Testing Individual Policies

1. **Upload via UI:**
   ```
   Open the Streamlit app → Upload page → Choose a sample file
   ```

2. **Test Translation:**
   ```
   Upload → Configure → Translate → Review generated SQL
   ```

3. **Apply (Dry Run):**
   ```
   Enable "Dry Run" → Apply → Review results without execution
   ```

### Testing Complete Workflows

**Test Access Policies:**
```bash
# Simple: Basic grant translation
access_simple.json → Should create 1 GRANT statement

# Medium: Multi-table with deny
access_medium.json → Should create grants + deny policies

# Complex: Wildcards and delegation
access_complex.json → Should handle wildcards, create tiered access
```

**Test Row Filters:**
```bash
# Simple: Single filter
rowfilter_simple.json → Should create 1 row filter function

# Medium: Multiple filters
rowfilter_medium.json → Should create 3 row filter functions

# Complex: Dynamic filters
rowfilter_complex.json → Should handle CURRENT_USER(), complex conditions
```

**Test Column Masking:**
```bash
# Simple: Basic masking
masking_simple.json → Should create mask function for SSN

# Medium: Multi-column
masking_medium.json → Should create 3 different mask types

# Complex: Conditional
masking_complex.json → Should create custom mask expressions
```

**Test Tag Policies:**
```bash
# Simple: Basic tags
tag_simple.json → Should create PII tag + apply to resources

# Medium: Classification
tag_medium.json → Should create 3 tags with different access

# Complex: Compliance
tag_complex.json → Should create 6 tags + combined policies
```

## 🔍 Expected Translations

### Access Policy Translation
```sql
-- From access_simple.json
GRANT SELECT ON main.sales.customers TO `analyst1@company.com`;
```

### Row Filter Translation
```sql
-- From rowfilter_simple.json
CREATE OR REPLACE FUNCTION main.sales.rf_orders_101_0(row ROW(orders))
RETURN IF(
  is_account_group_member('west_manager@company.com'),
  region = 'WEST',
  FALSE
);

ALTER TABLE main.sales.orders SET ROW FILTER rf_orders_101_0 ON (`west_manager@company.com`);
```

### Column Masking Translation
```sql
-- From masking_simple.json
CREATE OR REPLACE FUNCTION main.hr.mask_employees_ssn_mask_show_last_4(column_value STRING)
RETURN CASE 
  WHEN is_account_group_member('hr_staff') THEN column_value 
  ELSE CONCAT(REPEAT('X', LENGTH(column_value)-4), RIGHT(column_value, 4)) 
END;

ALTER TABLE main.hr.employees ALTER COLUMN ssn SET MASK mask_employees_ssn_mask_show_last_4;
```

### Tag Policy Translation
```sql
-- From tag_simple.json
CREATE TAG IF NOT EXISTS main.ranger_migration.PII;
ALTER TABLE sales.customers SET TAGS ('main.ranger_migration.PII' = 'true');
GRANT SELECT ON TABLE sales.customers TO `data_protection_team` WHERE TAG('PII') = 'true';
```

## 📝 Notes

* **Resource Mapping:** Default mapping assumes `database` → `catalog.schema` format
* **User Mapping:** Sample users use email format; adjust in config for your environment
* **Catalog/Schema:** Samples use `sales`, `hr`, `finance`, `customer_360` as schemas
* **Groups:** Sample groups should exist in your Unity Catalog workspace
* **Dry Run First:** Always test with dry run enabled before applying to production

## 🐛 Troubleshooting

**Issue: "Could not determine resource"**
* Check that database/table values match expected format
* Verify resource mapping in config

**Issue: "Function already exists"**
* Row filter/mask functions may exist from previous runs
* Drop existing or use CREATE OR REPLACE

**Issue: "Invalid tag name"**
* Ensure tags are valid Unity Catalog identifiers
* Check tag definition format

## 🔗 References

Based on Apache Ranger policy engine test resources:
https://github.com/apache/ranger/tree/master/agents-common/src/test/resources/policyengine

---

**Note:** These are synthetic samples for demonstration. Adapt to your organization's actual policies and naming conventions.
