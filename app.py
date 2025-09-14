
import os
import random
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Nurse NCLEX Coach", page_icon="🩺", layout="centered")

st.title("🩺 Nurse NCLEX Coach")
st.caption("Practice NCLEX-style questions with instant rationales. Educational use only.")

@st.cache_data
def load_questions():
    path = "nclex_questions.csv"
    if not os.path.exists(path):
        st.error("nclex_questions.csv not found. Add your CSV to the repo.")
        st.stop()
    df = pd.read_csv(path)
    # basic cleanup
    df["Type"] = df["Type"].fillna("MCQ")
    df["Category"] = df["Category"].fillna("General")
    df["Difficulty"] = df["Difficulty"].fillna("Moderate")
    df["Options (A–E)"] = df["Options (A–E)"].fillna("")
    return df

df = load_questions()

# ----- sidebar: filters & score -----
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

# ----- helpers -----
LABELS_ALPHA = ["A","B","C","D","E"]

def parse_options(opt_str):
    # split by pipe and strip
    parts = [p.strip() for p in str(opt_str).split("|")]
    return [p for p in parts if p]

def get_selected_label(choice_text):
    # choice like "A) something" or "1) something" --> "A" or "1"
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
                lab = str(idx+1)
            except:
                lab = s
        labels.append(lab)
    return [str(x) for x in labels]

def check_answer(row, user_choice, user_multi):
    correct_field = str(row["Correct Answer(s)"]).strip()
    qtype = row["Type"].strip().upper()
    if qtype == "SATA":
        correct_set = set([c.strip() for c in correct_field.split(",") if c.strip()])
        sel_labels = set(normalize_sata_selection(user_multi or []))
        return sel_labels == correct_set
    else:
        if not user_choice:
            return False
        picked_label = get_selected_label(user_choice)
        if picked_label and picked_label.isdigit():
            try:
                picked_label = LABELS_ALPHA[int(picked_label)-1]
            except:
                pass
        return (picked_label or "").upper() == correct_field.upper()

# ----- main area -----
if "current_row" not in st.session_state:
    st.session_state.current_row = None

col1, col2 = st.columns([1,1])
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

    if row["Type"].strip().upper() == "SATA":
        st.session_state.user_multi = st.multiselect("Select all that apply:", options, default=st.session_state.get("user_multi", []))
    else:
        st.session_state.user_choice = st.radio("Choose one:", options, index=None)

    if col2.button("✅ Check Answer"):
        st.session_state.score["total"] += 1
        ok = check_answer(row, st.session_state.get("user_choice"), st.session_state.get("user_multi"))
        if ok:
            st.session_state.score["correct"] += 1
            st.success("Correct! 🎉")
        else:
            st.error("Not quite. Keep going — you’ve got this.")
        st.info(f"**Rationale:** {row['Rationale']}")
        st.caption(f"Last Updated: {row['Last Updated']}")

st.sidebar.header("Progress")
t = st.session_state.score["total"]
c = st.session_state.score["correct"]
if t:
    pct = round(100*c/t)
    st.sidebar.metric("Score", f"{c}/{t}", delta=f"{pct}%")
else:
    st.sidebar.write("Score: 0/0")
st.sidebar.markdown("---")
st.sidebar.write("© Your Brand • Educational use only • Not medical advice.")
