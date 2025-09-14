import os
import pandas as pd
import streamlit as st
import urllib.parse as up

# ============= BRAND / PILOT SETTINGS =============
BRAND_NAME = "Nurse NCLEX Coach"
ACCENT_HEX = "#6C63FF"  # tweak if you want
FOOTER_TEXT = "© Your Brand • Educational use only • Not medical advice."
# Put your Google Form "base" URL here (leave "" to hide feedback link)
# Example: "https://docs.google.com/forms/d/e/FORM_ID/viewform"
FEEDBACK_FORM_BASE = ""

# Field IDs from your Google Form's "Get prefilled link" (optional)
FORM_FIELD_QID   = "entry.111111"  # Question ID
FORM_FIELD_CAT   = "entry.222222"  # Category
FORM_FIELD_TYPE  = "entry.333333"  # Type

# ============= PAGE SETUP =============
st.set_page_config(page_title=BRAND_NAME, page_icon="🩺", layout="centered")
st.markdown(
    f"""
    <style>
      .st-emotion-cache-ocqkz7 {{ color:{ACCENT_HEX} !important; }} /* some titles */
      .stButton>button {{ border-radius:10px; }}
    </style>
    """,
    unsafe_allow_html=True,
)
st.title(f"🩺 {BRAND_NAME}")
st.caption("Practice NCLEX-style questions with instant rationales. Educational use only.")

# ============= DATA LOADING =============
@st.cache_data
def load_questions():
    path = "nclex_questions.csv"
    if not os.path.exists(path):
        st.error("nclex_questions.csv not found. Add your CSV to the repo root.")
        st.stop()
    df = pd.read_csv(path)

    # Basic hygiene
    for col, default in [
        ("Type", "MCQ"),
        ("Category", "General"),
        ("Difficulty", "Moderate"),
        ("Options (A–E)", ""),
    ]:
        if col not in df.columns:
            st.error(f"Missing column: {col}")
            st.stop()
        df[col] = df[col].fillna(default)

    # Hide any old placeholder rows just in case
    if "Question" in df.columns:
        df = df[~df["Question"].str.startswith("Sample NCLEX Question", na=False)]

    return df

df = load_questions()
st.caption(
    f"Loaded **{len(df)}** questions • Latest update: "
    f"{df['Last Updated'].max() if 'Last Updated' in df.columns else '—'}"
)

# ============= SIDEBAR FILTERS & SCORE =============
if "score" not in st.session_state:
    st.session_state.score = {"total": 0, "correct": 0}

st.sidebar.header("Filters")
cats = ["All"] + sorted(df["Category"].dropna().unique().tolist())
types = ["All"] + sorted(df["Type"].dropna().unique().tolist())
diffs = ["All"] + sorted(df["Difficulty"].dropna().unique().tolist())

sel_cat = st.sidebar.selectbox("Category", cats)
sel_type = st.sidebar.selectbox("Type", types)
sel_diff = st.sidebar.selectbox("Difficulty", diffs)

def filtered_df():
    d = df.copy()
    if sel_cat != "All":
        d = d[d["Category"] == sel_cat]
    if sel_type != "All":
        d = d[d["Type"] == sel_type]
    if sel_diff != "All":
        d = d[d["Difficulty"] == sel_diff]
    return d

# ============= HELPERS =============
LABELS_ALPHA = ["A", "B", "C", "D", "E"]

def parse_options(opt_str: str):
    parts = [p.strip() for p in str(opt_str).split("|")]
    return [p for p in parts if p]

def get_selected_label(choice_text: str):
    if not choice_text:
        return None
    if ") " in choice_text:
        return choice_text.split(")")[0].strip()
    return None

def normalize_sata_selection(selections):
    labels = []
    for s in selections:
        lab = get_selected_label(s)
        if lab is None:
            try:
                idx = selections.index(s)
                lab = str(idx + 1)
            except Exception:
                lab = s
        labels.append(str(lab))
    return labels

def check_answer(row, user_choice, user_multi):
    correct_field = str(row["Correct Answer(s)"]).strip()
    qtype = (row["Type"] or "").strip().upper()

    if qtype == "SATA":
        correct_set = set([c.strip() for c in correct_field.split(",") if c.strip()])
        sel_labels = set(normalize_sata_selection(user_multi or []))
        return sel_labels == correct_set

    if not user_choice:
        return False
    picked_label = get_selected_label(user_choice)

    if picked_label and picked_label.isdigit():
        try:
            picked_label = LABELS_ALPHA[int(picked_label) - 1]
        except Exception:
            pass

    return (picked_label or "").upper() == correct_field.upper()

# ============= SESSION STATE (Daily 10) =============
ss = st.session_state
if "current_row" not in ss:
    ss.current_row = None
if "in_batch" not in ss:
    ss.in_batch = False
if "batch_df" not in ss:
    ss.batch_df = None
if "batch_idx" not in ss:
    ss.batch_idx = 0
if "answered" not in ss:
    ss.answered = False
if "batch_correct" not in ss:
    ss.batch_correct = 0

# ============= TOP CONTROLS =============
col_l, col_r = st.columns([1,1])

# Start/stop Daily 10
with col_l:
    if not ss.in_batch:
        if st.button("🔥 Start Daily 10"):
            d = filtered_df()
            if d.empty:
                st.warning("No questions match your filters.")
            else:
                take = min(10, len(d))
                ss.batch_df = d.sample(take).reset_index(drop=True)
                ss.batch_idx = 0
                ss.in_batch = True
                ss.answered = False
                ss.batch_correct = 0
                ss.current_row = ss.batch_df.iloc[0]
                ss.user_choice = None
                ss.user_multi = []
    else:
        pb = (ss.batch_idx) / max(1, len(ss.batch_df))
        st.progress(pb, text=f"Daily 10 • {ss.batch_idx}/{len(ss.batch_df)} done")
        if st.button("⏹ End Daily 10"):
            ss.in_batch = False
            st.experimental_rerun()

# Ad-hoc random practice
with col_r:
    if not ss.in_batch and st.button("🎲 New Question"):
        d = filtered_df()
        if d.empty:
            st.warning("No questions match your filters.")
        else:
            ss.current_row = d.sample(1).iloc[0]
            ss.answered = False
            ss.user_choice = None
            ss.user_multi = []

# ============= RENDER QUESTION =============
if ss.current_row is not None:
    row = ss.current_row
    st.subheader(row["Question"])
    st.caption(f"Category: {row['Category']} • Type: {row['Type']} • Difficulty: {row['Difficulty']}")

    options = parse_options(row["Options (A–E)"])
    qtype = (row["Type"] or "").strip().upper()

    if qtype == "SATA":
        ss.user_multi = st.multiselect(
            "Select all that apply:", options, default=ss.get("user_multi", [])
        )
    else:
        ss.user_choice = st.radio("Choose one:", options, index=None)

    # ---- Grade (rationale only) ----
    if st.button("✅ Check Answer", type="primary"):
        ss.score["total"] += 1
        ok = check_answer(row, ss.get("user_choice"), ss.get("user_multi"))
        if ok:
            st.success("Correct! 🎉")
            ss.score["correct"] += 1
            if ss.in_batch:
                ss.batch_correct += 1
        else:
            st.error("Not quite. Keep going — you’ve got this.")
        st.info(f"**Rationale:** {row['Rationale']}")
        st.caption(f"Last Updated: {row.get('Last Updated','—')}")
        ss.answered = True

    # ---- Next in Daily 10 ----
    if ss.in_batch and ss.answered:
        coln1, coln2 = st.columns([1,4])
        with coln1:
            if st.button("➡ Next"):
                ss.batch_idx += 1
                ss.answered = False
                if ss.batch_idx >= len(ss.batch_df):
                    # summary
                    total = len(ss.batch_df)
                    correct = ss.batch_correct
                    st.success(f"Daily 10 complete! Score: {correct}/{total} ({round(100*correct/total)}%)")
                    ss.in_batch = False
                    ss.current_row = None
                else:
                    ss.current_row = ss.batch_df.iloc[ss.batch_idx]
                    ss.user_choice = None
                    ss.user_multi = []

# ============= SIDEBAR: PROGRESS & FOOTER =============
st.sidebar.header("Progress")
t = ss.score["total"]
c = ss.score["correct"]
if t:
    pct = round(100 * c / t)
    st.sidebar.metric("Score", f"{c}/{t}", delta=f"{pct}%")
else:
    st.sidebar.write("Score: 0/0")

st.sidebar.markdown("---")
st.sidebar.write(FOOTER_TEXT)

# ============= FEEDBACK LINK (optional) =============
def feedback_link(row):
    if not FEEDBACK_FORM_BASE:
        return ""
    params = {
        FORM_FIELD_QID: int(row.get("ID", 0)),
        FORM_FIELD_CAT: str(row.get("Category", "")),
        FORM_FIELD_TYPE: str(row.get("Type", "")),
    }
    return FEEDBACK_FORM_BASE + "?" + up.urlencode(params)

if ss.current_row is not None and FEEDBACK_FORM_BASE:
    with st.expander("💬 Give quick feedback on this question"):
        url = feedback_link(ss.current_row)
        st.markdown(f"[Open feedback form]({url})")

