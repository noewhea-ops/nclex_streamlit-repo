import os
import pandas as pd
import streamlit as st

# ---------- Page setup ----------
st.set_page_config(page_title="Nurse NCLEX Coach", page_icon="🩺", layout="centered")
st.title("🩺 Nurse NCLEX Coach")
st.caption("Practice NCLEX-style questions with instant rationales. Educational use only.")

# ---------- Data loading ----------
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

# ---------- Sidebar: filters & score ----------
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

# ---------- Helpers ----------
LABELS_ALPHA = ["A", "B", "C", "D", "E"]

def parse_options(opt_str: str):
    """Split pipe-delimited options and trim."""
    parts = [p.strip() for p in str(opt_str).split("|")]
    return [p for p in parts if p]

def get_selected_label(choice_text: str):
    """
    Extract the leading label from a choice like 'A) foo' or '1) foo'.
    Returns 'A'/'B'/... or '1'/'2'/...; None if not found.
    """
    if not choice_text:
        return None
    if ") " in choice_text:
        return choice_text.split(")")[0].strip()
    return None

def normalize_sata_selection(selections):
    """Turn a list of selected option texts into label strings (e.g., ['1','4'] or ['A','C'])."""
    labels = []
    for s in selections:
        lab = get_selected_label(s)
        if lab is None:
            # fallback: try to map by list position
            try:
                idx = selections.index(s)
                lab = str(idx + 1)
            except Exception:
                lab = s
        labels.append(str(lab))
    return labels

def check_answer(row, user_choice, user_multi):
    """
    Return True/False depending on whether the user's selection matches the correct answer(s).
    Works for MCQ and SATA (select-all-that-apply).
    """
    correct_field = str(row["Correct Answer(s)"]).strip()
    qtype = (row["Type"] or "").strip().upper()

    if qtype == "SATA":
        correct_set = set([c.strip() for c in correct_field.split(",") if c.strip()])
        sel_labels = set(normalize_sata_selection(user_multi or []))
        return sel_labels == correct_set

    # MCQ, Case, Prioritization => one choice only
    if not user_choice:
        return False
    picked_label = get_selected_label(user_choice)

    # Map numeric '2' -> 'B'
    if picked_label and picked_label.isdigit():
        try:
            picked_label = LABELS_ALPHA[int(picked_label) - 1]
        except Exception:
            pass

    return (picked_label or "").upper() == correct_field.upper()

# ---------- Main area ----------
if "current_row" not in st.session_state:
    st.session_state.current_row = None

col1, col2 = st.columns([1, 1])

if col1.button("🎲 New Question"):
    d = filtered_df()
    if d.empty:
        st.warning("No questions match your filters.")
    else:
        st.session_state.current_row = d.sample(1).iloc[0]
        st.session_state.feedback = None
        st.session_state.user_choice = None
        st.session_state.user_multi = []

if st.session_state.current_row is not None:
    row = st.session_state.current_row
    st.subheader(row["Question"])
    st.caption(f"Category: {row['Category']} • Type: {row['Type']} • Difficulty: {row['Difficulty']}")

    options = parse_options(row["Options (A–E)"])

    # UI for selection
    if (row["Type"] or "").strip().upper() == "SATA":
        st.session_state.user_multi = st.multiselect(
            "Select all that apply:", options, default=st.session_state.get("user_multi", [])
        )
    else:
        st.session_state.user_choice = st.radio("Choose one:", options, index=None)

    # ---------- CHECK ANSWER (grade + rationale only) ----------
    if col2.button("✅ Check Answer"):
        st.session_state.score["total"] += 1

        ok = check_answer(
            row,
            st.session_state.get("user_choice"),
            st.session_state.get("user_multi"),
        )

        if ok:
            st.success("Correct! 🎉")
            st.session_state.score["correct"] += 1
        else:
            st.error("Not quite. Keep going — you’ve got this.")

        # Always show the rationale only
        st.info(f"**Rationale:** {row['Rationale']}")
        st.caption(f"Last Updated: {row['Last Updated']}")

# ---------- Sidebar: progress ----------
st.sidebar.header("Progress")
t = st.session_state.score["total"]
c = st.session_state.score["correct"]
if t:
    pct = round(100 * c / t)
    st.sidebar.metric("Score", f"{c}/{t}", delta=f"{pct}%")
else:
    st.sidebar.write("Score: 0/0")

st.sidebar.markdown("---")
st.sidebar.write("© Your Brand • Educational use only • Not medical advice.")
