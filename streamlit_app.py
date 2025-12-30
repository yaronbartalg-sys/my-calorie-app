import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.graph_objects as go
from google.api_core import exceptions

# 1. הגדרות דף
st.set_page_config(page_title="מחשבון תזונה AI", layout="wide")

# 2. הגדרת מודל חכמה למניעת 404
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def get_model():
    try:
        # ניסיון להשתמש במודל החדש ביותר
        return genai.GenerativeModel('gemini-1.5-flash')
    except:
        # גיבוי למודל היציב הישן
        return genai.GenerativeModel('gemini-pro')

model = get_model()
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. פונקציות חישוב
def calculate_targets(weight, height, age, gender):
    if gender == "זכר":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    tdee = int(bmr * 1.2)
    return tdee, int(weight * 1.8), int((tdee * 0.25) / 9), (30 if gender == "זכר" else 25)

# 4. טעינת פרופיל מהגיליון (לשונית Profile)
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

# 5. סרגל צד (Sidebar)
with st.sidebar:
    st.header("👤 פרופיל משתמש")
    with st.expander("עדכון נתונים אישיים"):
        s_gender = st.radio("מין", ["זכר", "נקבה"], index=0 if init_gender == "זכר" else 1)
        s_weight = st.number_input("משקל (ק\"ג)", value=init_weight, step=0.1)
        s_height = st.number_input("גובה (ס\"מ)", value=init_height, step=1)
        s_age = st.number_input("גיל", value=init_age, step=1)
        s_steps = st.number_input("יעד צעדים יומי", value=init_steps, step=500)
        
        if st.button("💾 שמור נתונים לצמיתות"):
            new_profile = pd.DataFrame([{
                "Gender": s_gender, "Weight": s_weight, "Height": s_height, 
                "Age": s_age, "Steps": s_steps
            }])
            conn.update(worksheet="Profile", data=new_profile)
            st.success("הנתונים נשמרו בגיליון!")
            st.rerun()
    
    t_cal, t_prot, t_fat, t_fib = calculate_targets(s_weight, s_height, s_age, s_gender)
    total_target = t_cal + int(s_steps * 0.04)
    st.metric("🎯 יעד קלוריות יומי", f"{total_target}")
    st.write(f"💪 יעד חלבון: {t_prot}g")

st.title("🍎 יומן תזונה חכם")

# 6. מנגנון הזנה ואיפוס
if "input_counter" not in st.session_state:
    st.session_state.input_counter = 0
if "preview" not in st.session_state:
    st.session_state.preview = None
if "last_query" not in st.session_state:
    st.session_state.last_query = ""

input_key = f"food_input_{st.session_state.input_counter}"
food_query = st.text_input("מה אכלת?", key=input_key, placeholder="לדוגמה: 3 כוסות אספרסו")

if food_query and st.session_state.last_query != food_query:
   try:
            df = conn.read(worksheet="Sheet1")
            today = datetime.now().strftime("%d/%m/%Y") # כאן היה חסר סימן המירכאות
            new_row = pd.DataFrame([{
                "Date": today, 
                "Food": p['name'], 
                "Quantity": p['qty'], 
                "Calories": p['cal'], 
                "Protein": p['prot'], 
                "Fat": p['fat'], 
                "Fiber": p['fib']
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            
            # איפוס המצב
            st.session_state.preview = None
            st.session_state.last_query = ""
            st.session_state.input_counter += 1
            st.success("נוסף בהצלחה!")
            st.rerun()
   except Exception as e:
            st.error(f"שגיאה בשמירה: {e}")

if st.session_state.preview:
    p = st.session_state.preview
    st.info(f"🔍 זוהה: {p['qty']} {p['name']} ({p['cal']} קק\"ל)")
    if st.button("✅ אשר והוסף ליומן"):
        try:
            # קריאת הנתונים הקיימים
            df = conn.read(worksheet="Sheet1")
            
            # יצירת השורה החדשה עם תאריך תקין
            new_row = pd.DataFrame([{
                "Date": datetime.now().strftime("%d/%m/%Y"), # סגירת המירכאות והסוגריים כאן
                "Food": p['name'], 
                "Quantity": p['qty'], 
                "Calories": p['cal'], 
                "Protein": p['prot'], 
                "Fat": p['fat'], 
                "Fiber": p['fib']
            }])
            
            # חיבור השורה החדשה ועדכון הגליון
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            
            # איפוס המצב ומעבר לריצה חדשה
            st.session_state.preview = None
            st.session_state.last_query = ""
            st.session_state.input_counter += 1
            st.success("נוסף בהצלחה!")
            st.rerun()
        except Exception as e:
            st.error(f"שגיאה בשמירה: {e}")
