import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

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
    st.header("👤 נתונים אישיים")
    gender = st.radio("מין", ["זכר", "נקבה"])
    weight = st.number_input("משקל (ק\"ג)", value=80.0)
    height = st.number_input("גובה (ס\"מ)", value=175)
    age = st.number_input("גיל", value=30)
    
    t_cal, t_prot, t_fat, t_fib = calculate_targets(weight, height, age, gender)
    
    st.divider()
    steps = st.number_input("צעדים היום", value=0, step=500)
    step_bonus = int(steps * 0.04) 
    
    st.info(f"🎯 יעד קלוריות: {t_cal + step_bonus} (כולל {step_bonus} בונוס פעילות)")

st.title("🍎 יומן תזונה חכם")

# --- ממשק הזנה עם בדיקה לפני שמירה ---
food_query = st.text_input("מה אכלת?", placeholder="לדוגמה: קערת אורז עם עדשים")

if food_query:
    # מנגנון למניעת הרצה כפולה של ה-AI על אותו טקסט
    if 'last_q' not in st.session_state or st.session_state.last_q != food_query:
        with st.spinner('מנתח נתונים...'):
            prompt = "Return ONLY: Food Name (Hebrew), Calories (int), Protein (float), Fat (float), Fiber (float) separated by commas."
            response = model.generate_content(f"{prompt} \n Input: {food_query}")
            res = response.text.strip().split(',')
            if len(res) >= 5:
                st.session_state.preview = {
                    "name": res[0], "cal": int(res[1]), "prot": float(res[2]),
                    "fat": float(res[3]), "fib": float(res[4])
                }
                st.session_state.last_q = food_query

    if 'preview' in st.session_state:
        p = st.session_state.preview
        st.warning(f"🔍 **בדיקה לפני שמירה:** {p['name']} | 🔥 קלוריות: {p['cal']} | 💪 חלבון: {p['prot']}g")
        if st.button("✅ אשר והוסף ליומן"):
            try:
                df = conn.read(worksheet="Sheet1")
                today = datetime.now().strftime("%d/%m/%Y")
                new_row = pd.DataFrame([{"Date": today, "Food": p['name'], "Calories": p['cal'], 
                                         "Protein": p['prot'], "Fat": p['fat'], "Fiber": p['fib']}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("הארוחה נוספה!")
                del st.session_state.preview
                st.rerun()
            except Exception as e:
                st.error(f"שגיאה בשמירה: {e}")

# --- תצוגת נתונים וסיכומים ---
st.divider()
try:
    data = conn.read(worksheet="Sheet1", ttl=0)
    if not data.empty:
        for c in ['Calories', 'Protein', 'Fat', 'Fiber']:
            data[c] = pd.to_numeric(data[c], errors='coerce').fillna(0)
        
        today_str = datetime.now().strftime("%d/%m/%Y")
        today_df = data[data['Date'] == today_str]
        
        c_cal = int(today_df['Calories'].sum())
        rem_cal = (t_cal + step_bonus) - c_cal

        # מדדים עליונים
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("נאכל היום", f"{c_cal} קק\"ל")
        col_m2.metric("בונוס צעדים", f"{step_bonus} קק\"ל")
        col_m3.metric("נותר לצריכה", f"{rem_cal} קק\"ל", delta=rem_cal, delta_color="normal")

        # טבלת ארוחות עם אפשרות מחיקה
        st.subheader("📋 ארוחות היום")
        for idx, row in today_df.iterrows():
            c_row = st.columns([4, 1, 1, 1, 1])
            c_row[0].write(f"🍴 {row['Food']}")
            c_row[1].write(f"🔥 {row['Calories']}")
            c_row[2].write(f"💪 {row['Protein']}g")
            c_row[3].write(f"🌾 {row['Fiber']}g")
            if c_row[4].button("🗑️", key=f"del_{idx}"):
                new_data = data.drop(idx)
                conn.update(worksheet="Sheet1", data=new_data)
                st.rerun()
except:
    st.info("ממתין לנתונים בגיליון...")
