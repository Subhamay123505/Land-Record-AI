import json
from pathlib import Path
import pandas as pd
import streamlit as st
from backend.data import load_trusted_records
from backend.extraction import extract_from_upload, extract_from_text
from backend.engine import analyze_record
from backend.db import init_db, add_review_event, get_review_events

ZIP_PATH = Path(__file__).resolve().parent / "LandRecordAI.zip"

st.set_page_config(page_title="LandRecordAI", page_icon="🗺️", layout="wide")
init_db()
st.markdown("""
<style>
.block-container {padding-top: 1.7rem; max-width: 1400px;}
.hero {background:linear-gradient(120deg,#10264f,#2457c5);padding:1.5rem 1.8rem;border-radius:18px;color:white;margin-bottom:1rem;}
.hero h1 {color:white;margin:0;font-size:2rem;}
.hero p {color:#dbe7ff;margin:.45rem 0 0 0;}
.small-muted {color:#64748b;font-size:.88rem;}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>🗺️ LandRecordAI</h1><p>Land record extraction • semantic matching • consistency reasoning • human review</p></div>', unsafe_allow_html=True)

trusted = load_trusted_records()

with st.sidebar:
    st.header("📦 Download Project")
    st.write("Download the complete source code, tests, documentation, sample datasets, and report.")
    if ZIP_PATH.exists():
        with open(ZIP_PATH, "rb") as f:
            st.download_button(
                label="⬇️ Download Project (.zip)",
                data=f.read(),
                file_name="LandRecordAI.zip",
                mime="application/zip",
                use_container_width=True,
                type="primary"
            )
        st.caption(f"Package: `LandRecordAI.zip` ({ZIP_PATH.stat().st_size / 1024:.1f} KB)")
    else:
        st.info("ZIP package is being generated...")

tab1, tab2, tab3, tab4 = st.tabs(["📄 Analyze record", "🧾 Trusted register", "📊 Evaluation guide", "🕵️ Audit history"])

with tab1:
    if "review_feedback" in st.session_state:
        st.success(st.session_state.pop("review_feedback"))

    st.write("Upload a synthetic/sample land record or paste its text. Extracted values are proposals and must be reviewed.")
    uploaded = st.file_uploader("Upload TXT, PDF, CSV, DOCX, PNG or JPG", type=["txt","pdf","csv","docx","png","jpg","jpeg"])
    default_text = "Owner Name: Rahul Kumar\nSurvey Number: 125/2\nParcel Area: 2.50 acres\nRecord Status: Active"
    manual_text = st.text_area("Or paste document text", value=default_text, height=130)
    if uploaded:
        raw_text, extracted = extract_from_upload(uploaded.name, uploaded.getvalue())
        st.caption(f"Source: {uploaded.name}")
        if raw_text:
            if "OCR unavailable" in raw_text or "extraction failed" in raw_text:
                st.warning(raw_text)
            with st.expander("View extracted OCR/text"):
                st.text(raw_text[:6000])
    else:
        extracted = extract_from_text(manual_text)
    if st.button("Analyze and compare", type="primary", use_container_width=True):
        st.session_state["extracted"] = extracted.to_dict()
        st.session_state["analysis"] = analyze_record(extracted.to_dict(), trusted)
        st.session_state["source"] = uploaded.name if uploaded else "manual-entry"

    if "analysis" in st.session_state:
        result = st.session_state["analysis"]
        rec = st.session_state["extracted"]
        candidate = result.get("candidate")
        c1,c2,c3 = st.columns(3)
        c1.metric("Proposed outcome", result["decision"].replace("_"," "))
        c2.metric("Heuristic confidence", f'{result["confidence"]:.1f}/100')
        c3.metric("Top candidate score", f'{candidate["candidate_score"]*100:.1f}%' if candidate else "N/A")
        st.subheader("1. Extracted fields")
        st.dataframe(pd.DataFrame([rec]), use_container_width=True, hide_index=True)
        if candidate:
            st.subheader("2. Proposed trusted-record match")
            st.dataframe(pd.DataFrame([candidate]), use_container_width=True, hide_index=True)
            st.caption("Candidate ranking uses survey-number similarity (55%) and owner-name similarity (45%).")
            if result.get("homonyms"):
                st.warning(f"⚠️ **Same-Name Disambiguation**: Found {len(result['homonyms'])} other trusted record(s) sharing the name '{candidate.get('owner_name')}' with different parcel details.")
                with st.expander("👥 Review other records sharing this owner name", expanded=True):
                    hdf = pd.DataFrame(result["homonyms"])[["record_id", "owner_name", "survey_number", "parcel_area", "record_status", "diff_summary"]]
                    hdf.columns = ["Record ID", "Owner Name", "Survey Number", "Parcel Area", "Record Status", "Differences"]
                    st.dataframe(hdf, use_container_width=True, hide_index=True)
            if result["comparison"].get("warnings"):
                for w in result["comparison"]["warnings"]:
                    st.info(f"💡 {w}")
            st.subheader("3. Consistency evidence and violated rules")
            checks = result["comparison"]["checks"]
            for field, detail in checks.items():
                st.write(("✅ " if detail["match"] else "⚠️ ") + f"**{field.replace('_',' ').title()}** — {detail['reason']}")
            if result["comparison"]["conflicts"]:
                st.error("Conflicts: " + ", ".join(result["comparison"]["conflicts"]))
            else:
                st.success("No configured consistency rule was violated.")
            st.info(result["explanation"]["summary"] + " " + result["explanation"]["confidence_note"])
            st.subheader("4. Human review")
            st.warning("A decision here records a review event only. It does not update the trusted register.")
            
            action = st.radio("Official decision", ["Approve proposed match", "Reject proposed match", "Correct extracted values"], horizontal=True)
            with st.form("review_form"):
                corrected = {}
                if action == "Correct extracted values":
                    st.caption("Enter corrected values below:")
                    col1,col2 = st.columns(2)
                    corrected["owner_name"] = col1.text_input("Correct owner name", rec.get("owner_name",""))
                    corrected["survey_number"] = col2.text_input("Correct survey number", rec.get("survey_number",""))
                    corrected["parcel_area"] = col1.text_input("Correct parcel area", rec.get("parcel_area",""))
                    corrected["record_status"] = col2.text_input("Correct record status", rec.get("record_status",""))
                note = st.text_area("Reviewer note / evidence reference")
                submitted = st.form_submit_button("Save review event", type="primary")
                if submitted:
                    decision = {"Approve proposed match":"APPROVED_BY_REVIEWER",
                                "Reject proposed match":"REJECTED_BY_REVIEWER",
                                "Correct extracted values":"CORRECTION_PROPOSED"}[action]
                    add_review_event(st.session_state.get("source","unknown"), decision,
                                     result["confidence"], candidate.get("record_id") if candidate else None,
                                     rec, corrected if corrected else None, note)
                    st.session_state["review_feedback"] = "Review event saved to the audit log. Trusted data was not modified."
                    st.session_state.pop("analysis", None)
                    st.rerun()
        else:
            st.error(result.get("reason","No candidate found."))

with tab2:
    st.subheader("Synthetic trusted reference register")
    st.dataframe(pd.DataFrame(trusted), use_container_width=True, hide_index=True)
    st.caption("This prototype loads a read-only CSV reference register. Do not place personal or confidential records in this demo.")

with tab3:
    st.subheader("Reproducible evaluation")
    st.markdown("""
    Run `python scripts/run_evaluation.py` and `pytest -q` from the project root.

    **Acceptance targets (to be validated, not assumed):**
    - Exact survey-number extraction accuracy ≥ 95% on a representative labelled test set.
    - Owner-name normalized exact/fuzzy match precision ≥ 95% at the selected threshold.
    - Conflict-classification macro F1 ≥ 0.90 on a balanced, independently labelled benchmark.
    - 100% of unresolved/low-confidence cases routed to human review.
    - 100% of review actions recorded in the audit log.
    - 0 silent modifications to trusted reference data.

    The bundled synthetic benchmark is for pipeline verification only and must not be presented as real-world accuracy.
    """)
    st.code("python scripts/run_evaluation.py\npytest -q", language="powershell")

with tab4:
    st.subheader("Append-only review events")
    events = get_review_events()
    if events:
        st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
    else:
        st.info("No review events have been recorded yet.")
st.divider()
st.markdown('<p class="small-muted">SIH 2026 prototype • Synthetic demonstration data • Human-in-the-loop decision support</p>', unsafe_allow_html=True)
