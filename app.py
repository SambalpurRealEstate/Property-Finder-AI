import os
import streamlit as st
from langchain_community.document_loaders import TextLoader
from langchain_community.llms import Ollama

st.set_page_config(page_title="Property Finder AI", page_icon="🏠", layout="centered")

st.title("🏠 Multi-Property Local AI Assistant")
st.write("Apne pasand ki location aur budget select karein, aur instant recommendations paayein!")

@st.cache_resource
def load_data():
    loader = TextLoader("properties.txt")
    documents = loader.load()
    return documents[0].page_content
property_data = load_data()

# Local Ollama Model
llm = Ollama(model="llama3")

# --- UI Filters (Phase 1) ---
st.sidebar.header("🔍 Advanced Filters")
selected_location = st.sidebar.selectbox("Location Chuniye:", ["Sabhi Locations", "Golf Course Road", "Prime City Center", "MG Road", "Sector 45"])
selected_bhk = st.sidebar.selectbox("BHK Chuniye:", ["Sabhi BHK", "1 BHK", "2 BHK", "3 BHK", "4 BHK"])
max_budget = st.sidebar.slider("Maximum Budget (in Lakhs):", min_value=20, max_value=500, value=200, step=10)

# --- Phase 3: EMI Calculator (Sidebar Widget) ---
st.sidebar.divider()
st.sidebar.header("🧮 Home Loan EMI Calculator")
loan_amount = st.sidebar.number_input("Loan Amount (₹ Lakhs):", value=float(max_budget * 0.8), step=5.0)
interest_rate = st.sidebar.slider("Interest Rate (% p.a.):", min_value=6.0, max_value=12.0, value=8.5, step=0.1)
tenure_years = st.sidebar.slider("Tenure (Years):", min_value=5, max_value=30, value=20, step=1)

# EMI Calculation Logic
r = (interest_rate / 12) / 100
n = tenure_years * 12
if loan_amount > 0 and r > 0:
    p = loan_amount * 100000
    emi = (p * r * ((1 + r)**n)) / (((1 + r)**n) - 1)
    st.sidebar.success(f"Est. Monthly EMI: ₹{int(emi):,}")

# Main input box
user_req = st.text_input("Aapki Special Requirement (Optional):", placeholder="jaise: Near park, modular kitchen...")

if st.button("Property Search Karein"):
    combined_requirement = f"Location filter: {selected_location}, BHK filter: {selected_bhk}, Max Budget: ₹{max_budget} Lakhs, Additional details: {user_req}"
    
    st.success("Yeh rahe aapke liye top matching recommendations:")
    
    prompt = f"""
Aap ek Real Estate Assistant hain. Niche diye gaye database me se user ki requirement aur filters ke liye sabse matching top 3 best properties recommend karein.

Property Database:
{property_data}

User Filters & Requirement: {combined_requirement}

Strict Instructions:
- Response sirf Hindi bhasha (language) mein hi dein.
- Har property ke liye 3-4 short bullet points dein (Property Name, Price, Location, Key Feature).
- Har property ke aakhiri bullet point mein us location ka brief Neighborhood Feedback (Connectivity, Safety) batayein.
- Agar 3 se kam matching properties hain, toh jitni milein utni hi dikhayein.
- Koi extra explanation mat likhein.
"""
    response = llm.invoke(prompt)
    
    # Text Response from Llama 3
    st.markdown(response)
    
    st.divider()
    
    # --- Phase 2: Media & Links ---
    st.subheader("📍 Quick Actions & Media")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.image("https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=600", caption="Property Preview", use_container_width=True)
    
    with col2:
        st.markdown("### Agent Contact & Location")
        st.markdown("[🗺️ View Location on Google Maps](https://maps.google.com)", unsafe_allow_html=True)
        
        # WhatsApp Chat Link
        whatsapp_url = "https://wa.me/919876543210?text=Hello,%20I%20am%20interested%20in%20the%20property%20listing."
        st.link_button("💬 WhatsApp Agent Par Baat Karein", whatsapp_url)

else:
    st.warning("Kripya sidebar se filters set karke 'Property Search Karein' par click karein.")