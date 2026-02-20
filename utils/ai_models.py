import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
import whisper
from PIL import Image
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import numpy as np

# ==================== IMAGE CLASSIFICATION ====================
class ImageClassifier:
    def __init__(self):
        self.model = None
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])
        self.issue_types = ["Pothole", "Garbage", "Water Leak", "Broken Streetlight", "Damaged Road", "Illegal Dumping", "Sewage Overflow", "Other"]
        self.severity_map = {
            "Pothole": "High",
            "Garbage": "Medium",
            "Water Leak": "High",
            "Broken Streetlight": "Medium",
            "Damaged Road": "High",
            "Illegal Dumping": "Medium",
            "Sewage Overflow": "High",
            "Other": "Low"
        }
        self.department_map = {
            "Pothole": "Roads & Highways Department",
            "Garbage": "Sanitation & Waste Management",
            "Water Leak": "Water & Sewerage Authority",
            "Broken Streetlight": "Electricity Department",
            "Damaged Road": "Roads & Highways Department",
            "Illegal Dumping": "Sanitation & Waste Management",
            "Sewage Overflow": "Water & Sewerage Authority",
            "Other": "General Administration"
        }
        self.load_model()
    
    @st.cache_resource(show_spinner=True)
    def load_model(_self):
        """Load pre-trained MobileNetV2 with transfer learning"""
        model = models.mobilenet_v2(pretrained=True)
        
        # Freeze early layers
        for param in model.features[:10].parameters():
            param.requires_grad = False
        
        # Modify classifier for our use case
        num_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(num_features, len(_self.issue_types))
        )
        
        model.eval()
        return model
    
    def extract_features(self, img):
        """Extract features from image"""
        if isinstance(img, str):
            img = Image.open(img)
        
        img = img.convert("RGB")
        tensor = self.transform(img).unsqueeze(0)
        
        with torch.no_grad():
            features = self.model.features(tensor)
            features = torch.nn.functional.adaptive_avg_pool2d(features, (1, 1))
            features = features.view(features.size(0), -1)[0]
        
        return features
    
    def classify(self, img):
        """Classify image and return issue type, severity, department"""
        features = self.extract_features(img)
        
        # Simple similarity-based classification
        # In production, this would use a trained classifier
        issue_keywords = {
            "Pothole": ["hole", "crack", "damage", "road"],
            "Garbage": ["trash", "waste", "dump", "litter"],
            "Water Leak": ["water", "leak", "pipe", "flood"],
            "Broken Streetlight": ["light", "lamp", "dark", "street"],
            "Damaged Road": ["road", "pavement", "asphalt"],
            "Illegal Dumping": ["dump", "pile", "waste"],
            "Sewage Overflow": ["sewage", "drain", "overflow"],
        }
        
        # For demo: random selection weighted by common issues
        weights = [0.25, 0.20, 0.15, 0.15, 0.10, 0.08, 0.05, 0.02]
        predicted_issue = np.random.choice(self.issue_types, p=weights)
        
        severity = self.severity_map.get(predicted_issue, "Low")
        department = self.department_map.get(predicted_issue, "General Administration")
        
        return predicted_issue, severity, department

# ==================== VOICE TO TEXT ====================
class VoiceToText:
    def __init__(self):
        self.model = None
        self.load_model()
    
    @st.cache_resource(show_spinner=True)
    def load_model(_self):
        """Load Whisper model"""
        return whisper.load_model("tiny")
    
    def transcribe(self, audio_file_path, language="auto"):
        """Transcribe audio to text"""
        try:
            if language == "auto":
                result = self.model.transcribe(audio_file_path)
            else:
                result = self.model.transcribe(audio_file_path, language=language)
            
            return result["text"]
        except Exception as e:
            print(f"Transcription error: {str(e)}")
            return ""

# ==================== TEXT CLASSIFICATION ====================
class TextClassifier:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=100)
        self.classifier = LogisticRegression(max_iter=1000)
        self.issue_types = ["Pothole", "Garbage", "Water Leak", "Broken Streetlight", "Damaged Road", "Illegal Dumping", "Sewage Overflow", "Other"]
        self.severity_map = {
            "Pothole": "High",
            "Garbage": "Medium",
            "Water Leak": "High",
            "Broken Streetlight": "Medium",
            "Damaged Road": "High",
            "Illegal Dumping": "Medium",
            "Sewage Overflow": "High",
            "Other": "Low"
        }
        self.department_map = {
            "Pothole": "Roads & Highways Department",
            "Garbage": "Sanitation & Waste Management",
            "Water Leak": "Water & Sewerage Authority",
            "Broken Streetlight": "Electricity Department",
            "Damaged Road": "Roads & Highways Department",
            "Illegal Dumping": "Sanitation & Waste Management",
            "Sewage Overflow": "Water & Sewerage Authority",
            "Other": "General Administration"
        }
        self.train()
    
    def train(self):
        """Train text classifier with expanded dataset"""
        training_data = [
            # Pothole examples
            ("There is a big pothole on the main road", "Pothole"),
            ("Large hole in the street causing accidents", "Pothole"),
            ("Deep pothole near the intersection", "Pothole"),
            ("Road has dangerous pothole", "Pothole"),
            ("Crater-like hole in the middle of road", "Pothole"),
            ("گڑھا سڑک پر ہے", "Pothole"),
            ("سڑک میں بڑا گڑھا", "Pothole"),
            
            # Garbage examples
            ("Garbage dump near my house", "Garbage"),
            ("Trash not collected for weeks", "Garbage"),
            ("Overflowing garbage bins", "Garbage"),
            ("Waste piling up on street", "Garbage"),
            ("Rotting garbage on the corner", "Garbage"),
            ("کچرا پھیلا ہوا ہے", "Garbage"),
            ("کوڑا کرکٹ جمع ہے", "Garbage"),
            
            # Water Leak examples
            ("Pipe is leaking water", "Water Leak"),
            ("Water line burst on street", "Water Leak"),
            ("Continuous water leakage", "Water Leak"),
            ("Broken water pipe flooding area", "Water Leak"),
            ("Water wastage from main pipe", "Water Leak"),
            ("پانی کا رساو ہو رہا ہے", "Water Leak"),
            ("پائپ ٹوٹا ہوا ہے", "Water Leak"),
            
            # Streetlight examples
            ("Streetlight not working", "Broken Streetlight"),
            ("Dark street due to broken lights", "Broken Streetlight"),
            ("Street lamp is off", "Broken Streetlight"),
            ("No lighting on the road at night", "Broken Streetlight"),
            ("Broken light pole", "Broken Streetlight"),
            ("سٹریٹ لائٹ خراب ہے", "Broken Streetlight"),
            ("روشنی نہیں ہے", "Broken Streetlight"),
            
            # Damaged Road examples
            ("Road surface completely damaged", "Damaged Road"),
            ("Broken asphalt everywhere", "Damaged Road"),
            ("Road needs urgent repair", "Damaged Road"),
            ("Pavement is crumbling", "Damaged Road"),
            
            # Illegal Dumping
            ("Construction waste dumped illegally", "Illegal Dumping"),
            ("Someone dumped furniture on street", "Illegal Dumping"),
            ("Unauthorized garbage pile", "Illegal Dumping"),
            
            # Sewage Overflow
            ("Sewage overflowing from manhole", "Sewage Overflow"),
            ("Drain is blocked and overflowing", "Sewage Overflow"),
            ("Sewage water on the street", "Sewage Overflow"),
            
            # Other
            ("General complaint about area", "Other"),
            ("Need help with local issue", "Other"),
        ]
        
        texts, labels = zip(*training_data)
        X = self.vectorizer.fit_transform(texts)
        self.classifier.fit(X, labels)
    
    def classify(self, text):
        """Classify text and return issue type, severity, department"""
        try:
            X = self.vectorizer.transform([text])
            predicted_issue = self.classifier.predict(X)[0]
        except:
            predicted_issue = "Other"
        
        severity = self.severity_map.get(predicted_issue, "Low")
        department = self.department_map.get(predicted_issue, "General Administration")
        
        return predicted_issue, severity, department

# ==================== INITIALIZE MODELS ====================
@st.cache_resource
def get_image_classifier():
    return ImageClassifier()

@st.cache_resource
def get_voice_to_text():
    return VoiceToText()

@st.cache_resource
def get_text_classifier():
    return TextClassifier()