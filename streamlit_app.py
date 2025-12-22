import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
from PIL import Image
import pandas as pd

# הגדרת כותרת
st.set_page_config(page_title="מחשבון תזונה AI")
st.title("🍎 מחשבון תזונה חכם")

# חיבור ל-Secrets (API ו-Google Sheets)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("חסר מפתח API או הגדרות Secrets ב-Streamlit Cloud")

# פונקציה לניתוח ושמירה
def analyze_and_save(user_input, is_image=False):
    try:
        # שינוי שם המודל לפורמט מלא ומפורש
        model = genai.GenerativeModel('gemini-1.5-flash') 
        prompt = "Analyze this food. Return ONLY: Food Name (in Hebrew), Calories (number), Protein (number) separated by commas."
        
        with st.spinner('מנתח...'):
            if is_image:
                response = model.generate_content([prompt, user_input])
            else:
                response = model.generate_content(prompt + " Input: " + user_input)
            
            if not response.text:
                st.error("הבינה המלאכותית לא החזירה תשובה. נסה שוב.")
                return

            res = response.text.split(',')
            if len(res) >= 3:
                name, cal, prot = res[0].strip(), res[1].strip(), res[2].strip()
                
                # קריאת הנתונים ועדכון
                df = conn.read(worksheet="Sheet1")
                new_data = pd.DataFrame([{"Food": name, "Calories": cal, "Protein": prot}])
                updated_df = pd.concat([df, new_data], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success(f"נשמר: {name} ({cal} קלוריות)")
            else:
                st.error(f"התשובה מגוגל לא הייתה בפורמט הנכון: {response.text}")
                
    except Exception as e:
        st.error(f"שגיאה בתקשורת עם גוגל: {str(e)}")

# --- ממשק משתמש ---
tab1, tab2 = st.tabs(["📷 צילום ארוחה", "✍️ הקלדה ידנית"])

with tab1:
    file = st.file_uploader("העלה תמונה", type=["jpg", "png", "jpeg"])
    if file and st.button("נתח תמונה"):
        img = Image.open(file)
        analyze_and_save(img, is_image=True)

with tab2:
    text_input = st.text_input("מה אכלת?", placeholder="לדוגמה: 2 פרוסות לחם עם חומוס")
    if text_input and st.button("חשב ושמור"):
        analyze_and_save(text_input, is_image=False)

st.divider()
st.subheader("📋 יומן ארוחות")
try:
    st.dataframe(conn.read(worksheet="Sheet1").tail(10))
except:
    st.write("הטבלה ריקה או לא מחוברת.")
