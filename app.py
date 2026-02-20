import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import streamlit as st
from PIL import Image
import tempfile
import random
import string
import requests
from geopy.geocoders import Nominatim
import folium
from streamlit_folium import st_folium
from datetime import datetime

# Import utilities
from utils.supabase_client import SupabaseDB
from utils.ai_models import get_image_classifier, get_voice_to_text, get_text_classifier
from utils.pdf_generator import generate_complaint_pdf
from utils.notifications import get_notification_service

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="🧠 SmartNaggar - AI Civic Reporter", 
    layout="wide", 
    page_icon="🛠️",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        font-weight: bold;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-card {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------
# INITIALIZE SERVICES
# ----------------------------
@st.cache_resource
def init_services():
    """Initialize all services"""
    return {
        'db': SupabaseDB(),
        'image_clf': get_image_classifier(),
        'voice_stt': get_voice_to_text(),
        'text_clf': get_text_classifier(),
        'notifier': get_notification_service()
    }

services = init_services()

# ----------------------------
# LANGUAGE TOGGLER
# ----------------------------
lang_option = st.sidebar.selectbox(
    "Select Language / زبان منتخب کریں", 
    ["English", "Urdu"],
    key="language_selector"
)

def get_label(key):
    labels = {
        "title": {"English": "SmartNaggar - AI Civic Problem Reporter", "Urdu": "سمارٹ نگر - اے آئی شہری مسائل رپورٹر"},
        "description": {"English": "Report civic issues via text, camera, image, or voice. Get instant tracking and updates.", "Urdu": "ٹیکسٹ، کیمرہ، تصویر یا آواز کے ذریعے شہری مسائل رپورٹ کریں۔ فوری ٹریکنگ حاصل کریں۔"},
        "select_input": {"English": "Select Input Method", "Urdu": "ان پٹ کا طریقہ منتخب کریں"},
        "text": {"English": "Text Description", "Urdu": "تحریری وضاحت"},
        "camera": {"English": "📷 Live Camera", "Urdu": "📷 لائیو کیمرہ"},
        "upload_image": {"English": "🖼️ Upload Image", "Urdu": "🖼️ تصویر اپ لوڈ کریں"},
        "upload_voice": {"English": "🎤 Upload Voice", "Urdu": "🎤 آواز اپ لوڈ کریں"},
        "describe_issue": {"English": "Describe the issue in detail...", "Urdu": "مسئلے کی تفصیل بیان کریں..."},
        "location_section": {"English": "📍 Location Information", "Urdu": "📍 مقام کی معلومات"},
        "enter_location": {"English": "Enter exact location", "Urdu": "صحیح مقام درج کریں"},
        "detect_location": {"English": "🌍 Auto-Detect Location", "Urdy": "🌍 خودکار مقام"},
        "select_district": {"English": "Select District/City", "Urdu": "ضلع / شہر منتخب کریں"},
        "contact_info": {"English": "📧 Contact Information (Optional)", "Urdu": "📧 رابطہ معلومات (اختیاری)"},
        "email": {"English": "Email address", "Urdu": "ای میل ایڈریس"},
        "phone": {"English": "Phone number", "Urdu": "فون نمبر"},
        "generate_complaint": {"English": "🚀 Submit Complaint", "Urdu": "🚀 شکایت جمع کریں"},
        "download_pdf": {"English": "📄 Download PDF", "Urdu": "📄 PDF ڈاؤن لوڈ کریں"},
        "tracking_id": {"English": "Tracking ID", "Urdu": "ٹریکنگ آئی ڈی"},
        "success": {"English": "✅ Complaint Submitted Successfully!", "Urdy": "✅ شکایت کامیابی سے جمع!"},
        "warning_input": {"English": "⚠️ Please provide input (text, image, or voice)", "Urdu": "⚠️ براہ کرم ان پٹ فراہم کریں"},
        "track_complaint": {"English": "🔍 Track Your Complaint", "Urdu": "🔍 اپنی شکایت ٹریک کریں"},
        "recent_complaints": {"English": "📊 Recent Complaints", "Urdu": "📊 حالیہ شکایات"},
        "ai_analyzing": {"English": "🤖 AI is analyzing your input...", "Urdu": "🤖 اے آئی تجزیہ کر رہا ہے..."},
    }
    return labels.get(key, {}).get(lang_option, key)

# ----------------------------
# UTILITY FUNCTIONS
# ----------------------------
def generate_tracking_id():
    """Generate unique tracking ID"""
    return "CIV-" + ''.join(random.choices(string.digits, k=6))

def detect_location():
    """Auto-detect location via IP"""
    try:
        res = requests.get("https://ipinfo.io/json", timeout=5).json()
        return f"{res.get('city', 'Unknown')}, {res.get('region', '')}, {res.get('country', '')}"
    except:
        return "Unknown"

def display_map(location_str, tracking_id):
    """Display location on map"""
    if not location_str or location_str.strip() == "" or location_str.lower() == "unknown":
        st.warning("📍 Location not found")
        return
    
    try:
        geolocator = Nominatim(user_agent="smartnaggar_app")
        loc = geolocator.geocode(location_str, timeout=10)
        
        if not loc:
            st.warning("📍 Could not find location on map")
            return
        
        # Create map
        m = folium.Map(location=[loc.latitude, loc.longitude], zoom_start=15)
        
        # Add marker
        folium.Marker(
            location=[loc.latitude, loc.longitude],
            popup=f"<b>Issue Location</b><br>Tracking: {tracking_id}",
            tooltip="Reported Issue",
            icon=folium.Icon(color='red', icon='exclamation-triangle', prefix='fa')
        ).add_to(m)
        
        # Display map
        st_folium(m, width=700, height=400)
    except Exception as e:
        st.error(f"🗺️ Map unavailable: {str(e)}")

# ----------------------------
# MAIN APP UI
# ----------------------------
st.markdown(f"""
<div class="main-header">
    <h1>🧠 {get_label('title')}</h1>
    <p>{get_label('description')}</p>
</div>
""", unsafe_allow_html=True)

# Sidebar Info
with st.sidebar:
    st.image("https://via.placeholder.com/300x100/667eea/ffffff?text=SmartNaggar+AI", use_container_width=True)
    st.markdown("### 📋 How It Works")
    st.markdown("""
    1. **Report**: Describe issue via text/photo/voice
    2. **AI Analysis**: Automatic classification
    3. **Submit**: Get tracking ID instantly
    4. **Track**: Monitor progress in real-time
    5. **Resolve**: Department takes action
    """)
    
    st.markdown("---")
    st.markdown("### 📞 Emergency Contacts")
    st.markdown("- Police: 15\n- Rescue: 1122\n- Fire: 16")
    
    st.markdown("---")
    st.markdown("### 🔗 Quick Links")
    if st.button("🔐 Admin Login", use_container_width=True):
        st.switch_page("pages/admin.py")

# ----------------------------
# INPUT SECTION
# ----------------------------
st.subheader(f"📝 {get_label('select_input')}")

# Create tabs for different input methods
tab1, tab2, tab3, tab4 = st.tabs([
    get_label("text"),
    get_label("camera"),
    get_label("upload_image"),
    get_label("upload_voice")
])

user_text = ""
image_input = None
voice_input = None

with tab1:
    user_text = st.text_area(
        get_label("describe_issue"),
        height=150,
        placeholder="Example: There is a large pothole on Main Street causing traffic issues..."
    )

with tab2:
    st.info("📸 Enable your camera to capture the issue")
    image_input = st.camera_input("Capture Photo")

with tab3:
    image_input = st.file_uploader(
        get_label("upload_image"),
        type=["png", "jpg", "jpeg"],
        help="Upload a clear photo of the issue"
    )
    if image_input:
        st.image(image_input, caption="Uploaded Image", use_container_width=True)

with tab4:
    voice_input = st.file_uploader(
        get_label("upload_voice"),
        type=["mp3", "wav", "m4a"],
        help="Upload audio describing the issue"
    )
    if voice_input:
        st.audio(voice_input)

# ----------------------------
# LOCATION SECTION
# ----------------------------
st.markdown("---")
st.subheader(f"{get_label('location_section')}")

col1, col2 = st.columns([3, 1])

with col1:
    location_input = st.text_input(
        get_label("enter_location"),
        placeholder="E.g., Mall Road, Lahore"
    )

with col2:
    if st.button(get_label("detect_location"), use_container_width=True):
        with st.spinner("Detecting location..."):
            detected_loc = detect_location()
            st.session_state['location'] = detected_loc
            st.success(f"📍 {detected_loc}")
            location_input = detected_loc

# District selection
districts = [
    "Select",
    "Lahore", "Karachi", "Islamabad", "Rawalpindi",
    "Multan", "Faisalabad", "Peshawar", "Quetta",
    "Sialkot", "Gujranwala", "Bahawalpur", "Sargodha",
    "Hyderabad", "Sukkur", "Mardan", "Abbottabad"
]

district_input = st.selectbox(get_label("select_district"), districts)

# ----------------------------
# CONTACT INFORMATION (Optional)
# ----------------------------
st.markdown("---")
st.subheader(f"{get_label('contact_info')}")
st.info("💡 Provide contact info to receive updates via email/SMS")

col1, col2 = st.columns(2)
with col1:
    user_email = st.text_input(get_label("email"), placeholder="your.email@example.com")
with col2:
    user_phone = st.text_input(get_label("phone"), placeholder="+92 300 1234567")

# ----------------------------
# SUBMIT BUTTON
# ----------------------------
st.markdown("---")
submitted = st.button(
    get_label("generate_complaint"),
    type="primary",
    use_container_width=True
)

if submitted:
    # Validate input
    if not (user_text.strip() or image_input or voice_input):
        st.error(get_label("warning_input"))
    elif district_input == "Select":
        st.error("⚠️ Please select a district")
    elif not location_input:
        st.error("⚠️ Please provide location information")
    else:
        with st.spinner(get_label("ai_analyzing")):
            # Generate tracking ID
            tracking_id = generate_tracking_id()
            
            # Process voice input
            if voice_input:
                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                temp_audio.write(voice_input.read())
                temp_audio.flush()
                user_text = services['voice_stt'].transcribe(temp_audio.name)
                st.success(f"🎤 Transcribed: {user_text[:100]}...")
            
            # AI Classification
            if image_input:
                issue_type, severity, department = services['image_clf'].classify(Image.open(image_input))
            else:
                issue_type, severity, department = services['text_clf'].classify(user_text)
            
            # Prepare complaint data
            complaint_data = {
                'tracking_id': tracking_id,
                'issue_type': issue_type,
                'severity': severity,
                'department': department,
                'description': user_text if user_text else "See attached image",
                'location': location_input,
                'district': district_input,
                'status': 'Pending',
                'created_at': datetime.now().isoformat(),
                'email': user_email if user_email else None,
                'phone': user_phone if user_phone else None,
                'admin_notes': ''
            }
            
            # Upload image to Supabase if provided
            if image_input:
                image_url = services['db'].upload_image(image_input, tracking_id)
                complaint_data['image_url'] = image_url
            
            # Save to database
            result = services['db'].create_complaint(complaint_data)
            
            if result:
                # Success message
                st.balloons()
                st.success(get_label("success"))
                
                # Display complaint details
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    <div class="info-card">
                        <h3>📋 Complaint Details</h3>
                        <p><b>Tracking ID:</b> <span style="color: #667eea; font-size: 1.2em;">{tracking_id}</span></p>
                        <p><b>Issue Type:</b> {issue_type}</p>
                        <p><b>Severity:</b> <span style="color: {'red' if severity == 'High' else 'orange' if severity == 'Medium' else 'green'};">{severity}</span></p>
                        <p><b>Department:</b> {department}</p>
                        <p><b>Status:</b> Pending</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="info-card">
                        <h3>📍 Location Details</h3>
                        <p><b>District:</b> {district_input}</p>
                        <p><b>Location:</b> {location_input}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Display map
                st.subheader("🗺️ Issue Location")
                display_map(location_input, tracking_id)
                
                # Generate and offer PDF download
                pdf_file = generate_complaint_pdf(complaint_data, image_input)
                st.download_button(
                    label=get_label("download_pdf"),
                    data=pdf_file,
                    file_name=f"Complaint_{tracking_id}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                
                # Send notifications
                if user_email:
                    services['notifier'].send_complaint_confirmation(
                        user_email, tracking_id, issue_type, location_input
                    )
                    st.success(f"📧 Confirmation email sent to {user_email}")
                
                if user_phone:
                    services['notifier'].send_complaint_confirmation_sms(user_phone, tracking_id)
                    st.success(f"📱 SMS sent to {user_phone}")
                
                # Save tracking ID to session
                if 'my_complaints' not in st.session_state:
                    st.session_state['my_complaints'] = []
                st.session_state['my_complaints'].append(tracking_id)
            else:
                st.error("❌ Failed to submit complaint. Please try again.")

# ----------------------------
# TRACKING SECTION
# ----------------------------
st.markdown("---")
st.subheader(f"🔍 {get_label('track_complaint')}")

track_id = st.text_input("Enter Tracking ID", placeholder="CIV-123456")

if st.button("Track Status", use_container_width=True):
    if track_id:
        complaint = services['db'].get_complaint_by_id(track_id)
        
        if complaint:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                <div class="info-card">
                    <h3>Complaint Status</h3>
                    <p><b>Tracking ID:</b> {complaint['tracking_id']}</p>
                    <p><b>Issue:</b> {complaint['issue_type']}</p>
                    <p><b>Status:</b> <span style="color: {'green' if complaint['status'] == 'Resolved' else 'orange'};">{complaint['status']}</span></p>
                    <p><b>Location:</b> {complaint['location']}</p>
                    <p><b>Submitted:</b> {complaint['created_at'][:10]}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Status progress
                statuses = ["Pending", "Under Review", "Assigned", "In Progress", "Resolved"]
                current_idx = statuses.index(complaint['status']) if complaint['status'] in statuses else 0
                
                st.markdown("### Progress")
                for i, status in enumerate(statuses):
                    if i <= current_idx:
                        st.markdown(f"✅ {status}")
                    else:
                        st.markdown(f"⭕ {status}")
            
            # Show update history
            history = services['db'].get_complaint_history(track_id)
            if history:
                st.markdown("### 📜 Update History")
                for update in history:
                    st.markdown(f"- **{update['status']}** - {update['updated_at'][:10]}")
                    if update.get('notes'):
                        st.markdown(f"  _{update['notes']}_")
        else:
            st.error("❌ Tracking ID not found")
    else:
        st.warning("⚠️ Please enter a tracking ID")

# ----------------------------
# RECENT COMPLAINTS DASHBOARD
# ----------------------------
st.markdown("---")
st.subheader(f"📊 {get_label('recent_complaints')}")

recent_complaints = services['db'].get_all_complaints()

if recent_complaints:
    # Show summary stats
    col1, col2, col3, col4 = st.columns(4)
    
    stats = services['db'].get_complaint_stats()
    
    with col1:
        st.metric("Total Complaints", stats['total'])
    with col2:
        pending = stats['by_status'].get('Pending', 0)
        st.metric("Pending", pending)
    with col3:
        resolved = stats['by_status'].get('Resolved', 0)
        st.metric("Resolved", resolved)
    with col4:
        resolution_rate = (resolved / stats['total'] * 100) if stats['total'] > 0 else 0
        st.metric("Resolution Rate", f"{resolution_rate:.1f}%")
    
    # Show recent complaints table
    st.markdown("### Latest 10 Complaints")
    for complaint in recent_complaints[:10]:
        with st.expander(f"{complaint['tracking_id']} - {complaint['issue_type']} ({complaint['status']})"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**District:** {complaint['district']}")
                st.markdown(f"**Location:** {complaint['location']}")
                st.markdown(f"**Severity:** {complaint['severity']}")
            with col2:
                st.markdown(f"**Department:** {complaint['department']}")
                st.markdown(f"**Submitted:** {complaint['created_at'][:10]}")
                st.markdown(f"**Status:** {complaint['status']}")
else:
    st.info("No complaints submitted yet. Be the first to report!")

# ----------------------------
# FOOTER
# ----------------------------
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p><b>SmartNaggar AI</b> - Making Cities Better Together 🏙️</p>
    <p>Powered by Generative AI | Built for HEC Hackathon 2025</p>
    <p>📧 support@smartnaggar.ai | 🌐 www.smartnaggar.ai</p>
</div>
""", unsafe_allow_html=True)