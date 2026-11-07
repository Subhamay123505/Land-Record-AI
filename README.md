# LandRecordAI — SIH 2026 Prototype

**Individual Land Record Extraction and Consistency Reasoning System for Decision Support**

A reproducible decision-support prototype that extracts fields from land-record documents, matches them against a trusted reference register, explains consistency conflicts, scores evidence, and routes uncertain cases to a human reviewer. It never silently overwrites trusted records.

> This is a research/demo prototype using synthetic records. It is not an official land-record system, legal opinion, title verification service, or substitute for a government registry.

## Features
- Upload TXT, PDF, PNG, JPG/JPEG, or CSV record files.
- Extract owner, survey number, parcel area/unit, and record status.
- Normalize common spelling/format differences.
- Match candidate trusted records using explainable fuzzy/token similarity.
- Optional local Sentence Transformers similarity if installed and explicitly enabled in code.
- Production rules classify owner, survey, area, status, missing-field, and duplicate-candidate conflicts.
- Confidence score and evidence breakdown.
- Human review: approve, reject, or correct proposed extracted values.
- Append-only review audit trail in SQLite; trusted reference data is read-only in the application.
- Synthetic clean/noisy/conflicting cases and a reproducible evaluation script.
- Unit tests and acceptance criteria.

## Quick start (Windows PowerShell)
```powershell
cd LandRecordAI
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```
Open the local URL printed by Streamlit (normally http://localhost:8501).

## OCR setup
Text PDFs and TXT files work without external OCR software. For scanned PDFs/images, install Tesseract OCR separately and ensure `tesseract.exe` is on PATH. On Windows, the common installer is maintained by UB Mannheim. Restart the terminal after installation. If OCR is unavailable, paste extracted text into the manual text area.

## Data
- `data/trusted_records.csv`: synthetic trusted reference records.
- `data/evaluation_cases.json`: labelled synthetic test cases.
- `data/samples/`: synthetic text documents for demo.
- Do not commit real personal land records or identity data.

## Evaluation
```powershell
python scripts/run_evaluation.py
pytest -q
```
The evaluation reports exact field extraction/matching and conflict classification metrics on the included synthetic benchmark. Results are not evidence of production performance; use a representative, legally authorized, independently labelled dataset before making real-world claims.

## Deployment (Streamlit Community Cloud)
1. Push this repository to GitHub.
2. Visit https://share.streamlit.io/ and connect GitHub.
3. Select this repository, branch `main`, and `app.py`.
4. Deploy. Add no secrets for the synthetic demo.
5. For production, use a secured database, authentication, authorization, encryption, retention controls, and approved hosting.

## Architecture
`Upload -> Extraction -> Normalization -> Candidate Matching -> Production Rules -> Confidence & Evidence -> Human Review -> Append-only Audit`

See `docs/PROJECT_REPORT.md` and `docs/PPT_OUTLINE.md`.

## Limitations and safety
- Synthetic data only; no live government registry integration.
- OCR quality depends on scan quality, language, layout, and Tesseract language packs.
- Matching thresholds are configurable and require domain validation.
- Confidence is a transparent heuristic score, not a calibrated probability.
- A human official must make the final decision. Approval records a review event; it does not alter trusted records.
