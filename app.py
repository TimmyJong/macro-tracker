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

# Function to compress image into a base64 data-URI thumbnail
def image_to_base64_uri(img):
    img_copy = img.copy()
    img_copy.thumbnail((300, 300))
    buffered = BytesIO()
    img_copy.save(buffered, format="JPEG", quality=75)
    b64 = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{b64}"

# Default historical table items
INITIAL_DATA = [
    {"Photo": None, "Category": "Home Staples", "Item Name": "Boiled Rice Vermicelli (Bún)", "Portion": "100g cooked", "Calories": 120, "Protein": 2.0, "Fat": 0.4, "Carbs": 26.5},
    {"Photo": None, "Category": "Home Staples", "Item Name": "Pork Hock (Giò Heo)", "Portion": "Plate (240g edible)", "Calories": 600, "Protein": 51.5, "Fat": 44.0, "Carbs": 0.0},
    {"Photo": None, "Category": "Home Staples", "Item Name": "Grass-Fed Eye Fillet", "Portion": "100g cooked", "Calories": 178, "Protein": 30.0, "Fat": 6.0, "Carbs": 0.0},
    {"Photo": None, "Category": "Home Staples", "Item Name": "Coles Slow Cook Pork Scotch", "Portion": "100g cooked", "Calories": 243, "Protein": 29.0, "Fat": 14.0, "Carbs": 0.0},
    {"Photo": None, "Category": "Home Staples", "Item Name": "MC Yee Thin Egg Noodles", "Portion": "Bowl (~200g)", "Calories": 360, "Protein": 18.0, "Fat": 3.2, "Carbs": 64.0},
    {"Photo": None, "Category": "Home Staples", "Item Name": "Pork & Prawn Wontons", "Portion": "Bowl (10 pcs)", "Calories": 420, "Protein": 24.5, "Fat": 18.0, "Carbs": 39.0},
    {"Photo": None, "Category": "Home Staples", "Item Name": "Beef Shin / Gravy Beef", "Portion": "100g braised", "Calories": 205, "Protein": 32.5, "Fat": 8.0, "Carbs": 0.0},
    {"Photo": None, "Category": "Home Staples", "Item Name": "Oakleigh Ranch Wagyu Shin", "Portion": "100g simmered", "Calories": 255, "Protein": 30.0, "Fat": 15.0, "Carbs": 0.0},
    {"Photo": None, "Category": "Home Staples", "Item Name": "Thick Bún Bò Huế Noodles", "Portion": "Colander (~600g)", "Calories": 740, "Protein": 13.5, "Fat": 2.5, "Carbs": 168.0},
    {"Photo": None, "Category": "Home Staples", "Item Name": "Bò Kho Beef Chunks", "Portion": "100g cooked meat", "Calories": 223, "Protein": 30.5, "Fat": 11.0, "Carbs": 1.5},
    {"Photo": None, "Category": "Home Staples", "Item Name": "Bò Kho Broth", "Portion": "1 Cup (~250 mL)", "Calories": 125, "Protein": 5.0, "Fat": 7.0, "Carbs": 9.0},
    {"Photo": None, "Category": "Snacks & Fruit", "Item Name": "White Guava (Ổi)", "Portion": "Plate (~220g sliced)", "Calories": 150, "Protein": 5.5, "Fat": 2.0, "Carbs": 31.5},
    {"Photo": None, "Category": "Restaurant", "Item Name": "Piqle Original Beef Sliders", "Portion": "2 Sliders", "Calories": 680, "Protein": 34.0, "Fat": 40.0, "Carbs": 46.0},
    {"Photo": None, "Category": "Restaurant", "Item Name": "Piqle French Fries", "Portion": "1 Serving", "Calories": 360, "Protein": 4.0, "Fat": 18.0, "Carbs": 45.0},
    {"Photo": None, "Category": "Restaurant", "Item Name": "Grill'd Caesar's Palace", "Portion": "1 Burger", "Calories": 680, "Protein": 51.0, "Fat": 33.0, "Carbs": 46.0},
    {"Photo": None, "Category": "Restaurant", "Item Name": "Phở An Beef Combination", "Portion": "Large Bowl", "Calories": 770, "Protein": 57.0, "Fat": 20.0, "Carbs": 92.0},
    {"Photo": None, "Category": "Restaurant", "Item Name": "Caraway Wagyu Udon & Marrow", "Portion": "Full Bowl + Canoe", "Calories": 1170, "Protein": 43.5, "Fat": 81.0, "Carbs": 73.5},
]

def load_data():
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(INITIAL_DATA)
        df.to_csv(CSV_FILE, index=False)
    df = pd.read_csv(CSV_FILE)
    if "Photo" not in df.columns:
        df["Photo"] = None
    return df

def save_entry(entry_dict, img_uri):
    df = load_data()
    entry_dict["Photo"] = img_uri
    new_df = pd.concat([pd.DataFrame([entry_dict]), df], ignore_index=True)
    new_df.to_csv(CSV_FILE, index=False)

st.title("🥗 Macro Tracker Hub")

with st.sidebar:
    st.header("Settings")
    default_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
    api_key = st.text_input("Gemini API Key", value=default_key, type="password")
    
    st.markdown("---")
    current_df = load_data()
    export_df = current_df.drop(columns=["Photo"], errors="ignore")
    st.download_button(
        label="📥 Download Clean CSV",
        data=export_df.to_csv(index=False).encode('utf-8'),
        file_name="macro_history.csv",
        mime="text/csv"
    )

col1, col2 = st.columns([1, 1])

# Photo Upload & Analysis
with col1:
    st.subheader("📷 Log Meal Photo")
    uploaded_file = st.file_uploader("Upload meal image", type=["jpg", "jpeg", "png"])
    user_notes = st.text_input("Extra details (optional)", placeholder="e.g. Marinated Wagyu cooked, ~280g")

    if uploaded_file and st.button("⚡ Analyze & Add to Table"):
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
                    uri = image_to_base64_uri(img)
                    save_entry(result, uri)
                    st.success(f"Added {result['Item Name']} to your table!")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error during analysis: {e}")

# Master Table with Inline Images
with col2:
    tab1, tab2 = st.tabs(["📊 Master Table", "🖼️ Photo Feed"])
    df = load_data()
    
    with tab1:
        st.dataframe(
            df,
            column_config={
                "Photo": st.column_config.ImageColumn(
                    "Photo",
                    help="Meal photo thumbnail (double-click to zoom)",
                    width="small"
                ),
                "Calories": st.column_config.NumberColumn("Calories (kcal)", format="%d"),
                "Protein": st.column_config.NumberColumn("Protein (g)", format="%.1f"),
                "Fat": st.column_config.NumberColumn("Fat (g)", format="%.1f"),
                "Carbs": st.column_config.NumberColumn("Carbs (g)", format="%.1f"),
            },
            column_order=["Photo", "Category", "Item Name", "Portion", "Calories", "Protein", "Fat", "Carbs"],
            use_container_width=True,
            height=600,
            hide_index=True
        )

    with tab2:
        feed_df = df[df["Photo"].notna() & (df["Photo"] != "")]
        if feed_df.empty:
            st.info("No meals with photos uploaded yet.")
        else:
            for _, row in feed_df.iterrows():
                with st.container():
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.image(row["Photo"], use_column_width=True)
                    with c2:
                        st.markdown(f"**{row['Item Name']}** ({row.get('Category', 'Meal')})")
                        st.caption(f"Portion: {row.get('Portion', 'N/A')}")
                        st.markdown(
                            f"🔥 **{row.get('Calories', 0)} kcal** | "
                            f"🥩 **{row.get('Protein', 0)}g P** | "
                            f"🥑 **{row.get('Fat', 0)}g F** | "
                            f"🍚 **{row.get('Carbs', 0)}g C**"
                        )
                    st.divider()
