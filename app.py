
import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.parser import RangerPolicyParser
from src.translator import EnhancedPolicyTranslator
from src.validator import RangerPolicyValidator
from src.config import TranslationConfig

# Page configuration
st.set_page_config(
    page_title="Ranger → UC Policy Translator",
    page_icon="🔐",
    layout="wide"
)

# Initialize session state variables
if "current_json" not in st.session_state:
    st.session_state.current_json = ""
if "translated_sql" not in st.session_state:
    st.session_state.translated_sql = []
if "validation_results" not in st.session_state:
    st.session_state.validation_results = None
if "translation_stats" not in st.session_state:
    st.session_state.translation_stats = None
# Track previous values to detect changes
if "previous_json" not in st.session_state:
    st.session_state.previous_json = ""
if "previous_sample" not in st.session_state:
    st.session_state.previous_sample = "-- Select a sample --"
if "previous_uploaded_file" not in st.session_state:
    st.session_state.previous_uploaded_file = None


# Helper function to clear right-side outputs
def clear_outputs():
    """Clear all outputs on the right side when new JSON is loaded."""
    st.session_state.translated_sql = []
    st.session_state.validation_results = None
    st.session_state.translation_stats = None

# ==================== HEADER ====================
st.title("🔐 Ranger → UC Policy Translator")
st.markdown("**Translate Apache Ranger policies to Unity Catalog SQL statements**")
st.divider()

# ==================== TWO-COLUMN LAYOUT ====================
left_col, right_col = st.columns([2, 3])

# ==================== LEFT COLUMN: JSON INPUT (40%) ====================
with left_col:
    st.subheader("📄 JSON Input")
    
    # Three tabs for different input methods
    tab1, tab2, tab3 = st.tabs(["📁 Upload", "✏️ Paste", "📋 Sample"])
    
    # Tab 1: Upload JSON file
    with tab1:
        uploaded_file = st.file_uploader(
            "Upload Ranger policy JSON file",
            type=["json"],
            key="file_uploader",
            help="Upload a JSON file containing Ranger policies"
        )
        
        # Detect file change (including switching to/from upload tab with different file)
        current_file_id = uploaded_file.name if uploaded_file is not None else None
        if current_file_id != st.session_state.previous_uploaded_file:
            clear_outputs()
            st.session_state.previous_uploaded_file = current_file_id
        
        if uploaded_file is not None:
            try:
                content = uploaded_file.read().decode("utf-8")
                # Update JSON only if content actually changed
                if content != st.session_state.current_json:
                    st.session_state.current_json = content
                    st.session_state.previous_json = content
                st.success(f"✅ Loaded {uploaded_file.name}")
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
    
    # Tab 2: Paste JSON text
    with tab2:
        pasted_json = st.text_area(
            "Paste JSON content here",
            height=200,
            placeholder="Paste your Ranger policy JSON here...",
            key="paste_area"
        )
        if st.button("Load Pasted JSON", key="load_paste", use_container_width=True):
            if pasted_json.strip():
                clear_outputs()  # Clear when loading pasted JSON
                st.session_state.current_json = pasted_json
                st.session_state.previous_json = pasted_json
                st.success("✅ JSON loaded from paste")
            else:
                st.warning("⚠️ Please paste JSON content first")
    
    # Tab 3: Select from sample dropdown
    with tab3:
        samples_dir = Path("samples")
        if samples_dir.exists():
            sample_files = sorted(list(samples_dir.glob("*.json")))
            if sample_files:
                sample_names = ["-- Select a sample --"] + [f.name for f in sample_files]
                selected_sample = st.selectbox(
                    "Choose a sample policy",
                    sample_names,
                    key="sample_selector"
                )
                
                # Auto-load when dropdown changes (no button needed)
                if selected_sample != st.session_state.previous_sample:
                    clear_outputs()  # Clear immediately on dropdown change
                    st.session_state.previous_sample = selected_sample
                    
                    if selected_sample != "-- Select a sample --":
                        sample_path = samples_dir / selected_sample
                        try:
                            with open(sample_path, "r") as f:
                                new_content = f.read()
                            st.session_state.current_json = new_content
                            st.session_state.previous_json = new_content
                            st.success(f"✅ Loaded {selected_sample}")
                        except Exception as e:
                            st.error(f"❌ Error loading sample: {str(e)}")
            else:
                st.info("ℹ️ No sample files found in samples/ directory")
        else:
            st.info("ℹ️ samples/ directory not found")
    
    st.divider()
    
    # Display current JSON with formatting
    st.markdown("**Current JSON:**")
    display_json = st.session_state.current_json
    
    # Try to pretty-print JSON for better readability
    if display_json:
        try:
            parsed = json.loads(display_json)
            display_json = json.dumps(parsed, indent=2)
        except:
            pass  # Keep original if not valid JSON
    
    json_display = st.text_area(
        "JSON Content",
        value=display_json,
        height=400,
        key="json_display",
        label_visibility="collapsed",
        placeholder="JSON will appear here..."
    )
    
    # Update session state if user manually edits JSON
    if json_display != st.session_state.current_json:
        if json_display != st.session_state.previous_json:
            clear_outputs()  # Clear immediately when JSON content changes
        st.session_state.current_json = json_display
        st.session_state.previous_json = json_display

# ==================== RIGHT COLUMN: SQL OUTPUT & ACTIONS (60%) ====================
with right_col:
    st.subheader("📝 SQL Output & Actions")
    
    # Action buttons in two columns
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        validate_clicked = st.button(
            "✅ Validate", 
            use_container_width=True, 
            type="secondary",
            help="Validate JSON structure and policy format"
        )
    
    with btn_col2:
        translate_clicked = st.button(
            "🔄 Translate", 
            use_container_width=True, 
            type="primary",
            help="Translate policies to Unity Catalog SQL"
        )
    
    st.divider()
    
    # ==================== HANDLE VALIDATE BUTTON ====================
    if validate_clicked:
        if not st.session_state.current_json.strip():
            st.error("❌ No JSON provided. Please upload, paste, or select a sample.")
        else:
            with st.spinner("Validating JSON..."):
                try:
                    # Parse JSON
                    policy_data = json.loads(st.session_state.current_json)
                    
                    # Validate using RangerPolicyValidator
                    validator = RangerPolicyValidator()
                    result = validator.validate_ranger_export(policy_data)
                    
                    # Store validation results
                    st.session_state.validation_results = {
                        "valid": result.is_valid,
                        "errors": result.errors,
                        "warnings": result.warnings
                    }
                    
                    # Display validation result
                    if result.is_valid:
                        st.success(f"✅ Validation passed! Found {len(result.policies)} valid policies")
                        if result.warnings:
                            with st.expander(f"⚠️ View {len(result.warnings)} warnings"):
                                for warning in result.warnings:
                                    st.warning(f"⚠️ {warning}")
                    else:
                        st.error("❌ Validation failed")
                        for error in result.errors:
                            st.error(f"❌ {error}")
                
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON format: {str(e)}")
                    st.session_state.validation_results = {
                        "valid": False,
                        "errors": [f"JSON syntax error: {str(e)}"],
                        "warnings": []
                    }
                except Exception as e:
                    st.error(f"❌ Validation error: {str(e)}")
                    st.session_state.validation_results = {
                        "valid": False,
                        "errors": [str(e)],
                        "warnings": []
                    }
    
    # ==================== HANDLE TRANSLATE BUTTON ====================
    if translate_clicked:
        if not st.session_state.current_json.strip():
            st.error("❌ No JSON provided. Please upload, paste, or select a sample.")
        else:
            with st.spinner("Translating policies..."):
                try:
                    # Parse JSON
                    policy_data = json.loads(st.session_state.current_json)
                    
                    # Parse policies using RangerPolicyParser
                    parser = RangerPolicyParser()
                    parser.parse_json(policy_data)
                    policies = parser.policies
                    
                    # Translate using EnhancedPolicyTranslator
                    config = TranslationConfig(
                        catalog="main",
                        apply_grants=True
                    )
                    translator = EnhancedPolicyTranslator(config)
                    
                    # Set tag metadata if available (for tag-based policies)
                    if 'tagDefinitions' in policy_data and 'resourceTags' in policy_data:
                        tag_definitions = policy_data['tagDefinitions']
                        resource_tags = policy_data['resourceTags']
                        translator.set_tag_metadata(tag_definitions, resource_tags)
                        st.info(f"ℹ️ Detected {len(tag_definitions)} tag definitions and {len(resource_tags)} tagged resources")
                    
                    uc_policies = translator.translate_all(policies)
                    
                    # Extract SQL statements from UCPolicy objects
                    # Each UCPolicy has a sql_statements list that we need to flatten
                    sql_statements = []
                    for uc_policy in uc_policies:
                        sql_statements.extend(uc_policy.sql_statements)
                    
                    # Store results in session state
                    st.session_state.translated_sql = sql_statements
                    st.session_state.translation_stats = {
                        "policies": len(policies),
                        "statements": len(sql_statements)
                    }
                    
                    # Show translator errors if any
                    if translator.errors:
                        st.warning(f"⚠️ Translation completed with {len(translator.errors)} warnings")
                        with st.expander("View Translation Warnings"):
                            for error in translator.errors:
                                st.text(f"• {error}")
                    
                    st.success(
                        f"✅ Translation complete! Generated {len(sql_statements)} SQL statements "
                        f"from {len(policies)} policies."
                    )
                    
                    # Force rerun to update UI immediately
                    st.rerun()
                
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON format: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Translation error: {str(e)}")
                    import traceback
                    with st.expander("🔍 View Error Details"):
                        st.code(traceback.format_exc())
    
    # ==================== DISPLAY VALIDATION RESULTS ====================
    if st.session_state.validation_results:
        results = st.session_state.validation_results
        if results["valid"]:
            st.info("✅ Last validation: Passed")
        else:
            st.error("❌ Last validation: Failed")
            with st.expander("⚠️ View Validation Errors"):
                for error in results["errors"]:
                    st.text(f"• {error}")
    
    # ==================== DISPLAY STATISTICS ====================
    if st.session_state.translation_stats:
        stats = st.session_state.translation_stats
        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            st.metric("📋 Policies Translated", stats["policies"])
        with metric_col2:
            st.metric("📝 SQL Statements", stats["statements"])
        st.divider()
    
    # ==================== DISPLAY SQL OUTPUT IN SINGLE BLOCK ====================
    if st.session_state.translated_sql:
        st.markdown("**Generated SQL Statements:**")
        
        # Combine all SQL statements with proper spacing and separators
        # Add clear separators between statements with comment blocks
        formatted_statements = []
        for i, stmt in enumerate(st.session_state.translated_sql, 1):
            # Ensure proper indentation and formatting for each statement
            stmt_clean = stmt.strip()
            separator = f"-- ============================================================\n-- Statement {i} of {len(st.session_state.translated_sql)}\n-- ============================================================"
            formatted_statements.append(f"{separator}\n{stmt_clean}")
        
        # Join with double newlines for clear separation
        sql_content = "\n\n".join(formatted_statements)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"uc_policies_{timestamp}.sql"
        
        # Download button above code block
        st.download_button(
            label="📥 Download SQL",
            data=sql_content,
            file_name=filename,
            mime="text/plain",
            key="download_sql",
            use_container_width=False,
            help="Download all SQL statements"
        )
        
        # Display SQL in code block with built-in copy button (appears in top-right corner)
        # wrap_lines ensures long lines wrap instead of requiring horizontal scroll
        st.code(sql_content, language="sql", line_numbers=True, wrap_lines=True)
    else:
        st.info("👆 Click **Translate** to generate SQL statements")

# ==================== FOOTER ====================
st.divider()
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.9em;'>" 
    "Ranger to UC Translator v2.0 | Translate Apache Ranger policies to Unity Catalog SQL"
    "</div>",
    unsafe_allow_html=True
)
