import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection

# הגדרות כותרת
st.title("🍎 מחשבון תזונה AI")

# חיבור ל-Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-flash-latest')
except Exception as e:
    st.error(f"שגיאה בחיבור ל-Gemini: {e}")

# חיבור לגיליון
conn = st.connection("gsheets", type=GSheetsConnection)

# תיבת טקסט לקלט
food_input = st.text_input("מה אכלת?", placeholder="לדוגמה: 2 פרוסות לחם עם חמאת בוטנים")

if st.button("חשב ושמור"):
    if food_input:
            try:
            # 1. ניתוח עם AI
            prompt = "Return ONLY: Food Name (in Hebrew), Calories (number), Protein (number) separated by commas."
            response = model.generate_content(f"{prompt} \n Input: {food_input}")
            res = response.text.strip().split(',')
            if len(res) >= 3:
                name, cal, prot = res[0].strip(), res[1].strip(), res[2].strip()
                
                # --- התיקון כאן ---
                # קריאת הנתונים הקיימים (כדי לדעת איפה הסוף)
                existing_data = conn.read(worksheet="Sheet1")
                
                # יצירת השורה החדשה כ-DataFrame
                new_row = pd.DataFrame([{"Food": name, "Calories": cal, "Protein": prot}])
                
                # חיבור השורה החדשה לסוף הנתונים הקיימים
                updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                
                # עדכון הגיליון עם כל המידע המצטבר
                conn.update(worksheet="Sheet1", data=updated_df)
                # ------------------
                
                st.success(f"נשמר: {name}")
            else:
                st.error("ה-AI לא החזיר פורמט תקין.")
            
         
            # 2. עיבוד התשובה
            res = response.text.strip().split(',')
            if len(res) >= 3:
                name, cal, prot = res[0].strip(), res[1].strip(), res[2].strip()
                
                # 3. שמירה לגיליון - הדרך הבטוחה
                # אנחנו קוראים את הנתונים הקיימים
                df = conn.read(worksheet="Sheet1")
                
                # יוצרים שורה חדשה
                new_row = pd.DataFrame([{"Food": name, "Calories": cal, "Protein": prot}])
                
                # מחברים ומעדכנים
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                
                st.success(f"נשמר: {name} ({cal} קלוריות)")
            else:
                st.error("ה-AI לא החזיר תשובה בפורמט תקין.")
        except Exception as e:
            st.error(f"שגיאה: {str(e)}")

# הצגת היסטוריה
st.divider()
st.subheader("📋 ארוחות אחרונות")
try:
    data = conn.read(worksheet="Sheet1")
    st.table(data.tail(5))
except:
    st.write("הגיליון ריק או לא מחובר כראוי.")
