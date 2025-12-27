import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

# הגדרות דף
st.set_page_config(page_title="מחשבון תזונה פרו", layout="wide")

# חיבורים
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-flash-lite-latest')
conn = st.connection("gsheets", type=GSheetsConnection)

# --- פונקציות עזר ---
def get_data():
    return conn.read(worksheet="Sheet1", ttl=0)

# --- ממשק הזנה עם תצוגה מקדימה ---
st.title("🍎 ניהול תזונה חכם - שלב השדרוגים")

col1, col2 = st.columns([2, 1])

with col1:
    food_query = st.text_input("מה אכלת?", placeholder="לדוגמה: 200 גרם פסטה ברוטב עגבניות")
    
    if food_query:
        if 'last_query' not in st.session_state or st.session_state.last_query != food_query:
            with st.spinner('מנתח...'):
                prompt = "Return ONLY: Food Name (Hebrew), Calories (int), Protein (float), Fat (float), Fiber (float) separated by commas."
                response = model.generate_content(f"{prompt} \n Input: {food_query}")
                res = response.text.strip().split(',')
                if len(res) >= 5:
                    st.session_state.temp_data = {
                        "Name": res[0], "Cal": int(res[1]), "Prot": float(res[2]),
                        "Fat": float(res[3]), "Fib": float(res[4])
                    }
                    st.session_state.last_query = food_query

        if 'temp_data' in st.session_state:
            d = st.session_state.temp_data
            st.info(f"📋 **תצוגה מקדימה:** {d['Name']} | קלוריות: {d['Cal']} | חלבון: {d['Prot']}g")
            
            satiety = st.select_slider("מדד שובע (1=רעב, 5=מפוצץ)", options=[1, 2, 3, 4, 5], value=3)
            
            if st.button("✅ אשר ושמור ביומן"):
                today = datetime.now().strftime("%d/%m/%Y")
                df = get_data()
                new_row = pd.DataFrame([{
                    "Date": today, "Food": d['Name'], "Calories": d['Cal'], 
                    "Protein": d['Prot'], "Fat": d['Fat'], "Fiber": d['Fib'], "Satiety": satiety
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("נשמר!")
                del st.session_state.temp_data
                st.rerun()

# --- ניהול ארוחות קיימות ומחיקה ספציפית ---
st.divider()
data = get_data()
if not data.empty:
    today_str = datetime.now().strftime("%d/%m/%Y")
    today_data = data[data['Date'] == today_str]
    
    st.subheader("📋 ארוחות היום")
    
    # מחיקה ספציפית
    for idx, row in today_data.iterrows():
        cols = st.columns([4, 1, 1, 1, 1])
        cols[0].write(f"🍴 {row['Food']}")
        cols[1].write(f"🔥 {row['Calories']}")
        cols[2].write(f"💪 {row['Protein']}g")
        cols[3].write(f"🤤 שובע: {row.get('Satiety', 'N/A')}")
        if cols[4].button("🗑️", key=f"del_{idx}"):
            updated_df = data.drop(idx)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.rerun()
