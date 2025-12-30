import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.graph_objects as go
from google.api_core import exceptions

# הגדרות דף
st.set_page_config(page_title="מחשבון תזונה AI", layout="wide")

# --- הגדרת מודל חכמה למניעת 404 ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def get_model():
    # רשימת עדיפויות למודלים
    model_options = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    
    # ניסיון למצוא מודל זמין מתוך הרשימה של גוגל
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for opt in model_options:
            # בודק אם השם קיים ברשימת המודלים (עם או בלי הקידומת models/)
            if any(opt in m for m in available_models):
                return genai.GenerativeModel(opt)
    except:
        # אם אין גישה לרשימה, נלך על בטוח
        return genai.GenerativeModel('gemini-pro')
    
    return genai.GenerativeModel('gemini-pro')

model = get_model()
conn = st.connection("gsheets", type=GSheetsConnection)

# --- פונקציות חישוב ---
def calculate_targets(weight, height, age, gender):
    if gender == "זכר":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    tdee = int(bmr * 1.2)
    return tdee, int(weight * 1.8), int((tdee * 0.25) / 9), (30 if gender == "זכר" else 25)

# --- טעינת פרופיל (שימור נתונים) ---
try:
    profile_df = conn.read(worksheet="Profile", ttl=0)
    if not profile_df.empty:
        p_data = profile_df.iloc[-1]
        init_gender = p_data['Gender']
        init_weight = float(p_data['Weight'])
        init_height = int(p_data['Height'])
        init_age = int(p_data['Age'])
        init_steps = int(p_data['Steps'])
    else:
        init_gender, init_weight, init_height, init_age, init_steps = "נקבה", 60.0, 165, 25, 5000
except:
    init_gender, init_weight, init_height, init_age, init_steps = "נקבה", 60.0, 165, 25, 5000

# --- סרגל צד (Sidebar) ---
with st.sidebar:
    st.header("👤 פרופיל משתמש")
    with st.expander("עדכון נתונים אישיים"):
        s_gender = st.radio("מין", ["זכר", "נקבה"], index=0 if init_gender == "זכר" else 1)
        s_weight = st.number_input("משקל (ק\"ג)", value=init_weight, step=0.1)
        s_height = st.number_input("גובה (ס\"מ)", value=init_height, step=1)
        s_age = st.number_input("גיל", value=init_age, step=1)
        s_steps = st.number_input("יעד צעדים יומי", value=init_steps, step=500)
        
        if st.button("💾 שמור נתונים"):
            new_profile = pd.DataFrame([{
                "Gender": s_gender, "Weight": s_weight, "Height": s_height, 
                "Age": s_age, "Steps": s_steps
            }])
            conn.update(worksheet="Profile", data=new_profile)
            st.success("נשמר!")
            st.rerun()
    
    t_cal, t_prot, t_fat, t_fib = calculate_targets(s_weight, s_height, s_age, s_gender)
    total_target = t_cal + int(s_steps * 0.04)
    st.metric("🎯 יעד קלוריות", f"{total_target}")

# --- הזנה (Rest of your code) ---
st.title("🍎 יומן תזונה חכם")
if "input_counter" not in st.session_state: st.session_state.input_counter = 0
if "preview" not in st.session_state: st.session_state.preview = None

input_key = f"food_input_{st.session_state.input_counter}"
food_query = st.text_input("מה אכלת?", key=input_key)

if food_query and st.session_state.get('last_query') != food_query:
    try:
        with st.spinner('מנתח...'):
            prompt = "Return ONLY: Food Name (Hebrew), Calories (int), Protein (float), Fat (float), Fiber (float), Quantity (Hebrew) separated by commas."
            response = model.generate_content(f"{prompt} \n Input: {food_query}")
            res = response.text.strip().split(',')
            if len(res) >= 6:
                st.session_state.preview = {
                    "name": res[0].strip(), "cal": int(res[1].strip()), 
                    "prot": float(res[2].strip()), "fat": float(res[3].strip()), 
                    "fib": float(res[4].strip()), "qty": res[5].strip()
                }
                st.session_state.last_query = food_query
    except Exception as e:
        st.error(f"שגיאה בניתוח: {e}")

if st.session_state.preview:
    p = st.session_state.preview
    st.info(f"🔍 זוהה: {p['qty']} {p['name']} ({p['cal']} קק\"ל)")
    if st.button("✅ הוסף"):
