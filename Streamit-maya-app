import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

st.set_page_config(page_title="מחשבון תזונה AI פרו", layout="wide")

# --- פונקציות עזר לחישובים ---
def calculate_targets(weight, height, age, gender):
    # חישוב BMR לפי נוסחת Mifflin-St Jeor
    if gender == "זכר":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    
    tdee = int(bmr * 1.2) # רמת פעילות בסיסית
    protein = int(weight * 1.8) # 1.8 גרם לקילו
    fat = int((tdee * 0.25) / 9) # 25% מהקלוריות
    fiber = 30 if gender == "זכר" else 25
    return tdee, protein, fat, fiber

# --- סרגל צד: נתונים אישיים ---
with st.sidebar:
    st.header("👤 נתונים אישיים")
    gender = st.radio("מין", ["זכר", "נקבה"])
    weight = st.number_input("משקל (ק\"ג)", value=80.0)
    height = st.number_input("גובה (ס\"מ)", value=175)
    age = st.number_input("גיל", value=30)
    
    t_cal, t_prot, t_fat, t_fib = calculate_targets(weight, height, age, gender)
    
    st.divider()
    st.subheader("🎯 יעדים מחושבים")
    st.write(f"קלוריות: **{t_cal}**")
    st.write(f"חלבון: **{t_prot}g** | שומן: **{t_fat}g**")
    st.write(f"סיבים: **{t_fib}g**")
    
    st.divider()
    steps = st.number_input("צעדים היום", value=0, step=500)
    step_bonus = int(steps * 0.04) # הערכה: 0.04 קלוריות לצעד
    st.info(f"בונוס צעדים: {step_bonus} קק\"ל")
    st.info("מודל פעיל: Gemini Flash Lite")

st.title("🍎 ניהול תזונה חכם")

# חיבור ל-AI ושיטס
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-flash-lite-latest')
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ממשק הזנה ---
col_in1, col_in2 = st.columns([3, 1])
with col_in1:
    food_input = st.text_input("מה אכלת?", placeholder="לדוגמה: 2 פרוסות לחם עם חביתה וגבינה")
with col_in2:
    st.write("") # מרווח
    add_btn = st.button("הוסף ליומן", use_container_width=True)

if add_btn and food_input:
    try:
        with st.spinner('מנתח...'):
            prompt = "Return ONLY: Food Name (Hebrew), Calories (int), Protein (float), Fat (float), Fiber (float) separated by commas."
            response = model.generate_content(f"{prompt} \n Input: {food_input}")
            res = response.text.strip().split(',')
            
            if len(res) >= 5:
                name, cal, prot, fat, fiber = res[0:5]
                today = datetime.now().strftime("%d/%m/%Y")
                
                df = conn.read(worksheet="Sheet1")
                new_row = pd.DataFrame([{"Date": today, "Food": name, "Calories": int(cal), 
                                         "Protein": float(prot), "Fat": float(fat), "Fiber": float(fiber)}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.rerun()
    except Exception as e:
        st.error(f"שגיאה: {e}")

# --- ניהול נתונים ותצוגה ---
try:
    data = conn.read(worksheet="Sheet1", ttl=0)
    if not data.empty:
        # המרת נתונים למספרים
        for col in ['Calories', 'Protein', 'Fat', 'Fiber']:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        
        today_str = datetime.now().strftime("%d/%m/%Y")
        today_df = data[data['Date'] == today_str]
        
        # סיכומים
        c_cal = int(today_df['Calories'].sum())
        c_prot = today_df['Protein'].sum()
        c_fat = today_df['Fat'].sum()
        c_fib = today_df['Fiber'].sum()
        
        # חישוב נותר לצריכה (כולל בונוס צעדים)
        remaining_cal = (t_cal + step_bonus) - c_cal

        # --- תצוגת סיכום יומי ---
        st.subheader(f"📊 סיכום להיום: {today_str}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("קלוריות שנאכלו", f"{c_cal} / {t_cal}")
        m2.metric("חלבון (ג')", f"{c_prot:.1f} / {t_prot}")
        m3.metric("שומן (ג')", f"{c_fat:.1f} / {t_fat}")
        m4.metric("סיבים (ג')", f"{c_fib:.1f} / {t_fib}")
        
        if remaining_cal > 0:
            st.success(f"🔥 נותרו לך עוד **{remaining_cal}** קלוריות לצרוך היום (כולל צעדים)")
        else:
            st.warning(f"⚠️ חרגת ב-**{abs(remaining_cal)}** קלוריות מהיעד")

        # --- כפתור מחיקה ---
        if st.button("🗑️ מחק שורה אחרונה"):
            updated_df = data.drop(data.index[-1])
            conn.update(worksheet="Sheet1", data=updated_df)
            st.rerun()

        # --- סיכום שבועי ---
        st.divider()
        st.subheader("📅 צריכה שבועית (קלוריות)")
        # קיבוץ לפי תאריך
        weekly_data = data.groupby('Date')['Calories'].sum().reset_index()
        weekly_data['Date'] = pd.to_datetime(weekly_data['Date'], format="%d/%m/%Y")
        weekly_data = weekly_data.sort_values('Date').tail(7)
        st.bar_chart(data=weekly_data, x='Date', y='Calories')

        st.write("📋 ארוחות היום:")
        st.dataframe(today_df[["Food", "Calories", "Protein", "Fat", "Fiber"]], use_container_width=True)

except Exception as e:
    st.info("ממתין לנתונים... וודא שיש כותרות בגיליון: Date, Food, Calories, Protein, Fat, Fiber")
