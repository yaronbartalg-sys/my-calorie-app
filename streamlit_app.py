import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.graph_objects as go

# 1. הגדרות דף
st.set_page_config(page_title="מחשבון תזונה AI", layout="wide")

# 2. הגדרת AI ומודל (הגדרה ישירה למניעת שגיאת undefined)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# נשתמש ב-gemini-1.5-flash כברירת מחדל
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception:
    # אם יש בעיה בגרסה, נשתמש ב-gemini-pro הישן והיציב
    model = genai.GenerativeModel('gemini-pro')

# 3. חיבור לגיליון גוגל
conn = st.connection("gsheets", type=GSheetsConnection)

# 4. פונקציות חישוב
def calculate_targets(weight, height, age, gender):
    if gender == "זכר":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    tdee = int(bmr * 1.2)
    return tdee, int(weight * 1.8), int((tdee * 0.25) / 9), (30 if gender == "זכר" else 25)

# 5. טעינת פרופיל מהגיליון
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
except Exception:
    init_gender, init_weight, init_height, init_age, init_steps = "נקבה", 60.0, 165, 25, 5000

# 6. סרגל צד (Sidebar)
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
            st.success("הנתונים נשמרו!")
            st.rerun()
    
    t_cal, t_prot, t_fat, t_fib = calculate_targets(s_weight, s_height, s_age, s_gender)
    total_target = t_cal + int(s_steps * 0.04)
    st.metric("🎯 יעד קלוריות יומי", f"{total_target}")

st.title("🍎 יומן תזונה חכם")

# 7. מנגנון הזנה
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
    if st.button("✅ אשר והוסף ליומן"):
        try:
            df = conn.read(worksheet="Sheet1")
            today = datetime.now().strftime("%d/%m/%Y")
            new_row = pd.DataFrame([{
                "Date": today, "Food": p['name'], "Quantity": p['qty'], 
                "Calories": p['cal'], "Protein": p['prot'], "Fat": p['fat'], "Fiber": p['fib']
            }])
            conn.update(worksheet="Sheet1", data=pd.concat([df, new_row], ignore_index=True))
            st.session_state.preview = None
            st.session_state.last_query = ""
            st.session_state.input_counter += 1
            st.rerun()
        except Exception as e:
            st.error(f"שגיאה בשמירה: {e}")

# 8. תצוגת נתונים
st.divider()
try:
    data = conn.read(worksheet="Sheet1", ttl=0)
    if not data.empty:
        for c in ['Calories', 'Protein', 'Fat', 'Fiber']:
            data[c] = pd.to_numeric(data[c], errors='coerce').fillna(0)
        today_str = datetime.now().strftime("%d/%m/%Y")
        today_df = data[data['Date'] == today_str]
        c_cal = int(today_df['Calories'].sum())
        rem_cal = max(0, total_target - c_cal)

        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(f"📊 סיכום להיום ({today_str})")
            m1, m2, m3 = st.columns(3)
            m1.metric("נאכל", f"{c_cal}")
            m2.metric("נותר", f"{rem_cal}")
            m3.metric("חלבון", f"{today_df['Protein'].sum():.1f}g")
        with col2:
            fig = go.Figure(data=[go.Pie(labels=['נאכל', 'נותר'], values=[c_cal, rem_cal], hole=.6, 
                             marker_colors=['#ff4b4b', '#f0f2f6'], textinfo='none')])
            fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=150)
            st.plotly_chart(fig, use_container_width=True)
        st.subheader("📋 ארוחות היום")
        st.dataframe(today_df[['Food', 'Quantity', 'Calories', 'Protein']], use_container_width=True)
    else:
        st.info("היומן ריק.")
except Exception as e:
    st.info("ממתין לנתונים...")
