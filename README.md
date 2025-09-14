
# 🩺 Nurse NCLEX Coach — Streamlit App

A lightweight web app that serves NCLEX-style questions with rationales.
Deploy on Streamlit Community Cloud in minutes.

## Files
- `app.py` — Streamlit app
- `nclex_questions.csv` — your question bank (same columns we used in ChatGPT)
- `requirements.txt` — minimal dependencies
- `README.md` — this guide

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud
1. Create a new **public GitHub repo** and upload these files.
2. Go to https://share.streamlit.io and click **New app**.
3. Point it at your repo and choose `app.py`.
4. Click **Deploy**. You’ll get a public URL to share.

## CSV schema
Columns (headers must match exactly):
- ID
- Question
- Type  (MCQ | SATA | Case | Prioritization)
- Options (A–E)  (pipe-separated string, e.g., `A) ... | B) ... | C) ... | D) ...` or `1) ... | 2) ... | 3) ... | 4) ... | 5) ...` for SATA)
- Correct Answer(s)  (e.g., `B` for MCQ or `1,3,4` for SATA)
- Rationale
- Category
- Difficulty (Easy | Moderate | Hard)
- Last Updated (YYYY-MM-DD)

## Tips
- Add more rows to `nclex_questions.csv` anytime and redeploy.
- To pull from Google Sheets instead: publish your sheet as CSV and replace the loader in `app.py` with `pd.read_csv(<published_csv_url>)`.
- Add branding by editing the `st.title()` and footer text in `app.py`.
