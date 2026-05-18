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

# ── Theme ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #0f1117; --sur: #1a1d27; --sur2: #22263a; --bdr: #2e3350;
  --acc: #e84a20; --pur: #9c6fde; --grn: #00c896; --amb: #f5a623;
  --red: #e74c3c; --txt: #e8eaf0; --mut: #7a8099;
  --mono: 'JetBrains Mono', 'Fira Code', monospace;
  --sans: 'Inter', system-ui, sans-serif;
}

/* Base */
.stApp { background: var(--bg) !important; color: var(--txt); font-family: var(--sans); }
section[data-testid="stSidebar"] { background: var(--sur) !important; border-right: 1px solid var(--bdr); }
header[data-testid="stHeader"] { background: var(--sur) !important; border-bottom: 1px solid var(--bdr); }
.block-container { padding-top: 1rem !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  background: var(--sur); border-bottom: 1px solid var(--bdr);
  gap: 2px; padding: 4px 6px; border-radius: 8px 8px 0 0;
}
.stTabs [data-baseweb="tab"] {
  background: transparent; color: var(--mut);
  font-size: 12px; font-weight: 600; letter-spacing: .04em;
  border-radius: 6px; padding: 5px 14px; border: none;
}
.stTabs [data-baseweb="tab"]:hover { background: var(--sur2); color: var(--txt); }
.stTabs [aria-selected="true"] { background: var(--acc) !important; color: #fff !important; }
.stTabs [data-baseweb="tab-panel"] { background: var(--bg); border: 1px solid var(--bdr); border-top: none; border-radius: 0 0 8px 8px; padding: 1rem; }

/* Buttons */
.stButton > button[kind="primary"] {
  background: var(--acc) !important; border: none !important; color: #fff !important;
  font-weight: 600; font-size: 12px; border-radius: 6px; transition: opacity .2s;
}
.stButton > button[kind="primary"]:hover { opacity: .85; }
.stButton > button[kind="secondary"] {
  background: var(--sur2) !important; border: 1px solid var(--bdr) !important;
  color: var(--txt) !important; font-size: 12px; border-radius: 6px;
}
.stButton > button[kind="secondary"]:hover { border-color: var(--mut) !important; }
.stDownloadButton > button {
  background: var(--sur2) !important; border: 1px solid var(--bdr) !important;
  color: var(--txt) !important; font-size: 11px; border-radius: 6px;
}

/* Inputs */
.stTextArea textarea, .stTextInput input {
  background: var(--bg) !important; color: var(--txt) !important;
  border: 1px solid var(--bdr) !important; border-radius: 6px;
  font-family: var(--mono); font-size: 12px; line-height: 1.7;
}
.stTextArea textarea:focus, .stTextInput input:focus { border-color: var(--acc) !important; }
.stSelectbox [data-baseweb="select"] > div {
  background: var(--sur2) !important; border-color: var(--bdr) !important; color: var(--txt) !important;
}

/* Metrics */
[data-testid="metric-container"] {
  background: var(--sur) !important; border: 1px solid var(--bdr); border-radius: 8px; padding: 12px 16px;
}
[data-testid="metric-container"] label { color: var(--mut) !important; font-size: 10px !important; text-transform: uppercase; letter-spacing: .08em; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: var(--acc) !important; font-size: 24px !important; font-weight: 700; }

/* Expanders */
details { background: var(--sur) !important; border: 1px solid var(--bdr) !important; border-radius: 6px !important; }
summary { color: var(--mut) !important; font-size: 12px !important; }

/* Code blocks */
.stCode, .stCodeBlock { background: var(--sur) !important; border: 1px solid var(--bdr) !important; border-radius: 6px; }
pre { background: var(--sur) !important; font-family: var(--mono) !important; font-size: 12px !important; }

/* File uploader */
[data-testid="stFileUploaderDropzone"] {
  background: var(--sur2) !important; border: 1.5px dashed var(--bdr) !important; border-radius: 8px !important;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--acc) !important; }

/* Alerts */
.stSuccess { background: rgba(0,200,150,.1) !important; border-left: 3px solid var(--grn) !important; border-radius: 0 6px 6px 0 !important; }
.stError   { background: rgba(231,76,60,.1)  !important; border-left: 3px solid var(--red) !important; border-radius: 0 6px 6px 0 !important; }
.stWarning { background: rgba(245,166,35,.1) !important; border-left: 3px solid var(--amb) !important; border-radius: 0 6px 6px 0 !important; }
.stInfo    { background: rgba(156,111,222,.1)!important; border-left: 3px solid var(--pur) !important; border-radius: 0 6px 6px 0 !important; }

/* Dividers */
hr { border-color: var(--bdr) !important; }

/* Dataframe */
.stDataFrame { border: 1px solid var(--bdr) !important; border-radius: 6px; }

/* Scrollbars */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--bdr); border-radius: 3px; }

/* Custom badges */
.badge-ranger { display:inline-block; font-size:9px; font-weight:700; padding:2px 7px; border-radius:10px; background:rgba(232,74,32,.15); color:var(--acc); }
.badge-uc     { display:inline-block; font-size:9px; font-weight:700; padding:2px 7px; border-radius:10px; background:rgba(156,111,222,.15); color:var(--pur); }
.badge-ok     { display:inline-block; font-size:9px; font-weight:700; padding:2px 7px; border-radius:10px; background:rgba(0,200,150,.15); color:var(--grn); }
.badge-warn   { display:inline-block; font-size:9px; font-weight:700; padding:2px 7px; border-radius:10px; background:rgba(245,166,35,.15); color:var(--amb); }
.badge-err    { display:inline-block; font-size:9px; font-weight:700; padding:2px 7px; border-radius:10px; background:rgba(231,76,60,.15); color:var(--red); }

.map-row { display:flex; align-items:center; gap:8px; padding:5px 10px; border-radius:5px; font-family:var(--mono); font-size:11px; border-bottom: 1px solid var(--bdr); }
.map-row:last-child { border-bottom: none; }
.map-row:hover { background: var(--sur2); }
.map-r { color:var(--acc); background:rgba(232,74,32,.08); padding:2px 6px; border-radius:3px; white-space:nowrap; }
.map-a { color:var(--mut); font-size:10px; }
.map-u { color:var(--pur); background:rgba(156,111,222,.08); padding:2px 6px; border-radius:3px; }
.map-x { color:var(--red); background:rgba(231,76,60,.08); padding:2px 6px; border-radius:3px; }

.section-hdr { font-size:10px; font-weight:700; color:var(--mut); text-transform:uppercase; letter-spacing:.1em; padding:8px 0 4px; margin-top:8px; border-bottom:1px solid var(--bdr); margin-bottom:4px; }
.hist-row { display:flex; align-items:center; gap:10px; padding:8px 10px; border-radius:6px; border:1px solid var(--bdr); margin-bottom:6px; background:var(--sur); font-size:11px; }
.hist-row:hover { background: var(--sur2); }
.hist-ts { color:var(--mut); font-size:10px; font-family:var(--mono); min-width:130px; }
.hist-src { color:var(--acc); font-weight:600; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.hist-path { color:var(--pur); font-family:var(--mono); font-size:10px; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in {
    "current_json": "",
    "translated_sql": [],
    "validation_results": None,
    "translation_stats": None,
    "previous_sample": "-- Select a sample --",
    "previous_uploaded_file": None,
    "load_status": None,
    "source_name": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helpers ────────────────────────────────────────────────────────────────────
def clear_outputs():
    st.session_state.translated_sql = []
    st.session_state.validation_results = None
    st.session_state.translation_stats = None


def get_samples_directory():
    for base in [Path(__file__).parent.resolve(), Path.cwd(),
                 Path(os.path.dirname(os.path.abspath(__file__))).resolve()]:
        d = base / "samples"
        if d.exists():
            return d
    return None


def get_output_directory():
    out = Path(__file__).parent.resolve() / "output"
    out.mkdir(exist_ok=True)
    return out


def save_translation(sql_content: str, source_name: str) -> Path:
    out_dir = get_output_directory()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = source_name.replace(".json", "").replace(" ", "_")[:40] if source_name else "upload"
    fname = f"uc_{slug}_{ts}.sql"
    path = out_dir / fname
    path.write_text(sql_content, encoding="utf-8")
    return path


def load_history():
    hist_path = get_output_directory() / "history.json"
    if hist_path.exists():
        try:
            return json.loads(hist_path.read_text())
        except Exception:
            return []
    return []


def append_history(entry: dict):
    hist_path = get_output_directory() / "history.json"
    history = load_history()
    history.insert(0, entry)
    history = history[:200]  # keep last 200
    hist_path.write_text(json.dumps(history, indent=2), encoding="utf-8")


# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:12px;padding:10px 4px 14px;border-bottom:1px solid #2e3350;margin-bottom:12px">
  <span style="font-size:14px;font-weight:700;letter-spacing:.07em;color:#e84a20;text-transform:uppercase;font-family:'Inter',sans-serif">
    RANGER <span style="color:#e8eaf0">→</span> UC
  </span>
  <span class="badge-ranger">Apache Ranger</span>
  <span style="color:#7a8099;font-size:12px">→</span>
  <span class="badge-uc">Unity Catalog</span>
  <span style="margin-left:auto;font-size:10px;color:#7a8099;font-family:'JetBrains Mono',monospace">v2.1</span>
</div>
""", unsafe_allow_html=True)

# ── Main tabs ──────────────────────────────────────────────────────────────────
tab_trans, tab_map, tab_hist = st.tabs(["🔄 Translator", "📊 Migration Map", "📜 History"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — TRANSLATOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_trans:
    left_col, right_col = st.columns([2, 3])

    with left_col:
        st.markdown('<div class="section-hdr">JSON Input</div>', unsafe_allow_html=True)

        if st.session_state.load_status:
            status_type, status_msg = st.session_state.load_status
            if status_type == "success":
                st.success(status_msg)
            elif status_type == "error":
                st.error(status_msg)
            elif status_type == "warning":
                st.warning(status_msg)
            st.session_state.load_status = None

        inp_tab1, inp_tab2, inp_tab3 = st.tabs(["📁 Upload", "✏️ Paste", "📋 Sample"])

        with inp_tab1:
            uploaded_file = st.file_uploader("Upload Ranger policy JSON", type=["json"], key="file_uploader")
            current_file_id = uploaded_file.name if uploaded_file is not None else None
            if current_file_id != st.session_state.previous_uploaded_file:
                clear_outputs()
                st.session_state.previous_uploaded_file = current_file_id
            if uploaded_file is not None:
                try:
                    content = uploaded_file.read().decode("utf-8")
                    if content != st.session_state.current_json:
                        st.session_state.current_json = content
                        st.session_state.json_display = content
                        st.session_state.source_name = uploaded_file.name
                        st.session_state.load_status = ("success", f"Loaded {uploaded_file.name}")
                        st.rerun()
                except Exception as e:
                    st.session_state.load_status = ("error", f"Error: {e}")

        with inp_tab2:
            pasted = st.text_area("Paste JSON here", height=180,
                                  placeholder="Paste your Ranger policy JSON here...", key="paste_area")
            if st.button("Load Pasted JSON", key="load_paste", use_container_width=True):
                if pasted.strip():
                    clear_outputs()
                    st.session_state.current_json = pasted
                    st.session_state.json_display = pasted
                    st.session_state.source_name = "pasted_input"
                    st.session_state.load_status = ("success", "JSON loaded from paste")
                    st.rerun()
                else:
                    st.session_state.load_status = ("warning", "Please paste JSON content first")

        with inp_tab3:
            samples_dir = get_samples_directory()
            if samples_dir and samples_dir.exists():
                sample_files = sorted(samples_dir.glob("*.json"))
                sample_names = ["-- Select a sample --"] + [f.name for f in sample_files]
                selected = st.selectbox("Choose a sample policy", sample_names, key="sample_selector")
                if st.button("Load Sample", key="load_sample_btn", use_container_width=True, type="primary"):
                    if selected != "-- Select a sample --":
                        try:
                            content = (samples_dir / selected).read_text()
                            clear_outputs()
                            st.session_state.current_json = content
                            st.session_state.json_display = content
                            st.session_state.source_name = selected
                            st.session_state.load_status = ("success", f"Loaded {selected}")
                            st.rerun()
                        except Exception as e:
                            st.session_state.load_status = ("error", f"Error: {e}")
            else:
                st.warning("samples/ directory not found")

        st.markdown('<div class="section-hdr" style="margin-top:12px">Current JSON</div>', unsafe_allow_html=True)
        json_display = st.text_area("JSON Content", value=st.session_state.current_json,
                                    height=380, key="json_display",
                                    label_visibility="collapsed",
                                    placeholder="JSON will appear here...")
        if json_display != st.session_state.current_json:
            clear_outputs()
            st.session_state.current_json = json_display

    with right_col:
        st.markdown('<div class="section-hdr">Actions & SQL Output</div>', unsafe_allow_html=True)

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            validate_clicked = st.button("✅ Validate", use_container_width=True, type="secondary")
        with btn_col2:
            translate_clicked = st.button("🔄 Translate", use_container_width=True, type="primary")

        st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)

        # ── Validate ──
        if validate_clicked:
            if not st.session_state.current_json.strip():
                st.error("No JSON provided")
            else:
                with st.spinner("Validating..."):
                    try:
                        data = json.loads(st.session_state.current_json)
                        result = RangerPolicyValidator().validate_ranger_export(data)
                        st.session_state.validation_results = {
                            "valid": result.is_valid,
                            "errors": result.errors,
                            "warnings": result.warnings,
                        }
                        if result.is_valid:
                            st.success(f"Validation passed — {len(result.policies)} policies found")
                            if result.warnings:
                                with st.expander(f"⚠ {len(result.warnings)} warnings"):
                                    for w in result.warnings:
                                        st.warning(w)
                        else:
                            st.error("Validation failed")
                            for e in result.errors:
                                st.error(e)
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {e}")
                    except Exception as e:
                        st.error(f"Error: {e}")

        # ── Translate ──
        if translate_clicked:
            if not st.session_state.current_json.strip():
                st.error("No JSON provided")
            else:
                with st.spinner("Translating..."):
                    try:
                        data = json.loads(st.session_state.current_json)
                        parser = RangerPolicyParser()
                        parser.parse_json(data)

                        config = TranslationConfig(catalog="main", apply_grants=True)
                        translator = EnhancedPolicyTranslator(config)

                        if 'tagDefinitions' in data and 'resourceTags' in data:
                            translator.set_tag_metadata(data['tagDefinitions'], data['resourceTags'])

                        uc_policies = translator.translate_all(parser.policies)
                        sql_stmts = [s for up in uc_policies for s in up.sql_statements]
                        translatable  = sum(1 for u in uc_policies if u.policy_type != "NOT_TRANSLATABLE")
                        not_trans     = sum(1 for u in uc_policies if u.policy_type == "NOT_TRANSLATABLE")

                        st.session_state.translated_sql = sql_stmts
                        st.session_state.translation_stats = {
                            "policies": len(parser.policies),
                            "statements": len(sql_stmts),
                            "translatable": translatable,
                            "not_translatable": not_trans,
                        }

                        # Save to output folder & history
                        if sql_stmts:
                            formatted = []
                            for i, stmt in enumerate(sql_stmts, 1):
                                sep = (f"-- ============================================================\n"
                                       f"-- Statement {i} of {len(sql_stmts)}\n"
                                       f"-- ============================================================")
                                formatted.append(f"{sep}\n{stmt.strip()}")
                            sql_content = "\n\n".join(formatted)
                            out_path = save_translation(sql_content, st.session_state.source_name)
                            append_history({
                                "timestamp": datetime.now().isoformat(),
                                "source": st.session_state.source_name or "unknown",
                                "policies": len(parser.policies),
                                "sql_statements": len(sql_stmts),
                                "translatable": translatable,
                                "not_translatable": not_trans,
                                "warnings": len(translator.errors),
                                "output_path": str(out_path),
                            })
                            st.session_state.last_output_path = str(out_path)

                        if translator.errors:
                            with st.expander(f"⚠ {len(translator.errors)} translation notes"):
                                for e in translator.errors:
                                    st.markdown(f"<span style='font-size:11px;color:#f5a623'>• {e}</span>",
                                                unsafe_allow_html=True)

                        st.success(f"Translation complete — {len(sql_stmts)} SQL statements generated")

                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {e}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                        import traceback
                        with st.expander("Details"):
                            st.code(traceback.format_exc())

        # ── Status row ──
        if st.session_state.validation_results:
            vr = st.session_state.validation_results
            if vr["valid"]:
                st.markdown('<span class="badge-ok">✓ Validation Passed</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge-err">✗ Validation Failed</span>', unsafe_allow_html=True)

        if st.session_state.translation_stats:
            stats = st.session_state.translation_stats
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Policies", stats["policies"])
            c2.metric("SQL Stmts", stats["statements"])
            c3.metric("Translated", stats.get("translatable", 0))
            c4.metric("Skipped", stats.get("not_translatable", 0))

            if hasattr(st.session_state, "last_output_path") and st.session_state.get("last_output_path"):
                st.markdown(
                    f'<div style="font-size:10px;color:#7a8099;margin:4px 0">📁 Saved to: '
                    f'<span style="color:#9c6fde;font-family:monospace">{st.session_state.last_output_path}</span></div>',
                    unsafe_allow_html=True
                )

            st.markdown("<hr style='margin:8px 0'>", unsafe_allow_html=True)

        # ── SQL output ──
        if st.session_state.translated_sql:
            formatted = []
            for i, stmt in enumerate(st.session_state.translated_sql, 1):
                sep = (f"-- ============================================================\n"
                       f"-- Statement {i} of {len(st.session_state.translated_sql)}\n"
                       f"-- ============================================================")
                formatted.append(f"{sep}\n{stmt.strip()}")
            sql_content = "\n\n".join(formatted)

            st.download_button(
                "📥 Download SQL",
                data=sql_content,
                file_name=f"uc_policies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
                mime="text/plain",
                key="download_sql",
            )
            st.code(sql_content, language="sql", line_numbers=True)
        else:
            st.markdown(
                '<div style="color:#7a8099;font-size:12px;padding:20px 0">Click <b>Translate</b> to generate SQL</div>',
                unsafe_allow_html=True
            )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MIGRATION MAP
# ══════════════════════════════════════════════════════════════════════════════
with tab_map:
    mc1, mc2 = st.columns(2)

    with mc1:
        # ── Resource type mapping ──
        st.markdown('<div class="section-hdr">Resource Type Mapping</div>', unsafe_allow_html=True)
        resource_map = [
            ("database", "→", "SCHEMA catalog.schema", "ok"),
            ("table", "→", "TABLE catalog.schema.table", "ok"),
            ("column", "→", "COLUMN (via masking function)", "ok"),
            ("udf", "→", "FUNCTION catalog.schema.func", "ok"),
            ("path (HDFS/S3)", "→", "EXTERNAL LOCATION", "ok"),
            ("url", "→", "EXTERNAL LOCATION", "ok"),
            ("tag", "→", "Tag-based GRANT (placeholder)", "warn"),
            ("topic (Kafka)", "✗", "No UC equivalent", "err"),
            ("cluster (Kafka)", "✗", "No UC equivalent", "err"),
            ("consumergroup", "✗", "No UC equivalent", "err"),
            ("delegationtoken", "✗", "No UC equivalent", "err"),
            ("entity (Atlas)", "✗", "No UC equivalent", "err"),
            ("entity-type", "✗", "No UC equivalent", "err"),
            ("entity-classification", "✗", "No UC equivalent", "err"),
            ("hiveservice", "✗", "No UC equivalent", "err"),
        ]
        rows_html = ""
        for ranger, arrow, uc, status in resource_map:
            uc_cls = "map-u" if status == "ok" else "badge-warn" if status == "warn" else "map-x"
            rows_html += (
                f'<div class="map-row">'
                f'<span class="map-r">{ranger}</span>'
                f'<span class="map-a">{arrow}</span>'
                f'<span class="{uc_cls}">{uc}</span>'
                f'</div>'
            )
        st.markdown(f'<div style="border:1px solid #2e3350;border-radius:6px;overflow:hidden">{rows_html}</div>',
                    unsafe_allow_html=True)

        # ── Policy type mapping ──
        st.markdown('<div class="section-hdr" style="margin-top:16px">Policy Type Mapping</div>',
                    unsafe_allow_html=True)
        policy_map = [
            ("ACCESS (policyType=0)", "GRANT privilege ON resource TO principal"),
            ("COLUMN_MASK (policyType=1)", "CREATE FUNCTION + ALTER TABLE SET MASK"),
            ("ROW_FILTER (policyType=2)", "CREATE FUNCTION + ALTER TABLE SET ROW FILTER"),
            ("TAG-based ACCESS", "GRANT on tag placeholder (replace with table)"),
            ("denyPolicyItems", "Noted in output — UC uses DENY not supported yet"),
            ("allowExceptions", "Noted in output — exception grants included"),
            ("policyDeltas (incremental)", "Delta policies extracted and translated"),
            ("testCases format", "servicePolicies extracted per test case"),
            ("securityZones", "Zone boundaries noted — not translatable to UC"),
        ]
        rows_html = ""
        for ranger, uc in policy_map:
            rows_html += (
                f'<div class="map-row">'
                f'<span class="map-r">{ranger}</span>'
                f'<span class="map-a">→</span>'
                f'<span class="map-u">{uc}</span>'
                f'</div>'
            )
        st.markdown(f'<div style="border:1px solid #2e3350;border-radius:6px;overflow:hidden">{rows_html}</div>',
                    unsafe_allow_html=True)

    with mc2:
        # ── Privilege mapping ──
        st.markdown('<div class="section-hdr">Privilege Mapping</div>', unsafe_allow_html=True)
        priv_map = [
            ("select", "SELECT"),
            ("read", "SELECT"),
            ("update", "MODIFY"),
            ("write", "MODIFY"),
            ("create", "CREATE"),
            ("drop", "DROP"),
            ("alter", "ALTER"),
            ("all", "ALL PRIVILEGES"),
            ("admin", "ALL PRIVILEGES"),
            ("hive:select", "SELECT (prefix stripped)"),
            ("hive:update", "MODIFY (prefix stripped)"),
            ("read (path)", "READ FILES"),
            ("write (path)", "WRITE FILES"),
            ("execute (path)", "READ FILES"),
            ("publish (Kafka)", "✗ Not translatable"),
            ("consume (Kafka)", "✗ Not translatable"),
            ("entity-read (Atlas)", "✗ Not translatable"),
        ]
        rows_html = ""
        for ranger, uc in priv_map:
            uc_cls = "map-x" if uc.startswith("✗") else "map-u"
            rows_html += (
                f'<div class="map-row">'
                f'<span class="map-r">{ranger}</span>'
                f'<span class="map-a">→</span>'
                f'<span class="{uc_cls}">{uc}</span>'
                f'</div>'
            )
        st.markdown(f'<div style="border:1px solid #2e3350;border-radius:6px;overflow:hidden">{rows_html}</div>',
                    unsafe_allow_html=True)

        # ── Mask type mapping ──
        st.markdown('<div class="section-hdr" style="margin-top:16px">Column Mask Type Mapping</div>',
                    unsafe_allow_html=True)
        mask_map = [
            ("MASK", "'XXXXX'"),
            ("MASK_SHOW_LAST_4", "CONCAT(REPEAT('X', LEN-4), RIGHT(col,4))"),
            ("MASK_SHOW_FIRST_4", "CONCAT(LEFT(col,4), REPEAT('X', LEN-4))"),
            ("MASK_HASH", "SHA2(col, 256)"),
            ("MASK_NULL", "NULL"),
            ("MASK_NONE", "col  (no masking — pass-through)"),
            ("MASK_DATE_SHOW_YEAR", "MAKE_DATE(YEAR(col), 1, 1)"),
            ("SHUFFLE", "SHA2(col, 256)  (approximation)"),
            ("NULL", "NULL"),
            ("CUSTOM", "Custom expression from policy"),
        ]
        rows_html = ""
        for ranger, uc in mask_map:
            rows_html += (
                f'<div class="map-row">'
                f'<span class="map-r">{ranger}</span>'
                f'<span class="map-a">→</span>'
                f'<span class="map-u">{uc}</span>'
                f'</div>'
            )
        st.markdown(f'<div style="border:1px solid #2e3350;border-radius:6px;overflow:hidden">{rows_html}</div>',
                    unsafe_allow_html=True)

    # ── Legend ──
    st.markdown("<hr style='margin:16px 0'>", unsafe_allow_html=True)
    st.markdown(
        '<span class="badge-ranger">Ranger</span>&nbsp;&nbsp;'
        '<span class="badge-uc">Unity Catalog</span>&nbsp;&nbsp;'
        '<span class="badge-ok">Translatable</span>&nbsp;&nbsp;'
        '<span class="badge-warn">Needs manual mapping</span>&nbsp;&nbsp;'
        '<span class="badge-err">Not translatable</span>',
        unsafe_allow_html=True
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — HISTORY
# ══════════════════════════════════════════════════════════════════════════════
with tab_hist:
    history = load_history()

    hdr_col, btn_col = st.columns([3, 1])
    with hdr_col:
        st.markdown('<div class="section-hdr">Translation History</div>', unsafe_allow_html=True)
    with btn_col:
        if st.button("🗑 Clear History", key="clear_hist", type="secondary"):
            hist_path = get_output_directory() / "history.json"
            if hist_path.exists():
                hist_path.unlink()
            st.rerun()

    if not history:
        st.markdown(
            '<div style="color:#7a8099;font-size:12px;padding:20px 0">No translations yet — run a translation to see history here.</div>',
            unsafe_allow_html=True
        )
    else:
        # Summary metrics
        total_policies = sum(h.get("policies", 0) for h in history)
        total_stmts    = sum(h.get("sql_statements", 0) for h in history)
        total_skipped  = sum(h.get("not_translatable", 0) for h in history)

        hc1, hc2, hc3, hc4 = st.columns(4)
        hc1.metric("Runs", len(history))
        hc2.metric("Total Policies", total_policies)
        hc3.metric("Total SQL Stmts", total_stmts)
        hc4.metric("Total Skipped", total_skipped)

        st.markdown("<hr style='margin:10px 0'>", unsafe_allow_html=True)

        # History rows
        for entry in history:
            ts_str = entry.get("timestamp", "")
            try:
                ts_fmt = datetime.fromisoformat(ts_str).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                ts_fmt = ts_str

            source   = entry.get("source", "unknown")
            policies = entry.get("policies", 0)
            stmts    = entry.get("sql_statements", 0)
            skipped  = entry.get("not_translatable", 0)
            warns    = entry.get("warnings", 0)
            out_path = entry.get("output_path", "")
            path_exists = Path(out_path).exists() if out_path else False

            skip_badge = (f'&nbsp;<span class="badge-warn">{skipped} skipped</span>' if skipped else "")
            warn_badge = (f'&nbsp;<span class="badge-warn">{warns} warns</span>' if warns else "")
            path_color = "#9c6fde" if path_exists else "#7a8099"
            path_label = out_path if out_path else "—"

            st.markdown(f"""
            <div class="hist-row">
              <span class="hist-ts">{ts_fmt}</span>
              <span class="hist-src">{source}</span>
              <span class="badge-ok">{policies} policies</span>
              <span class="badge-uc">{stmts} SQL</span>
              {skip_badge}{warn_badge}
              <span style="margin-left:auto;font-size:10px;color:{path_color};font-family:monospace;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{path_label}">
                {"📄 " + Path(out_path).name if out_path else "—"}
              </span>
            </div>
            """, unsafe_allow_html=True)

            # Show SQL preview if file exists
            if path_exists and st.button(f"View SQL", key=f"view_{ts_str}"):
                sql_content = Path(out_path).read_text()
                with st.expander(f"SQL — {Path(out_path).name}", expanded=True):
                    st.markdown(
                        f'<div style="font-size:10px;color:#7a8099;margin-bottom:6px">📁 {out_path}</div>',
                        unsafe_allow_html=True
                    )
                    st.download_button(
                        "📥 Download",
                        data=sql_content,
                        file_name=Path(out_path).name,
                        mime="text/plain",
                        key=f"dl_{ts_str}"
                    )
                    st.code(sql_content, language="sql", line_numbers=True)

        # Full table view
        with st.expander("📋 Full history as table"):
            df = pd.DataFrame(history)
            if not df.empty:
                cols = ["timestamp", "source", "policies", "sql_statements",
                        "translatable", "not_translatable", "warnings", "output_path"]
                df = df[[c for c in cols if c in df.columns]]
                st.dataframe(df, use_container_width=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center;color:#2e3350;font-size:10px;padding:12px 0;font-family:monospace">'
    'Ranger → UC Translator v2.1 &nbsp;|&nbsp; Databricks Unity Catalog Migration Tool'
    '</div>',
    unsafe_allow_html=True
)
