from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import streamlit as st

try:
    from groq import Groq
except ImportError:  # Deterministic search still works without the optional AI client.
    Groq = None  # type: ignore[assignment,misc]


APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "properties.txt"
DEFAULT_MODEL = "llama-3.1-8b-instant"

st.set_page_config(page_title="Property Finder AI", page_icon="🏠", layout="wide")
st.title("🏠 Property Finder AI")
st.write("Apne pasand ki location aur budget select karein, aur instant recommendations paayein!")


def get_secret(name: str, default: str = "") -> str:
    """Read Streamlit Secrets safely, then fall back to environment variables."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    return str(value or os.getenv(name, default) or default).strip()


def number_from(text: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", text.replace(",", ""))
    return float(match.group()) if match else None


def parse_properties(text: str) -> list[dict[str, Any]]:
    """Parse both the existing labelled format and pipe-separated rows."""
    properties: list[dict[str, Any]] = []
    block: dict[str, str] = {}

    def flush() -> None:
        nonlocal block
        if not block:
            return
        price = number_from(block.get("price", ""))
        bhk = number_from(block.get("name", ""))
        location = block.get("location", "").strip()
        if price is not None and location:
            properties.append(
                {
                    "title": block.get("name", "Property").strip(),
                    "location": location,
                    "bhk": int(bhk or number_from(block.get("features", "")) or 0),
                    "price_lakhs": price * 100 if "crore" in block.get("price", "").lower() else price,
                    "details": " ".join(
                        value.strip()
                        for key, value in block.items()
                        if key in {"features", "status"} and value.strip()
                    ),
                }
            )
        block = {}

    for raw_line in text.splitlines() + [""]:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            flush()
            continue
        if "|" in line and not block:
            parts = [part.strip() for part in line.split("|", 4)]
            if len(parts) >= 4:
                price = number_from(parts[3])
                if price is not None:
                    properties.append(
                        {
                            "title": parts[0],
                            "location": parts[1],
                            "bhk": int(number_from(parts[2]) or 0),
                            "price_lakhs": price,
                            "details": parts[4] if len(parts) == 5 else "",
                        }
                    )
                    continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if key.startswith("property name"):
                block["name"] = value
            elif key.startswith("location"):
                block["location"] = value
            elif key.startswith("price"):
                block["price"] = value
            elif key.startswith("features"):
                block["features"] = value
            elif key.startswith("status"):
                block["status"] = value
    return properties


@st.cache_data(show_spinner=False)
def load_properties() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    return parse_properties(DATA_FILE.read_text(encoding="utf-8"))


def contains_request(item: dict[str, Any], query: str) -> bool:
    if not query.strip():
        return True
    haystack = " ".join(str(value) for value in item.values()).lower()
    return all(token in haystack for token in re.findall(r"[\w.-]+", query.lower()))


def filter_properties(
    properties: list[dict[str, Any]], location: str, bhk: str, budget: float, query: str
) -> list[dict[str, Any]]:
    selected_bhk = number_from(bhk) if bhk != "Sabhi BHK" else None
    return [
        item
        for item in properties
        if (location == "Sabhi Locations" or item["location"].lower() == location.lower())
        and (selected_bhk is None or item["bhk"] == int(selected_bhk))
        and item["price_lakhs"] <= budget
        and contains_request(item, query)
    ]


def calculate_emi(loan_lakhs: float, annual_rate: float, years: int) -> float:
    months = years * 12
    monthly_rate = annual_rate / 12 / 100
    if loan_lakhs <= 0 or monthly_rate <= 0:
        return 0.0
    principal = loan_lakhs * 100000
    factor = (1 + monthly_rate) ** months
    return principal * monthly_rate * factor / (factor - 1)


def ai_summary(matches: list[dict[str, Any]], location: str, bhk: str, budget: float, query: str) -> str:
    api_key = get_secret("GROQ_API_KEY")
    if not api_key or Groq is None or not matches:
        return ""
    context = "\n".join(
        f"- {item['title']} | {item['location']} | {item['bhk']} BHK | ₹{item['price_lakhs']:.0f} lakh | {item['details']}"
        for item in matches[:10]
    )
    prompt = (
        "You are a concise Indian real-estate assistant. Reply in Hindi/Hinglish. "
        "Only use properties in the supplied list; never invent facts. "
        f"Filters: location={location}; BHK={bhk}; max budget=₹{budget:.0f} lakh; request={query or 'none'}.\n\n"
        f"Matching properties:\n{context}\n\nGive a short comparison and next step."
    )
    try:
        client = Groq(api_key=api_key)
        result = client.chat.completions.create(
            model=get_secret("GROQ_MODEL", DEFAULT_MODEL),
            messages=[
                {"role": "system", "content": "Be accurate, brief, and grounded in the supplied data."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=350,
        )
        return (result.choices[0].message.content or "").strip()
    except Exception as exc:
        st.warning(f"AI summary unavailable; verified filter results are shown. ({exc})")
        return ""


properties = load_properties()
if not properties:
    st.error("properties.txt missing ya invalid hai. Repository mein valid property data add karein.")
    st.stop()

locations = ["Sabhi Locations"] + sorted({item["location"] for item in properties})
bhks = ["Sabhi BHK"] + [f"{value} BHK" for value in sorted({item["bhk"] for item in properties if item["bhk"]})]

with st.sidebar:
    st.header("🔍 Advanced Filters")
    selected_location = st.selectbox("Location Chuniye:", locations)
    selected_bhk = st.selectbox("BHK Chuniye:", bhks)
    max_budget = st.slider("Maximum Budget (in Lakhs):", 20, 500, 200, 10)
    st.divider()
    st.header("🧮 Home Loan EMI Calculator")
    loan_amount = st.number_input("Loan Amount (₹ Lakhs):", min_value=0.0, value=float(max_budget * 0.8), step=5.0)
    interest_rate = st.slider("Interest Rate (% p.a.):", 6.0, 12.0, 8.5, 0.1)
    tenure_years = st.slider("Tenure (Years):", 5, 30, 20, 1)
    st.success(f"Estimated Monthly EMI: ₹{calculate_emi(loan_amount, interest_rate, tenure_years):,.0f}")

user_req = st.text_input("Aapki Special Requirement (Optional):", placeholder="jaise: Near park, modular kitchen...")

if st.button("Property Search Karein", type="primary"):
    matches = filter_properties(properties, selected_location, selected_bhk, max_budget, user_req)
    st.subheader(f"{len(matches)} matching recommendation(s)")
    if not matches:
        st.info("Is filter combination ke liye property nahi mili. Budget ya filters badal kar try karein.")
    else:
        for item in matches:
            with st.container(border=True):
                st.markdown(f"### {item['title']}")
                st.write(f"**{item['location']} · {item['bhk']} BHK · ₹{item['price_lakhs']:.0f} lakh**")
                if item["details"]:
                    st.write(item["details"])
        summary = ai_summary(matches, selected_location, selected_bhk, max_budget, user_req)
        if summary:
            st.divider()
            st.subheader("AI Assistant Summary")
            st.info(summary)
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.image(
                "https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=600",
                caption="Property Preview",
                use_container_width=True,
            )
        with col2:
            st.subheader("Agent Contact & Location")
            st.markdown("[🗺️ View Location on Google Maps](https://maps.google.com)")
            st.link_button(
                "💬 WhatsApp Agent Par Baat Karein",
                "https://wa.me/919876543210?text=Hello%2C%20I%20am%20interested%20in%20the%20property%20listing.",
            )
else:
    st.info("Sidebar se filters set karke 'Property Search Karein' par click karein.")
