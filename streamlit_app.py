import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# הגדרות דף
st.set_page_config(page_title="מחשבון תזונה AI", layout="centered")
st.title("🍎 יומן תזונה חכם")

# חיבור ל-Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # מחר נשתמש ב-1.5 פלאש כי הוא הכי יציב
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"שגיאת חיבור: {e}")

# חיבור לגיליון
conn = st.connection("gsheets", type=GSheetsConnection)

# ממשק משתמש
food_input = st.text_input("מה אכלת?", placeholder="לדוגמה: 2 פרוסות לחם עם אבוקדו")

if st.button("חשב ושמור ביומן"):
    if food_input:
        try:
            # 1. ניתוח עם AI
            prompt = "Return ONLY: Food Name (in Hebrew), Calories (number), Protein (number) separated by commas."
            response = model.generate_content(f"{prompt} \n Input: {food_input}")
            
            res = response.text.strip().split(',')
            if len(res) >= 3:
                name, cal, prot = res[0].strip(), res[1].strip(), res[2].strip()
                today_date = datetime.now().strftime("%d/%m/%Y")
                
                # 2. פתרון ה-Overwrite: קוראים את הקיים ומוסיפים לסוף
                try:
                    existing_df = conn.read(worksheet="Sheet1")
                except:
                    existing_df = pd.DataFrame(columns=["Date", "Food", "Calories", "Protein"])
                
                new_row = pd.DataFrame([{
                    "Date": today_date,
                    "Food": name, 
                    "Calories": int(cal), 
                    "Protein": float(prot)
                }])
                
                updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                
                # 3. עדכון הגיליון
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success(f"נשמר: {name}")
                st.rerun() # רענון לעדכון הסיכומים
        except Exception as e:
            st.error(f"שגיאה: {str(e)}")

# --- חלק הסיכומים והתצוגה ---
st.divider()
try:
    df = conn.read(worksheet="Sheet1")
    if not df.empty:
        # המרה למספרים למקרה של תקלות בפורמט
        df['Calories'] = pd.to_numeric(df['Calories'], errors='coerce').fillna(0)
        df['Protein'] = pd.to_numeric(df['Protein'], errors='coerce').fillna(0)
        
        # סינון להיום בלבד
        today_str = datetime.now().strftime("%d/%m/%Y")
        today_data = df[df['Date'] == today_str]
        
        # הצגת סיכום יומי בתיבות (Metrics)
        col1, col2 = st.columns(2)
        col1.metric("סה\"כ קלוריות היום", f"{int(today_data['Calories'].sum())}")
        col2.metric("סה\"כ חלבון היום", f"{today_data['Protein'].sum():.1f}g")
        
        st.subheader("📋 5 ארוחות אחרונות")
        st.table(df.tail(5))
except:
    st.info("ממתין לנתונים ראשונים...")
