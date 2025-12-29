import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.graph_objects as go
from google.api_core import exceptions

# הגדרות דף
st.set_page_config(page_title="מחשבון תזונה AI", layout="wide")

# חיבורים
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')
conn = st.connection("gsheets", type=GSheetsConnection)

# --- פונקציות חישוב ---
def calculate_targets(weight, height, age, gender):
    if gender == "זכר":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    tdee = int(bmr * 1.2)
    return tdee, int(weight * 1.8), int((tdee * 0.25) / 9), (30 if gender == "זכר" else 25)

# --- טעינת פרופיל מהגיליון ---
try:
    profile_df = conn.read(worksheet="Profile", ttl=0)
    if not profile_df.empty:
        p_data = profile_df.iloc[0]
        initial_gender = p_data['Gender']
        initial_weight = float(p_data['Weight'])
        initial_height = int(p_data['Height'])
        initial_age = int(p_data['Age'])
        initial_steps = int(p_data['Steps'])
    else:
        initial_gender, initial_weight, initial_height, initial_age, initial_steps = "נקבה", 60.0, 165, 25, 5000
except:
    initial_gender, initial_weight, initial_height, initial_age, initial_steps = "נקבה", 60.0, 165, 25, 5000

# --- סרגל צד (Sidebar) ---
with st.sidebar:
    st.header("👤 פרופיל משתמש")
    with st.expander("עדכון נתונים אישיים"):
        s_gender = st.radio("מין", ["זכר", "נקבה"], index=0 if initial_gender == "זכר" else 1)
        s_weight = st.number_input("משקל (ק\"ג)", value=initial_weight, step=0.1)
        s_height = st.number_input("גובה (ס\"מ)", value=initial_height, step=1)
        s_age = st.number_input("גיל", value=initial_age, step=1)
        s_steps = st.number_input("יעד צעדים יומי", value=initial_steps, step=500)
        
        if st.button("💾 שמור נתונים לצמיתות"):
            new_profile = pd.DataFrame([{
                "Gender": s_gender, "Weight": s_weight, "Height": s_height, 
                "Age": s_age, "Steps": s_steps
            }])
            conn.update(worksheet="Profile", data=new_profile)
            st.success("הנתונים נשמרו בגיליון!")
            st.rerun()
    
    st.write(f"📊 **נתונים:** {s_gender} | {s_weight} ק\"ג | {s_height} ס\"מ")
    t_cal, t_prot, t_fat, t_fib = calculate_targets(s_weight, s_height, s_age, s_gender)
    
    st.divider()
    # חישוב בונוס צעדים
    step_bonus = int(s_steps * 0.04) 
    total_target = t_cal + step_bonus
    st.info(f"🎯 יעד קלוריות יומי: {total_target}")

st.title("🍎 יומן תזונה חכם")

# (כאן מגיע שאר הקוד של הזנת הארוחות והגרפים - הוא נשאר אותו דבר)
# --- מנגנון איפוס חכם ---
if "input_counter" not in st.session_state:
    st.session_state.input_counter = 0
if "preview" not in st.session_state:
    st.session_state.preview = None
if "last_processed_query" not in st.session_state:
    st.session_state.last_processed_query = ""

input_key = f"food_input_{st.session_state.input_counter}"
food_query = st.text_input("מה אכלת?", key=input_key, placeholder="לדוגמה: 3 כוסות אספרסו")

if food_query and st.session_state.last_processed_query != food_query:
    try:
        with st.spinner('מנתח נתונים...'):
            prompt = "Return ONLY: Food Name (Hebrew), Calories (int), Protein (float), Fat (float), Fiber (float), Detected Quantity (Short Hebrew description) separated by commas."
            response = model.generate_content(f"{prompt} \n Input: {food_query}")
            res = response.text.strip().split(',')
            if len(res) >= 6:
                st.session_state.preview = {
                    "name": res[0].strip(), "cal": int(res[1].strip()), 
                    "prot": float(res[2].strip()), "fat": float(res[3].strip()), 
                    "fib": float(res[4].strip()), "qty": res[5].strip()
                }
                st.session_state.last_processed_query = food_query
    except exceptions.ResourceExhausted:
        st.error("⚠️ הגענו למכסת הבקשות. נסה שוב בעוד דקה.")
    except Exception as e:
        st.error(f"שגיאה: {e}")

if st.session_state.preview:
    p = st.session_state.preview
    st.warning(f"🔍 **ה-AI זיהה:** {p['qty']} של {p['name']} | 🔥 {p['cal']} קק\"ל")
    if st.button("✅ אשר והוסף ליומן"):
        df = conn.read(worksheet="Sheet1")
        new_row = pd.DataFrame([{"Date": datetime.now().strftime("%d/%m/%Y"), "Food": p['name'], "Quantity": p['qty'], "Calories": p['cal'], "Protein": p['prot'], "Fat": p['fat'], "Fiber": p['fib']}])
        conn.update(worksheet="Sheet1", data=pd.concat([df, new_row], ignore_index=True))
        st.session_state.preview = None
        st.session_state.last_processed_query = ""
        st.session_state.input_counter += 1
        st.rerun()

# הצגת הגרפים והסיכומים (כמו בקוד הקודם)
# ... [המשך הקוד עם הגרפים] ...
