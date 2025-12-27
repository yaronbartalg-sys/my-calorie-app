import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# הגדרות דף
st.set_page_config(page_title="מחשבון תזונה AI", layout="centered")

# --- הגדרות יעד בסרגל הצד ---
with st.sidebar:
    st.header("🎯 הגדרות יעד")
    target_cal = st.number_input("יעד קלוריות יומי", value=2000, step=50)
    target_prot = st.number_input("יעד חלבון יומי (גרם)", value=120, step=5)
    st.divider()
    st.info("האפליקציה משתמשת ב-Gemini 1.5")

st.title("🍎 יומן תזונה חכם")

# חיבור ל-Gemini - מעבר למודל היציב והנדיב ביותר
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
   # ננסה את השם הסטנדרטי ביותר שעובד ב-v1beta
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"שגיאה בחיבור ל-AI: {e}")

# חיבור לגוגל שיטס
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ממשק הזנה ---
food_input = st.text_input("מה אכלת?", placeholder="לדוגמה: קערת שיבולת שועל עם חלב")

if st.button("חשב ושמור ביומן"):
    if food_input:
        try:
            with st.spinner('מנתח את המנה...'):
                prompt = "Return ONLY: Food Name (in Hebrew), Calories (number), Protein (number) separated by commas."
                response = model.generate_content(f"{prompt} \n Input: {food_input}")
                res = response.text.strip().split(',')
                
                if len(res) >= 3:
                    name, cal, prot = res[0].strip(), res[1].strip(), res[2].strip()
                    today = datetime.now().strftime("%d/%m/%Y")
                    
                    # מניעת Overwrite: קוראים את הקיים ומוסיפים לסוף
                    try:
                        existing_df = conn.read(worksheet="Sheet1")
                    except:
                        existing_df = pd.DataFrame(columns=["Date", "Food", "Calories", "Protein"])
                    
                    new_row = pd.DataFrame([{"Date": today, "Food": name, "Calories": int(cal), "Protein": float(prot)}])
                    updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                    
                    conn.update(worksheet="Sheet1", data=updated_df)
                    st.success(f"נשמר: {name}")
                    st.rerun()
                else:
                    st.error("ה-AI החזיר תשובה בפורמט לא תקין.")
        except Exception as e:
            st.error(f"שגיאה בתהליך השמירה: {e}")

# --- תצוגת צריכה יומית (Daily Intake) ---
st.divider()
try:
    # קריאת כל הנתונים
    df = conn.read(worksheet="Sheet1", ttl=0)
    
    if not df.empty:
        # ניקוי נתונים והמרה למספרים
        df['Calories'] = pd.to_numeric(df['Calories'], errors='coerce').fillna(0)
        df['Protein'] = pd.to_numeric(df['Protein'], errors='coerce').fillna(0)
        
        today_str = datetime.now().strftime("%d/%m/%Y")
        today_df = df[df['Date'] == today_str]
        
        current_cal = int(today_df['Calories'].sum())
        current_prot = today_df['Protein'].sum()

        st.subheader(f"📊 סיכום צריכה להיום ({today_str})")
        
        # תצוגת פרוגרס ברים
        c1, c2 = st.columns(2)
        with c1:
            st.metric("קלוריות", f"{current_cal} / {target_cal}")
            st.progress(min(current_cal / target_cal, 1.0))
        with c2:
            st.metric("חלבון", f"{current_prot:.1f}g / {target_prot}g")
            st.progress(min(current_prot / target_prot, 1.0))

        st.write("📋 ארוחות מהיום:")
        st.dataframe(today_df[["Food", "Calories", "Protein"]].tail(10), use_container_width=True)
    else:
        st.info("היומן ריק. התחל להזין מאכלים!")
except Exception as e:
    st.info("ממתין לנתונים ראשונים...")
