import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.graph_objects as go

# הגדרות דף
st.set_page_config(page_title="מחשבון תזונה AI", layout="wide")

# חיבורים
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-flash-lite-latest')
conn = st.connection("gsheets", type=GSheetsConnection)

# --- פונקציות חישוב ---
def calculate_targets(weight, height, age, gender):
    if gender == "זכר":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    tdee = int(bmr * 1.2)
    return tdee, int(weight * 1.8), int((tdee * 0.25) / 9), (30 if gender == "זכר" else 25)

# --- סרגל צד (Sidebar) ---
with st.sidebar:
    st.header("👤 פרופיל משתמש")
    with st.expander("עדכון נתונים אישיים"):
        s_gender = st.radio("מין", ["זכר", "נקבה"], index=0)
        s_weight = st.number_input("משקל (ק\"ג)", value=80.0, step=0.1)
        s_height = st.number_input("גובה (ס\"מ)", value=175, step=1)
        s_age = st.number_input("גיל", value=30, step=1)
    
    st.write(f"📊 **נתונים:** {s_gender} | {s_weight} ק\"ג | {s_height} ס\"מ | גיל {s_age}")
    t_cal, t_prot, t_fat, t_fib = calculate_targets(s_weight, s_height, s_age, s_gender)
    
    st.divider()
    steps = st.number_input("צעדים היום", value=0, step=500)
    step_bonus = int(steps * 0.04) 
    total_target = t_cal + step_bonus
    st.info(f"🎯 יעד קלוריות: {total_target}")

st.title("🍎 יומן תזונה חכם")

# --- מנגנון הזנה ואיפוס ---
if "preview" not in st.session_state:
    st.session_state.preview = None

# שימוש ב-key כדי לשלוט באיפוס השדה
food_query = st.text_input("מה אכלת?", key="food_entry", placeholder="לדוגמה: חביתה משתי ביצים")

if food_query and st.session_state.get('last_processed_query') != food_query:
    with st.spinner('מנתח נתונים...'):
        prompt = "Return ONLY: Food Name (Hebrew), Calories (int), Protein (float), Fat (float), Fiber (float) separated by commas."
        response = model.generate_content(f"{prompt} \n Input: {food_query}")
        res = response.text.strip().split(',')
        if len(res) >= 5:
            st.session_state.preview = {
                "name": res[0], "cal": int(res[1]), "prot": float(res[2]),
                "fat": float(res[3]), "fib": float(res[4])
            }
            st.session_state.last_processed_query = food_query

if st.session_state.preview:
    p = st.session_state.preview
    st.warning(f"🔍 **בדיקה:** {p['name']} | 🔥 {p['cal']} קק\"ל | 💪 {p['prot']}g חלבון")
    
    if st.button("✅ אשר והוסף ליומן"):
        try:
            df = conn.read(worksheet="Sheet1")
            today = datetime.now().strftime("%d/%m/%Y")
            new_row = pd.DataFrame([{"Date": today, "Food": p['name'], "Calories": p['cal'], 
                                     "Protein": p['prot'], "Fat": p['fat'], "Fiber": p['fib']}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            
            # איפוס המצב
            st.session_state.preview = None
            st.session_state.last_processed_query = ""
            st.session_state.food_entry = "" # מאפס את שדה הטקסט
            
            st.success("נוסף בהצלחה!")
