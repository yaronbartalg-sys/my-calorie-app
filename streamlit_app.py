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
    st.header("👤 נתונים אישיים")
    gender = st.radio("מין", ["זכר", "נקבה"])
    weight = st.number_input("משקל (ק\"ג)", value=80.0)
    height = st.number_input("גובה (ס\"מ)", value=175)
    age = st.number_input("גיל", value=30)
    
    t_cal, t_prot, t_fat, t_fib = calculate_targets(weight, height, age, gender)
    
    st.divider()
    steps = st.number_input("צעדים היום", value=0, step=500)
    step_bonus = int(steps * 0.04) 
    total_target = t_cal + step_bonus
    st.info(f"🎯 יעד קלוריות כולל: {total_target}")

st.title("🍎 יומן תזונה חכם")

# --- ממשק הזנה עם בדיקה לפני שמירה ---
food_query = st.text_input("מה אכלת?", placeholder="לדוגמה: קערת אורז עם עדשים")

if food_query:
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
        st.warning(f"🔍 **בדיקה:** {p['name']} | 🔥 {p['cal']} קק\"ל | 💪 {p['prot']}g חלבון")
        if st.button("✅ אשר והוסף ליומן"):
            df = conn.read(worksheet="Sheet1")
            today = datetime.now().strftime("%d/%m/%Y")
            new_row = pd.DataFrame([{"Date": today, "Food": p['name'], "Calories": p['cal'], 
                                     "Protein": p['prot'], "Fat": p['fat'], "Fiber": p['fib']}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success("נוסף!")
            del st.session_state.preview
            st.rerun()

# --- תצוגת נתונים וגרפים ---
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

        # --- שורת מדדים וגרף דונאט ---
        col_stats, col_donut = st.columns([2, 1])
        
        with col_stats:
            st.subheader(f"📊 סיכום להיום ({today_str})")
            m1, m2, m3 = st.columns(3)
            m1.metric("נאכל", f"{c_cal} קק\"ל")
            m2.metric("נותר", f"{rem_cal} קק\"ל")
            m3.metric("חלבון", f"{today_df['Protein'].sum():.1f}g")

        with col_donut:
            # יצירת גרף דונאט
            fig = go.Figure(data=[go.Pie(labels=['נאכל', 'נותר'], 
                             values=[c_cal, rem_cal], 
                             hole=.6, 
                             marker_colors=['#ff4b4b', '#f0f2f6'],
                             textinfo='none')])
            fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=150)
            st.plotly_chart(fig, use_container_width=True)

        # --- סיכום שבועי ---
        st.divider()
        st.subheader("📅 צריכה שבועית")
        weekly_data = data.copy()
        weekly_data['Date_dt'] = pd.to_datetime(weekly_data['Date'], format="%d/%m/%Y")
        weekly_summary = weekly_data.groupby('Date_dt')['Calories'].sum().reset_index().tail(7)
        st.bar_chart(data=weekly_summary, x='Date_dt', y='Calories', color="#ff4b4b")

        # --- רשימת ארוחות עם מחיקה ---
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
    st.info("ממתין לנתונים...")
