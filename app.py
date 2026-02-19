import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import streamlit as st
from fpdf import FPDF
from io import BytesIO
from PIL import Image
import tempfile
import random
import string
import requests
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import st_folium
import torch
import torchvision.transforms as transforms
from torchvision import models
import whisper
import sqlite3
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(page_title="🧠Smart Naggar - AI Civic Reporter", layout="wide", page_icon="🛠️")

# ----------------------------
# LANGUAGE TOGGLER
# ----------------------------
lang_option = st.sidebar.selectbox("Select Language / زبان منتخب کریں", ["English", "Urdu"])

def get_label(key):
    labels = {
        "title": {"English":"Smart Naggar-AI Civic Problem Reporter","Urdu":"ای آئی شہری مسائل رپورٹر"},
        "description": {"English":"Report issues via text, camera, upload image, or voice. Download complaint PDF.","Urdu":"ٹیکسٹ، کیمرہ، تصویر یا آواز کے ذریعے مسائل رپورٹ کریں۔ شکایت PDF ڈاؤن لوڈ کریں۔"},
        "select_input": {"English":"Select Input Type","Urdu":"ان پٹ کی قسم منتخب کریں"},
        "text": {"English":"Text","Urdu":"ٹیکسٹ"},
        "camera": {"English":"Live Camera","Urdu":"لائیو کیمرہ"},
        "upload_image": {"English":"Upload Image","Urdu":"تصویر اپ لوڈ کریں"},
        "record_voice": {"English":"Record Voice","Urdu":"آواز ریکارڈ کریں"},
        "upload_voice": {"English":"Upload Voice","Urdu":"آواز اپ لوڈ کریں"},
        "describe_issue": {"English":"Describe the issue","Urdu":"مسئلے کی وضاحت کریں"},
        "enter_location": {"English":"Enter Location or Detect Automatically","Urdu":"مقام درج کریں یا خودکار طور پر معلوم کریں"},
        "generate_complaint": {"English":"Generate Complaint","Urdu":"شکایت تیار کریں"},
        "download_pdf": {"English":"Download Complaint PDF","Urdu":"شکایت PDF ڈاؤن لوڈ کریں"},
        "tracking_id": {"English":"Tracking ID","Urdu":"ٹریکنگ آئی ڈی"},
        "success": {"English":"Complaint Generated Successfully! ✅","Urdu":"شکایت کامیابی سے تیار ہوگئی! ✅"},
        "warning_input": {"English":"Please provide text, image, or voice input","Urdu":"براہ کرم ٹیکسٹ، تصویر یا آواز فراہم کریں"},
        "location_not_found": {"English":"Location not found","Urdu":"مقام نہیں ملا"},
        "map_unavailable": {"English":"Map service unavailable","Urdu":"نقشہ دستیاب نہیں"},
        "select_district": {"English":"Select District/City","Urdu":"ضلع / شہر منتخب کریں"},
        "detect_location": {"English":"Detect My Location","Urdu":"میری موجودہ جگہ معلوم کریں"},
        "tracking_dashboard": {"English":"Tracking Dashboard","Urdu":"ٹریکنگ ڈیش بورڈ"}
    }
    return labels[key][lang_option]

# ----------------------------
# TRACKING ID
# ----------------------------
def generate_tracking_id():
    return "CIV-" + ''.join(random.choices(string.digits, k=4))

# ----------------------------
# DATABASE SETUP
# ----------------------------
conn = sqlite3.connect("complaints.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS complaints (
            tracking_id TEXT PRIMARY KEY,
            text TEXT,
            location TEXT,
            district TEXT,
            image_path TEXT,
            issue_type TEXT,
            severity TEXT,
            department TEXT,
            status TEXT,
            created_at TEXT
            )""")
conn.commit()

# ----------------------------
# LOAD IMAGE MODEL
# ----------------------------
@st.cache_resource(show_spinner=True)
def load_image_model():
    model = models.mobilenet_v2(pretrained=True)
    model.eval()
    return model

model = load_image_model()
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])
])

# Placeholder features for demo
ISSUE_FEATURES = {
    "Pothole": torch.randn(1280),
    "Garbage": torch.randn(1280),
    "Water Leak": torch.randn(1280),
    "Broken Streetlight": torch.randn(1280)
}
SEVERITY_MAP = {"Pothole":"High","Garbage":"Medium","Water Leak":"High","Broken Streetlight":"Medium"}
DEPARTMENT_MAP = {"Pothole":"Roads Department","Garbage":"Sanitation","Water Leak":"Water & Sewage","Broken Streetlight":"Electricity"}

def classify_image(img):
    img = img.convert("RGB")
    tensor = transform(img).unsqueeze(0)
    with torch.no_grad():
        features = model.features(tensor)
        features = torch.nn.functional.adaptive_avg_pool2d(features, (1,1))
        features = features.view(features.size(0), -1)[0]
    max_sim = -1
    predicted_issue = "Other"
    for issue, feat in ISSUE_FEATURES.items():
        sim = torch.nn.functional.cosine_similarity(features, feat, dim=0)
        if sim > max_sim:
            max_sim = sim
            predicted_issue = issue
    severity = SEVERITY_MAP.get(predicted_issue, "Low")
    department = DEPARTMENT_MAP.get(predicted_issue, "General")
    return predicted_issue, severity, department

# ----------------------------
# VOICE MODEL
# ----------------------------
@st.cache_resource(show_spinner=True)
def load_voice_model():
    return whisper.load_model("tiny")
voice_model = load_voice_model()

def voice_to_text(audio_file):
    try:
        result = voice_model.transcribe(audio_file)
        return result["text"]
    except:
        return ""

# ----------------------------
# PDF GENERATOR
# ----------------------------
def generate_pdf(tracking_id, complaint_text, location, uploaded_file=None):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"AI Civic Problem Complaint",ln=True,align="C")
    pdf.ln(10)
    pdf.set_font("Arial","",12)
    pdf.cell(0,10,f"Tracking ID: {tracking_id}",ln=True)
    pdf.cell(0,10,f"Location: {location}",ln=True)
    pdf.ln(5)
    pdf.multi_cell(0,10,complaint_text)
    if uploaded_file:
        try:
            image = Image.open(uploaded_file)
            temp_file = tempfile.NamedTemporaryFile(delete=False,suffix=".png")
            image.save(temp_file.name)
            pdf.ln(10)
            pdf.image(temp_file.name,x=15,w=180)
        except:
            pass
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_bytes)

# ----------------------------
# LOCATION DETECTION
# ----------------------------
def detect_location():
    try:
        res = requests.get("https://ipinfo.io/json").json()
        return f"{res.get('city','Unknown')}, {res.get('region','')}, {res.get('country','')}"
    except:
        return "Unknown"

# ----------------------------
# MAP DISPLAY
# ----------------------------
def display_map(location_str, tracking_id):
    if not location_str or location_str.strip() == "" or location_str.lower() == "unknown":
        st.warning(get_label("location_not_found"))
        return
    try:
        geolocator = Nominatim(user_agent="civic_app")
        loc = geolocator.geocode(location_str, timeout=10)
        if not loc:
            st.warning(get_label("location_not_found"))
            return
        m = folium.Map(location=[loc.latitude, loc.longitude], zoom_start=15)
        folium.Marker(
            location=[loc.latitude, loc.longitude],
            popup=str(f"Issue Location - {tracking_id}"),
            tooltip=str("Reported Issue")
        ).add_to(m)
        st_folium(m, width=700, height=500)
    except Exception as e:
        st.error(f"{get_label('map_unavailable')} ({e})")

# ----------------------------
# TEXT CLASSIFIER (NLP)
# ----------------------------
# Simple TF-IDF + LogisticRegression for demo
text_examples = [
    ("There is a big pothole on the main road", "Pothole"),
    ("Garbage dump near my house", "Garbage"),
    ("Pipe is leaking water", "Water Leak"),
    ("Streetlight not working", "Broken Streetlight")
]
texts, labels = zip(*text_examples)
vectorizer = TfidfVectorizer()
X_train = vectorizer.fit_transform(texts)
clf = LogisticRegression()
clf.fit(X_train, labels)

def classify_text(text):
    X_test = vectorizer.transform([text])
    pred = clf.predict(X_test)[0]
    return pred, SEVERITY_MAP.get(pred,"Low"), DEPARTMENT_MAP.get(pred,"General")

# ----------------------------
# APP UI
# ----------------------------
st.header(get_label("title"))
st.write(get_label("description"))
st.subheader(get_label("select_input"))

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    get_label("text"),
    get_label("camera"),
    get_label("upload_image"),
    get_label("record_voice"),
    get_label("upload_voice")
])

user_text, image_input, voice_input, recorded_audio = "", None, None, None

with tab1:
    user_text = st.text_area(get_label("describe_issue"))
with tab2:
    image_input = st.camera_input("Click to turn camera ON")
with tab3:
    image_input = st.file_uploader(get_label("upload_image"), type=["png","jpg","jpeg"])
with tab4:
    recorded_audio = st.file_uploader(get_label("record_voice"), type=["mp3","wav"])
with tab5:
    voice_input = st.file_uploader(get_label("upload_voice"), type=["mp3","wav"])

districts = ["Select"] + ["Lahore","Karachi","Islamabad","Rawalpindi","Multan","Faisalabad","Peshawar","Quetta"]
district_input = st.selectbox(get_label("select_district"), districts)

if "location_input" not in st.session_state:
    st.session_state["location_input"] = ""
col1, col2 = st.columns([2,1])
with col1:
    st.session_state["location_input"] = st.text_input(get_label("enter_location"), st.session_state["location_input"])
with col2:
    if st.button(get_label("detect_location")):
        st.session_state["location_input"] = detect_location()
        st.success(f"Detected Location: {st.session_state['location_input']}")
location_input = st.session_state["location_input"]

# ----------------------------
# SUBMIT BUTTON
# ----------------------------
submitted = st.button(get_label("generate_complaint"))

if submitted:
    if user_text.strip() or image_input or voice_input or recorded_audio:
        tracking_id = generate_tracking_id()

        # Voice handling
        if voice_input:
            temp_audio_file = tempfile.NamedTemporaryFile(delete=False)
            temp_audio_file.write(voice_input.read())
            temp_audio_file.flush()
            user_text = voice_to_text(temp_audio_file.name)
        elif recorded_audio:
            temp_audio_file = tempfile.NamedTemporaryFile(delete=False)
            temp_audio_file.write(recorded_audio.read())
            temp_audio_file.flush()
            user_text = voice_to_text(temp_audio_file.name)

        # Image / Text classification
        if image_input:
            issue_type, severity, department = classify_image(Image.open(image_input))
        else:
            issue_type, severity, department = classify_text(user_text)

        # Complaint status
        status = "Pending"

        complaint_text = f"""
Issue Type: {issue_type}
Severity: {severity}
Assigned Department: {department}

Citizen report at {location_input if location_input else 'Unknown Location'} (District: {district_input if district_input != 'Select' else 'Unknown'}):
{user_text if user_text else 'See attached image'}

Tracking ID: {tracking_id}
Status: {status}
"""

        # Save image temporarily
        image_path = None
        if image_input:
            temp_file = tempfile.NamedTemporaryFile(delete=False,suffix=".png")
            img = Image.open(image_input)
            img.save(temp_file.name)
            image_path = temp_file.name

        # Save complaint to DB
        c.execute("INSERT INTO complaints VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (tracking_id, complaint_text, location_input, district_input, image_path,
                   issue_type, severity, department, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

        st.success(get_label("success"))
        st.subheader("📝 Complaint")
        st.write(complaint_text)

        # Show map
        display_map(location_input, tracking_id)

        # PDF download
        pdf_file = generate_pdf(tracking_id, complaint_text, location_input, image_input)
        st.download_button(label=get_label("download_pdf"),
                           data=pdf_file,
                           file_name=f"Complaint_{tracking_id}.pdf",
                           mime="application/pdf")
        if image_input:
            st.image(image_input, caption="Captured/Uploaded Evidence", use_column_width=True)
    else:
        st.warning(get_label("warning_input"))

# ----------------------------
# TRACKING DASHBOARD
# ----------------------------
st.subheader(get_label("tracking_dashboard"))
rows = c.execute("SELECT tracking_id, district, location, status FROM complaints").fetchall()
if rows:
    for row in rows:
        st.write(f"**{row[0]}** | District: {row[1]} | Location: {row[2]} | Status: {row[3]}")
else:
    st.write("No complaints submitted yet.")
