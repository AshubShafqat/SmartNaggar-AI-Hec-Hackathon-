import streamlit as st
import hashlib
from utils.supabase_client import SupabaseDB

class AdminAuth:
    def __init__(self):
        self.db = SupabaseDB()
    
    def hash_password(self, password):
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_admin(self, username, password):
        """Verify admin credentials"""
        # For demo purposes - hardcoded admin credentials
        # In production, store in Supabase
        admin_users = {
            "admin": self.hash_password("admin123"),
            "supervisor": self.hash_password("super123")
        }
        
        password_hash = self.hash_password(password)
        
        if username in admin_users and admin_users[username] == password_hash:
            return True
        return False
    
    def login(self, username, password):
        """Admin login"""
        if self.verify_admin(username, password):
            st.session_state['admin_logged_in'] = True
            st.session_state['admin_username'] = username
            return True
        return False
    
    def logout(self):
        """Admin logout"""
        st.session_state['admin_logged_in'] = False
        st.session_state['admin_username'] = None
    
    def is_logged_in(self):
        """Check if admin is logged in"""
        return st.session_state.get('admin_logged_in', False)
    
    def get_current_user(self):
        """Get current admin username"""
        return st.session_state.get('admin_username', None)

def require_admin_auth():
    """Decorator to require admin authentication"""
    auth = AdminAuth()
    if not auth.is_logged_in():
        st.warning("⚠️ Please login to access the admin dashboard")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("🔐 Admin Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            
            if st.button("Login", use_container_width=True):
                if auth.login(username, password):
                    st.success("✅ Login successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")
            
            st.info("Demo credentials: admin / admin123")
        
        st.stop()
    
    return auth