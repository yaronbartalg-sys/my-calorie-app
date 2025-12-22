import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# הגדרות כותרת
st.set_page_config(page_title="מחשבון תזונה AI", layout="centered")
st.title("🍎 יומן תזונה חכם")

# חיבור ל-Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-flash-latest')
except Exception as e:
    st.error(f"שגיאה בחיבור ל-Gemini: {e}")

# חיבור לגיליון
conn = st.connection("gsheets", type=GSheetsConnection)

# ממשק משתמש
food_input = st.text_input("מה אכלת?", placeholder="לדוגמה: 2 ביצים וסלט")

if st.button("חשב ושמור"):
    if food_input:
        try:
            # 1. ניתוח עם AI
            prompt = "Return ONLY: Food Name (in Hebrew), Calories (number), Protein (number) separated by commas."
            response = model.generate_content(f"{prompt} \n Input: {food_input}")
            
            res = response.text.strip().split(',')
            if len(res) >= 3:
                name, cal, prot = res[0].strip(), res[1].strip(), res[2].strip()
                current_date = datetime.now().strftime("%d/%m/%Y")
                
                # 2. קריאת הנתונים הקיימים
                # הערה: אם הגיליון ריק, הוא יצור DataFrame חדש
                df = conn.read(worksheet="Sheet1")
                
                # 3. יצירת השורה החדשה (כולל תאריך)
                new_row = pd.DataFrame([{
                    "Date": current_date,
                    "Food": name, 
                    "Calories": int(cal), 
                    "Protein": float(prot)
                }])
                
                # 4. איחוד ועדכון (מניעת דריסה)
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                
                st.success(f"נשמר: {name}")
                st.balloons()
            else:
                st.error("ה-AI לא החזיר פורמט תקין.")
        except Exception as e:
            st.error(f"שגיאה בשמירה: {str(e)}")

# --- חלק הסיכומים והתצוגה ---
st.divider()

try:
    # קריאת כל הנתונים
    all_data = conn.read(worksheet="Sheet1")
    
    if not all_data.empty:
        # המרת עמודות למספרים ליתר ביטחון
        all_data['Calories'] = pd.to_numeric(all_data['Calories'], errors='coerce')
        all_data['Protein'] = pd.to_numeric(all_data['Protein'], errors='coerce')
        
        # סיכום לפי יום (היום הנוכחי)
        today = datetime.now().strftime("%d/%m/%Y")
        today_data = all_data[all_data['Date'] == today]
        
        # תצוגת סיכום יומית בתיבות מעוצבות
        col1, col2 = st.columns(2)
        with col1:
            st.metric("סה\"כ קלוריות היום", f"{int(today_data['Calories'].sum())} קק\"ל")
        with col2:
            st.metric("סה\"כ חלבון היום", f"{today_data['Protein'].sum():.1f} גרם")
        
        st.subheader("📋 הארוחות האחרונות שלך")
        st.dataframe(all_data.tail(10), use_container_width=True)
    else:
        st.info("עדיין אין נתונים ביומן.")
except Exception as e:
    st.write("ממתין לנתונים ראשונים...")
