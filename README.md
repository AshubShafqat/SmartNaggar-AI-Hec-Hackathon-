# SmartNaggar AI 🧠🏙️

## **Project Overview**
**SmartNaggar AI** is a **Generative AI-powered platform** that allows citizens to report urban issues like potholes, garbage, water leaks, broken streetlights, and unsafe public spaces using **photo, text, or voice input**.  
The AI automatically interprets the input, generates a formal complaint, assigns it to the correct department, and tracks the status of the issue.  

**Goal:** Make civic reporting **easy, accessible, and actionable**, increasing **transparency**, **citizen engagement**, and **accountability** in city governance.  

---

## **Problem Statement**
Many cities face recurring urban issues, but citizens often struggle to report them because:

- Reporting systems are complicated and fragmented  
- Citizens don’t know which department to contact  
- Processes are time-consuming and confusing  
- Most complaints are left unresolved  

This leads to:

- Poor infrastructure  
- Unsafe streets  
- Frustration and disengagement among citizens  

**Solution:** Simplify the reporting process using AI so everyone can participate in improving their city.  

---

## **Solution Description**
The platform allows citizens to report problems effortlessly:

1. **Input:** Users can submit issues via **photo, voice, or text**.  
2. **AI Understanding:** AI analyzes input, classifies the problem type, severity, and location.  
3. **Complaint Generation:** AI generates a **professional complaint** for city authorities.  
4. **Submission & Tracking:** Complaint is stored in a **database**, tracking ID is issued, and users can monitor progress.  
5. **Feedback:** The system provides updates in simple language, keeping citizens informed.  

**Key Features:**

- Multi-modal input (photo, text, voice)  
- Problem classification and severity scoring  
- AI-generated formal complaint  
- Real-time tracking dashboard  
- Demo-ready government dashboard simulation  

---

## **Target Users**
- General citizens (especially elderly or non-technical users)  
- City planners and authorities  
- NGOs monitoring civic issues  
- University campuses or housing societies (as pilot environments)  

---

## **Social Impact**
- **Civic Engagement:** Citizens can actively participate in governance.  
- **Transparency:** People can track complaints and see government response.  
- **Accountability:** Authorities receive structured, actionable data.  
- **Inclusion:** Voice-first or illiterate users can report problems.  
- **Safer, cleaner cities:** More reported and resolved issues improve quality of life.  

---

## **System Workflow**
1. **User Input:** Citizen reports an issue via photo, text, or voice.  
2. **AI Understanding:** AI detects problem type, severity, and location.  
3. **AI Complaint Generation:** AI creates a professional complaint.  
4. **Submission & Tracking:** Complaint saved to database with tracking ID.  
5. **Feedback Loop:** Dashboard displays real-time complaint status until resolution.  

---

## **Tech Stack**
- **Frontend & Backend:** Streamlit (Python)  
- **Image Classification:** PyTorch (MobileNetV2)  
- **Voice-to-Text:** OpenAI Whisper  
- **Text Classification:** TF-IDF + Logistic Regression  
- **Database:** SQLite  
- **PDF Generation:** FPDF  
- **Mapping:** Folium + geopy  
- **File Handling:** PIL, tempfile  
- **Real-time Updates:** Session state + database polling  

---

## **How to Run**
1. Clone the repository:
```bash
git clone <repo-url>
cd smartnaggar-ai

pip install -r requirements.txt
streamlit run app.py
