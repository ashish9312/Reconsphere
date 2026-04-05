import streamlit as st

from email_leak_checker import run_email_checker
from face_module import run_face_module
from phone_leak_checker import run_phone_checker

st.set_page_config(
    page_title="ReconSphere — AI OSINT Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject Professional CSS ──────────────────────────────────────────
st.markdown(
    """
<style>
/* ─── Google Fonts ─── */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Manrope:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

/* ─── Root Variables ─── */
:root {
    --bg-void: #0A0E1A;
    --surface: #0F141A;
    --surface-container: #151A21;
    --surface-high: #1B2028;
    --surface-highest: #20262F;
    --surface-bright: #262C36;
    --primary: #00E5FF;
    --primary-dim: #81ECFF;
    --secondary: #7C3AED;
    --secondary-light: #AF88FF;
    --tertiary: #60A5FA;
    --on-surface: #F1F3FC;
    --on-surface-variant: #A8ABB3;
    --outline: #72757D;
    --outline-variant: #44484F;
    --error: #FF716C;
    --success: #10B981;
    --warning: #F59E0B;
    --ghost-border: rgba(114, 117, 125, 0.15);
    --glow-primary: rgba(0, 229, 255, 0.15);
    --glow-secondary: rgba(124, 58, 237, 0.15);
}

/* ─── Global Resets ─── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-void) !important;
    font-family: 'Manrope', sans-serif !important;
}
[data-testid="stApp"] {
    background: var(--bg-void) !important;
}

/* ─── Subtle Grid Background ─── */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(129, 236, 255, 0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(129, 236, 255, 0.02) 1px, transparent 1px);
    background-size: 32px 32px;
    pointer-events: none;
    z-index: 0;
}

/* ─── Sidebar ─── */
[data-testid="stSidebar"] {
    background: #000000 !important;
    border-right: 1px solid var(--ghost-border) !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.5rem;
}

/* Sidebar brand area */
[data-testid="stSidebar"] .stMarkdown h1 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    background: linear-gradient(135deg, var(--primary), var(--secondary-light));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.02em;
    margin-bottom: 0.25rem !important;
}

/* Sidebar navigation radio */
[data-testid="stSidebar"] .stRadio > label {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--on-surface-variant) !important;
    margin-bottom: 0.5rem;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {
    display: flex !important;
    align-items: center !important;
    gap: 0.65rem;
    width: 100%;
    margin: 0;
    padding: 0.15rem 0;
    border-radius: 10px;
    transition: all 0.25s ease;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label > div:first-child {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 1rem;
    margin: 0;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label [data-testid="stMarkdownContainer"] {
    flex: 1 1 auto;
}
[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
    font-family: 'Manrope', sans-serif !important;
    font-size: 0.92rem !important;
    font-weight: 500 !important;
    padding: 0.6rem 0.75rem;
    margin: 0 !important;
    border-radius: 8px;
    transition: all 0.25s ease;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:hover [data-testid="stMarkdownContainer"] p {
    color: var(--primary) !important;
    background: rgba(0, 229, 255, 0.06);
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-checked="true"] {
    border-left: 2px solid var(--primary) !important;
}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-checked="true"] [data-testid="stMarkdownContainer"] p {
    color: var(--primary) !important;
    font-weight: 600 !important;
}

/* ─── Headings ─── */
h1, .stMarkdown h1 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em;
}
h2, .stMarkdown h2 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em;
}
h3, .stMarkdown h3 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
}

/* Main title gradient */
[data-testid="stAppViewContainer"] > section > div > div > div > div > .stMarkdown:first-child h1,
.main-title {
    background: linear-gradient(135deg, var(--primary), var(--secondary-light), var(--tertiary));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.2rem !important;
}

/* ─── Glassmorphism Containers ─── */
[data-testid="stExpander"],
[data-testid="stForm"] {
    background: linear-gradient(135deg, rgba(32, 38, 47, 0.5), rgba(15, 20, 26, 0.7)) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid var(--ghost-border) !important;
    border-radius: 12px !important;
    padding: 1rem !important;
}

/* ─── Metric Cards ─── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(27, 32, 40, 0.8), rgba(15, 20, 26, 0.9)) !important;
    border: 1px solid var(--ghost-border) !important;
    border-left: 3px solid var(--primary) !important;
    border-radius: 10px !important;
    padding: 1rem 1.25rem !important;
    transition: all 0.3s ease;
}
[data-testid="stMetric"]:hover {
    border-color: rgba(0, 229, 255, 0.3) !important;
    box-shadow: 0 0 20px var(--glow-primary);
}
[data-testid="stMetric"] [data-testid="stMetricLabel"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--on-surface-variant) !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 700 !important;
    color: var(--primary-dim) !important;
}

/* ─── Buttons ─── */
.stButton > button {
    background: linear-gradient(135deg, var(--primary), #00B4D8) !important;
    color: #003840 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.65rem 2rem !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 0 15px var(--glow-primary) !important;
}
.stButton > button:hover {
    box-shadow: 0 0 30px rgba(0, 229, 255, 0.4), 0 0 60px rgba(0, 229, 255, 0.15) !important;
    transform: translateY(-1px);
}
.stButton > button:active {
    transform: translateY(0);
}

/* ─── Text Inputs ─── */
.stTextInput > div > div > input,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
    background: var(--surface-container) !important;
    border: 1px solid var(--outline-variant) !important;
    border-radius: 8px !important;
    color: var(--on-surface) !important;
    font-family: 'Manrope', sans-serif !important;
    transition: all 0.25s ease;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 8px var(--glow-primary), 0 0 20px rgba(0, 229, 255, 0.08) !important;
}
.stTextInput label,
.stSelectbox label,
.stNumberInput label,
.stFileUploader label {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--on-surface-variant) !important;
}

/* ─── File Uploader ─── */
[data-testid="stFileUploader"] {
    border: none !important;
}
[data-testid="stFileUploader"] section {
    background: linear-gradient(135deg, rgba(15, 20, 26, 0.8), rgba(10, 14, 26, 0.9)) !important;
    border: 2px dashed var(--outline-variant) !important;
    border-radius: 12px !important;
    padding: 2.5rem 2rem !important;
    transition: all 0.3s ease;
}
[data-testid="stFileUploader"] section:hover {
    border-color: var(--primary) !important;
    background: linear-gradient(135deg, rgba(0, 229, 255, 0.03), rgba(15, 20, 26, 0.9)) !important;
    box-shadow: 0 0 30px var(--glow-primary);
}
[data-testid="stFileUploader"] section button {
    background: transparent !important;
    border: 1px solid var(--primary) !important;
    color: var(--primary) !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
}

/* ─── Alerts / Status ─── */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-left: 3px solid !important;
    backdrop-filter: blur(6px);
}
.stSuccess, [data-baseweb="notification"][kind="positive"] {
    background: rgba(16, 185, 129, 0.08) !important;
    border-left-color: var(--success) !important;
}
.stWarning {
    background: rgba(245, 158, 11, 0.08) !important;
    border-left-color: var(--warning) !important;
}
.stError {
    background: rgba(255, 113, 108, 0.08) !important;
    border-left-color: var(--error) !important;
}
.stInfo {
    background: rgba(0, 229, 255, 0.06) !important;
    border-left-color: var(--primary) !important;
}

/* ─── Spinner ─── */
.stSpinner > div {
    border-top-color: var(--primary) !important;
}

/* ─── Image Containers ─── */
[data-testid="stImage"] {
    border-radius: 10px !important;
    overflow: hidden;
    border: 1px solid var(--ghost-border);
}

/* ─── Divider ─── */
hr {
    border-color: var(--ghost-border) !important;
    margin: 1.5rem 0 !important;
}

/* ─── Captions & Small Text ─── */
.stCaption, [data-testid="stCaptionContainer"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.72rem !important;
    letter-spacing: 0.03em;
    color: var(--outline) !important;
}

/* ─── Progress Bar ─── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, var(--primary), var(--secondary)) !important;
    border-radius: 4px !important;
}

/* ─── Selectbox Dropdown ─── */
[data-baseweb="select"] {
    background: var(--surface-container) !important;
}
[data-baseweb="select"] [data-baseweb="tag"] {
    background: var(--surface-high) !important;
}

/* ─── Tabs ─── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid var(--ghost-border);
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--on-surface-variant);
    border-bottom: 2px solid transparent;
    transition: all 0.25s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--primary);
}
.stTabs [aria-selected="true"] {
    color: var(--primary) !important;
    border-bottom-color: var(--primary) !important;
}

/* ─── Custom scrollbar ─── */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: var(--bg-void);
}
::-webkit-scrollbar-thumb {
    background: var(--outline-variant);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: var(--outline);
}

/* ─── Links ─── */
a {
    color: var(--primary) !important;
    text-decoration: none !important;
    transition: all 0.2s ease;
}
a:hover {
    text-shadow: 0 0 8px var(--glow-primary);
}

/* ─── Column gap fix ─── */
[data-testid="column"] {
    padding: 0 0.4rem;
}

/* ─── Number Input fix ─── */
.stNumberInput button {
    background: var(--surface-high) !important;
    color: var(--on-surface) !important;
    border: 1px solid var(--ghost-border) !important;
}

/* ─── Custom module card class ─── */
div[data-testid="stVerticalBlock"] > div.element-container .module-card {
    background: linear-gradient(135deg, rgba(32, 38, 47, 0.5), rgba(15, 20, 26, 0.7));
    backdrop-filter: blur(12px);
    border: 1px solid var(--ghost-border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("# 🛡️ ReconSphere")
    st.caption("AI-POWERED OSINT PLATFORM")
    st.markdown("---")
    module = st.radio(
        "MODULES",
        [
            "🖼️  Face Recon",
            "📧  Email Leak Checker",
            "📱  Phone Leak Checker",
        ],
        label_visibility="visible",
    )
    st.markdown("---")
    st.markdown(
        """
        <div style="
            background: linear-gradient(135deg, rgba(32,38,47,0.5), rgba(15,20,26,0.7));
            border: 1px solid rgba(114,117,125,0.15);
            border-radius: 10px;
            padding: 1rem;
            margin-top: 0.5rem;
        ">
            <p style="font-family:'Inter',sans-serif; font-size:0.65rem; font-weight:600;
               text-transform:uppercase; letter-spacing:0.08em; color:#72757D; margin:0 0 0.4rem 0;">
               SYSTEM STATUS</p>
            <p style="font-family:'Manrope',sans-serif; font-size:0.82rem; color:#10B981; margin:0 0 0.3rem 0;">
               ● All Systems Operational</p>
            <p style="font-family:'Inter',sans-serif; font-size:0.68rem; color:#A8ABB3; margin:0;">
               v2.0 — Omniscient Lens</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Main Content ─────────────────────────────────────────────────────
st.markdown(
    '<h1 style="font-family:\'Space Grotesk\',sans-serif; font-weight:700; font-size:2rem; '
    'background:linear-gradient(135deg,#00E5FF,#AF88FF,#60A5FA); '
    '-webkit-background-clip:text; -webkit-text-fill-color:transparent; '
    'background-clip:text; margin-bottom:0.1rem;">ReconSphere</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="font-family:\'Manrope\',sans-serif; font-size:0.92rem; color:#A8ABB3; '
    'margin-top:0; margin-bottom:1.5rem;">'
    "Unified OSINT platform for image analysis, email breach detection, and phone intelligence.</p>",
    unsafe_allow_html=True,
)

if module == "🖼️  Face Recon":
    run_face_module()
elif module == "📧  Email Leak Checker":
    run_email_checker()
elif module == "📱  Phone Leak Checker":
    run_phone_checker()

# ── Footer ───────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<p style="font-family:\'Inter\',sans-serif; font-size:0.7rem; text-align:center; '
    'color:#44484F; letter-spacing:0.05em;">'
    "DEVELOPED BY ASHISH &nbsp;|&nbsp; MCA MAJOR PROJECT &nbsp;|&nbsp; © 2026 RECONSPHERE</p>",
    unsafe_allow_html=True,
)
