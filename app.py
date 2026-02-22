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
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import folium
from streamlit_folium import st_folium
from datetime import datetime
import pycountry

# Import utilities
from utils.supabase_client import SupabaseDB
from utils.ai_models import get_image_classifier, get_voice_to_text, get_text_classifier
from utils.pdf_generator import generate_complaint_pdf
from utils.notifications import get_notification_service
from utils.user_auth import require_auth
from utils.groq_client import get_groq_generator

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="🧠 SmartNaggar - AI Civic Reporter", 
    layout="wide", 
    page_icon="🛠️",
    initial_sidebar_state="expanded"
)

# Custom CSS with Urdu font fix
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Nastaliq+Urdu:wght@400;700&display=swap');
    
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
    .urdu-text {
        font-family: 'Noto Nastaliq Urdu', serif !important;
        direction: rtl;
        text-align: right;
        font-size: 1.1em;
        line-height: 1.8;
    }
    .map-container {
        border: 2px solid #667eea;
        border-radius: 10px;
        padding: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------
# REQUIRE AUTHENTICATION
# ----------------------------
auth = require_auth()
user = auth.get_current_user()

# ----------------------------
# INITIALIZE SERVICES
# ----------------------------
@st.cache_resource
def init_services():
    return {
        'db': SupabaseDB(),
        'image_clf': get_image_classifier(),
        'voice_stt': get_voice_to_text(),
        'text_clf': get_text_classifier(),
        'notifier': get_notification_service(),
        'groq': get_groq_generator()
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
        "title": {"English": "SmartNaggar - AI Civic Problem Reporter", "Urdu": "سمارٹ نگر - شہری مسائل رپورٹر"},
        "welcome": {"English": f"Welcome, {user['name']}!", "Urdu": f"خوش آمدید، {user['name']}!"},
        "logout": {"English": "🚪 Logout", "Urdu": "🚪 لاگ آؤٹ"},
        "my_complaints": {"English": "📋 My Complaints", "Urdu": "📋 میری شکایات"},
        "new_complaint": {"English": "➕ New Complaint", "Urdu": "➕ نئی شکایت"},
    }
    return labels.get(key, {}).get(lang_option, key)

# ----------------------------
# UTILITY FUNCTIONS
# ----------------------------
def generate_tracking_id():
    return "CIV-" + ''.join(random.choices(string.digits, k=6))

@st.cache_data
def get_countries():
    """Get list of all countries"""
    try:
        countries = [(country.name, country.alpha_2) for country in pycountry.countries]
        return sorted(countries, key=lambda x: x[0])
    except:
        return []

@st.cache_data
def get_regions_for_country(country_code):
    """Fetch administrative divisions (regions) for a country using Geonames API"""
    try:
        url = f"http://api.geonames.org/childrenJSON?geonameId=2988507&username=demo"
        # For Pakistan
        if country_code == "PK":
            regions = [
                "Punjab",
                "Sindh", 
                "Khyber Pakhtunkhwa",
                "Balochistan",
                "Islamabad Capital Territory",
                "Gilgit-Baltistan",
                "Azad Jammu and Kashmir"
            ]
            return regions
        
        # Try to fetch from API for other countries
        response = requests.get(f"https://restcountries.com/v3.1/alpha/{country_code.lower()}", timeout=5)
        if response.status_code == 200:
            return ["Region"]  # Placeholder for non-Pakistan countries
        return ["Region"]
    except:
        return ["Region"]

@st.cache_data
def get_cities_for_region(country_name, region_name):
    """Fetch cities for a region"""
    try:
        # For Pakistan regions
        pakistan_cities = {
            "Punjab": ["Lahore", "Faisalabad", "Multan", "Gujranwala", "Sialkot", "Okara", "Sargodha", "Bahawalpur", "Jhang", "Gujrat"],
            "Sindh": ["Karachi", "Hyderabad", "Sukkur", "Larkana", "Nawabshah", "Mirpur Khas", "Thatta", "Badin", "Khairpur"],
            "Khyber Pakhtunkhwa": ["Peshawar", "Mardan", "Swabi", "Kohat", "Dera Ismail Khan", "Abbottabad", "Mansehra", "Swat", "Buner", "Charsadda"],
            "Balochistan": ["Quetta", "Gwadar", "Turbat", "Zhob", "Loralai", "Kalat", "Pishin", "Sibi", "Khuzdar"],
            "Islamabad Capital Territory": ["Islamabad", "Rawalpindi"],
            "Gilgit-Baltistan": ["Gilgit", "Skardu", "Hunza", "Nagar"],
            "Azad Jammu and Kashmir": ["Muzaffarabad", "Mirpur", "Rawalakot"]
        }
        
        if country_name == "Pakistan":
            return pakistan_cities.get(region_name, [region_name])
        
        return [region_name]
    except:
        return [region_name]

def reverse_geocode_location(lat, lon):
    """Get address details from coordinates"""
    try:
        geolocator = Nominatim(user_agent="smartnaggar_app")
        location = geolocator.reverse(f"{lat}, {lon}", language='en', timeout=10)
        
        # Parse the address components
        address_parts = location.address.split(', ')
        
        return {
            'address': location.address,
            'latitude': lat,
            'longitude': lon
        }
    except (GeocoderTimedOut, GeocoderUnavailable):
        st.error("⏱️ Geocoding service timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"❌ Error getting address: {str(e)}")
        return None

def get_geolocation_html():
    """Return HTML/JS for browser geolocation with localStorage"""
    return """
    <script>
    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const data = {
                        lat: position.coords.latitude,
                        lon: position.coords.longitude,
                        accuracy: position.coords.accuracy
                    };
                    localStorage.setItem('geolocation_data', JSON.stringify(data));
                    console.log("Location saved:", data);
                    alert("✅ Location detected! Lat: " + data.lat.toFixed(4) + ", Lon: " + data.lon.toFixed(4) + "\\n\\nClick 'Refresh' button to load it.");
                },
                function(error) {
                    let msg = "Location access denied or unavailable.\\n\\n";
                    if (error.code === 1) msg += "Please enable location in browser settings.";
                    else if (error.code === 2) msg += "Location service is unavailable.";
                    else if (error.code === 3) msg += "Location request timeout. Try again.";
                    alert("❌ " + msg);
                    console.log("Geolocation error:", error);
                }
            );
        } else {
            alert("❌ Your browser doesn't support geolocation.");
        }
    }
    getLocation();
    </script>
    """

def load_geolocation_from_storage():
    """Load geolocation data from browser localStorage"""
    try:
        # This would require a way to read localStorage, which is tricky in Streamlit
        # For now, we'll use a workaround
        return None
    except:
        return None

def get_location_from_ip():
    try:
        # Try ipapi.co first
        response = requests.get("https://ipapi.co/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('latitude') and data.get('longitude'):
                return {
                    'latitude': float(data.get('latitude')),
                    'longitude': float(data.get('longitude')),
                    'city': data.get('city', 'Unknown'),
                    'region': data.get('region', ''),
                    'address': f"{data.get('city', 'Unknown')}, {data.get('region', '')}, {data.get('country_name', '')}"
                }
        
        # Fallback to ip-api.com if ipapi.co fails
        response = requests.get("http://ip-api.com/json/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('lat') and data.get('lon'):
                return {
                    'latitude': float(data.get('lat')),
                    'longitude': float(data.get('lon')),
                    'city': data.get('city', 'Unknown'),
                    'region': data.get('regionName', ''),
                    'address': f"{data.get('city', 'Unknown')}, {data.get('regionName', '')}, {data.get('country', '')}"
                }
    except requests.exceptions.Timeout:
        st.error("⏱️ Location detection timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        st.error("🌐 Network error. Please check your internet connection.")
    except Exception as e:
        st.error(f"❌ Error detecting location: {str(e)}")
    
    return None

# ----------------------------
# SIDEBAR
# ----------------------------
with st.sidebar:
    st.markdown(f"### {get_label('welcome')}")
    st.markdown(f"**Email:** {user['email']}")
    
    if st.button(get_label("logout"), use_container_width=True):
        auth.logout_user()
        st.rerun()
    
    st.markdown("---")
    
    if st.button(get_label("my_complaints"), use_container_width=True):
        st.session_state['view'] = 'my_complaints'
    
    if st.button(get_label("new_complaint"), use_container_width=True):
        st.session_state['view'] = 'new_complaint'

# ----------------------------
# HEADER
# ----------------------------
st.markdown(f"""
<div class="main-header">
    <h1>🧠 {get_label('title')}</h1>
</div>
""", unsafe_allow_html=True)

# ----------------------------
# MY COMPLAINTS VIEW
# ----------------------------
if st.session_state.get('view') == 'my_complaints':
    st.header(get_label("my_complaints"))
    
    my_complaints = auth.get_user_complaints()
    
    if my_complaints:
        for c in my_complaints:
            with st.expander(f"{c['tracking_id']} - {c['issue_type']} ({c['status']})"):
                st.markdown(f"**Issue:** {c['issue_type']}")
                st.markdown(f"**Location:** {c['location']}")
                st.markdown(f"**Status:** {c['status']}")
                st.markdown(f"**Submitted:** {c['created_at'][:10]}")
    else:
        st.info("No complaints yet.")
    
    st.stop()

# ----------------------------
# NEW COMPLAINT FORM
# ----------------------------
st.subheader("📝 Submit New Complaint")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📝 Text", "📷 Camera", "🖼️ Upload Image", "🎤 Voice"])

user_text = ""
image_input = None
voice_input = None

with tab1:
    user_text = st.text_area("Describe issue", height=150)

with tab2:
    image_input = st.camera_input("Capture Photo")

with tab3:
    image_input = st.file_uploader("Upload Image", type=["png", "jpg", "jpeg"])

with tab4:
    voice_input = st.file_uploader("Upload Voice", type=["mp3", "wav"])

# ----------------------------
# LOCATION SECTION
# ----------------------------
st.markdown("---")
st.subheader("📍 Location")

# Initialize location state
if 'lat' not in st.session_state:
    st.session_state['lat'] = None
    st.session_state['lon'] = None
    st.session_state['address'] = ""
    st.session_state['country'] = "Pakistan"
    st.session_state['region'] = "Punjab"
    st.session_state['city'] = "Select"

# Get browser location
col1, col2, col3 = st.columns([2, 1, 1])

with col2:
    if st.button("📍 Browser Location", use_container_width=True, help="Get exact GPS coordinates"):
        st.html(get_geolocation_html())

with col3:
    if st.button("🌍 Auto-Detect", use_container_width=True, help="Approximate location from IP"):
        with st.spinner("🔄 Detecting location..."):
            loc = get_location_from_ip()
            if loc:
                st.session_state['lat'] = loc['latitude']
                st.session_state['lon'] = loc['longitude']
                st.session_state['address'] = loc['address']
                st.success(f"✅ Located: {loc['address']}")
                st.rerun()
            else:
                st.error("❌ Could not detect IP location. Use map below.")

with col1:
    location_input = st.text_input("Full Address", value=st.session_state.get('address', ''), help="Your complete address or search location")

# Country selection
countries = get_countries()
country_names = [c[0] for c in countries]
default_country_idx = country_names.index("Pakistan") if "Pakistan" in country_names else 0

selected_country = st.selectbox(
    "Country",
    country_names,
    index=default_country_idx,
    key="country_selector"
)
st.session_state['country'] = selected_country

# Get regions for selected country
country_code = next((c[1] for c in countries if c[0] == selected_country), "PK")
regions = get_regions_for_country(country_code)

selected_region = st.selectbox(
    "Region/Province",
    regions,
    index=regions.index(st.session_state.get('region')) if st.session_state.get('region') in regions else 0,
    key="region_selector"
)
st.session_state['region'] = selected_region

# Get cities for selected region
cities = get_cities_for_region(selected_country, selected_region)

selected_city = st.selectbox(
    "City/District",
    cities,
    index=0 if st.session_state.get('city') not in cities else cities.index(st.session_state.get('city')),
    key="city_selector"
)
st.session_state['city'] = selected_city

# Map - Most Reliable Way to Set Location
st.markdown("---")
st.markdown("### 📍 Set Your Location (Click on Map)")
with st.expander("ℹ️ How to use the map", expanded=True):
    st.markdown("""
    **3 Easy Steps:**
    1. 🔍 **Zoom in/out** using the mouse wheel or zoom buttons
    2. 🖱️ **Click** exactly on your location on the map
    3. ✅ **Address auto-fills** below with your exact coordinates
    
    **Alternative Methods:**
    - Use **"🌍 Auto-Detect"** for approximate location from your IP
    - Use **"📍 Browser Location"** for precise GPS (if your browser supports it)
    - Manually type your **Full Address** above
    """)

m = folium.Map(
    location=[st.session_state.get('lat') or 30.3753, st.session_state.get('lon') or 69.3451],
    zoom_start=12 if st.session_state.get('lat') else 5
)
m.add_child(folium.LatLngPopup())

if st.session_state.get('lat'):
    folium.Marker(
        [st.session_state['lat'], st.session_state['lon']],
        popup=st.session_state.get('address', 'Selected Location'),
        tooltip=f"Lat: {st.session_state['lat']:.4f}, Lon: {st.session_state['lon']:.4f}",
        icon=folium.Icon(color='red', icon='info-sign')
    ).add_to(m)

map_data = st_folium(m, width=700, height=450)

if map_data and map_data.get('last_clicked'):
    st.session_state['lat'] = float(map_data['last_clicked']['lat'])
    st.session_state['lon'] = float(map_data['last_clicked']['lng'])
    
    # Reverse geocode the clicked location
    with st.spinner("🔄 Getting address details..."):
        geo_info = reverse_geocode_location(st.session_state['lat'], st.session_state['lon'])
        if geo_info:
            st.session_state['address'] = geo_info['address']
            st.success(f"✅ Location set: {geo_info['address'][:120]}...")
            st.info(f"📍 Coordinates: Lat {st.session_state['lat']:.6f}, Lon {st.session_state['lon']:.6f}")
        st.rerun()

# ----------------------------
# SUBMIT
# ----------------------------
st.markdown("---")
if st.button("🚀 Submit Complaint", type="primary", use_container_width=True):
    if not (user_text or image_input or voice_input):
        st.error("Provide input!")
    elif not location_input:
        st.error("Provide location!")
    else:
        with st.spinner("Processing..."):
            tracking_id = generate_tracking_id()
            
            # Voice
            if voice_input:
                temp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                temp.write(voice_input.read())
                temp.flush()
                user_text = services['voice_stt'].transcribe(temp.name)
            
            # Classify
            if image_input:
                issue_type, severity, department = services['image_clf'].classify(Image.open(image_input))
            else:
                issue_type, severity, department = services['text_clf'].classify(user_text)
            
            # Generate formal complaint with Groq
            complaint_data = {
                'issue_type': issue_type,
                'severity': severity,
                'department': department,
                'location': location_input,
                'district': district_input,
                'description': user_text or "See image"
            }
            
            formal_complaint = services['groq'].generate_formal_complaint(
                complaint_data,
                language='urdu' if lang_option == 'Urdu' else 'english'
            )
            
            # Save
            db_data = {
                'tracking_id': tracking_id,
                'user_id': user['id'],
                'issue_type': issue_type,
                'severity': severity,
                'department': department,
                'description': formal_complaint,
                'location': location_input,
                'district': district_input,
                'status': 'Pending',
                'email': user['email'],
                'created_at': datetime.now().isoformat()
            }
            
            if image_input:
                db_data['image_url'] = services['db'].upload_image(image_input, tracking_id)
            
            result = services['db'].create_complaint(db_data)
            
            if result:
                st.balloons()
                st.success(f"✅ Submitted! Tracking ID: **{tracking_id}**")
                
                st.markdown("### 📄 Formal Complaint")
                if lang_option == "Urdu":
                    st.markdown(f'<div class="urdu-text">{formal_complaint}</div>', unsafe_allow_html=True)
                else:
                    st.text_area("", formal_complaint, height=200)
                
                # PDF
                pdf = generate_complaint_pdf(db_data, image_input)
                st.download_button("📄 Download PDF", pdf, f"Complaint_{tracking_id}.pdf", "application/pdf")
                
                # Email
                email_sent = services['notifier'].send_complaint_confirmation(
                    user['email'], tracking_id, issue_type, location_input
                )
                
                if email_sent:
                    st.success("📧 Tracking ID sent to your email!")
                else:
                    st.warning("Email failed. Save tracking ID manually!")