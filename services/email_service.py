import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

class EmailService:
    def __init__(self):
        self.api_key = os.getenv('SENDGRID_API_KEY')
        self.from_email = os.getenv('FROM_EMAIL', 'noreply@photosite360.com')

    def send_invitation_email(self, to_email: str, invitation_token: str):
        """Send invitation email to new user"""
        if not self.api_key:
            print("⚠️ SendGrid API key not configured, skipping email")
            return False

        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject='Invitación a PhotoSite360',
                html_content=f'''
                <h2>Has sido invitado a PhotoSite360</h2>
                <p>Usa el siguiente token para registrarte:</p>
                <p><strong>{invitation_token}</strong></p>
                <p>Este token expira en 7 días.</p>
                '''
            )

            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)

            return response.status_code == 202
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

print("USANDO EMAIL_SERVICE CON SENDGRID v2.0")
