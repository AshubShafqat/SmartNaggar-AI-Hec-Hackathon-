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
        """Verify admin credentials from database"""
        try:
            if not self.db.client:
                st.error("Database connection not available")
                return False, None
            
            password_hash = self.hash_password(password)
            
            # Query database for admin
            result = self.db.client.table('admin_users').select("*").eq('username', username).eq('password_hash', password_hash).eq('is_active', True).execute()
            
            if result.data:
                admin = result.data[0]
                # Update last login
                self.db.client.table('admin_users').update({
                    'last_login': st.session_state.get('login_time', None)
                }).eq('id', admin['id']).execute()
                
                return True, admin
            return False, None
        except Exception as e:
            st.error(f"Authentication error: {str(e)}")
            return False, None
    
    def login(self, username, password):
        """Admin login"""
        success, admin_data = self.verify_admin(username, password)
        
        if success and admin_data:
            st.session_state['admin_logged_in'] = True
            st.session_state['admin_username'] = username
            st.session_state['admin_id'] = admin_data['id']
            st.session_state['admin_role'] = admin_data.get('role', 'admin')
            st.session_state['admin_name'] = admin_data.get('full_name', username)
            st.session_state['admin_email'] = admin_data.get('email', '')
            
            # Log activity
            self._log_activity(admin_data['id'], 'login', None, f'Admin {username} logged in')
            
            return True
        return False
    
    def logout(self):
        """Admin logout"""
        if self.is_logged_in():
            admin_id = st.session_state.get('admin_id')
            username = st.session_state.get('admin_username')
            
            # Log activity
            self._log_activity(admin_id, 'logout', None, f'Admin {username} logged out')
        
        st.session_state['admin_logged_in'] = False
        st.session_state['admin_username'] = None
        st.session_state['admin_id'] = None
        st.session_state['admin_role'] = None
        st.session_state['admin_name'] = None
        st.session_state['admin_email'] = None
    
    def is_logged_in(self):
        """Check if admin is logged in"""
        return st.session_state.get('admin_logged_in', False)
    
    def get_current_admin(self):
        """Get current admin info"""
        if self.is_logged_in():
            return {
                'username': st.session_state.get('admin_username'),
                'id': st.session_state.get('admin_id'),
                'role': st.session_state.get('admin_role'),
                'name': st.session_state.get('admin_name'),
                'email': st.session_state.get('admin_email')
            }
        return None
    
    def _log_activity(self, admin_id, action_type, tracking_id, description):
        """Log admin activity"""
        try:
            if self.db.client:
                log_data = {
                    'admin_id': admin_id,
                    'action_type': action_type,
                    'tracking_id': tracking_id,
                    'description': description
                }
                self.db.client.table('admin_activity_log').insert(log_data).execute()
        except Exception as e:
            print(f"Error logging activity: {str(e)}")
    
    def log_complaint_action(self, tracking_id, action_type, description):
        """Log complaint-related admin action"""
        if self.is_logged_in():
            admin_id = st.session_state.get('admin_id')
            self._log_activity(admin_id, action_type, tracking_id, description)

def require_admin_auth():
    """Decorator to require admin authentication"""
    auth = AdminAuth()
    if not auth.is_logged_in():
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h1>🔐 Admin Login</h1>
            <p>SmartNaggar AI - Administration Panel</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.container():
                st.markdown("### Login to Continue")
                
                username = st.text_input("Username", placeholder="Enter admin username")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    if st.button("🔓 Login", use_container_width=True, type="primary"):
                        if username and password:
                            if auth.login(username, password):
                                st.success("✅ Login successful!")
                                st.rerun()
                            else:
                                st.error("❌ Invalid credentials")
                        else:
                            st.warning("⚠️ Please enter username and password")
                
                with col_b:
                    if st.button("🏠 Back to App", use_container_width=True):
                        st.switch_page("app.py")
                
                st.markdown("---")
                st.info("""
                **Default Admin Accounts:**
                - Username: `admin` / Password: `admin123`
                - Username: `supervisor` / Password: `super123`
                - Username: `manager` / Password: `manager123`
                """)
        
        st.stop()
    
    return auth