from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import secrets

def create_invitation_models(Base):
    """Crea los modelos de invitaciones"""
    
    class ProjectCollaborator(Base):
        __tablename__ = "project_collaborators"
        
        id = Column(Integer, primary_key=True, index=True)
        project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
        user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
        permission_level = Column(String)  # OWNER, GLOBAL_COLLABORATOR, PROJECT_COLLABORATOR, VIEWER
        can_edit = Column(Boolean, default=False)
        can_delete = Column(Boolean, default=False)
        can_invite = Column(Boolean, default=False)
        added_at = Column(DateTime, default=datetime.utcnow)
        added_by = Column(Integer, ForeignKey("users.id"))

    class Invitation(Base):
        __tablename__ = "invitations"
        
        id = Column(Integer, primary_key=True, index=True)
        token = Column(String, unique=True, index=True, default=lambda: secrets.token_urlsafe(32))
        inviter_id = Column(Integer, ForeignKey("users.id"))
        invitee_email = Column(String, index=True)
        permission_level = Column(String)
        project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
        status = Column(String, default="PENDING")  # PENDING, ACCEPTED, REJECTED, EXPIRED
        message = Column(Text, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
        accepted_at = Column(DateTime, nullable=True)
    
    return ProjectCollaborator, Invitation