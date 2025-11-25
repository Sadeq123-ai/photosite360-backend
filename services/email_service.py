import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import os

class EmailService:
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_USER = "sadeqalmoddai123@gmail.com"
    EMAIL_PASSWORD = "jqyu cavi ttkl mgbz"
    EMAIL_FROM = "PhotoSite360 <sadeqalmoddai123@gmail.com>"
    
    @staticmethod
    def send_invitation_email(
        to_email: str,
        project_name: str,
        invitation_token: str,
        frontend_url: str = "https://photosite360-frontend.onrender.com"
    ) -> bool:
        """
        Envía email de invitación a colaborador
        """
        try:
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Invitación a proyecto: {project_name}"
            msg['From'] = EmailService.EMAIL_FROM
            msg['To'] = to_email
            
            # Generar link de invitación
            invitation_link = f"{frontend_url}/invitation/{invitation_token}"
            
            # HTML del email
            html = f"""
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
            
            # Texto plano alternativo
            text = f"""
PhotoSite360 - Invitación a Proyecto

Has sido invitado a colaborar en el proyecto: {project_name}

Haz clic en el siguiente enlace para aceptar la invitación:
{invitation_link}

Si no solicitaste esta invitación, puedes ignorar este email.

© 2025 PhotoSite360
            """
            
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            
            msg.attach(part1)
            msg.attach(part2)
            
            # Enviar email
            with smtplib.SMTP(EmailService.SMTP_SERVER, EmailService.SMTP_PORT) as server:
                server.starttls()
                server.login(EmailService.EMAIL_USER, EmailService.EMAIL_PASSWORD)
                server.send_message(msg)
            
            print(f"✅ Email enviado a {to_email}")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando email: {e}")
            return False