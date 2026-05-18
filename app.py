import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.parser import RangerPolicyParser
from src.translator import EnhancedPolicyTranslator
from src.validator import RangerPolicyValidator
from src.config import TranslationConfig

st.set_page_config(
    page_title="Ranger → UC Policy Translator",
    page_icon="🔐",
    layout="wide"
)

# Initialize session state
if "current_json" not in st.session_state:
    st.session_state.current_json = ""
if "translated_sql" not in st.session_state:
    st.session_state.translated_sql = []
if "validation_results" not in st.session_state:
    st.session_state.validation_results = None
if "translation_stats" not in st.session_state:
    st.session_state.translation_stats = None
if "previous_sample" not in st.session_state:
    st.session_state.previous_sample = "-- Select a sample --"
if "previous_uploaded_file" not in st.session_state:
    st.session_state.previous_uploaded_file = None
if "load_status" not in st.session_state:
    st.session_state.load_status = None


def clear_outputs():
    st.session_state.translated_sql = []
    st.session_state.validation_results = None
    st.session_state.translation_stats = None


def get_samples_directory():
    try:
        script_dir = Path(__file__).parent.resolve()
        samples_dir = script_dir / "samples"
        if samples_dir.exists():
            return samples_dir
    except Exception:
        pass
    
    try:
        cwd = Path.cwd()
        samples_dir = cwd / "samples"
        if samples_dir.exists():
            return samples_dir
    except Exception:
        pass
    
    try:
        script_dir = Path(os.path.dirname(os.path.abspath(__file__))).resolve()
        samples_dir = script_dir / "samples"
        if samples_dir.exists():
            return samples_dir
    except Exception:
        pass
    
    return None


st.title("🔐 Ranger → UC Policy Translator")
st.markdown("**Translate Apache Ranger policies to Unity Catalog SQL statements**")
st.divider()

left_col, right_col = st.columns([2, 3])

with left_col:
    st.subheader("📄 JSON Input")
    
    # Show load status
    if st.session_state.load_status:
        status_type, status_msg = st.session_state.load_status
        if status_type == "success":
            st.success(status_msg)
        elif status_type == "error":
            st.error(status_msg)
        elif status_type == "warning":
            st.warning(status_msg)
        st.session_state.load_status = None
    
    tab1, tab2, tab3 = st.tabs(["📁 Upload", "✏️ Paste", "📋 Sample"])
    
    with tab1:
        uploaded_file = st.file_uploader(
            "Upload Ranger policy JSON file",
            type=["json"],
            key="file_uploader"
        )
        
        current_file_id = uploaded_file.name if uploaded_file is not None else None
        if current_file_id != st.session_state.previous_uploaded_file:
            clear_outputs()
            st.session_state.previous_uploaded_file = current_file_id
        
        if uploaded_file is not None:
            try:
                content = uploaded_file.read().decode("utf-8")
                if content != st.session_state.current_json:
                    st.session_state.current_json = content
                    # IMPORTANT: Force text_area widget to update
                    st.session_state.json_display = content
                    st.session_state.load_status = ("success", f"✅ Loaded {uploaded_file.name}")
                    st.rerun()
            except Exception as e:
                st.session_state.load_status = ("error", f"❌ Error: {str(e)}")
    
    with tab2:
        pasted_json = st.text_area(
            "Paste JSON content here",
            height=200,
            placeholder="Paste your Ranger policy JSON here...",
            key="paste_area"
        )
        if st.button("Load Pasted JSON", key="load_paste", use_container_width=True):
            if pasted_json.strip():
                clear_outputs()
                st.session_state.current_json = pasted_json
                # IMPORTANT: Force text_area widget to update
                st.session_state.json_display = pasted_json
                st.session_state.load_status = ("success", "✅ JSON loaded from paste")
                st.rerun()
            else:
                st.session_state.load_status = ("warning", "⚠️ Please paste JSON content first")
    
    with tab3:
        samples_dir = get_samples_directory()
        
        if samples_dir is not None and samples_dir.exists():
            sample_files = sorted(list(samples_dir.glob("*.json")))
            if sample_files:
                sample_names = ["-- Select a sample --"] + [f.name for f in sample_files]
                selected_sample = st.selectbox(
                    "Choose a sample policy",
                    sample_names,
                    key="sample_selector"
                )
                
                # if selected_sample != st.session_state.previous_sample:
                #     st.session_state.previous_sample = selected_sample
                    
                #     if selected_sample != "-- Select a sample --":
                #         sample_path = samples_dir / selected_sample
                #         try:
                #             with open(sample_path, "r") as f:
                #                 new_content = f.read()
                #             clear_outputs()
                #             st.session_state.current_json = new_content
                #             st.session_state.load_status = ("success", f"✅ Loaded {selected_sample}")
                #             st.rerun()
                #         except Exception as e:
                #             st.session_state.load_status = ("error", f"❌ Error: {str(e)}")

                if st.button(
                    "Load Sample",
                    key="load_sample_btn",
                    use_container_width=True,
                    type="primary"
                ):

                    if selected_sample != "-- Select a sample --":

                        sample_path = samples_dir / selected_sample

                        try:
                            with open(sample_path, "r") as f:
                                new_content = f.read()

                            clear_outputs()

                            st.session_state.current_json = new_content

                            # IMPORTANT: Force text_area widget to update
                            st.session_state.json_display = new_content

                            st.session_state.load_status = (
                                "success",
                                f"✅ Loaded {selected_sample}"
                            )

                            st.rerun()

                        except Exception as e:
                            st.session_state.load_status = (
                                "error",
                                f"❌ Error: {str(e)}"
                            )

            else:
                st.info("ℹ️ No sample files found")
        else:
            st.warning("ℹ️ samples/ directory not found")
    
    st.divider()
    st.markdown("**Current JSON:**")
    
    # Text area bound directly to session state - no intermediate processing
    json_display = st.text_area(
        "JSON Content",
        value=st.session_state.current_json,
        height=400,
        key="json_display",
        label_visibility="collapsed",
        placeholder="JSON will appear here..."
    )
    
    # Only update session state if user manually changed the content
    if json_display != st.session_state.current_json:
        clear_outputs()
        st.session_state.current_json = json_display

with right_col:
    st.subheader("📝 SQL Output & Actions")
    
    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        validate_clicked = st.button("✅ Validate", use_container_width=True, type="secondary")
    
    with btn_col2:
        translate_clicked = st.button("🔄 Translate", use_container_width=True, type="primary")
    
    st.divider()
    
    if validate_clicked:
        if not st.session_state.current_json.strip():
            st.error("❌ No JSON provided")
        else:
            with st.spinner("Validating..."):
                try:
                    policy_data = json.loads(st.session_state.current_json)
                    validator = RangerPolicyValidator()
                    result = validator.validate_ranger_export(policy_data)
                    
                    st.session_state.validation_results = {
                        "valid": result.is_valid,
                        "errors": result.errors,
                        "warnings": result.warnings
                    }
                    
                    if result.is_valid:
                        st.success(f"✅ Validation passed! Found {len(result.policies)} policies")
                        if result.warnings:
                            with st.expander(f"⚠️ {len(result.warnings)} warnings"):
                                for warning in result.warnings:
                                    st.warning(warning)
                    else:
                        st.error("❌ Validation failed")
                        for error in result.errors:
                            st.error(error)
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    if translate_clicked:
        if not st.session_state.current_json.strip():
            st.error("❌ No JSON provided")
        else:
            with st.spinner("Translating..."):
                try:
                    policy_data = json.loads(st.session_state.current_json)
                    parser = RangerPolicyParser()
                    parser.parse_json(policy_data)
                    policies = parser.policies
                    
                    config = TranslationConfig(catalog="main", apply_grants=True)
                    translator = EnhancedPolicyTranslator(config)
                    
                    if 'tagDefinitions' in policy_data and 'resourceTags' in policy_data:
                        translator.set_tag_metadata(policy_data['tagDefinitions'], policy_data['resourceTags'])
                        st.info(f"ℹ️ {len(policy_data['tagDefinitions'])} tag definitions detected")
                    
                    uc_policies = translator.translate_all(policies)
                    sql_statements = []
                    for uc_policy in uc_policies:
                        sql_statements.extend(uc_policy.sql_statements)
                    
                    st.session_state.translated_sql = sql_statements
                    st.session_state.translation_stats = {
                        "policies": len(policies),
                        "statements": len(sql_statements)
                    }
                    
                    if translator.errors:
                        st.warning(f"⚠️ {len(translator.errors)} warnings")
                        with st.expander("View"):
                            for error in translator.errors:
                                st.text(f"• {error}")
                    
                    st.success(f"✅ {len(sql_statements)} SQL statements generated")
                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON: {str(e)}")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    import traceback
                    with st.expander("Details"):
                        st.code(traceback.format_exc())
    
    if st.session_state.validation_results:
        results = st.session_state.validation_results
        st.info("✅ Last validation: Passed" if results["valid"] else "❌ Last validation: Failed")
    
    if st.session_state.translation_stats:
        stats = st.session_state.translation_stats
        m1, m2 = st.columns(2)
        with m1:
            st.metric("📋 Policies", stats["policies"])
        with m2:
            st.metric("📝 SQL Statements", stats["statements"])
        st.divider()
    
    if st.session_state.translated_sql:
        st.markdown("**Generated SQL:**")
        
        formatted = []
        for i, stmt in enumerate(st.session_state.translated_sql, 1):
            sep = f"-- ============================================================\n-- Statement {i} of {len(st.session_state.translated_sql)}\n-- ============================================================"
            formatted.append(f"{sep}\n{stmt.strip()}")
        
        sql_content = "\n\n".join(formatted)
        
        st.download_button(
            label="📥 Download SQL",
            data=sql_content,
            file_name=f"uc_policies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
            mime="text/plain",
            key="download_sql"
        )
        
        st.code(sql_content, language="sql", line_numbers=True)
    else:
        st.info("👆 Click **Translate** to generate SQL")

st.divider()
st.markdown("<div style='text-align: center; color: gray; font-size: 0.9em;'>Ranger to UC Translator v2.0</div>", unsafe_allow_html=True)
