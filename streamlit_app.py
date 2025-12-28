import streamlit as st
import pandas as pd
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import plotly.graph_objects as go
from google.api_core import exceptions

# הגדרות דף
st.set_page_config(page_title="מחשבון תזונה AI", layout="wide")

# חיבורים
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash') # שימוש במודל יציב
conn = st.connection("gsheets", type=GSheetsConnection)

# --- פונקציות חישוב ---
def calculate_targets(weight, height, age, gender):
    if gender == "זכר":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    tdee = int(bmr * 1.2)
    return tdee, int(weight * 1.8), int((tdee * 0.25) / 9), (30 if gender == "זכר" else 25)

# --- סרגל צד (Sidebar) ---
with st.sidebar:
    st.header("👤 פרופיל משתמש")
    with st.expander("עדכון נתונים אישיים"):
        s_gender = st.radio("מין", ["זכר", "נקבה"], index=0)
        s_weight = st.number_input("משקל (ק\"ג)", value=80.0, step=0.1)
        s_height = st.number_input("גובה (ס\"מ)", value=175, step=1)
        s_age = st.number_input("גיל", value=30, step=1)
    
    st.write(f"📊 **נתונים:** {s_gender} | {s_weight} ק\"ג | {s_height} ס\"מ | גיל {s_age}")
    t_cal, t_prot, t_fat, t_fib = calculate_targets(s_weight, s_height, s_age, s_gender)
    
    st.divider()
    steps = st.number_input("צעדים היום", value=0, step=500)
    step_bonus = int(steps * 0.04) 
    total_target = t_cal + step_bonus
    st.info(f"🎯 יעד קלוריות: {total_target}")

st.title("🍎 יומן תזונה חכם")

# --- מנגנון איפוס חכם ---
if "input_counter" not in st.session_state:
    st.session_state.input_counter = 0
if "preview" not in st.session_state:
    st.session_state.preview = None
if "last_processed_query" not in st.session_state:
    st.session_state.last_processed_query = ""

input_key = f"food_input_{st.session_state.input_counter}"
food_query = st.text_input("מה אכלת?", key=input_key, placeholder="לדוגמה: 3 כוסות אספרסו")

# פנייה ל-AI רק אם יש טקסט חדש
if food_query and st.session_state.last_processed_query != food_query:
    try:
        with st.spinner('מנתח נתונים...'):
            prompt = "Return ONLY: Food Name (Hebrew), Calories (int), Protein (float), Fat (float), Fiber (float), Detected Quantity (Short Hebrew description) separated by commas."
            response = model.generate_content(f"{prompt} \n Input: {food_query}")
            res = response.text.strip().split(',')
            if len(res) >= 6:
                st.session_state.preview = {
                    "name": res[0].strip(), 
                    "cal": int(res[1].strip()), 
                    "prot": float(res[2].strip()),
                    "fat": float(res[3].strip()), 
                    "fib": float(res[4].strip()),
                    "qty": res[5].strip()
                }
                st.session_state.last_processed_query = food_query
    except exceptions.ResourceExhausted:
        st.error("⚠️ הגענו למכסת הבקשות החינמית של גוגל. אנא המתן כ-60 שניות ונסה שוב.")
    except Exception as e:
        st.error(f"שגיאה בניתוח המנה: {e}")

if st.session_state.preview:
    p = st.session_state.preview
    st.warning(f"🔍 **ה-AI זיהה:** {p['qty']} של {p['name']} | 🔥 {p['cal']} קק\"ל")
    
    if st.button("✅ אשר והוסף ליומן"):
        try:
            df = conn.read(worksheet="Sheet1")
            today = datetime.now().strftime("%d/%m/%Y")
            new_row = pd.DataFrame([{
                "Date": today, "Food": p['name'], "Quantity": p['qty'],
                "Calories": p['cal'], "Protein": p['prot'], "Fat": p['fat'], "Fiber": p['fib']
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            
            # איפוס מוחלט
            st.session_state.preview = None
            st.session_state.last_processed_query = ""
            st.session_state.input_counter += 1
            st.rerun()
        except Exception as e:
            st.error(f"שגיאה בשמירה: {e}")

# --- תצוגת נתונים ---
st.divider()
try:
    data = conn.read(worksheet="Sheet1", ttl=0)
    if not data.empty:
        if 'Quantity' not in data.columns: data['Quantity'] = "-"
        for c in ['Calories', 'Protein', 'Fat', 'Fiber']:
            data[c] = pd.to_numeric(data[c], errors='coerce').fillna(0)
        
        today_str = datetime.now().strftime("%d/%m/%Y")
        today_df = data[data['Date'] == today_str]
        c_cal = int(today_df['Calories'].sum())
        rem_cal = max(0, total_target - c_cal)

        col_stats, col_donut = st.columns([2, 1])
        with col_stats:
            st.subheader(f"📊 סיכום להיום ({today_str})")
            m1, m2, m3 = st.columns(3)
            m1.metric("נאכל", f"{c_cal} קק\"ל")
            m2.metric("נותר", f"{rem_cal} קק\"ל")
            m3.metric("חלבון", f"{today_df['Protein'].sum():.1f}g")
        
        with col_donut:
            fig = go.Figure(data=[go.Pie(labels=['נאכל', 'נותר'], values=[c_cal, rem_cal], hole=.6, 
                             marker_colors=['#ff4b4b', '#f0f2f6'], textinfo='none')])
            fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=150)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📋 ארוחות היום")
        for idx, row in today_df.iterrows():
            c_row = st.columns([2, 1.5, 1, 1, 1, 1])
            c_row[0].write(f"🍴 {row['Food']}")
            c_row[1].write(f"⚖️ {row['Quantity']}")
            c_row[2].write(f"{int(row['Calories'])}")
            c_row[3].write(f"{row['Protein']}g")
            
            with c_row[4]:
                with st.popover("✏️"):
                    n_name = st.text_input("שם", value=row['Food'], key=f"e_n_{idx}")
                    n_qty = st.text_input("כמות", value=row['Quantity'], key=f"e_q_{idx}")
                    n_cal = st.number_input("קק\"ל", value=int(row['Calories']), key=f"e_c_{idx}")
                    if st.button("שמור", key=f"s_{idx}"):
                        data.at[idx, 'Food'] = n_name
                        data.at[idx, 'Quantity'] = n_qty
                        data.at[idx, 'Calories'] = n_cal
                        conn.update(worksheet="Sheet1", data=data)
                        st.rerun()
            
            if c_row[5].button("🗑️", key=f"d_{idx}"):
                new_df = data.drop(idx)
                conn.update(worksheet="Sheet1", data=new_df)
                st.rerun()

except Exception as e:
    st.info("ממתין לנתונים...")
