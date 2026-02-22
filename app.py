import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import streamlit as st
import uuid
from datetime import datetime
from PIL import Image

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SmartNaggar AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .result-card {
        background: #f8f9fa;
        border-left: 5px solid #667eea;
        padding: 1.2rem 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .severity-high   { color: #dc3545; font-weight: bold; }
    .severity-medium { color: #fd7e14; font-weight: bold; }
    .severity-low    { color: #28a745; font-weight: bold; }
    .caption-box {
        background: #e8f4fd;
        border: 1px solid #bee5eb;
        padding: 0.8rem 1rem;
        border-radius: 6px;
        font-style: italic;
        margin: 0.5rem 0 1rem 0;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        font-size: 1rem;
    }
    .stButton > button:hover { opacity: 0.9; }
    .track-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ─── Lazy imports ────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_classifier():
    from utils.ai_models import get_complaint_classifier
    return get_complaint_classifier()

@st.cache_resource(show_spinner=False)
def load_groq():
    from utils.groq_client import get_groq_generator
    return get_groq_generator()

@st.cache_resource(show_spinner=False)
def load_db():
    from utils.supabase_client import SupabaseDB
    return SupabaseDB()

@st.cache_resource(show_spinner=False)
def load_notifier():
    from utils.notifications import get_notification_service
    return get_notification_service()

# ─── Auth ────────────────────────────────────────────────────────────────────
from utils.user_auth import require_auth
auth = require_auth()
current_user = auth.get_current_user()

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 👋 Hello, **{current_user['name']}**")
    st.markdown("---")

    page = st.radio(
        "Navigate",
        ["🏠 Report Issue", "🔍 Track Complaint", "📋 My Complaints"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        auth.logout_user()
        st.rerun()

    st.markdown("---")
    st.caption("SmartNaggar AI v2.0\nMaking Cities Better Together 🌆")

# ─── Helper: generate tracking ID ────────────────────────────────────────────
def make_tracking_id():
    return "SN-" + str(uuid.uuid4())[:8].upper()

# ─── Helper: severity badge ───────────────────────────────────────────────────
def severity_html(sev: str) -> str:
    cls = f"severity-{sev.lower()}"
    icons = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}
    return f'<span class="{cls}">{icons.get(sev, "⚪")} {sev}</span>'

# ════════════════════════════════════════════════════════════════════════════
#  PAGE 1 — REPORT ISSUE
# ════════════════════════════════════════════════════════════════════════════
if page == "🏠 Report Issue":

    st.markdown("""
    <div class="main-header">
        <h1>🧠 SmartNaggar AI</h1>
        <p>AI-Powered Civic Problem Reporter — Report issues in seconds</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Step 1: Choose input method ──────────────────────────────────────────
    st.subheader("Step 1 — Choose how to report")

    input_method = st.radio(
        "Input method",
        ["📝 Text Description", "📷 Upload Photo", "📸 Capture Photo", "🎙️ Voice Recording"],
        horizontal=True,
        label_visibility="collapsed",
    )

    st.markdown("---")

    # ── Classification state ──────────────────────────────────────────────────
    issue_type  = None
    severity    = None
    department  = None
    caption     = None      # BLIP caption or Whisper transcription
    image_file  = None      # Keep for PDF

    classifier  = load_classifier()

    # ─────────────────────────────────────────────────────────────────────────
    #  TEXT INPUT
    # ─────────────────────────────────────────────────────────────────────────
    if input_method == "📝 Text Description":
        st.subheader("Describe the civic issue")

        lang = st.selectbox(
            "Language",
            ["English", "Urdu"],
            key="text_lang",
        )

        user_text = st.text_area(
            "Describe the problem in detail",
            height=150,
            placeholder="e.g. There is a large pothole on Main Boulevard near the petrol station...",
        )

        if st.button("🔍 Analyse Issue", key="analyse_text"):
            if not user_text.strip():
                st.warning("Please describe the issue first.")
            else:
                with st.spinner("Analysing with AI..."):
                    issue_type, severity, department = classifier.classify_text(user_text)
                    caption = user_text      # raw text used directly
                    st.session_state["classified"] = dict(
                        issue_type=issue_type,
                        severity=severity,
                        department=department,
                        caption=caption,
                        image_file=None,
                        input_method="text",
                    )

    # ─────────────────────────────────────────────────────────────────────────
    #  UPLOAD PHOTO
    # ─────────────────────────────────────────────────────────────────────────
    elif input_method == "📷 Upload Photo":
        st.subheader("Upload a photo of the issue")

        uploaded = st.file_uploader(
            "Choose an image",
            type=["jpg", "jpeg", "png", "webp"],
            key="photo_upload",
        )

        if uploaded is not None:
            pil_img = Image.open(uploaded).convert("RGB")
            st.image(pil_img, caption="Uploaded image", use_column_width=True)
            image_file = uploaded

            if st.button("🔍 Analyse Photo", key="analyse_upload"):
                with st.spinner("Generating caption with BLIP…"):
                    issue_type, severity, department, caption = classifier.classify_image(pil_img)
                    st.session_state["classified"] = dict(
                        issue_type=issue_type,
                        severity=severity,
                        department=department,
                        caption=caption,
                        image_file=uploaded,
                        input_method="image",
                    )

    # ─────────────────────────────────────────────────────────────────────────
    #  CAPTURE PHOTO (camera)
    # ─────────────────────────────────────────────────────────────────────────
    elif input_method == "📸 Capture Photo":
        st.subheader("Take a photo with your camera")

        camera_img = st.camera_input("Point your camera at the civic issue")  # returns UploadedFile

        if camera_img is not None:
            pil_img = Image.open(camera_img).convert("RGB")
            image_file = camera_img

            if st.button("🔍 Analyse Captured Photo", key="analyse_camera"):
                with st.spinner("Generating caption with BLIP…"):
                    issue_type, severity, department, caption = classifier.classify_image(pil_img)
                    st.session_state["classified"] = dict(
                        issue_type=issue_type,
                        severity=severity,
                        department=department,
                        caption=caption,
                        image_file=camera_img,
                        input_method="camera",
                    )

    # ─────────────────────────────────────────────────────────────────────────
    #  REAL-TIME VOICE RECORDING  ← fixed: uses st.audio_input()
    # ─────────────────────────────────────────────────────────────────────────
    elif input_method == "🎙️ Voice Recording":
        st.subheader("Record your complaint (real-time)")

        lang_audio = st.selectbox(
            "Speaking language",
            ["auto", "en", "ur"],
            format_func=lambda x: {"auto": "Auto-detect", "en": "English", "ur": "Urdu"}[x],
            key="audio_lang",
        )

        st.info("🎙️ Click the microphone button below to start recording. Click again to stop.")

        # st.audio_input — Streamlit ≥ 1.31 built-in mic recorder
        audio_value = st.audio_input("Record your complaint")

        if audio_value is not None:
            st.audio(audio_value)   # playback so user can verify

            if st.button("🔍 Transcribe & Analyse", key="analyse_audio"):
                with st.spinner("Transcribing with Whisper…"):
                    issue_type, severity, department, transcription = classifier.classify_audio(
                        audio_value, language=lang_audio
                    )
                    caption = transcription
                    st.session_state["classified"] = dict(
                        issue_type=issue_type,
                        severity=severity,
                        department=department,
                        caption=caption,
                        image_file=None,
                        input_method="audio",
                    )

    # ─────────────────────────────────────────────────────────────────────────
    #  CLASSIFICATION RESULTS (shared across all input methods)
    # ─────────────────────────────────────────────────────────────────────────
    if "classified" in st.session_state:
        cl = st.session_state["classified"]
        issue_type = cl["issue_type"]
        severity   = cl["severity"]
        department = cl["department"]
        caption    = cl["caption"]
        image_file = cl.get("image_file")

        st.markdown("---")
        st.subheader("Step 2 — AI Classification Results")

        col1, col2, col3 = st.columns(3)
        col1.metric("Issue Type", issue_type)
        col2.metric("Severity", severity)
        col3.metric("Department", department)

        if caption:
            label = "🤖 BLIP Caption" if cl["input_method"] in ("image", "camera") else (
                "🎤 Transcription" if cl["input_method"] == "audio" else "📝 Your description"
            )
            st.markdown(f'<div class="caption-box"><b>{label}:</b> {caption}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Step 3 — Your Details")

        col1, col2 = st.columns(2)
        with col1:
            district = st.selectbox(
                "District / City",
                ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Multan", "Faisalabad", "Other"],
            )
            location = st.text_input("Exact Location / Landmark", placeholder="e.g. Main Boulevard, near Total petrol station")
        with col2:
            citizen_email = st.text_input(
                "Email (for updates)",
                value=current_user.get("email", ""),
                placeholder="you@example.com",
            )
            citizen_phone = st.text_input("Phone (optional)", placeholder="+92 3xx xxxxxxx")

        add_description = st.text_area(
            "Additional details (optional)",
            height=100,
            placeholder="Any extra information about the issue…",
        )

        # ── Formal complaint generation ──────────────────────────────────────
        st.markdown("---")
        st.subheader("Step 4 — Formal Complaint")

        lang_complaint = st.radio(
            "Generate complaint in",
            ["English", "Urdu"],
            horizontal=True,
            key="complaint_lang",
        )

        full_description = (caption or "") + (" " + add_description if add_description else "")

        issue_data = {
            "issue_type":  issue_type,
            "severity":    severity,
            "department":  department,
            "location":    location or "Not specified",
            "district":    district,
            "description": full_description,
        }

        groq_gen = load_groq()
        formal_complaint = groq_gen.generate_formal_complaint(
            issue_data, language=lang_complaint.lower()
        )

        st.text_area("Generated Formal Complaint", formal_complaint, height=300)

        # ── Submit ──────────────────────────────────────────────────────────
        st.markdown("---")
        if st.button("📤 Submit Complaint", use_container_width=True, key="submit_btn"):
            if not location:
                st.warning("Please enter the exact location before submitting.")
            else:
                tracking_id = make_tracking_id()
                db = load_db()

                # Upload image if present
                image_url = None
                if image_file is not None:
                    try:
                        image_file.seek(0)
                    except Exception:
                        pass
                    image_url = db.upload_image(image_file, tracking_id)

                complaint_record = {
                    "tracking_id": tracking_id,
                    "issue_type":  issue_type,
                    "severity":    severity,
                    "department":  department,
                    "district":    district,
                    "location":    location,
                    "description": full_description,
                    "status":      "Pending",
                    "email":       citizen_email,
                    "phone":       citizen_phone,
                    "image_url":   image_url,
                    "user_id":     current_user.get("id"),
                    "created_at":  datetime.now().isoformat(),
                }

                # Store formal_complaint separately for PDF only —
                # only include in DB insert if the column exists in your schema.
                # To persist it, run: add_formal_complaint_column.sql in Supabase.
                complaint_record_for_pdf = {**complaint_record, "formal_complaint": formal_complaint}

                # Try inserting with formal_complaint (requires column to exist in Supabase).
                # Falls back silently to insert without it if column is missing.
                try:
                    saved = db.create_complaint({**complaint_record, "formal_complaint": formal_complaint})
                    if not saved:
                        raise Exception("empty result")
                except Exception:
                    saved = db.create_complaint(complaint_record)

                if saved:
                    st.success(f"✅ Complaint submitted! **Tracking ID: {tracking_id}**")
                    st.balloons()

                    # Notifications
                    notifier = load_notifier()
                    if citizen_email:
                        notifier.send_complaint_confirmation(
                            citizen_email, tracking_id, issue_type, location
                        )
                    if citizen_phone:
                        notifier.send_complaint_confirmation_sms(citizen_phone, tracking_id)

                    # PDF download
                    from utils.pdf_generator import generate_complaint_pdf
                    pdf_bytes = generate_complaint_pdf(complaint_record_for_pdf, image_file)
                    st.download_button(
                        "📄 Download PDF Receipt",
                        data=pdf_bytes,
                        file_name=f"{tracking_id}_complaint.pdf",
                        mime="application/pdf",
                    )

                    # Clear classification state for next report
                    del st.session_state["classified"]
                else:
                    st.error("❌ Failed to save complaint. Please try again.")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE 2 — TRACK COMPLAINT
# ════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Track Complaint":

    st.markdown("""
    <div class="main-header">
        <h1>🔍 Track Your Complaint</h1>
        <p>Enter your Tracking ID to see the latest status</p>
    </div>
    """, unsafe_allow_html=True)

    tracking_input = st.text_input(
        "Tracking ID",
        placeholder="SN-XXXXXXXX",
        max_chars=12,
    ).strip().upper()

    if st.button("🔎 Search", key="track_search"):
        if not tracking_input:
            st.warning("Please enter a Tracking ID.")
        else:
            db = load_db()
            complaint = db.get_complaint_by_id(tracking_input)

            if complaint:
                st.markdown(f"""
                <div class="track-card">
                    <h3>🎫 {complaint['tracking_id']}</h3>
                    <p><b>Issue:</b> {complaint['issue_type']} &nbsp;|&nbsp;
                       <b>Severity:</b> {complaint['severity']} &nbsp;|&nbsp;
                       <b>Status:</b> {complaint['status']}</p>
                    <p><b>Location:</b> {complaint['location']}, {complaint['district']}</p>
                    <p><b>Department:</b> {complaint['department']}</p>
                    <p><b>Submitted:</b> {complaint['created_at'][:16]}</p>
                    {f"<p><b>Admin Notes:</b> {complaint['admin_notes']}</p>" if complaint.get('admin_notes') else ""}
                </div>
                """, unsafe_allow_html=True)

                # History
                history = db.get_complaint_history(tracking_input)
                if history:
                    st.markdown("#### 📜 Update History")
                    for h in history:
                        st.markdown(f"- **{h['status']}** — {h['updated_at'][:16]}"
                                    + (f" — _{h['notes']}_" if h.get("notes") else ""))
            else:
                st.error("No complaint found with that Tracking ID.")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE 3 — MY COMPLAINTS
# ════════════════════════════════════════════════════════════════════════════
elif page == "📋 My Complaints":

    st.markdown("""
    <div class="main-header">
        <h1>📋 My Complaints</h1>
        <p>View all complaints submitted by you</p>
    </div>
    """, unsafe_allow_html=True)

    complaints = auth.get_user_complaints()

    if not complaints:
        st.info("You haven't submitted any complaints yet.")
    else:
        for c in complaints:
            severity_color = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(c["severity"], "⚪")
            with st.expander(
                f"🎫 {c['tracking_id']}  |  {c['issue_type']}  |  {severity_color} {c['severity']}  |  {c['status']}"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**District:** {c['district']}")
                    st.markdown(f"**Location:** {c['location']}")
                    st.markdown(f"**Department:** {c['department']}")
                    st.markdown(f"**Submitted:** {c['created_at'][:16]}")
                with col2:
                    st.markdown(f"**Status:** {c['status']}")
                    if c.get("admin_notes"):
                        st.markdown(f"**Admin Notes:** {c['admin_notes']}")
                    if c.get("image_url"):
                        st.image(c["image_url"], width=300)

# ─── Footer ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:#888; font-size:0.85rem; padding: 0.5rem;">
    SmartNaggar AI — Making Cities Better Together 🌆 &nbsp;|&nbsp;
    <a href="mailto:support@smartnaggar.ai">support@smartnaggar.ai</a>
</div>
""", unsafe_allow_html=True)