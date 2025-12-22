import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd

# הגדרות בסיסיות
st.set_page_config(page_title="מחשבון תזונה AI", layout="centered")
st.title("🍎 יומן תזונה חכם (טקסט בלבד)")

# חיבור ל-Secrets
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"שגיאת חיבור: {e}")

# פונקציה לניתוח ושמירה
def analyze_and_save(user_text):
    try:
        # שימוש במודל היציב ביותר עבורך
        model = genai.GenerativeModel('gemini-flash-latest') 
        
        prompt = """
        Analyze the food described. Return ONLY: Food Name (in Hebrew), Calories (number), Protein (number) separated by commas.
        Example response: פיצה מרגריטה, 300, 12
        """
        
        with st.spinner('מנתח נתונים...'):
            response = model.generate_content(f"{prompt} \n Input: {user_text}")
            
            # עיבוד התשובה
            res = response.text.strip().split(',')
            if len(res) >= 3:
                name, cal, prot = res[0].strip(), res[1].strip(), res[2].strip()
                
                # קריאה ועדכון הגיליון
                df = conn.read(worksheet="Sheet1")
                new_data = pd.DataFrame([{"Food": name, "Calories": cal, "Protein": prot}])
                updated_df = pd.concat([df, new_data], ignore_index=True)
                
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success(f"נשמר: {name} | {cal} קלוריות | {prot} גרם חלבון")
            else:
                st.error("הבינה המלאכותית לא החזירה תשובה בפורמט הנכון. נסה שוב.")
    except Exception as e:
        st.error(f"שגיאה בתהליך: {str(e)}")

# ממשק המשתמש
food_input = st.text_input("מה אכלת?", placeholder="לדוגמה: חביתה מ-2 ביצים ופרוסת לחם")

if st.button("חשב ושמור ביומן"):
    if food_input:
        analyze_and_save(food_input)
    else:
        st.warning("נא להזין טקסט קודם.")

st.divider()

# הצגת ההיסטוריה
st.subheader("📋 10 ארוחות אחרונות")
try:
    history_df = conn.read(worksheet="Sheet1")
    if not history_df.empty:
        st.table(history_df.tail(10))
    else:
        st.info("היומן ריק כרגע.")
except Exception:
 st.write("לא ניתן להציג את ההיסטוריה כרגע.")
