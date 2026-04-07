import streamlit as st
from html import escape

from utils import fetch_hibp_breach, is_valid_email, lookup_offline_leak


def run_email_checker():
    # ── Header ───────────────────────────────────────────────────────
    st.markdown(
        '<h2 style="font-family:\'Space Grotesk\',sans-serif; font-weight:700; '
        'background:linear-gradient(135deg,#00E5FF,#AF88FF); '
        '-webkit-background-clip:text; -webkit-text-fill-color:transparent; '
        'background-clip:text; margin-bottom:0.3rem;">'
        "📧 Email Leak Checker</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="font-family:\'Manrope\',sans-serif; font-size:0.9rem; color:#A8ABB3; '
        'margin-bottom:1.5rem;">Check if an email has been exposed in known data breaches.</p>',
        unsafe_allow_html=True,
    )

    # ── Input Card ───────────────────────────────────────────────────
    st.markdown(
        """<div style="
            background: linear-gradient(135deg, rgba(32,38,47,0.5), rgba(15,20,26,0.7));
            backdrop-filter: blur(12px);
            border: 1px solid rgba(114,117,125,0.15);
            border-radius: 12px;
            padding: 1.75rem;
            margin-bottom: 1.25rem;
        ">
            <p style="font-family:'Inter',sans-serif; font-size:0.65rem; font-weight:600;
               text-transform:uppercase; letter-spacing:0.08em; color:#72757D; margin:0 0 0.75rem 0;">
               🔍 BREACH INTELLIGENCE SCAN</p>
        </div>""",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([3, 2])
    with col1:
        email_input = st.text_input(
            "EMAIL ADDRESS",
            "",
            placeholder="someone@example.com",
        )
    with col2:
        hibp_api_key = st.text_input(
            "HIBP API KEY (REQUIRED FOR LIVE CHECK)",
            type="password",
            placeholder="Enter API key",
        )

    # ── Data Sources Info ────────────────────────────────────────────
    src_col1, src_col2 = st.columns(2)
    with src_col1:
        st.markdown(
            """<div style="
                background: linear-gradient(135deg, rgba(27,32,40,0.8), rgba(15,20,26,0.9));
                border: 1px solid rgba(114,117,125,0.15);
                border-left: 3px solid #00E5FF;
                border-radius: 10px;
                padding: 1rem 1.25rem;
            ">
                <p style="font-family:'Inter',sans-serif; font-size:0.65rem; font-weight:600;
                   text-transform:uppercase; letter-spacing:0.08em; color:#72757D; margin:0 0 0.4rem 0;">
                   DATA SOURCE — PRIMARY</p>
                <p style="font-family:'Manrope',sans-serif; font-size:0.92rem; color:#81ECFF;
                   font-weight:600; margin:0 0 0.2rem 0;">Have I Been Pwned</p>
                <p style="font-family:'Inter',sans-serif; font-size:0.72rem; color:#A8ABB3; margin:0;">
                   Live API breach database</p>
            </div>""",
            unsafe_allow_html=True,
        )
    with src_col2:
        st.markdown(
            """<div style="
                background: linear-gradient(135deg, rgba(27,32,40,0.8), rgba(15,20,26,0.9));
                border: 1px solid rgba(114,117,125,0.15);
                border-left: 3px solid #AF88FF;
                border-radius: 10px;
                padding: 1rem 1.25rem;
            ">
                <p style="font-family:'Inter',sans-serif; font-size:0.65rem; font-weight:600;
                   text-transform:uppercase; letter-spacing:0.08em; color:#72757D; margin:0 0 0.4rem 0;">
                   DATA SOURCE — FALLBACK</p>
                <p style="font-family:'Manrope',sans-serif; font-size:0.92rem; color:#AF88FF;
                   font-weight:600; margin:0 0 0.2rem 0;">Offline Leak Database</p>
                <p style="font-family:'Inter',sans-serif; font-size:0.72rem; color:#A8ABB3; margin:0;">
                   Local JSON breach samples</p>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("⚡ CHECK FOR BREACHES", use_container_width=True):
        if email_input:
            with st.spinner("🔎 Scanning breach intelligence sources..."):
                if is_valid_email(email_input):
                    result = fetch_hibp_breach(email_input, hibp_api_key)
                    status = result.get("status")
                    leaks = result.get("breaches", [])

                    if status == "breached":
                        st.error(f"🚨 **BREACH DETECTED** — {len(leaks)} breach(es) found:")
                        for leak in leaks:
                            safe_leak = escape(str(leak))
                            st.markdown(
                                f'<div style="background:rgba(255,113,108,0.06); '
                                f"border-left:3px solid #FF716C; border-radius:6px; "
                                f'padding:0.5rem 0.75rem; margin:0.3rem 0; '
                                f"font-family:'Manrope',sans-serif; font-size:0.88rem; "
                                f'color:#FFA8A3;">'
                                f"● {safe_leak}</div>",
                                unsafe_allow_html=True,
                            )
                    elif status == "clean":
                        st.success("✅ **LIVE CHECK CLEAR** — Email not found in HIBP.")
                    else:
                        offline = lookup_offline_leak(email_input)
                        st.warning(
                            "⚠️ Live HIBP verification unavailable. Showing fallback coverage only."
                        )
                        if status == "missing_api_key":
                            st.info("Add a valid HIBP API key to enable live breach verification.")
                        elif result.get("message"):
                            st.info(f"Live source status: {result['message']}")

                        if offline:
                            st.error("🚨 **OFFLINE MATCH FOUND** — Present in local dataset:")
                            for item in offline:
                                safe_item = escape(str(item))
                                st.markdown(
                                    f'<div style="background:rgba(255,113,108,0.06); '
                                    f"border-left:3px solid #FF716C; border-radius:6px; "
                                    f'padding:0.5rem 0.75rem; margin:0.3rem 0; '
                                    f"font-family:'Manrope',sans-serif; font-size:0.88rem; "
                                    f'color:#FFA8A3;">'
                                    f"● {safe_item}</div>",
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.info(
                                "ℹ️ No offline evidence found. Final verdict remains **UNKNOWN** without live source confirmation."
                            )
                else:
                    st.warning("⚠️ Please enter a valid email address.")
        else:
            st.warning("⚠️ Please enter an email address to scan.")
