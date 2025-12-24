import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# הגדרות דף
st.set_page_config(page_title="Nutrition Tracker AI", layout="centered")

# --- הגדרת יעדים בסרגל הצד ---
with st.sidebar:
    st.header("🎯 הגדרות יעד")
    target_calories = st.number_input("יעד קלוריות יומי", value=2000, step=50)
    target_protein = st.number_input("יעד חלבון יומי (גרם)", value=120, step=5)
    st.info("שנה את היעדים כאן והמדדים יתעדכנו אוטומטית")

st.title("🍎 יומן תזונה חכם")

# חיבור ל-Gemini (שימוש בשם המעודכן ביותר)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    st.error(f"שגיאה בחיבור ל-AI: {e}")

# חיבור לגיליון
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ממשק הזנה ---
food_input = st.text_input("מה אכלת?", placeholder="לדוגמה: 200 גרם חזה עוף ואורז")

if st.button("חשב ושמור"):
    if food_input:
        try:
            with st.spinner('מנתח נתונים...'):
                prompt = "Return ONLY: Food Name (in Hebrew), Calories (number), Protein (number) separated by commas."
                response = model.generate_content(f"{prompt} \n Input: {food_input}")
                res = response.text.strip().split(',')
                
                if len(res) >= 3:
                    name, cal, prot = res[0].strip(), res[1].strip(), res[2].strip()
                    today = datetime.now().strftime("%d/%m/%Y")
                    
                    # קריאה למניעת דריסה
                    try:
                        df = conn.read(worksheet="Sheet1")
                    except:
                        df = pd.DataFrame(columns=["Date", "Food", "Calories", "Protein"])
                    
                    # הוספת שורה חדשה
                    new_row = pd.DataFrame([{"Date": today, "Food": name, "Calories": int(cal), "Protein": float(prot)}])
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    
                    # עדכון הגיליון המלא
                    conn.update(worksheet="Sheet1", data=updated_df)
                    st.success(f"נשמר: {name}")
                    st.rerun()
        except Exception as e:
            st.error(f"שגיאה: {e}")

# --- תצוגת צריכה יומית (Daily Intake) ---
st.divider()
try:
    all_data = conn.read(worksheet="Sheet1", ttl=0)
    if not all_data.empty:
        # וידוא פורמט מספרים
        all_data['Calories'] = pd.to_numeric(all_data['Calories'], errors='coerce').fillna(0)
        all_data['Protein'] = pd.to_numeric(all_data['Protein'], errors='coerce').fillna(0)
        
        today_str = datetime.now().strftime("%d/%m/%Y")
        today_data = all_data[all_data['Date'] == today_str]
        
        current_cal = int(today_data['Calories'].sum())
        current_prot = today_data['Protein'].sum()

        st.subheader(f"📊 סיכום צריכה להיום ({today_str})")
        
        # הצגת התקדמות ויזואלית
        col1, col2 = st.columns(2)
        with col1:
            st.metric("קלוריות", f"{current_cal} / {target_calories}")
            st.progress(min(current_cal / target_calories, 1.0))
        with col2:
            st.metric("חלבון", f"{current_prot:.1f}g / {target_protein}g")
            st.progress(min(current_prot / target_protein, 1.0))

        st.write("📋 ארוחות אחרונות:")
        st.dataframe(today_data[["Food", "Calories", "Protein"]].tail(5), use_container_width=True)
except:
    st.info("ממתין לנתונים...")
