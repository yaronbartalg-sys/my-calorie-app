import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# הגדרות דף
st.set_page_config(page_title="מחשבון תזונה AI", layout="centered")
st.title("🍎 יומן תזונה חכם")

# חיבור ל-Gemini - שימוש בשם המדויק מהרשימה שלך
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    model = genai.GenerativeModel('models/gemini-1.5-flash')
except Exception as e:
    st.error(f"שגיאת אתחול: {e}")

# חיבור לגוגל שיטס
conn = st.connection("gsheets", type=GSheetsConnection)

# פונקציה לקריאת הנתונים
def load_data():
    try:
        return conn.read(worksheet="Sheet1", ttl="0")
    except:
        return pd.DataFrame(columns=["Date", "Food", "Calories", "Protein"])

# ממשק המשתמש
food_input = st.text_input("מה אכלת?", placeholder="לדוגמה: קערת שיבולת שועל עם בננה")

if st.button("חשב ושמור ביומן"):
    if food_input:
        try:
            prompt = "Return ONLY: Food Name (in Hebrew), Calories (number), Protein (number) separated by commas. Example: תפוח, 52, 0.3"
            
            with st.spinner('מנתח את המנה...'):
                response = model.generate_content(f"{prompt} \n Input: {food_input}")
                res = response.text.strip().split(',')
            
            if len(res) >= 3:
                name, cal, prot = res[0].strip(), res[1].strip(), res[2].strip()
                today = datetime.now().strftime("%d/%m/%Y")
                
                # מניעת דריסה: קוראים את הקיים, מוסיפים שורה, ומעדכנים הכל
                existing_df = load_data()
                new_row = pd.DataFrame([{"Date": today, "Food": name, "Calories": int(cal), "Protein": float(prot)}])
                updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success(f"נשמר בהצלחה: {name}")
                st.rerun() # מרענן את הדף כדי לעדכן את הטבלה והסיכומים
            else:
                st.error("ה-AI החזיר תשובה בפורמט לא ברור. נסה שוב.")
                
        except Exception as e:
            st.error(f"שגיאה: {str(e)}")

# --- הצגת סיכומים והיסטוריה ---
st.divider()
data = load_data()

if not data.empty:
    # המרת נתונים למספרים למקרה שנשמרו כטקסט
    data['Calories'] = pd.to_numeric(data['Calories'], errors='coerce').fillna(0)
    data['Protein'] = pd.to_numeric(data['Protein'], errors='coerce').fillna(0)
    
    # סיכום יומי
    today_str = datetime.now().strftime("%d/%m/%Y")
    today_data = data[data['Date'] == today_str]
    
    col1, col2 = st.columns(2)
    col1.metric("קלוריות היום", f"{int(today_data['Calories'].sum())} kcal")
    col2.metric("חלבון היום", f"{today_data['Protein'].sum():.1f} g")
    
    st.subheader("📋 ארוחות אחרונות")
    st.dataframe(data.tail(10), use_container_width=True)
else:
    st.info("היומן ריק. התחל להזין מאכלים!")
