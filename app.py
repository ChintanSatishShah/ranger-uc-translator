"""
Streamlit UI for Ranger to Unity Catalog Policy Translation Engine.
Main application entry point.
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(__file__))

from parser import RangerPolicyParser, PolicyType
from translator import PolicyTranslator, TagPolicyTranslator, UCPolicy
from applier import PolicyApplier, AuditLogger
from config import TranslationConfig, default_config
import utils

# Page configuration
st.set_page_config(
    page_title="Ranger to UC Migration",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'parser' not in st.session_state:
    st.session_state.parser = None
if 'translator' not in st.session_state:
    st.session_state.translator = None
if 'translated_policies' not in st.session_state:
    st.session_state.translated_policies = []
if 'config' not in st.session_state:
    st.session_state.config = default_config
if 'apply_results' not in st.session_state:
    st.session_state.apply_results = []

# Sidebar navigation
st.sidebar.title("🔐 Ranger → UC Migration")
page = st.sidebar.radio(
    "Navigation",
    ["📤 Upload", "⚙️ Configure", "🔄 Translate", "👁️ Review", "✅ Apply", "📊 Monitor"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Current Status")
if st.session_state.parser:
    summary = st.session_state.parser.get_policy_summary()
    st.sidebar.success(f"✓ {summary['total']} policies loaded")
else:
    st.sidebar.info("No policies loaded")

if st.session_state.translated_policies:
    st.sidebar.success(f"✓ {len(st.session_state.translated_policies)} policies translated")

# ==================== PAGE 1: UPLOAD ====================
if page == "📤 Upload":
    st.title("📤 Upload Ranger Policies")
    st.markdown("Upload Ranger policy JSON files to begin the migration process.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upload Policy File")
        uploaded_file = st.file_uploader(
            "Choose a Ranger policy JSON file",
            type=['json'],
            help="Upload your Ranger policy export file"
        )
        
        if uploaded_file:
            try:
                # Parse uploaded JSON
                content = uploaded_file.read().decode('utf-8')
                policy_data = json.loads(content)
                
                # Create parser and parse
                parser = RangerPolicyParser()
                if parser.parse_json(policy_data):
                    st.session_state.parser = parser
                    st.success(f"✅ Successfully parsed {uploaded_file.name}")
                    
                    # Show summary
                    summary = parser.get_policy_summary()
                    
                    col_a, col_b, col_c, col_d = st.columns(4)
                    col_a.metric("Total Policies", summary['total'])
                    col_b.metric("ACL Policies", summary['access'])
                    col_c.metric("Row Filters", summary['row_filter'])
                    col_d.metric("Column Masks", summary['column_mask'])
                    
                    if parser.parse_errors:
                        st.warning(f"⚠️ {len(parser.parse_errors)} parsing errors")
                        with st.expander("View Errors"):
                            for error in parser.parse_errors:
                                st.error(error)
                else:
                    st.error("❌ Failed to parse policy file")
                    for error in parser.parse_errors:
                        st.error(error)
                        
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON file: {str(e)}")
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
    
    with col2:
        st.subheader("Sample Format")
        st.code("""{
  "policies": [
    {
      "id": 1,
      "name": "sample_policy",
      "service": "hive",
      "resources": {
        "database": {"values": ["default"]},
        "table": {"values": ["customers"]}
      },
      "policyItems": [
        {
          "users": ["user1"],
          "groups": ["analysts"],
          "accesses": [
            {"type": "select", "isAllowed": true}
          ]
        }
      ]
    }
  ]
}""", language="json")
    
    if st.session_state.parser:
        st.markdown("---")
        st.subheader("📋 Loaded Policies")
        
        # Show policies by type
        tab1, tab2, tab3 = st.tabs(["ACL Policies", "Row Filters", "Column Masks"])
        
        with tab1:
            acl_policies = st.session_state.parser.get_policies_by_type(PolicyType.ACCESS)
            if acl_policies:
                for policy in acl_policies[:10]:  # Show first 10
                    with st.expander(f"Policy {policy.id}: {policy.name}"):
                        st.write(f"**Service:** {policy.service}")
                        st.write(f"**Resources:** {', '.join([f'{k}={v.values}' for k,v in policy.resources.items()])}")
                        st.write(f"**Enabled:** {policy.is_enabled}")
            else:
                st.info("No ACL policies found")
        
        with tab2:
            rf_policies = st.session_state.parser.get_policies_by_type(PolicyType.ROW_FILTER)
            if rf_policies:
                for policy in rf_policies[:10]:
                    with st.expander(f"Policy {policy.id}: {policy.name}"):
                        st.write(f"**Service:** {policy.service}")
                        if policy.row_filter_items:
                            for item in policy.row_filter_items:
                                st.code(item.filter_expr, language="sql")
            else:
                st.info("No row filter policies found")
        
        with tab3:
            mask_policies = st.session_state.parser.get_policies_by_type(PolicyType.COLUMN_MASK)
            if mask_policies:
                for policy in mask_policies[:10]:
                    with st.expander(f"Policy {policy.id}: {policy.name}"):
                        st.write(f"**Service:** {policy.service}")
                        if policy.masking_items:
                            for item in policy.masking_items:
                                st.write(f"Mask Type: {item.mask_type}")
            else:
                st.info("No column masking policies found")

# ==================== PAGE 2: CONFIGURE ====================
elif page == "⚙️ Configure":
    st.title("⚙️ Configuration")
    st.markdown("Configure translation settings and custom mappings.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Unity Catalog Settings")
        catalog = st.text_input("Target Catalog", value=st.session_state.config.catalog)
        schema = st.text_input("Target Schema", value=st.session_state.config.schema)
        
        st.subheader("Translation Options")
        dry_run = st.checkbox("Dry Run (preview without applying)", value=True)
        skip_errors = st.checkbox("Continue on errors", value=True)
        create_tags = st.checkbox("Create governed tags", value=True)
        apply_grants = st.checkbox("Apply ACL grants", value=True)
        apply_row_filters = st.checkbox("Apply row filters", value=True)
        apply_column_masks = st.checkbox("Apply column masks", value=True)
        
        if st.button("💾 Save Configuration"):
            st.session_state.config.catalog = catalog
            st.session_state.config.schema = schema
            st.session_state.config.dry_run = dry_run
            st.session_state.config.skip_errors = skip_errors
            st.session_state.config.create_tags = create_tags
            st.session_state.config.apply_grants = apply_grants
            st.session_state.config.apply_row_filters = apply_row_filters
            st.session_state.config.apply_column_masks = apply_column_masks
            st.success("✅ Configuration saved!")
    
    with col2:
        st.subheader("Custom Mappings")
        st.markdown("Define custom mappings for resources and principals.")
        
        # Resource mapping
        st.markdown("**Resource Mapping**")
        st.caption("Map Ranger resource paths to UC catalog.schema.table")
        resource_mapping = st.text_area(
            "Resource Mappings (one per line: ranger_path=uc_path)",
            placeholder="/hive/db/table=main.db.table\n/hive/db2/*=main.db2.*",
            height=100
        )
        
        # Principal mapping
        st.markdown("**Principal Mapping**")
        st.caption("Map Ranger users/groups to UC principals")
        principal_mapping = st.text_area(
            "Principal Mappings (one per line: ranger_principal=uc_principal)",
            placeholder="ranger_user=uc_user@company.com\nranger_group=uc_group",
            height=100
        )
        
        if st.button("📥 Load Mappings"):
            # Parse resource mappings
            if resource_mapping:
                mappings = {}
                for line in resource_mapping.strip().split('\n'):
                    if '=' in line:
                        k, v = line.split('=', 1)
                        mappings[k.strip()] = v.strip()
                st.session_state.config.resource_mapping = mappings
            
            # Parse principal mappings
            if principal_mapping:
                mappings = {}
                for line in principal_mapping.strip().split('\n'):
                    if '=' in line:
                        k, v = line.split('=', 1)
                        mappings[k.strip()] = v.strip()
                st.session_state.config.principal_mapping = mappings
            
            st.success("✅ Mappings loaded!")

# ==================== PAGE 3: TRANSLATE ====================
elif page == "🔄 Translate":
    st.title("🔄 Translate Policies")
    
    if not st.session_state.parser:
        st.warning("⚠️ Please upload Ranger policies first")
        st.stop()
    
    st.markdown("Translate Ranger policies to Unity Catalog format.")
    
    if st.button("🔄 Start Translation", type="primary"):
        with st.spinner("Translating policies..."):
            # Create translator
            translator = PolicyTranslator(st.session_state.config)
            
            # Translate all policies
            policies = st.session_state.parser.policies
            translated = translator.translate_all(policies)
            
            st.session_state.translator = translator
            st.session_state.translated_policies = translated
            
            # Show summary
            summary = translator.get_summary()
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Translated", summary['total_translated'])
            col2.metric("ACL Policies", summary['by_type']['ACL'])
            col3.metric("Row Filters", summary['by_type']['ROW_FILTER'])
            col4.metric("Column Masks", summary['by_type']['COLUMN_MASK'])
            
            col5, col6 = st.columns(2)
            col5.metric("SQL Statements", summary['total_sql_statements'])
            col6.metric("Errors", summary['errors'], delta_color="inverse")
            
            if translator.errors:
                with st.expander("⚠️ View Translation Errors"):
                    for error in translator.errors:
                        st.error(error)
    
    if st.session_state.translated_policies:
        st.markdown("---")
        st.subheader("📝 Translation Results")
        
        # Filter by policy type
        policy_type_filter = st.selectbox(
            "Filter by type",
            ["All", "ACL", "ROW_FILTER", "COLUMN_MASK"]
        )
        
        filtered_policies = st.session_state.translated_policies
        if policy_type_filter != "All":
            filtered_policies = [p for p in filtered_policies if p.policy_type == policy_type_filter]
        
        # Show policies
        for policy in filtered_policies:
            with st.expander(f"{policy.policy_type} - Policy {policy.policy_id}: {policy.description}"):
                st.write(f"**Resource:** `{policy.resource}`")
                st.write(f"**Principals:** {', '.join(policy.principals[:5])}{'...' if len(policy.principals) > 5 else ''}")
                st.write(f"**SQL Statements:** {len(policy.sql_statements)}")
                
                st.code("\n\n".join(policy.sql_statements), language="sql")

# ==================== PAGE 4: REVIEW ====================
elif page == "👁️ Review":
    st.title("👁️ Review Changes")
    
    if not st.session_state.translated_policies:
        st.warning("⚠️ Please translate policies first")
        st.stop()
    
    st.markdown("Review all SQL statements that will be executed.")
    
    # Summary
    total_statements = sum(len(p.sql_statements) for p in st.session_state.translated_policies)
    st.info(f"📊 Total: {len(st.session_state.translated_policies)} policies, {total_statements} SQL statements")
    
    # Export option
    if st.button("📥 Export SQL Script"):
        all_sql = []
        for policy in st.session_state.translated_policies:
            all_sql.append(f"-- Policy {policy.policy_id}: {policy.description}")
            all_sql.extend(policy.sql_statements)
            all_sql.append("")
        
        sql_script = "\n".join(all_sql)
        st.download_button(
            "Download SQL",
            sql_script,
            file_name=f"uc_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
            mime="text/plain"
        )
    
    # Show all SQL
    st.subheader("Complete SQL Script")
    all_sql = []
    for policy in st.session_state.translated_policies:
        all_sql.append(f"-- {policy.policy_type} - Policy {policy.policy_id}")
        all_sql.extend(policy.sql_statements)
        all_sql.append("")
    
    st.code("\n".join(all_sql), language="sql", line_numbers=True)

# ==================== PAGE 5: APPLY ====================
elif page == "✅ Apply":
    st.title("✅ Apply Policies")
    
    if not st.session_state.translated_policies:
        st.warning("⚠️ Please translate policies first")
        st.stop()
    
    st.markdown("Execute translated policies in Unity Catalog.")
    
    # Warning for production
    if not st.session_state.config.dry_run:
        st.warning("⚠️ **WARNING:** Dry run is disabled. Policies will be applied to Unity Catalog!")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        dry_run = st.checkbox("Dry Run (preview only)", value=st.session_state.config.dry_run)
        
        if st.button("▶️ Execute Policies", type="primary"):
            with st.spinner("Applying policies..."):
                try:
                    # Get spark session (will be available in Databricks App)
                    from pyspark.sql import SparkSession
                    spark = SparkSession.builder.getOrCreate()
                    
                    # Create applier
                    applier = PolicyApplier(st.session_state.config, spark)
                    
                    # Apply policies
                    results = applier.apply_policies(st.session_state.translated_policies, dry_run)
                    st.session_state.apply_results = results
                    
                    # Show summary
                    summary = applier.get_summary()
                    
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("Success", summary['success'])
                    col_b.metric("Errors", summary['errors'])
                    col_c.metric("Skipped", summary['skipped'])
                    
                    st.metric("Success Rate", summary['success_rate'])
                    
                    if not dry_run:
                        # Log to audit table
                        applier.log_to_audit_table(results)
                        st.success("✅ Results logged to audit table")
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    with col2:
        st.info("**Note:** Make sure you have appropriate permissions in Unity Catalog to create/modify policies.")
    
    if st.session_state.apply_results:
        st.markdown("---")
        st.subheader("📊 Execution Results")
        
        # Show results table
        df = PolicyApplier(st.session_state.config).generate_report()
        df['apply_results'] = st.session_state.apply_results
        st.dataframe(df, use_container_width=True)
        
        # Show errors
        errors = [r for r in st.session_state.apply_results if r.status == 'error']
        if errors:
            with st.expander(f"❌ View {len(errors)} Errors"):
                for result in errors:
                    st.error(f"**Policy {result.policy_id}:** {result.message}")
                    if result.error_details:
                        st.code(result.error_details)

# ==================== PAGE 6: MONITOR ====================
elif page == "📊 Monitor":
    st.title("📊 Monitor & Audit")
    
    st.markdown("View audit trail and migration history.")
    
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()
        
        tab1, tab2, tab3 = st.tabs(["Translation Log", "Applied Policies", "Errors"])
        
        with tab1:
            st.subheader("Translation History")
            try:
                df = spark.table("main.ranger_migration.v_translation_summary").toPandas()
                st.dataframe(df, use_container_width=True)
            except:
                st.info("No translation history available. Run setup.sql first.")
        
        with tab2:
            st.subheader("Applied Policies")
            try:
                df = spark.table("main.ranger_migration.v_application_summary").toPandas()
                st.dataframe(df, use_container_width=True)
            except:
                st.info("No application history available. Run setup.sql first.")
        
        with tab3:
            st.subheader("Recent Errors")
            try:
                df = spark.table("main.ranger_migration.v_recent_errors").toPandas()
                if len(df) > 0:
                    st.dataframe(df, use_container_width=True)
                else:
                    st.success("✅ No errors!")
            except:
                st.info("No error history available. Run setup.sql first.")
    
    except Exception as e:
        st.error(f"❌ Error accessing audit tables: {str(e)}")
        st.info("Make sure to run setup.sql to create audit tables.")

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("**Ranger to UC Migration Tool**")
st.sidebar.caption("v1.0.0 - MVP")
