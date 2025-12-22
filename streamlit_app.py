import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
from PIL import Image
import datetime
import pandas as pd

# הגדרות API
genai.configure(api_key="AIzaSyB-uBsl_tshkxja6UXies5pVRq8O5bYkZY")

st.title("https://docs.google.com/spreadsheets/d/1EPVoO5Yx8CV8ZcO_6UdZmO8hwnVpUueB8_y4yEd_33E/edit?usp=sharing")

# חיבור ל-Google Sheets (הגדרת הקישור תתבצע ב-Secrets של Streamlit)
conn = st.connection("gsheets", type=GSheetsConnection)

# פונקציה לשמירת נתונים לגיליון
def save_to_sheet(food_name, calories, protein):
    # קריאת הנתונים הקיימים
    existing_data = conn.read(worksheet="Sheet1")
    
    # יצירת שורה חדשה
    new_row = pd.DataFrame([{
        "Date": datetime.date.today().strftime("%Y-%m-%d"),
        "Time": datetime.datetime.now().strftime("%H:%M"),
        "Food_Item": food_name,
        "Calories": calories,
        "Proteins": protein
    }])
    
    # עדכון הגיליון
    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
    conn.update(worksheet="Sheet1", data=updated_df)
    st.success("הנתונים נשמרו ב-Google Sheets!")

# --- ממשק המשתמש ---
uploaded_file = st.file_uploader("צלם ארוחה...", type=["jpg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, width=300)
    
    if st.button("נתח ושמור"):
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # הנחייה לקבלת נתונים מובנים
        prompt = "Analyze this food. Return ONLY a comma-separated list: Food Name, Calories (number), Protein (number)."
        
        response = model.generate_content([prompt, image])
        res_text = response.text.split(',')
        
        if len(res_text) >= 3:
            name, cal, prot = res_text[0].strip(), res_text[1].strip(), res_text[2].strip()
            st.write(f"זיהיתי: {name} ({cal} קלוריות)")
            
            # שמירה לענן
            save_to_sheet(name, cal, prot)

# הצגת היסטוריה מהענן
st.subheader("היסטוריה מ-Google Sheets")
data = conn.read(worksheet="Sheet1")
st.dataframe(data.tail(10)) # מציג את 10 הארוחות האחרונות
