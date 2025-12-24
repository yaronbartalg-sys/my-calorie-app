import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# הגדרות דף
st.set_page_config(page_title="מחשבון תזונה AI", layout="centered")

# --- יעדים יומיים בסרגל הצד ---
with st.sidebar:
    st.header("🎯 הגדרת יעדים")
    target_cal = st.number_input("יעד קלוריות יומי", value=2000, step=50)
    target_prot = st.number_input("יעד חלבון יומי (גרם)", value=120, step=5)

st.title("🍎 יומן תזונה חכם (Gemini 2.0)")

# חיבור ל-Gemini 2.0 Flash
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # זה השם המדויק לגרסה 2 ב-v1beta
    model = genai.GenerativeModel('gemini-2.0-flash-exp') 
except Exception as e:
    st.error(f"שגיאה באתחול המודל: {e}")

# חיבור לגוגל שיטס
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ממשק הזנה ---
food_input = st.text_input("מה אכלת?", placeholder="לדוגמה: 2 פרוסות לחם עם חביתה")

if st.button("חשב ושמור"):
    if food_input:
        try:
            with st.spinner('AI מנתח את הארוחה...'):
                prompt = "Return ONLY: Food Name (in Hebrew), Calories (number), Protein (number) separated by commas. Example: ביצה, 70, 6"
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
                    
                    # הוספת השורה החדשה
                    new_row = pd.DataFrame([{
                        "Date": today, 
                        "Food": name, 
                        "Calories": int(cal), 
                        "Protein": float(prot)
                    }])
                    
                    # איחוד ועדכון הגיליון המלא
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=updated_df)
                    
                    st.success(f"נשמר בהצלחה: {name}")
                    st.rerun()
        except Exception as e:
            st.error(f"שגיאה: {e}")

# --- תצוגת צריכה יומית (Daily Intake) ---
st.divider()
try:
    data = conn.read(worksheet="Sheet1", ttl=0)
    if not data.empty:
        # וידוא עמודות מספריות
        data['Calories'] = pd.to_numeric(data['Calories'], errors='coerce').fillna(0)
        data['Protein'] = pd.to_numeric(data['Protein'], errors='coerce').fillna(0)
        
        today_str = datetime.now().strftime("%d/%m/%Y")
        today_data = data[data['Date'] == today_str]
        
        # חישוב סיכומים
        total_cal = int(today_data['Calories'].sum())
        total_prot = today_data['Protein'].sum()

        st.subheader(f"📊 סיכום צריכה להיום ({today_str})")
        
        # הצגה ויזואלית של התקדמות
        col1, col2 = st.columns(2)
        with col1:
            st.metric("קלוריות", f"{total_cal} / {target_cal}")
            st.progress(min(total_cal / target_cal, 1.0))
        with col2:
            st.metric("חלבון", f"{total_prot:.1f}g / {target_prot}g")
            st.progress(min(total_prot / target_prot, 1.0))

        st.divider()
        st
