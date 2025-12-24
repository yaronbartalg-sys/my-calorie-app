import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# הגדרות דף
st.set_page_config(page_title="מחשבון תזונה AI", layout="centered")

# --- יעדים יומיים (בצד המסך) ---
with st.sidebar:
    st.header("🎯 הגדרת יעדים")
    target_cal = st.number_input("יעד קלוריות יומי", value=2000)
    target_prot = st.number_input("יעד חלבון יומי (גרם)", value=120)

st.title("🍎 יומן תזונה חכם")

# חיבור ל-Gemini - שימוש בשם המודל הכי יציב
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # השם הזה הוא הכי סטנדרטי למניעת 404
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"שגיאה בחיבור ל-AI: {e}")

# חיבור לגוגל שיטס
conn = st.connection("gsheets", type=GSheetsConnection)

# --- קלט משתמש ---
food_input = st.text_input("מה אכלת?", placeholder="לדוגמה: חביתה מ-2 ביצים ופרוסת לחם")

if st.button("חשב ושמור"):
    if food_input:
        try:
            with st.spinner('מנתח...'):
                prompt = "Return ONLY: Food Name (in Hebrew), Calories (number), Protein (number) separated by commas."
                response = model.generate_content(f"{prompt} \n Input: {food_input}")
                res = response.text.strip().split(',')
                
                if len(res) >= 3:
                    name, cal, prot = res[0].strip(), res[1].strip(), res[2].strip()
                    today = datetime.now().strftime("%d/%m/%Y")
                    
                    # פתרון ה-Overwrite: קריאה, הוספה, עדכון
                    existing_df = conn.read(worksheet="Sheet1")
                    new_row = pd.DataFrame([{"Date": today, "Food": name, "Calories": int(cal), "Protein": float(prot)}])
                    updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                    
                    conn.update(worksheet="Sheet1", data=updated_df)
                    st.success(f"נשמר: {name}")
                    st.rerun()
        except Exception as e:
            st.error(f"שגיאה: {e}")

# --- תצוגת צריכה יומית (Daily Intake) ---
st.divider()
try:
    data = conn.read(worksheet="Sheet1", ttl=0)
    if not data.empty:
        # המרה למספרים לחישוב
        data['Calories'] = pd.to_numeric(data['Calories'], errors='coerce').fillna(0)
        data['Protein'] = pd.to_numeric(data['Protein'], errors='coerce').fillna(0)
        
        today_str = datetime.now().strftime("%d/%m/%Y")
        today_df = data[data['Date'] == today_str]
        
        total_cal = int(today_df['Calories'].sum())
        total_prot = today_df['Protein'].sum()

        st.subheader(f"📊 סיכום צריכה להיום ({today_str})")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("קלוריות", f"{total_cal} / {target_cal}")
            st.progress(min(total_cal / target_cal, 1.0))
        with col2:
            st.metric("חלבון", f"{total_prot:.1f}g / {target_prot}g")
            st.progress(min(total_prot / target_prot, 1.0))

        st.divider()
        st.write("📋 ארוחות אחרונות היום:")
        st.dataframe(today_df[["Food", "Calories", "Protein"]], use_container_width=True)
    else:
        st.info("היומן ריק.")
except:
    st.info("ממתין לנתון ראשון...")
