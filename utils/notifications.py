import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import streamlit as st

class NotificationService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", st.secrets.get("SMTP_SERVER", "smtp.gmail.com"))
        self.smtp_port = int(os.getenv("SMTP_PORT", st.secrets.get("SMTP_PORT", "587")))
        self.sender_email = os.getenv("SENDER_EMAIL", st.secrets.get("SENDER_EMAIL", ""))
        self.sender_password = os.getenv("SENDER_PASSWORD", st.secrets.get("SENDER_PASSWORD", ""))
    
    def send_email(self, recipient_email, subject, body_html):
        """Send email notification"""
        if not self.sender_email or not self.sender_password:
            print("Email credentials not configured")
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient_email
            
            # Add HTML body
            html_part = MIMEText(body_html, "html")
            message.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)
            
            print(f"Email sent successfully to {recipient_email}")
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    def send_sms(self, phone_number, message):
        """Send SMS notification (simulated for demo)"""
        # In production, integrate with Twilio, MSG91, or similar service
        print(f"[SMS SIMULATION] To: {phone_number}")
        print(f"[SMS SIMULATION] Message: {message}")
        return True
    
    def send_complaint_confirmation(self, recipient_email, tracking_id, issue_type, location):
        """Send complaint confirmation email"""
        subject = f"Complaint Submitted - {tracking_id}"
        
        body_html = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                             color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .tracking-id {{ background: #4CAF50; color: white; padding: 15px; 
                                   text-align: center; font-size: 24px; font-weight: bold; 
                                   border-radius: 5px; margin: 20px 0; }}
                    .details {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                    .detail-row {{ padding: 10px 0; border-bottom: 1px solid #eee; }}
                    .label {{ font-weight: bold; color: #667eea; }}
                    .footer {{ text-align: center; color: #777; margin-top: 30px; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🧠 SmartNaggar AI</h1>
                        <p>Complaint Submitted Successfully</p>
                    </div>
                    <div class="content">
                        <p>Dear Citizen,</p>
                        <p>Thank you for reporting a civic issue. Your complaint has been successfully registered in our system.</p>
                        
                        <div class="tracking-id">
                            Tracking ID: {tracking_id}
                        </div>
                        
                        <div class="details">
                            <div class="detail-row">
                                <span class="label">Issue Type:</span> {issue_type}
                            </div>
                            <div class="detail-row">
                                <span class="label">Location:</span> {location}
                            </div>
                            <div class="detail-row">
                                <span class="label">Status:</span> Pending Review
                            </div>
                        </div>
                        
                        <p><strong>What happens next?</strong></p>
                        <ul>
                            <li>Your complaint will be reviewed by our team</li>
                            <li>It will be assigned to the appropriate department</li>
                            <li>You will receive updates via email and SMS</li>
                            <li>Track your complaint status anytime using the tracking ID</li>
                        </ul>
                        
                        <p><strong>Important:</strong> Please save your Tracking ID for future reference.</p>
                        
                        <div class="footer">
                            <p>SmartNaggar AI - Making Cities Better Together</p>
                            <p>Visit: www.smartnaggar.ai | Email: support@smartnaggar.ai</p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(recipient_email, subject, body_html)
    
    def send_status_update(self, recipient_email, tracking_id, old_status, new_status, admin_notes=""):
        """Send status update email"""
        subject = f"Status Update - {tracking_id}"
        
        status_colors = {
            "Pending": "#FFA726",
            "Under Review": "#42A5F5",
            "Assigned": "#66BB6A",
            "In Progress": "#26C6DA",
            "Resolved": "#4CAF50",
            "Rejected": "#EF5350"
        }
        
        status_color = status_colors.get(new_status, "#999")
        
        body_html = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                             color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 10px 10px; }}
                    .status-update {{ background: {status_color}; color: white; padding: 20px; 
                                     text-align: center; font-size: 20px; font-weight: bold; 
                                     border-radius: 5px; margin: 20px 0; }}
                    .details {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ text-align: center; color: #777; margin-top: 30px; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📢 Status Update</h1>
                        <p>Tracking ID: {tracking_id}</p>
                    </div>
                    <div class="content">
                        <p>Dear Citizen,</p>
                        <p>Your complaint status has been updated.</p>
                        
                        <div class="status-update">
                            {old_status} → {new_status}
                        </div>
                        
                        <div class="details">
                            <p><strong>Tracking ID:</strong> {tracking_id}</p>
                            <p><strong>New Status:</strong> {new_status}</p>
                            {f'<p><strong>Admin Notes:</strong> {admin_notes}</p>' if admin_notes else ''}
                        </div>
                        
                        <p>You can track your complaint anytime using the tracking ID on our platform.</p>
                        
                        <div class="footer">
                            <p>SmartNaggar AI - Making Cities Better Together</p>
                            <p>Visit: www.smartnaggar.ai | Email: support@smartnaggar.ai</p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
        
        return self.send_email(recipient_email, subject, body_html)
    
    def send_complaint_confirmation_sms(self, phone_number, tracking_id):
        """Send SMS confirmation"""
        message = f"Your complaint has been registered. Tracking ID: {tracking_id}. Track status at smartnaggar.ai"
        return self.send_sms(phone_number, message)
    
    def send_status_update_sms(self, phone_number, tracking_id, new_status):
        """Send SMS status update"""
        message = f"Complaint {tracking_id} status updated to: {new_status}. Visit smartnaggar.ai for details."
        return self.send_sms(phone_number, message)

# Initialize notification service
def get_notification_service():
    return NotificationService()