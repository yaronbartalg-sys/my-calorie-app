import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# הגדרות דף
st.set_page_config(page_title="מחשבון תזונה AI", layout="centered")

# --- יעדים בסרגל הצד ---
with st.sidebar:
    st.header("🎯 יעדים יומיים")
    target_cal = st.number_input("יעד קלוריות", value=2000, step=50)
    target_prot = st.number_input("יעד חלבון (גרם)", value=120, step=5)
    
    # כפתור עזר למקרה של שגיאות מודל - יציג לך מה זמין
    if st.button("בדוק מודלים זמינים"):
        models = [m.name for m in genai.list_models()]
        st.write(models)

st.title("🍎 יומן תזונה חכם")

# חיבור ל-Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # השם היציב ביותר ל-v1beta
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    st.error(f"שגיאת חיבור: {e}")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- ממשק הזנה ---
food_input = st.text_input("מה אכלת?", placeholder="לדוגמה: חביתה וסלט")

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
                    
                    # פתרון ה-Overwrite
                    try:
                        existing_df = conn.read(worksheet="Sheet1")
                    except:
                        existing_df = pd.DataFrame(columns=["Date", "Food", "Calories", "Protein"])
                    
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
        data['Calories'] = pd.to_numeric(data['Calories'], errors='coerce').fillna(0)
        data['Protein'] = pd.to_numeric(data['Protein'], errors='coerce').fillna(0)
        
        today_str = datetime.now().strftime("%d/%m/%Y")
        today_df = data[data['Date'] == today_str]
        
        current_cal = int(today_df['Calories'].sum())
        current_prot = today_df['Protein'].sum()

        st.subheader(f"📊 סטטוס להיום ({today_str})")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("קלוריות", f"{current_cal} / {target_cal}")
            st.progress(min(current_cal / target_cal, 1.0))
        with col2:
            st.metric("חלבון", f"{current_prot:.1f}g / {target_prot}g")
            st.progress(min(current_prot / target_prot, 1.0))

        st.divider()
        st.write("📋 ארוחות אחרונות מהיום:")
        st.table(today_df[["Food", "Calories", "Protein"]].tail(5))
except:
    st.info("ממתין לנתונים...")
