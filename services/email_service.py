import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

class EmailService:
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@photosite360.com")
    
    @staticmethod
    def send_invitation_email(
        to_email: str,
        project_name: str,
        invitation_token: str,
        frontend_url: str = None
    ) -> bool:
        """
        Envía email de invitación usando SendGrid
        """
        if not frontend_url:
            frontend_url = os.getenv("FRONTEND_URL", "https://photosite360-frontend.onrender.com")
        
        try:
            # Generar link de invitación
            invitation_link = f"{frontend_url}/invitation/{invitation_token}"
            
            # HTML del email
            html_content = f"""
            <html>
              <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                  <h1 style="color: white; margin: 0;">PhotoSite360</h1>
                  <p style="color: white; margin: 10px 0 0 0;">Gestión de Fotos 360°</p>
                </div>
                
                <div style="padding: 30px; background: #f9f9f9;">
                  <h2 style="color: #333;">Has sido invitado a colaborar</h2>
                  
                  <p style="color: #666; font-size: 16px; line-height: 1.6;">
                    Has sido invitado a colaborar en el proyecto:
                  </p>
                  
                  <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #667eea; margin: 0;">{project_name}</h3>
                  </div>
                  
                  <p style="color: #666; font-size: 16px; line-height: 1.6;">
                    Haz clic en el botón de abajo para aceptar la invitación y acceder al proyecto:
                  </p>
                  
                  <div style="text-align: center; margin: 30px 0;">
                    <a href="{invitation_link}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                              color: white;
                              padding: 15px 40px;
                              text-decoration: none;
                              border-radius: 8px;
                              font-size: 16px;
                              font-weight: bold;
                              display: inline-block;">
                      Aceptar Invitación
                    </a>
                  </div>
                  
                  <p style="color: #999; font-size: 14px; line-height: 1.6;">
                    Si no solicitaste esta invitación, puedes ignorar este email.
                  </p>
                  
                  <p style="color: #999; font-size: 14px; line-height: 1.6;">
                    O copia este enlace en tu navegador:<br>
                    <a href="{invitation_link}" style="color: #667eea; word-break: break-all;">{invitation_link}</a>
                  </p>
                </div>
                
                <div style="background: #333; padding: 20px; text-align: center;">
                  <p style="color: #999; margin: 0; font-size: 14px;">
                    © 2025 PhotoSite360. Todos los derechos reservados.
                  </p>
                </div>
              </body>
            </html>
            """
            
            # Crear mensaje
            message = Mail(
                from_email=Email(EmailService.EMAIL_FROM, "PhotoSite360"),
                to_emails=To(to_email),
                subject=f"Invitación a proyecto: {project_name}",
                html_content=Content("text/html", html_content)
            )
            
            # Enviar con SendGrid
            sg = SendGridAPIClient(EmailService.SENDGRID_API_KEY)
            response = sg.send(message)
            
            print(f"✅ Email enviado a {to_email} (Status: {response.status_code})")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando email con SendGrid: {e}")
            import traceback
            traceback.print_exc()
            return False