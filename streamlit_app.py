import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# הגדרות יעדים (ניתן לשנות כאן)
CALORIE_GOAL = 2000
PROTEIN_GOAL = 120

st.title("🍎 יומן תזונה עם יעדים יומיים")

# חיבור ל-Gemini 1.5 Flash 8B
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash-8b-latest')
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ממשק הזנה ---
food_input = st.text_input("מה אכלת?", placeholder="לדוגמה: 100 גרם חזה עוף ואורז")

if st.button("שמור ביומן"):
    if food_input:
        try:
            prompt = "Return ONLY: Food Name (in Hebrew), Calories (number), Protein (number) separated by commas."
            response = model.generate_content(f"{prompt} \n Input: {food_input}")
            res = response.text.strip().split(',')
            
            if len(res) >= 3:
                name, cal, prot = res[0].strip(), res[1].strip(), res[2].strip()
                today = datetime.now().strftime("%d/%m/%Y")
                
                # קריאה ושמירה (ללא דריסה)
                existing_df = conn.read(worksheet="Sheet1")
                new_row = pd.DataFrame([{"Date": today, "Food": name, "Calories": int(cal), "Protein": float(prot)}])
                updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                
                st.success(f"נשמר: {name}")
                st.rerun()
        except Exception as e:
            st.error(f"שגיאה: {e}")

# --- חישוב נתונים יומיים ---
st.divider()
try:
    df = conn.read(worksheet="Sheet1")
    if not df.empty:
        df['Calories'] = pd.to_numeric(df['Calories'], errors='coerce').fillna(0)
        df['Protein'] = pd.to_numeric(df['Protein'], errors='coerce').fillna(0)
        
        today_str = datetime.now().strftime("%d/%m/%Y")
        today_data = df[df['Date'] == today_str]
        
        total_cal = int(today_data['Calories'].sum())
        total_prot = today_data['Protein'].sum()

        # הצגת מדדים ויעדים
        st.subheader(f"📊 סיכום להיום: {today_str}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("קלוריות", f"{total_cal} / {CALORIE_GOAL}")
            progress_cal = min(total_cal / CALORIE_GOAL, 1.0)
            st.progress(progress_cal)
            
        with c2:
            st.metric("חלבון", f"{total_prot:.1f}g / {PROTEIN_GOAL}g")
            progress_prot = min(total_prot / PROTEIN_GOAL, 1.0)
            st.progress(progress_prot)

        st.divider()
        st.write("📋 ארוחות אחרונות:")
        st.dataframe(today_data[["Food", "Calories", "Protein"]], use_container_width=True)
except:
    st.info("ממתין לנתונים...")
