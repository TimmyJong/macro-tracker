import streamlit as st
import pandas as pd
import json
import os
import base64
from io import BytesIO
from PIL import Image
from google import genai
from google.genai import types

st.set_page_config(page_title="Macro Tracker Hub", layout="wide")

CSV_FILE = "macro_history.csv"

# Function to compress image and turn into a base64 string for persistent CSV storage
def image_to_base64(img):
    img_copy = img.copy()
    img_copy.thumbnail((400, 400)) # Compress to thumbnail size
    buffered = BytesIO()
    img_copy.save(buffered, format="JPEG", quality=75)
    return base64.b64encode(buffered.getvalue()).decode()

def load_data():
    if not os.path.exists(CSV_FILE):
        columns = ["Category", "Item Name", "Portion", "Calories", "Protein", "Fat", "Carbs", "Image_Base64"]
        df = pd.DataFrame(columns=columns)
        df.to_csv(CSV_FILE, index=False)
    df = pd.read_csv(CSV_FILE)
    if "Image_Base64" not in df.columns:
        df["Image_Base64"] = ""
    return df

def save_entry(entry_dict, b64_img):
    df = load_data()
    entry_dict["Image_Base64"] = b64_img
    new_df = pd.concat([pd.DataFrame([entry_dict]), df], ignore_index=True)
    new_df.to_csv(CSV_FILE, index=False)

st.title("🥗 Macro Tracker Hub")

# Sidebar setup
with st.sidebar:
    st.header("Settings")
    # Tries to read from Streamlit Secrets first, falls back to manual entry
    default_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
    api_key = st.text_input("Gemini API Key", value=default_key, type="password")
    
    st.markdown("---")
    current_df = load_data()
    # Export clean CSV (without heavy image base64 strings) for Google Sheets
    export_df = current_df.drop(columns=["Image_Base64"], errors="ignore")
    st.download_button(
        label="📥 Download CSV for Google Sheets",
        data=export_df.to_csv(index=False).encode('utf-8'),
        file_name="macro_history.csv",
        mime="text/csv"
    )

col1, col2 = st.columns([1, 1])

# Column 1: Upload and Analyze
with col1:
    st.subheader("📷 Upload Food Photo")
    uploaded_file = st.file_uploader("Snap or upload meal", type=["jpg", "jpeg", "png"])
    user_notes = st.text_input("Extra details (optional)", placeholder="e.g. 200g raw wagyu, no sugar in dressing")

    if uploaded_file and st.button("⚡ Analyze & Save Entry"):
        if not api_key:
            st.error("Please add your Gemini API Key in the sidebar or Secrets.")
        else:
            img = Image.open(uploaded_file).convert("RGB")
            st.image(img, caption="Analyzing meal...", use_column_width=True)

            with st.spinner("AI estimating macros..."):
                try:
                    client = genai.Client(api_key=api_key)
                    prompt = f"""
                    Identify the dish or food items in this photo.
                    User contextual notes: {user_notes}
                    Provide realistic estimates for:
                    - Category (Home Staples, Restaurant, Snack, Fruit, Drink)
                    - Item Name
                    - Portion / Serving basis
                    - Calories (kcal)
                    - Protein (g)
                    - Fat (g)
                    - Carbs (g)

                    Return ONLY a JSON object with this schema:
                    {{
                        "Category": str,
                        "Item Name": str,
                        "Portion": str,
                        "Calories": float,
                        "Protein": float,
                        "Fat": float,
                        "Carbs": float
                    }}
                    """

                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=[img, prompt],
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )

                    result = json.loads(response.text)
                    b64_str = image_to_base64(img)
                    save_entry(result, b64_str)
                    st.success(f"Saved {result['Item Name']} with photo!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error during analysis: {e}")

# Column 2: Dashboard (Table & Photo Gallery)
with col2:
    tab1, tab2 = st.tabs(["📊 Master Table", "🖼️ Photo Gallery"])
    
    df = load_data()
    
    with tab1:
        # Show clean text table
        table_view = df.drop(columns=["Image_Base64"], errors="ignore")
        st.dataframe(table_view, use_container_width=True, height=550)

    with tab2:
        # Visual feed showing photos paired with macro cards
        if df.empty:
            st.info("No meals logged yet.")
        else:
            for _, row in df.iterrows():
                with st.container():
                    c_img, c_info = st.columns([1, 2])
                    with c_img:
                        if pd.notna(row.get("Image_Base64")) and row["Image_Base64"]:
                            st.image(f"data:image/jpeg;base64,{row['Image_Base64']}", use_column_width=True)
                        else:
                            st.caption("No photo available")
                    with c_info:
                        st.markdown(f"**{row['Item Name']}** ({row.get('Category', 'Meal')})")
                        st.caption(f"Portion: {row.get('Portion', 'N/A')}")
                        st.markdown(
                            f"🔥 **{row.get('Calories', 0)} kcal** | "
                            f"🥩 **{row.get('Protein', 0)}g P** | "
                            f"🥑 **{row.get('Fat', 0)}g F** | "
                            f"🍚 **{row.get('Carbs', 0)}g C**"
                        )
                    st.divider()
