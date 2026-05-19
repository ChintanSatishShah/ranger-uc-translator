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
    page_title="Ranger → UC Translator",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",   # always start expanded
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg:#0f1117;--sur:#1a1d27;--sur2:#22263a;--bdr:#2e3350;
  --acc:#e84a20;--pur:#9c6fde;--grn:#00c896;--amb:#f5a623;
  --red:#e74c3c;--blu:#1e88e5;
  --txt:#e8eaf0;--mut:#7a8099;
  --mono:'JetBrains Mono','Fira Code',monospace;
  --sans:'Inter',system-ui,sans-serif;
}

/* ── Base ── */
.stApp { background: var(--bg) !important; color: var(--txt); font-family: var(--sans); }
.block-container { padding: 0 1rem 1rem !important; max-width: 100% !important; }

/* ── Hide Streamlit's native header bar; we use our own ── */
header[data-testid="stHeader"]  { display: none !important; }
[data-testid="stToolbar"]       { display: none !important; }
#MainMenu                       { display: none !important; }

/* ── Sidebar — always visible, never collapsible ── */
section[data-testid="stSidebar"] {
  background: var(--sur) !important;
  border-right: 1px solid var(--bdr) !important;
  min-width: 240px !important; max-width: 260px !important;
  transform: translateX(0) !important;
  visibility: visible !important;
  display: flex !important;
}
section[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }
[data-testid="stSidebarContent"] { padding: 0 !important; }

/* Hide all collapse/expand toggle buttons */
[data-testid="stSidebarCollapseButton"] { display: none !important; }
[data-testid="collapsedControl"]        { display: none !important; }
[data-testid="stSidebarNavCollapseIcon"]{ display: none !important; }

/* ── Main tabs — push them to look like a header row ── */
.stTabs { margin-top: 0 !important; }
.stTabs [data-baseweb="tab-list"] {
  background: var(--sur);
  border-bottom: 1px solid var(--bdr);
  gap: 2px; padding: 8px 16px;
  justify-content: flex-end;
}
.stTabs [data-baseweb="tab"] {
  background: transparent; color: var(--mut);
  font-size: 12px; font-weight: 600; letter-spacing: .04em;
  border-radius: 6px; padding: 5px 14px; border: none;
}
.stTabs [data-baseweb="tab"]:hover { background: var(--sur2); color: var(--txt); }
.stTabs [aria-selected="true"] { background: var(--acc) !important; color: #fff !important; }
.stTabs [data-baseweb="tab-panel"] {
  background: var(--bg); border: none;
  padding: 0 !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* ── Buttons ── */
.stButton > button {
  background: var(--sur2) !important; border: 1px solid var(--bdr) !important;
  color: var(--txt) !important; font-size: 12px; border-radius: 6px;
  font-family: var(--sans); font-weight: 500;
}
.stButton > button:hover { border-color: var(--mut) !important; }
.stButton > button[kind="primary"] {
  background: var(--acc) !important; border-color: var(--acc) !important;
  color: #fff !important; font-weight: 600;
}
.stButton > button[kind="primary"]:hover { opacity: .85; }
.stDownloadButton > button {
  background: var(--sur2) !important; border: 1px solid var(--bdr) !important;
  color: var(--txt) !important; font-size: 11px; border-radius: 6px;
}

/* ── Inputs ── */
.stTextArea textarea, .stTextInput input {
  background: var(--bg) !important; color: var(--txt) !important;
  border: 1px solid var(--bdr) !important; border-radius: 6px;
  font-family: var(--mono); font-size: 12px; line-height: 1.7;
}
.stTextArea textarea:focus, .stTextInput input:focus { border-color: var(--acc) !important; box-shadow: none !important; }
.stSelectbox [data-baseweb="select"] > div {
  background: var(--sur2) !important; border-color: var(--bdr) !important;
  color: var(--txt) !important; border-radius: 6px;
}
[data-baseweb="popover"] { background: var(--sur2) !important; border: 1px solid var(--bdr) !important; }
[data-baseweb="menu"] { background: var(--sur2) !important; }
[role="option"] { color: var(--txt) !important; }
[role="option"]:hover { background: var(--bdr) !important; }

/* ── File uploader — styled like index.html drag zone ── */
[data-testid="stFileUploaderDropzone"] {
  background: var(--sur2) !important;
  border: 1.5px dashed var(--bdr) !important;
  border-radius: 8px !important;
  padding: 14px 10px !important;
  text-align: center !important;
  cursor: pointer !important;
  transition: border-color .2s, background .2s !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
  border-color: var(--acc) !important;
  background: rgba(232,74,32,.06) !important;
}
[data-testid="stFileUploaderDropzone"] p {
  color: var(--mut) !important;
  font-size: 11px !important;
  line-height: 1.5 !important;
}
/* "Browse files" button inside uploader */
[data-testid="stFileUploaderDropzone"] button {
  background: transparent !important;
  border: 1px solid var(--bdr) !important;
  color: var(--acc) !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  border-radius: 5px !important;
  padding: 4px 12px !important;
  cursor: pointer !important;
}
[data-testid="stFileUploaderDropzone"] button:hover {
  border-color: var(--acc) !important;
  background: rgba(232,74,32,.08) !important;
}
[data-testid="stFileUploaderDropzone"] small {
  color: var(--mut) !important;
  font-size: 10px !important;
}

/* ── Metrics ── */
[data-testid="metric-container"] {
  background: var(--sur) !important; border: 1px solid var(--bdr);
  border-radius: 8px; padding: 10px 14px;
}
[data-testid="metric-container"] label { color: var(--mut) !important; font-size: 10px !important; text-transform: uppercase; letter-spacing: .08em; }
[data-testid="stMetricValue"] { color: var(--acc) !important; font-size: 22px !important; font-weight: 700; }

/* ── Expanders ── */
details { background: var(--sur) !important; border: 1px solid var(--bdr) !important; border-radius: 6px !important; }
summary { color: var(--mut) !important; font-size: 12px !important; }

/* ── Code ── */
.stCode, .stCodeBlock, pre { background: var(--sur) !important; border: 1px solid var(--bdr) !important; border-radius: 6px; }
pre { font-family: var(--mono) !important; font-size: 12px !important; }

/* ── Alerts ── */
.stSuccess { background: rgba(0,200,150,.08) !important; border-left: 3px solid var(--grn) !important; border-radius: 0 6px 6px 0 !important; }
.stError   { background: rgba(231,76,60,.08)  !important; border-left: 3px solid var(--red) !important; border-radius: 0 6px 6px 0 !important; }
.stWarning { background: rgba(245,166,35,.08) !important; border-left: 3px solid var(--amb) !important; border-radius: 0 6px 6px 0 !important; }
.stInfo    { background: rgba(156,111,222,.08)!important; border-left: 3px solid var(--pur) !important; border-radius: 0 6px 6px 0 !important; }
div[data-testid="stAlert"] p { font-size: 12px !important; }

/* ── Dividers ── */
hr { border-color: var(--bdr) !important; margin: 8px 0 !important; }

/* ── DataFrame ── */
.stDataFrame { border: 1px solid var(--bdr) !important; border-radius: 6px; }
.stDataFrame th { background: var(--sur) !important; color: var(--mut) !important; font-size: 10px !important; text-transform: uppercase; letter-spacing: .06em; }

/* ── Scrollbars ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--bdr); border-radius: 3px; }

/* ── Custom component classes ── */
.app-header {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px 10px;
  background: var(--sur);
  border-bottom: 1px solid var(--bdr);
  margin-bottom: 0;
}
.logo { font-size: 13px; font-weight: 700; letter-spacing: .07em; color: var(--acc); text-transform: uppercase; font-family: var(--sans); }
.logo span { color: var(--txt); }
.hbadge { font-size: 10px; padding: 2px 8px; border-radius: 10px; background: rgba(156,111,222,.15); color: var(--pur); font-weight: 600; }

.slbl { font-size: 10px; font-weight: 600; color: var(--mut); letter-spacing: .1em; text-transform: uppercase; padding: 10px 14px 6px; }

.badge { display: inline-block; font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 10px; }
.badge-r  { background: rgba(232,74,32,.15);  color: var(--acc); }
.badge-u  { background: rgba(156,111,222,.15); color: var(--pur); }
.badge-ok { background: rgba(0,200,150,.15);  color: var(--grn); }
.badge-w  { background: rgba(245,166,35,.15); color: var(--amb); }
.badge-e  { background: rgba(231,76,60,.15);  color: var(--red); }

.pane-hdr {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 12px; background: var(--sur);
  border: 1px solid var(--bdr); border-radius: 6px 6px 0 0;
  font-size: 10px; font-weight: 600; color: var(--mut);
  text-transform: uppercase; letter-spacing: .06em;
  margin-bottom: -1px;
}
.pane-hdr .pbadge { font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 8px; }
.pb-r { background: rgba(232,74,32,.15); color: var(--acc); }
.pb-u { background: rgba(156,111,222,.15); color: var(--pur); }

.bar {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 12px; background: var(--sur);
  border: 1px solid var(--bdr); border-radius: 0 0 6px 6px;
  border-top: none; font-size: 10px; color: var(--mut);
  margin-top: -1px;
}
.dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.dot-ok { background: var(--grn); }
.dot-warn { background: var(--amb); }
.dot-err { background: var(--red); }

.section-hdr {
  font-size: 10px; font-weight: 700; color: var(--mut);
  text-transform: uppercase; letter-spacing: .1em;
  padding: 6px 0 4px; border-bottom: 1px solid var(--bdr); margin-bottom: 6px;
}

.map-row {
  display: flex; align-items: baseline; gap: 8px;
  padding: 4px 8px; border-radius: 4px;
  font-family: var(--mono); font-size: 10px;
  border-bottom: 1px solid rgba(46,51,80,.6);
}
.map-row:last-child { border-bottom: none; }
.map-row:hover { background: var(--sur2); }
.map-r { color: var(--acc); background: rgba(232,74,32,.08); padding: 1px 5px; border-radius: 3px; white-space: nowrap; flex-shrink: 0; }
.map-a { color: var(--mut); font-size: 9px; flex-shrink: 0; }
.map-u { color: var(--pur); background: rgba(156,111,222,.08); padding: 1px 5px; border-radius: 3px; }
.map-x { color: var(--red); background: rgba(231,76,60,.08); padding: 1px 5px; border-radius: 3px; }
.map-w { color: var(--amb); background: rgba(245,166,35,.08); padding: 1px 5px; border-radius: 3px; }

.map-section {
  border: 1px solid var(--bdr); border-radius: 6px; overflow: hidden; margin-bottom: 12px;
}
.map-section-hdr {
  font-size: 9px; font-weight: 700; color: var(--mut);
  text-transform: uppercase; letter-spacing: .1em;
  padding: 6px 10px; background: var(--sur);
  border-bottom: 1px solid var(--bdr);
}

.limit-box {
  border: 1px solid rgba(245,166,35,.3); border-radius: 8px;
  background: rgba(245,166,35,.05); padding: 12px 16px; margin-bottom: 10px;
}
.limit-box h4 { font-size: 11px; font-weight: 700; color: var(--amb); margin-bottom: 8px; text-transform: uppercase; letter-spacing: .06em; }
.limit-box ul { margin: 0; padding-left: 16px; }
.limit-box li { font-size: 11px; color: var(--txt); line-height: 1.8; font-family: var(--sans); }
.limit-box li span { color: var(--mut); font-family: var(--mono); font-size: 10px; }

.cant-box {
  border: 1px solid rgba(231,76,60,.3); border-radius: 8px;
  background: rgba(231,76,60,.04); padding: 12px 16px; margin-bottom: 10px;
}
.cant-box h4 { font-size: 11px; font-weight: 700; color: var(--red); margin-bottom: 8px; text-transform: uppercase; letter-spacing: .06em; }
.cant-box ul { margin: 0; padding-left: 16px; }
.cant-box li { font-size: 11px; color: var(--txt); line-height: 1.8; }
.cant-box li code { font-family: var(--mono); font-size: 10px; color: var(--mut); background: var(--sur2); padding: 1px 4px; border-radius: 3px; }

.hist-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: 6px;
  border: 1px solid var(--bdr); margin-bottom: 6px;
  background: var(--sur); font-size: 13px;
}
.hist-row:hover { background: var(--sur2); }
.hist-ts { color: var(--mut); font-size: 12px; font-family: var(--mono); min-width: 145px; flex-shrink: 0; }
.hist-src { color: var(--acc); font-weight: 600; font-size: 13px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hist-path { color: var(--pur); font-family: var(--mono); font-size: 11px; }

.fi-row {
  display: flex; align-items: center; gap: 7px;
  padding: 6px 8px; border-radius: 5px; font-size: 11px;
  border: 1px solid transparent; margin-bottom: 2px;
  cursor: default;
}
.fi-row:hover { background: var(--sur2); }
.fi-icon {
  width: 20px; height: 20px; border-radius: 3px;
  display: flex; align-items: center; justify-content: center;
  font-size: 8px; font-weight: 700; flex-shrink: 0;
  background: rgba(232,74,32,.15); color: var(--acc);
}
.fi-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--txt); }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in {
    "current_json": "",
    "translated_sql": [],
    "validation_results": None,
    "translation_stats": None,
    "previous_uploaded_file": None,
    "load_status": None,
    "source_name": "",
    "last_output_path": "",
    "loaded_files": [],   # list of {name, content}
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helpers ────────────────────────────────────────────────────────────────────
def clear_outputs():
    st.session_state.translated_sql = []
    st.session_state.validation_results = None
    st.session_state.translation_stats = None


def get_samples_dir():
    for base in [Path(__file__).parent.resolve(), Path.cwd()]:
        d = base / "samples"
        if d.exists():
            return d
    return None


def get_output_dir():
    out = Path(__file__).parent.resolve() / "output"
    out.mkdir(exist_ok=True)
    return out


def get_input_dir():
    inp = Path(__file__).parent.resolve() / "input"
    inp.mkdir(exist_ok=True)
    return inp


def save_input(json_str: str, source_name: str, is_sample: bool = False) -> str:
    """Save input JSON to input/. Sample files point to samples/ directly (no copy)."""
    if is_sample:
        samples_dir = get_samples_dir()
        if samples_dir:
            p = samples_dir / source_name
            if p.exists():
                return str(p)
    inp_dir = get_input_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = source_name.replace(".json", "").replace(" ", "_")[:40] if source_name else "upload"
    # Prefix: pasted_input_ for paste, otherwise use slug directly (uploaded filename)
    if source_name == "pasted_input":
        fname = f"pasted_input_{ts}.json"
    else:
        fname = f"{slug}_{ts}.json"
    path = inp_dir / fname
    path.write_text(json_str, encoding="utf-8")
    return str(path)


def save_translation(sql_content: str, source_name: str) -> Path:
    out_dir = get_output_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = source_name.replace(".json", "").replace(" ", "_")[:40] if source_name else "upload"
    path = out_dir / f"uc_{slug}_{ts}.sql"
    path.write_text(sql_content, encoding="utf-8")
    return path


def load_history():
    p = get_output_dir() / "history.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return []
    return []


def append_history(entry: dict):
    p = get_output_dir() / "history.json"
    history = load_history()
    history.insert(0, entry)
    p.write_text(json.dumps(history[:200], indent=2), encoding="utf-8")


def run_translation(json_str: str, source_name: str):
    data = json.loads(json_str)
    parser = RangerPolicyParser()
    parser.parse_json(data)
    config = TranslationConfig(catalog="main", apply_grants=True)
    translator = EnhancedPolicyTranslator(config)
    if "tagDefinitions" in data or "resourceTags" in data:
        translator.set_tag_metadata(
            data.get("tagDefinitions", {}),
            data.get("resourceTags", {})
        )
    # Emit SET TAGS statements first (tag propagation before access grants)
    tag_sql = translator.generate_tag_sql()
    uc_policies = translator.translate_all(parser.policies)
    sql_stmts = tag_sql + [s for up in uc_policies for s in up.sql_statements]
    translatable = sum(1 for u in uc_policies if u.policy_type != "NOT_TRANSLATABLE")
    not_trans    = sum(1 for u in uc_policies if u.policy_type == "NOT_TRANSLATABLE")
    return parser, translator, sql_stmts, translatable, not_trans


def format_sql(stmts):
    parts = []
    for i, stmt in enumerate(stmts, 1):
        parts.append(
            f"-- ============================================================\n"
            f"-- Statement {i} of {len(stmts)}\n"
            f"-- ============================================================\n"
            f"{stmt.strip()}"
        )
    return "\n\n".join(parts)


# ── App header ─────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <div>
    <div class="logo">Ranger <span>→ Unity Catalog</span>
      <span class="hbadge" style="margin-left:8px;vertical-align:middle">Databricks Practice</span>
    </div>
    <div style="font-size:11px;color:var(--mut);margin-top:3px;font-family:var(--sans)">
      Translate Apache Ranger security policies → Databricks Unity Catalog SQL &nbsp;·&nbsp;
      GRANT · EXTERNAL LOCATION · Column Mask · Row Filter
    </div>
  </div>
  <div style="margin-left:auto;font-size:10px;color:var(--mut);font-family:var(--mono);white-space:nowrap">v2.2</div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="slbl">Upload policy</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Browse or drag .json file", type=["json"],
        label_visibility="collapsed", key="file_uploader",
        help="Click to browse or drag and drop a Ranger policy JSON file",
    )

    cur_file_id = uploaded_file.name if uploaded_file else None
    if cur_file_id != st.session_state.previous_uploaded_file:
        clear_outputs()
        st.session_state.previous_uploaded_file = cur_file_id
        if uploaded_file:
            try:
                content = uploaded_file.read().decode("utf-8")
                st.session_state.current_json = content
                st.session_state.json_editor = content   # sync text area widget
                st.session_state.source_name = uploaded_file.name
                # Add to loaded files list
                names = [f["name"] for f in st.session_state.loaded_files]
                if uploaded_file.name not in names:
                    st.session_state.loaded_files.append({"name": uploaded_file.name, "content": content})
                st.session_state.load_status = ("success", f"Loaded {uploaded_file.name}")
            except Exception as e:
                st.session_state.load_status = ("error", str(e))

    st.markdown('<div class="slbl" style="padding-top:6px">Sample policies</div>', unsafe_allow_html=True)
    samples_dir = get_samples_dir()
    sample_files = sorted(samples_dir.glob("*.json")) if samples_dir else []
    sample_names = ["— select sample —"] + [f.name for f in sample_files]
    selected_sample = st.selectbox("", sample_names, key="sample_sel", label_visibility="collapsed")
    if st.button("Load sample", key="load_sample_btn", use_container_width=True, type="primary"):
        if selected_sample != "— select sample —" and samples_dir:
            try:
                content = (samples_dir / selected_sample).read_text()
                clear_outputs()
                st.session_state.current_json = content
                st.session_state.json_editor = content   # sync text area widget
                st.session_state.source_name = selected_sample
                names = [f["name"] for f in st.session_state.loaded_files]
                if selected_sample not in names:
                    st.session_state.loaded_files.append({"name": selected_sample, "content": content})
                st.session_state.load_status = ("success", f"Loaded {selected_sample}")
                st.rerun()
            except Exception as e:
                st.session_state.load_status = ("error", str(e))

    if st.session_state.loaded_files:
        st.markdown('<div class="slbl" style="padding-top:6px">Queued files</div>', unsafe_allow_html=True)
        for f in st.session_state.loaded_files[-8:]:
            is_active = f["name"] == st.session_state.source_name
            border = f"border-color: var(--bdr); background: var(--sur2);" if is_active else ""
            st.markdown(
                f'<div class="fi-row" style="{border}">'
                f'<div class="fi-icon">RG</div>'
                f'<div class="fi-name" title="{f["name"]}">{f["name"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if st.button("Clear list", key="clear_files", use_container_width=True):
            st.session_state.loaded_files = []
            st.rerun()
    else:
        st.markdown(
            '<div style="font-size:11px;color:var(--mut);text-align:center;padding:14px 10px">No files loaded</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<hr>", unsafe_allow_html=True)

    # Paste shortcut in sidebar
    st.markdown('<div class="slbl">Or paste JSON</div>', unsafe_allow_html=True)
    pasted = st.text_area("", height=80, placeholder="Paste JSON here...", key="paste_area", label_visibility="collapsed")
    if st.button("Load pasted JSON", key="load_paste", use_container_width=True):
        if pasted.strip():
            try:
                json.loads(pasted)  # validate
                clear_outputs()
                st.session_state.current_json = pasted
                st.session_state.json_editor = pasted    # sync text area widget
                st.session_state.source_name = "pasted_input"
                st.session_state.load_status = ("success", "JSON loaded from paste")
                st.rerun()
            except json.JSONDecodeError as e:
                st.session_state.load_status = ("error", f"Invalid JSON: {e}")
        else:
            st.session_state.load_status = ("warning", "Nothing pasted")


# ── Main tabs ──────────────────────────────────────────────────────────────────
tab_conv, tab_map, tab_hist = st.tabs(["Converter", "Mapping", "History"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CONVERTER
# ══════════════════════════════════════════════════════════════════════════════
with tab_conv:
    # Status from sidebar actions
    if st.session_state.load_status:
        status_type, status_msg = st.session_state.load_status
        if status_type == "success":
            st.success(status_msg)
        elif status_type == "error":
            st.error(status_msg)
        elif status_type == "warning":
            st.warning(status_msg)
        st.session_state.load_status = None

    left_col, right_col = st.columns([1, 1], gap="small")

    # ── Left pane: Ranger JSON input ──
    with left_col:
        st.markdown("""
        <div class="pane-hdr">
          <span>Ranger policy input</span>
          <span class="pbadge pb-r">RANGER</span>
        </div>
        """, unsafe_allow_html=True)

        json_val = st.text_area(
            "", value=st.session_state.current_json,
            height=520, key="json_editor",
            label_visibility="collapsed",
            placeholder="Paste Ranger policy JSON here, or load from sidebar...",
        )
        if json_val != st.session_state.current_json:
            clear_outputs()
            st.session_state.current_json = json_val

        st.markdown(
            f'<div class="bar"><div class="dot dot-{"ok" if st.session_state.current_json.strip() else "err"}"></div>'
            f'<span>{len(st.session_state.current_json)} chars</span>'
            f'{"&nbsp;&nbsp;<span class=\'badge badge-r\'>" + st.session_state.source_name + "</span>" if st.session_state.source_name else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Right pane: UC SQL output ──
    with right_col:
        st.markdown("""
        <div class="pane-hdr">
          <span>Unity Catalog SQL output</span>
          <span class="pbadge pb-u">UNITY CATALOG</span>
        </div>
        """, unsafe_allow_html=True)

        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            validate_clicked = st.button("✅ Validate", use_container_width=True, key="validate_btn")
        with btn_c2:
            translate_clicked = st.button("⚡ Translate", use_container_width=True, type="primary", key="translate_btn")

        # Validate
        if validate_clicked:
            if not st.session_state.current_json.strip():
                st.error("No JSON loaded")
            else:
                with st.spinner("Validating..."):
                    try:
                        data = json.loads(st.session_state.current_json)
                        result = RangerPolicyValidator().validate_ranger_export(data)
                        st.session_state.validation_results = {
                            "valid": result.is_valid,
                            "errors": result.errors,
                            "warnings": result.warnings,
                            "policies": len(result.policies),
                        }
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {e}")
                    except Exception as e:
                        st.error(f"Error: {e}")

        if st.session_state.validation_results:
            vr = st.session_state.validation_results
            if vr["valid"]:
                st.success(f"Validation passed — {vr['policies']} policies found")
                if vr["warnings"]:
                    with st.expander(f"⚠ {len(vr['warnings'])} warnings"):
                        for w in vr["warnings"]:
                            st.warning(w)
            else:
                st.error("Validation failed")
                for e in vr["errors"]:
                    st.error(e)

        # Translate
        if translate_clicked:
            if not st.session_state.current_json.strip():
                st.error("No JSON loaded")
            else:
                with st.spinner("Translating..."):
                    try:
                        parser, translator, sql_stmts, translatable, not_trans = run_translation(
                            st.session_state.current_json, st.session_state.source_name
                        )
                        st.session_state.translated_sql = sql_stmts
                        st.session_state.translation_stats = {
                            "policies": len(parser.policies),
                            "statements": len(sql_stmts),
                            "translatable": translatable,
                            "not_translatable": not_trans,
                            "warnings": len(translator.errors),
                        }
                        if sql_stmts:
                            out_path = save_translation(format_sql(sql_stmts), st.session_state.source_name)
                            st.session_state.last_output_path = str(out_path)
                            # Save input (skip copy for sample files — point directly)
                            samples_dir = get_samples_dir()
                            is_sample = bool(
                                samples_dir and st.session_state.source_name
                                and (samples_dir / st.session_state.source_name).exists()
                            )
                            inp_path = save_input(
                                st.session_state.current_json,
                                st.session_state.source_name,
                                is_sample=is_sample,
                            )
                            append_history({
                                "timestamp": datetime.now().isoformat(),
                                "source": st.session_state.source_name or "unknown",
                                "policies": len(parser.policies),
                                "sql_statements": len(sql_stmts),
                                "translatable": translatable,
                                "not_translatable": not_trans,
                                "warnings": len(translator.errors),
                                "input_path": inp_path,
                                "output_path": str(out_path),
                            })
                        if translator.errors:
                            with st.expander(f"⚠ {len(translator.errors)} translation notes"):
                                for e in translator.errors:
                                    st.markdown(f'<span style="font-size:11px;color:var(--amb)">• {e}</span>', unsafe_allow_html=True)
                        st.success(f"Translation complete — {len(sql_stmts)} SQL statements")
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {e}")
                    except Exception as e:
                        st.error(f"Error: {e}")
                        import traceback
                        with st.expander("Stack trace"):
                            st.code(traceback.format_exc())

        # Stats row
        if st.session_state.translation_stats:
            stats = st.session_state.translation_stats
            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Policies", stats["policies"])
            sc2.metric("SQL Stmts", stats["statements"])
            sc3.metric("Translated", stats["translatable"])
            sc4.metric("Skipped", stats["not_translatable"])
            if st.session_state.last_output_path:
                st.markdown(
                    f'<div style="font-size:10px;color:var(--mut);margin:4px 0">📁 '
                    f'<span style="color:var(--pur);font-family:var(--mono)">{st.session_state.last_output_path}</span></div>',
                    unsafe_allow_html=True,
                )

        # SQL output area
        if st.session_state.translated_sql:
            sql_content = format_sql(st.session_state.translated_sql)
            # Download button here (below translate button) always renders after translation
            st.download_button(
                "📥 Download SQL",
                data=sql_content,
                file_name=f"uc_{st.session_state.source_name.replace('.json','') or 'output'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
                mime="text/plain",
                use_container_width=True,
                key="dl_btn_below",
            )
            st.code(sql_content, language="sql", line_numbers=True)
        else:
            if st.session_state.current_json.strip():
                hint = "Policy loaded — click <b style='color:var(--acc)'>⚡ Translate</b> to generate SQL."
            else:
                hint = "Select a sample or upload a file, then click <b style='color:var(--acc)'>⚡ Translate</b>."
            st.markdown(f"""
            <div style="font-family:var(--mono);font-size:12px;color:var(--mut);
                        background:var(--bg);border:1px solid var(--bdr);border-radius:0 0 6px 6px;
                        padding:20px 16px;line-height:2;min-height:200px">
              <div style="margin-bottom:14px;font-family:var(--sans);font-size:12px">{hint}</div>
              <span style="color:var(--bdr)">-- STEP 1: External Locations / Storage Credentials</span><br>
              <span style="color:var(--bdr)">-- STEP 2: Schema / Catalog Setup</span><br>
              <span style="color:var(--bdr)">-- STEP 3: GRANT Statements</span><br>
              <span style="color:var(--bdr)">-- STEP 4: Column Masks</span><br>
              <span style="color:var(--bdr)">-- STEP 5: Row Filters</span><br>
              <span style="color:var(--bdr)">-- STEP 6: No-Equivalent Constructs (TODO)</span>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — MAPPING REFERENCE
# ══════════════════════════════════════════════════════════════════════════════
with tab_map:
    st.markdown("""
    <div style="padding:16px 0 8px">
      <span style="font-size:16px;font-weight:500;color:var(--txt)">Ranger → Unity Catalog mapping reference</span>
      <span style="font-size:11px;color:var(--mut);margin-left:12px">all implemented translations</span>
    </div>
    """, unsafe_allow_html=True)

    mc1, mc2 = st.columns(2, gap="medium")

    def map_section(title, rows, col_cls_fn=None):
        html = f'<div class="map-section"><div class="map-section-hdr">{title}</div>'
        for row in rows:
            ranger, arrow, uc = row[0], row[1], row[2]
            cls = col_cls_fn(row) if col_cls_fn else ("map-x" if "✗" in uc or "cannot" in uc.lower() else "map-u")
            html += f'<div class="map-row"><span class="map-r">{ranger}</span><span class="map-a">{arrow}</span><span class="{cls}">{uc}</span></div>'
        html += '</div>'
        return html

    with mc1:
        # Resource types
        st.markdown('<div class="section-hdr">Resource type mapping</div>', unsafe_allow_html=True)
        res_rows = [
            ("database (db only)",   "→", "SCHEMA main.{db}",            "ok"),
            ("database + table=*",   "→", "SCHEMA main.{db}",            "ok"),
            ("database.*.*",         "→", "CATALOG main",                "ok"),
            ("table",                "→", "TABLE main.{db}.{table}",     "ok"),
            ("column",               "→", "via mask/filter function",    "ok"),
            ("udf",                  "→", "FUNCTION main.{db}.{udf}",    "ok"),
            ("path (HDFS/ADLS/S3)",  "→", "EXTERNAL LOCATION (placeholder)", "warn"),
            ("url (Hive URL policy)","→", "EXTERNAL LOCATION (placeholder)", "warn"),
            ("tag",                  "→", "Tag-based GRANT (placeholder)","warn"),
            ("topic (Kafka)",        "✗", "No UC equivalent",            "err"),
            ("cluster (Kafka)",      "✗", "No UC equivalent",            "err"),
            ("consumergroup (Kafka)","✗", "No UC equivalent",            "err"),
            ("delegationtoken",      "✗", "No UC equivalent",            "err"),
            ("entity (Atlas)",       "✗", "No UC equivalent",            "err"),
            ("entity-type (Atlas)",  "✗", "No UC equivalent",            "err"),
            ("hiveservice",          "✗", "No UC equivalent",            "err"),
            ("queue (YARN)",         "✗", "No UC equivalent",            "err"),
            ("column-family (HBase)","✗", "No UC equivalent",            "err"),
        ]
        def res_cls(row): return {"ok":"map-u","warn":"map-w","err":"map-x"}[row[3]]
        st.markdown(map_section("", res_rows, res_cls), unsafe_allow_html=True)

        # Policy type mapping
        st.markdown('<div class="section-hdr" style="margin-top:14px">Policy type mapping</div>', unsafe_allow_html=True)
        pol_rows = [
            ("ACCESS  (policyType=0)", "→", "GRANT privilege ON resource TO principal"),
            ("COLUMN_MASK (policyType=1)", "→", "CREATE FUNCTION + ALTER TABLE SET MASK"),
            ("ROW_FILTER (policyType=2)", "→", "CREATE FUNCTION + ALTER TABLE SET ROW FILTER"),
            ("TAG-based ACCESS", "→", "GRANT on table matching tag (placeholder)"),
            ("TAG-based MASK", "→", "CREATE FUNCTION on table matching tag"),
            ("policyDeltas format", "→", "Delta policies extracted and translated"),
            ("testCases format", "→", "servicePolicies extracted per test case"),
            ("securityZones", "~", "Zone names noted in output — boundaries not translatable"),
        ]
        html = '<div class="map-section">'
        for ranger, arrow, uc in pol_rows:
            cls = "map-w" if arrow == "~" else "map-u"
            html += f'<div class="map-row"><span class="map-r">{ranger}</span><span class="map-a">{arrow}</span><span class="{cls}">{uc}</span></div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        # Principal mapping
        st.markdown('<div class="section-hdr" style="margin-top:14px">Principal mapping</div>', unsafe_allow_html=True)
        prin_rows = [
            ("users: [alice, bob]", "→", "GRANT ... TO alice; GRANT ... TO bob", "ok"),
            ("groups: [data_eng]", "→", "GRANT ... TO data_eng", "ok"),
            ("roles: [analyst_role]", "→", "GRANT ... TO analyst_role (role)", "ok"),
            ("public / everyone", "~", "-- TODO: assign to account-level group", "warn"),
            ("service account", "→", "GRANT ... TO `svc_account` (service principal)", "ok"),
        ]
        html = '<div class="map-section">'
        for ranger, arrow, uc, status in prin_rows:
            cls = {"ok":"map-u","warn":"map-w","err":"map-x"}[status]
            html += f'<div class="map-row"><span class="map-r">{ranger}</span><span class="map-a">{arrow}</span><span class="{cls}">{uc}</span></div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

    with mc2:
        # Privilege mapping
        st.markdown('<div class="section-hdr">Privilege mapping</div>', unsafe_allow_html=True)
        priv_rows = [
            ("select",              "→", "SELECT",                    "ok"),
            ("read",                "→", "SELECT",                    "ok"),
            ("update",              "→", "MODIFY",                    "ok"),
            ("write",               "→", "MODIFY",                    "ok"),
            ("create",              "→", "CREATE TABLE / CREATE SCHEMA","ok"),
            ("drop",                "→", "DROP",                      "ok"),
            ("alter",               "→", "ALTER",                     "ok"),
            ("all",                 "→", "ALL PRIVILEGES",            "ok"),
            ("admin",               "→", "ALL PRIVILEGES",            "ok"),
            ("hive:select",         "→", "SELECT  (hive: prefix stripped)", "ok"),
            ("hive:update",         "→", "MODIFY  (hive: prefix stripped)", "ok"),
            ("hive:all",            "→", "ALL PRIVILEGES",            "ok"),
            ("read (path resource)","→", "READ FILES",                "ok"),
            ("write (path resource)","→", "WRITE FILES",              "ok"),
            ("execute (path)",      "→", "READ FILES  (closest equiv)","warn"),
            ("execute (udf)",       "→", "EXECUTE ON FUNCTION",       "ok"),
            ("publish (Kafka)",     "✗", "Not translatable",          "err"),
            ("consume (Kafka)",     "✗", "Not translatable",          "err"),
            ("entity-read (Atlas)", "✗", "Not translatable",          "err"),
            ("index (Hive)",        "~", "No UC equivalent — Delta handles internally","warn"),
            ("lock (Hive)",         "~", "No UC equivalent",          "warn"),
        ]
        html = '<div class="map-section">'
        for ranger, arrow, uc, status in priv_rows:
            cls = {"ok":"map-u","warn":"map-w","err":"map-x"}[status]
            html += f'<div class="map-row"><span class="map-r">{ranger}</span><span class="map-a">{arrow}</span><span class="{cls}">{uc}</span></div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        # Masking types
        st.markdown('<div class="section-hdr" style="margin-top:14px">Column mask type mapping</div>', unsafe_allow_html=True)
        mask_rows = [
            ("MASK",              "'XXXXX'  (full redact)"),
            ("MASK_SHOW_LAST_4",  "CONCAT(REPEAT('X', LEN-4), RIGHT(col, 4))"),
            ("MASK_SHOW_FIRST_4", "CONCAT(LEFT(col, 4), REPEAT('X', LEN-4))"),
            ("MASK_HASH",         "SHA2(CAST(col AS STRING), 256)"),
            ("MASK_NULL",         "NULL"),
            ("MASK_NONE",         "col  (pass-through, no masking)"),
            ("MASK_DATE_SHOW_YEAR","MAKE_DATE(YEAR(col), 1, 1)"),
            ("MASK_REDACT",       "'[REDACTED]'"),
            ("NULL",              "NULL  (alias for MASK_NULL)"),
            ("SHUFFLE",           "SHA2(col, 256)  (approximation)"),
            ("CUSTOM",            "Custom conditionExpr from policy"),
        ]
        html = '<div class="map-section">'
        for ranger, uc in mask_rows:
            html += f'<div class="map-row"><span class="map-r">{ranger}</span><span class="map-a">→</span><span class="map-u">{uc}</span></div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

        # HDFS/External Location
        st.markdown('<div class="section-hdr" style="margin-top:14px">HDFS / External Location mapping</div>', unsafe_allow_html=True)
        hdfs_rows = [
            ("read on /path/*",              "GRANT READ FILES ON EXTERNAL LOCATION loc TO grp"),
            ("write on /path/*",             "GRANT WRITE FILES ON EXTERNAL LOCATION loc TO grp"),
            ("read+write+execute",           "GRANT READ FILES, WRITE FILES ON EXTERNAL LOCATION loc"),
            ("all on path",                  "GRANT ALL PRIVILEGES ON EXTERNAL LOCATION loc TO grp"),
            ("isRecursive: true",            "No change — External Location covers sub-paths"),
            ("URL-based Hive (hive://...)",  "Treated as path → EXTERNAL LOCATION"),
        ]
        html = '<div class="map-section">'
        for ranger, uc in hdfs_rows:
            html += f'<div class="map-row"><span class="map-r">{ranger}</span><span class="map-a">→</span><span class="map-u">{uc}</span></div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

    # ── Limitations / Cautions / Cannot translate ──
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:14px;font-weight:600;color:var(--txt);margin-bottom:12px">Limitations, cautions &amp; unsupported services</div>', unsafe_allow_html=True)

    lc1, lc2, lc3 = st.columns(3, gap="medium")

    with lc1:
        st.markdown("""
        <div class="limit-box">
          <h4>⚠ Caution areas — output is approximate</h4>
          <ul>
            <li><b>denyPolicyItems</b> — noted in SQL output with a <code>-- WARNING: DENY</code> comment but UC has no DENY verb; restructure as allow-only <span>(UC is deny-by-default)</span></li>
            <li><b>allowExceptions / denyExceptions</b> — exceptions appear in output as individual GRANTs but exception semantics are not fully replicated</li>
            <li><b>isDenyAllElse: true</b> — UC is already deny-by-default; this flag is noted but requires no extra SQL</li>
            <li><b>Security zones</b> — zone names appear as comments; zone boundaries have no UC equivalent (permissions apply to the whole metastore)</li>
            <li><b>Tag-based policies</b> — GRANT/MASK is generated against a <code>&lt;table_placeholder&gt;</code>; you must manually replace it with the actual table that carries the tag</li>
            <li><b>External Location names</b> — path policies generate <code>your_location_name</code> placeholder; replace with your actual external location</li>
            <li><b>Catalog name</b> — defaults to <code>main</code>; edit the catalog config if target is different</li>
          </ul>
        </div>
        """, unsafe_allow_html=True)

    with lc2:
        st.markdown("""
        <div class="limit-box">
          <h4>⚠ Features not translated</h4>
          <ul>
            <li><b>ip-range conditions</b> — enforce at Databricks workspace IP access list level <span>(Settings → IP Access List)</span></li>
            <li><b>validity periods</b> — time-bound policies have no UC equivalent; use IAM token expiry or external governance</li>
            <li><b>row-level conditions on principals</b> (e.g., <code>owner = current_user()</code>) — must be embedded manually in the row-filter function body</li>
            <li><b>HBase column-family granularity</b> — HBase ACLs operate at column-family level; Delta/UC has no equivalent; migrate to Delta first, then apply table-level GRANTs</li>
            <li><b>Ranger audit policies</b> — audit configuration is not translatable to UC; UC has its own audit log via system tables</li>
            <li><b>delegateAdmin</b> — noted in output; no direct UC equivalent (use <code>GRANT WITH GRANT OPTION</code> in newer UC versions)</li>
          </ul>
        </div>
        """, unsafe_allow_html=True)

    with lc3:
        st.markdown("""
        <div class="cant-box">
          <h4>✗ Services that cannot be covered</h4>
          <ul>
            <li><b>Apache Kafka</b> — <code>topic</code>, <code>cluster</code>, <code>consumergroup</code>, <code>delegationtoken</code> resources have no Unity Catalog equivalent; Kafka ACLs stay in Ranger or Confluent Platform</li>
            <li><b>Apache Atlas</b> — <code>entity</code>, <code>entity-type</code>, <code>entity-classification</code>, <code>business-metadata</code> are Atlas governance constructs; use Databricks Unity Catalog tags + lineage instead</li>
            <li><b>YARN / MapReduce</b> — queue-level policies map to Databricks Cluster Policy + <code>CAN_USE</code> permission, not SQL GRANTs; must be configured in the Databricks workspace UI</li>
            <li><b>Solr / Elasticsearch</b> — no SQL-based equivalent in UC</li>
            <li><b>Storm / NiFi</b> — no equivalent in the Databricks ecosystem</li>
            <li><b>Knox topology policies</b> — gateway-level; handle at network/proxy layer</li>
            <li><b>Ranger plugins for ADLS/GCS</b> — migrate storage-level ACLs to Azure RBAC or GCS IAM; then add UC External Location grants</li>
          </ul>
        </div>
        """, unsafe_allow_html=True)

    # Legend
    st.markdown(
        '<div style="margin-top:8px">'
        '<span class="badge badge-u">✓ Translatable</span>&nbsp;&nbsp;'
        '<span class="badge badge-w">~ Needs manual mapping</span>&nbsp;&nbsp;'
        '<span class="badge badge-e">✗ Not translatable</span>&nbsp;&nbsp;'
        '<span style="font-size:10px;color:var(--mut)">placeholder = replace before running</span>'
        '</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — HISTORY
# ══════════════════════════════════════════════════════════════════════════════
with tab_hist:
    history = load_history()

    hdr_c, btn_c = st.columns([3, 1])
    with hdr_c:
        st.markdown('<div class="section-hdr" style="padding-top:16px">Translation history</div>', unsafe_allow_html=True)
    with btn_c:
        st.markdown("<div style='padding-top:16px'></div>", unsafe_allow_html=True)
        if st.button("🗑 Clear", key="clear_hist", type="secondary"):
            p = get_output_dir() / "history.json"
            if p.exists():
                p.unlink()
            st.rerun()

    if not history:
        st.markdown(
            '<div style="color:var(--mut);font-size:12px;padding:20px 0">No translations yet — run a translation to see history here.</div>',
            unsafe_allow_html=True,
        )
    else:
        total_policies = sum(h.get("policies", 0) for h in history)
        total_stmts    = sum(h.get("sql_statements", 0) for h in history)
        total_skipped  = sum(h.get("not_translatable", 0) for h in history)

        hc1, hc2, hc3, hc4 = st.columns(4)
        hc1.metric("Runs", len(history))
        hc2.metric("Total Policies", total_policies)
        hc3.metric("Total SQL Stmts", total_stmts)
        hc4.metric("Total Skipped", total_skipped)

        st.markdown("<hr>", unsafe_allow_html=True)

        for entry in history:
            ts_str = entry.get("timestamp", "")
            try:
                ts_fmt = datetime.fromisoformat(ts_str).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                ts_fmt = ts_str

            source    = entry.get("source", "unknown")
            policies  = entry.get("policies", 0)
            stmts     = entry.get("sql_statements", 0)
            skipped   = entry.get("not_translatable", 0)
            warns     = entry.get("warnings", 0)
            out_path  = entry.get("output_path", "")
            inp_path  = entry.get("input_path", "")
            out_exists = Path(out_path).exists() if out_path else False
            inp_exists = Path(inp_path).exists() if inp_path else False

            skip_badge = f'&nbsp;<span class="badge badge-w">{skipped} skipped</span>' if skipped else ""
            warn_badge = f'&nbsp;<span class="badge badge-w">{warns} warns</span>' if warns else ""
            out_fname  = Path(out_path).name if out_path else "—"
            inp_fname  = Path(inp_path).name if inp_path else "—"

            st.markdown(f"""
            <div class="hist-row">
              <span class="hist-ts">{ts_fmt}</span>
              <span class="hist-src">{source}</span>
              <span class="badge badge-ok">{policies} policies</span>
              <span class="badge badge-u">{stmts} SQL</span>
              {skip_badge}{warn_badge}
              <span style="margin-left:auto;display:flex;gap:10px;align-items:center;flex-shrink:0">
                <span style="font-size:11px;color:{'var(--acc)' if inp_exists else 'var(--mut)'};font-family:var(--mono);white-space:nowrap" title="{inp_path}">
                  {"📋 " + inp_fname if inp_fname != "—" else ""}
                </span>
                <span style="font-size:11px;color:{'var(--pur)' if out_exists else 'var(--mut)'};font-family:var(--mono);white-space:nowrap" title="{out_path}">
                  {"📄 " + out_fname if out_fname != "—" else "—"}
                </span>
              </span>
            </div>
            """, unsafe_allow_html=True)

            # Toggle-based view buttons — each opens/closes independently
            row_key = f"{ts_str}_{source[:8]}"
            sk_json = f"open_json_{row_key}"
            sk_sql  = f"open_sql_{row_key}"
            if sk_json not in st.session_state:
                st.session_state[sk_json] = False
            if sk_sql not in st.session_state:
                st.session_state[sk_sql] = False

            vcols = st.columns([1, 1])
            with vcols[0]:
                if inp_exists:
                    lbl = "📋 Hide JSON" if st.session_state[sk_json] else "📋 View Input JSON"
                    if st.button(lbl, key=f"btn_json_{row_key}", use_container_width=True):
                        st.session_state[sk_json] = not st.session_state[sk_json]
                        st.rerun()
            with vcols[1]:
                if out_exists:
                    lbl = "📄 Hide SQL" if st.session_state[sk_sql] else "📄 View Output SQL"
                    if st.button(lbl, key=f"btn_sql_{row_key}", use_container_width=True):
                        st.session_state[sk_sql] = not st.session_state[sk_sql]
                        st.rerun()

            if st.session_state[sk_json] and inp_exists:
                inp_content = Path(inp_path).read_text()
                st.markdown(f'<div style="font-size:12px;color:var(--mut);margin:6px 0 4px">📋 {inp_path}</div>', unsafe_allow_html=True)
                st.download_button("📥 Download JSON", data=inp_content, file_name=inp_fname,
                                   mime="application/json", key=f"dljson_{row_key}", use_container_width=True)
                st.code(inp_content, language="json")

            if st.session_state[sk_sql] and out_exists:
                sql_content = Path(out_path).read_text()
                st.markdown(f'<div style="font-size:12px;color:var(--mut);margin:6px 0 4px">📄 {out_path}</div>', unsafe_allow_html=True)
                st.download_button("📥 Download SQL", data=sql_content, file_name=out_fname,
                                   mime="text/plain", key=f"dlsql_{row_key}", use_container_width=True)
                st.code(sql_content, language="sql", line_numbers=True)

        with st.expander("📋 Full table view"):
            df = pd.DataFrame(history)
            if not df.empty:
                cols = ["timestamp","source","policies","sql_statements","translatable","not_translatable","warnings","input_path","output_path"]
                df = df[[c for c in cols if c in df.columns]]
                st.dataframe(df, use_container_width=True)

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center;color:var(--bdr);font-size:10px;padding:10px 0;font-family:var(--mono)">'
    'Ranger → UC Translator v2.2 &nbsp;|&nbsp; Databricks Unity Catalog Migration Tool'
    '</div>',
    unsafe_allow_html=True,
)
