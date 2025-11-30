from services.email_service import EmailService
from fastapi import FastAPI, Request, Response  # Añade Response aquí
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from passlib.context import CryptContext
from jose.exceptions import JWTError as JWTException
from jose import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, List
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import shutil
from pathlib import Path
import re
import cloudinary
import cloudinary.uploader
import cloudinary.api
import secrets

# ✅ IMPORTS DE SERVICIOS
from services.cloudinary_service import CloudinaryService

# Configuración
SECRET_KEY = "tu_clave_secreta_super_segura_cambiala_en_produccion"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200  # 30 días (30 * 24 * 60 = 43200 minutos)

# Configuración de Cloudinary
cloudinary.config(
    cloud_name="dryuzad8w",
    api_key="281976991233177",
    api_secret="oVv51LHUFYrmmux8oFuU0t-836s",
    secure=True
)

# Base de datos
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./photosite360.db")
print("\n" + "=" * 80)
print("🗄️🗄️🗄️ CONFIGURACIÓN DE BASE DE DATOS 🗄️🗄️🗄️")
print("=" * 80)
print(f"DATABASE_URL: {DATABASE_URL}")
print("=" * 80 + "\n")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("postgresql://"):
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelos de base de datos
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    projects = relationship("Project", back_populates="owner")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    location = Column(String, nullable=True)
    is_public = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="projects")
    photos = relationship("Photo", back_populates="project", cascade="all, delete-orphan")

class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String, nullable=True)
    url = Column(String)
    latitude = Column(String, nullable=True)
    longitude = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    project = relationship("Project", back_populates="photos")

# ✅ MODELOS PARA GALERÍA
class GalleryImage(Base):
    __tablename__ = "gallery_images"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    url = Column(String)
    unique_url = Column(String, unique=True)
    file_size = Column(Integer)
    mime_type = Column(String)
    project_id = Column(Integer, ForeignKey("projects.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    
    # Metadatos estructurados para el sistema de etiquetas
    image_type = Column(String, default="edification")
    level = Column(String, nullable=True)
    room = Column(String, nullable=True)
    pk_value = Column(String, nullable=True)
    section = Column(String, nullable=True)
    custom_tags = Column(String, nullable=True)
    
    project = relationship("Project")
    uploader = relationship("User")

class GalleryTag(Base):
    __tablename__ = "gallery_tags"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    tag_type = Column(String)
    tag_value = Column(String)
    tag_color = Column(String, default='#3b82f6')
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    project = relationship("Project")
    creator = relationship("User")

# ========================================
# ✅ MODELOS DE INVITACIONES
class ProjectCollaborator(Base):
    __tablename__ = "project_collaborators"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    permission_level = Column(String)
    can_edit = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_invite = Column(Boolean, default=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    added_by = Column(Integer, ForeignKey("users.id"))

class Invitation(Base):
    __tablename__ = "invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)
    inviter_id = Column(Integer, ForeignKey("users.id"))
    invitee_email = Column(String, index=True)
    permission_level = Column(String)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    status = Column(String, default="PENDING")
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    accepted_at = Column(DateTime, nullable=True)

# Crear tablas
Base.metadata.create_all(bind=engine)

# Crear carpeta para fotos si no existe
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Configuración de seguridad
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Aplicación FastAPI
app = FastAPI(title="PhotoSite360 API")

# CORS - CONFIGURACIÓN SEGURA PARA PRODUCCIÓN
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://photosite360-frontend.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"📍 Request: {request.method} {request.url}")
    print(f"📍 Origin: {request.headers.get('origin')}")
    
    response = await call_next(request)
    
    print(f"📍 Response: {response.status_code}")
    return response

# Handler para OPTIONS requests
@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str):
    return JSONResponse(status_code=200)

@app.options("/api/{rest_of_path:path}")
async def api_preflight_handler(rest_of_path: str):
    return JSONResponse(status_code=200)

# Servir archivos estáticos
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Modelos Pydantic
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    username: str

class UserLogin(BaseModel):
    email: str
    password: str
    
    class Config:
        extra = "allow"

class Token(BaseModel):
    access_token: str
    token_type: str

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    location: Optional[str]
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PhotoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    url: str
    latitude: Optional[str]
    longitude: Optional[str]
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ✅ MODELOS PYDANTIC PARA GALERÍA
class GalleryImageCreate(BaseModel):
    filename: str
    image_type: str = "edification"
    level: Optional[str] = None
    room: Optional[str] = None
    pk_value: Optional[str] = None
    section: Optional[str] = None
    custom_tags: Optional[List[str]] = None

class GalleryImageResponse(BaseModel):
    id: int
    filename: str
    url: str
    unique_url: str
    file_size: int
    mime_type: str
    project_id: int
    uploaded_at: datetime
    image_type: str
    level: Optional[str]
    room: Optional[str]
    pk_value: Optional[str]
    section: Optional[str]
    custom_tags: Optional[List[str]]

    class Config:
        from_attributes = True

class GalleryTagCreate(BaseModel):
    tag_type: str
    tag_value: str
    tag_color: Optional[str] = '#3b82f6'

class GalleryTagResponse(BaseModel):
    id: int
    tag_type: str
    tag_value: str
    tag_color: str
    created_at: datetime

    class Config:
        from_attributes = True

# Funciones auxiliares
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTException:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# ========================================
# RUTAS DE AUTENTICACIÓN
# ========================================

@app.post("/api/auth/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        full_name=user.full_name,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    print(f"🔐 Intento de login: {user.email}")
    
    db_user = db.query(User).filter(User.email == user.email).first()
    
    if not db_user:
        print(f"❌ Usuario no encontrado: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    print(f"✅ Usuario encontrado: ID={db_user.id}, Email={db_user.email}")
    print(f"🔑 Hash almacenado: {db_user.hashed_password[:50]}...")
    
    is_valid = verify_password(user.password, db_user.hashed_password)
    print(f"🔍 ¿Password válido?: {is_valid}")
    
    if not is_valid:
        print(f"❌ Password incorrecto para {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    print(f"✅ Login exitoso para {user.email}")
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}
# POST /api/invitations/invite-global
@app.post("/api/invitations/invite-global")
def invite_global_collaborator(
    invitee_email: str = Body(...),
    message: str = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crear invitación global y enviar email"""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    invitation = Invitation(
        token=token,
        inviter_id=current_user.id,
        invitee_email=invitee_email,
        permission_level="GLOBAL_COLLABORATOR",
        project_id=None,
        message=message,
        expires_at=expires_at
    )
    
    db.add(invitation)
    db.commit()
    
    # Enviar email en background
    import threading
    threading.Thread(
        target=EmailService.send_invitation_email,
        args=(invitee_email, "Colaboración Global en PhotoSite360", token)
    ).start()
    
    return {
        "message": "Invitación creada. Email enviándose en segundo plano.",
        "invitation_id": invitation.id,
        "expires_at": expires_at.isoformat()
    }
# POST /api/invitations/{token}/accept-and-login
@app.post("/api/invitations/{token}/accept-and-login")
def accept_invitation_and_login(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Aceptar invitación y hacer login automático (sin contraseña)
    Crea usuario temporal si no existe
    """
    invitation = db.query(Invitation).filter(
        Invitation.token == token,
        Invitation.status == "PENDING"
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitación no encontrada o ya usada")
    
    if invitation.expires_at < datetime.utcnow():
        invitation.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=400, detail="Invitación expirada")
    
    # Buscar o crear usuario
    user = db.query(User).filter(User.email == invitation.invitee_email).first()
    
    if not user:
        # Crear usuario temporal (sin contraseña)
        user = User(
            email=invitation.invitee_email,
            full_name=invitation.invitee_email.split('@')[0],  # Usar parte del email como nombre
            hashed_password=pwd_context.hash(secrets.token_urlsafe(32))  # Password aleatoria
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Crear colaboración si es para un proyecto
    if invitation.project_id:
        # Verificar si ya es colaborador
        existing = db.query(ProjectCollaborator).filter(
            ProjectCollaborator.project_id == invitation.project_id,
            ProjectCollaborator.user_id == user.id
        ).first()
        
        if not existing:
            collaboration = ProjectCollaborator(
                project_id=invitation.project_id,
                user_id=user.id,
                permission_level=invitation.permission_level,
                can_edit=invitation.permission_level != "VIEWER",
                can_delete=False,
                can_invite=False,
                added_by=invitation.inviter_id
            )
            db.add(collaboration)
    
    # Marcar invitación como aceptada
    invitation.status = "ACCEPTED"
    invitation.accepted_at = datetime.utcnow()
    db.commit()
    
    # Generar token JWT (30 días)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        },
        "message": "Invitación aceptada y sesión iniciada",
        "project_id": invitation.project_id
    }
# POST /api/projects/{project_id}/invite
@app.post("/api/projects/{project_id}/invite")
def invite_to_project(
    project_id: int,
    invitee_email: str = Body(...),
    permission_level: str = Body(...),
    message: str = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invitar colaborador a proyecto específico y enviar email"""
    # Verificar que el proyecto existe
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Verificar que el usuario es propietario
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el propietario puede invitar")
    
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    invitation = Invitation(
        token=token,
        inviter_id=current_user.id,
        invitee_email=invitee_email,
        permission_level=permission_level,
        project_id=project_id,
        message=message,
        expires_at=expires_at
    )
    
    db.add(invitation)
    db.commit()
    
    # Enviar email en background (no bloquea la respuesta)
    import threading
    threading.Thread(
        target=EmailService.send_invitation_email,
        args=(invitee_email, project.name, token)
    ).start()
    
    return {
        "message": "Invitación creada. Email enviándose en segundo plano.",
        "invitation_id": invitation.id,
        "expires_at": expires_at.isoformat()
    }


@app.get("/api/invitations/pending")
async def get_pending_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener invitaciones pendientes del usuario actual
    """
    invitations = db.query(Invitation).filter(
        Invitation.invitee_email == current_user.email,
        Invitation.status == "PENDING",
        Invitation.expires_at > datetime.utcnow()
    ).all()
    
    result = []
    for inv in invitations:
        inviter = db.query(User).filter(User.id == inv.inviter_id).first()
        project = None
        if inv.project_id:
            project = db.query(Project).filter(Project.id == inv.project_id).first()
        
        result.append({
            "id": inv.id,
            "token": inv.token,
            "inviter_name": inviter.username if inviter else "Usuario desconocido",
            "project_name": project.name if project else None,
            "permission_level": inv.permission_level,
            "message": inv.message,
            "created_at": inv.created_at.isoformat(),
            "expires_at": inv.expires_at.isoformat()
        })
    
    return result


@app.post("/api/invitations/{token}/accept")
async def accept_invitation(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Aceptar una invitación
    """
    invitation = db.query(Invitation).filter(
        Invitation.token == token,
        Invitation.status == "PENDING"
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    
    if invitation.invitee_email != current_user.email:
        raise HTTPException(status_code=403, detail="Esta invitación no es para ti")
    
    if invitation.expires_at < datetime.utcnow():
        invitation.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=400, detail="Invitación expirada")
    
    # Crear colaboración si es para un proyecto
    if invitation.project_id:
        collaboration = ProjectCollaborator(
            project_id=invitation.project_id,
            user_id=current_user.id,
            permission_level=invitation.permission_level,
            can_edit=invitation.permission_level != "VIEWER",
            can_delete=False,
            can_invite=False,
            added_by=invitation.inviter_id
        )
        db.add(collaboration)
    
    # Marcar invitación como aceptada
    invitation.status = "ACCEPTED"
    invitation.accepted_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Invitación aceptada exitosamente"}


@app.post("/api/invitations/{token}/reject")
async def reject_invitation(
    token: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rechazar una invitación
    """
    invitation = db.query(Invitation).filter(
        Invitation.token == token,
        Invitation.status == "PENDING"
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    
    if invitation.invitee_email != current_user.email:
        raise HTTPException(status_code=403, detail="Esta invitación no es para ti")
    
    invitation.status = "REJECTED"
    db.commit()
    
    return {"message": "Invitación rechazada"}


# GET /api/projects/{project_id}/collaborators
@app.get("/api/projects/{project_id}/collaborators")
def get_project_collaborators(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obtener lista de colaboradores del proyecto"""
    # Verificar acceso al proyecto
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Solo el propietario o colaboradores pueden ver la lista
    if project.owner_id != current_user.id:
        collaborator = db.query(ProjectCollaborator).filter(
            ProjectCollaborator.project_id == project_id,
            ProjectCollaborator.user_id == current_user.id
        ).first()
        if not collaborator:
            raise HTTPException(status_code=403, detail="No tienes acceso a este proyecto")
    
    # Obtener colaboradores
    collaborators = db.query(ProjectCollaborator).filter(
        ProjectCollaborator.project_id == project_id
    ).all()
    
    result = []
    for collab in collaborators:
        user = db.query(User).filter(User.id == collab.user_id).first()
        if user:
            result.append({
                "id": collab.id,
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "permission_level": collab.permission_level,
                "can_edit": collab.can_edit,
                "can_delete": collab.can_delete,
                "can_invite": collab.can_invite,
                "added_at": collab.added_at.isoformat()
            })
    
    return result

# DELETE /api/projects/{project_id}/collaborators/{user_id}
@app.delete("/api/projects/{project_id}/collaborators/{user_id}")
def remove_collaborator(
    project_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Eliminar colaborador del proyecto"""
    # Verificar que el proyecto existe
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    # Solo el propietario puede eliminar colaboradores
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el propietario puede eliminar colaboradores")
    
    # Eliminar colaborador
    collaborator = db.query(ProjectCollaborator).filter(
        ProjectCollaborator.project_id == project_id,
        ProjectCollaborator.user_id == user_id
    ).first()
    
    if not collaborator:
        raise HTTPException(status_code=404, detail="Colaborador no encontrado")
    
    db.delete(collaborator)
    db.commit()
    
    return {"message": "Colaborador eliminado"}

# ========================================
# RUTAS DE PROYECTOS
# ========================================

@app.post("/api/projects/", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_project = Project(
        name=project.name,
        description=project.description,
        location=project.location,
        owner_id=current_user.id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project

@app.get("/api/projects/", response_model=List[ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    projects = db.query(Project).filter(Project.owner_id == current_user.id).all()
    return projects

@app.get("/api/projects/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.delete("/api/projects/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina un proyecto y TODOS sus archivos en Cloudinary
    """
    try:
        # 1. Buscar el proyecto
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.owner_id == current_user.id
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        print(f"🗑️ Iniciando eliminación del proyecto {project_id}: {project.name}")
        
        # 2. Obtener conteo de archivos antes de eliminar
        photos_count = db.query(Photo).filter(Photo.project_id == project_id).count()
        gallery_count = db.query(GalleryImage).filter(GalleryImage.project_id == project_id).count()
        
        print(f"📊 Archivos a eliminar: {photos_count} fotos 360°, {gallery_count} imágenes normales")
        
        # 3. Eliminar TODA la carpeta del proyecto en Cloudinary
        cloudinary_result = CloudinaryService.delete_project_folder(project_id)
        
        if cloudinary_result.get('success'):
            print(f"✅ Cloudinary: {cloudinary_result.get('message')}")
        else:
            print(f"⚠️ Cloudinary: {cloudinary_result.get('error')}")
        
        # 4. Eliminar registros de fotos 360° en BD
        db.query(Photo).filter(Photo.project_id == project_id).delete()
        
        # 5. Eliminar registros de galería en BD
        db.query(GalleryImage).filter(GalleryImage.project_id == project_id).delete()
        
        # 6. Eliminar tags de galería
        db.query(GalleryTag).filter(GalleryTag.project_id == project_id).delete()
        
        # 7. Eliminar el proyecto
        db.delete(project)
        db.commit()
        
        print(f"✅ Proyecto {project_id} eliminado completamente")
        
        return {
            "message": "Proyecto eliminado exitosamente",
            "project_id": project_id,
            "project_name": project.name,
            "deleted_photos_360": photos_count,
            "deleted_gallery": gallery_count,
            "cloudinary_cleanup": cloudinary_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error eliminando proyecto: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error eliminando proyecto: {str(e)}")

@app.get("/api/projects/{project_id}/storage-info")
def get_project_storage_info(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene información de almacenamiento del proyecto en Cloudinary
    """
    try:
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.owner_id == current_user.id
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        storage_info = CloudinaryService.get_project_storage_info(project_id)
        
        return {
            "project_id": project_id,
            "project_name": project.name,
            "storage": storage_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error obteniendo info de almacenamiento: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# RUTAS DE FOTOS 360°
# ========================================

@app.get("/api/projects/{project_id}/photos", response_model=List[PhotoResponse])
def get_photos(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    photos = db.query(Photo).filter(Photo.project_id == project_id).all()
    return photos

@app.post("/api/projects/{project_id}/photos/upload")
async def upload_photo(
    project_id: int,
    file: UploadFile = File(...),
    title: str = "",
    description: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id, 
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        print(f"📤 Subiendo {file.filename} a Cloudinary...")
        
        contents = await file.read()
        
        upload_result = cloudinary.uploader.upload(
            contents,
            folder=f"photosite360/project_{project_id}",
            public_id=f"{datetime.utcnow().timestamp()}_{file.filename}",
            resource_type="auto"
        )
        
        cloudinary_url = upload_result['secure_url']
        print(f"✓ Subido exitosamente: {cloudinary_url}")
        
        photo = Photo(
            title=title or file.filename,
            description="",
            url=cloudinary_url,
            project_id=project_id
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)
        
        print(f"✓ Foto guardada en BD con ID: {photo.id}")
        
        return photo
        
    except Exception as e:
        print(f"✗ Error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.post("/api/projects/{project_id}/photos/{photo_id}/coordinates")
async def upload_coordinates(
    project_id: int,
    photo_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.project_id == project_id
    ).first()
    if not photo:
        print(f"✗ Foto con ID {photo_id} no encontrada en proyecto {project_id}")
        raise HTTPException(status_code=404, detail="Photo not found")
    
    content = await file.read()
    content_str = content.decode('utf-8')
    
    print(f"\n=== PARSEANDO COORDENADAS ===")
    print(f"Foto ID: {photo_id}")
    
    pos_match = re.search(r'position\s*=\s*\[([-\d.eE+]+),\s*([-\d.eE+]+),\s*([-\d.eE+]+)\]', content_str)
    orient_match = re.search(r'orientation\s*=\s*\[([-\d.eE+]+),\s*([-\d.eE+]+),\s*([-\d.eE+]+),\s*([-\d.eE+]+)\]', content_str)
    
    if pos_match:
        x = pos_match.group(1)
        y = pos_match.group(2)
        z = pos_match.group(3)
        
        print(f"Coordenadas encontradas: X={x}, Y={y}, Z={z}")
        
        photo.latitude = x
        photo.longitude = y
        
        desc_parts = [f"z:{z}"]
        
        if orient_match:
            qx = orient_match.group(1)
            qy = orient_match.group(2)
            qz = orient_match.group(3)
            qw = orient_match.group(4)
            desc_parts.append(f"orientation:[{qx},{qy},{qz},{qw}]")
            print(f"Orientación encontrada")
        
        photo.description = "|".join(desc_parts)
        
        db.commit()
        db.refresh(photo)
        
        print(f"✓ Coordenadas guardadas")
        
        return {
            "message": "Coordinates updated",
            "latitude": photo.latitude,
            "longitude": photo.longitude,
            "description": photo.description
        }
    else:
        print("✗ NO SE ENCONTRARON COORDENADAS")
        raise HTTPException(status_code=400, detail="No coordinates found in file")

@app.delete("/api/projects/{project_id}/photos/{photo_id}")
def delete_photo(
    project_id: int,
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.project_id == project_id
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    # ✅ Eliminar de Cloudinary también
    try:
        # Extraer public_id de la URL
        url_parts = photo.url.split('/')
        public_id_with_ext = '/'.join(url_parts[-3:])  # photosite360/project_X/filename.jpg
        public_id = public_id_with_ext.rsplit('.', 1)[0]  # Sin extensión
        
        CloudinaryService.delete_photo(public_id)
        print(f"✓ Foto eliminada de Cloudinary: {public_id}")
    except Exception as e:
        print(f"⚠️ No se pudo eliminar de Cloudinary: {e}")
    
    db.delete(photo)
    db.commit()
    return {"message": "Photo deleted successfully"}

# ========================================
# RUTAS DE GALERÍA DE IMÁGENES NORMALES
# ========================================

@app.post("/api/projects/{project_id}/gallery/upload")
async def upload_gallery_image(
    project_id: int,
    file: UploadFile = File(...),
    image_type: str = "edification",
    level: Optional[str] = None,
    room: Optional[str] = None,
    pk_value: Optional[str] = None,
    section: Optional[str] = None,
    custom_tags: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        print(f"📤 Subiendo imagen de galería: {file.filename}")
        
        contents = await file.read()
        
        upload_result = cloudinary.uploader.upload(
            contents,
            folder=f"photosite360/gallery/project_{project_id}",
            public_id=f"gallery_{datetime.utcnow().timestamp()}_{file.filename}",
            resource_type="image"
        )
        
        cloudinary_url = upload_result['secure_url']
        print(f"✓ Imagen subida exitosamente: {cloudinary_url}")
        
        unique_url = f"gallery_{project_id}_{datetime.utcnow().timestamp()}_{file.filename}"
        
        processed_custom_tags = None
        if custom_tags:
            try:
                tags_list = [tag.strip() for tag in custom_tags.split(",") if tag.strip()]
                processed_custom_tags = ",".join(tags_list)
            except:
                processed_custom_tags = custom_tags
        
        gallery_image = GalleryImage(
            filename=file.filename,
            url=cloudinary_url,
            unique_url=unique_url,
            file_size=len(contents),
            mime_type=file.content_type,
            project_id=project_id,
            uploaded_by=current_user.id,
            image_type=image_type,
            level=level,
            room=room,
            pk_value=pk_value,
            section=section,
            custom_tags=processed_custom_tags
        )
        
        db.add(gallery_image)
        db.commit()
        db.refresh(gallery_image)
        
        print(f"✓ Imagen de galería guardada con ID: {gallery_image.id}")
        
        return {
            "id": gallery_image.id,
            "filename": gallery_image.filename,
            "url": gallery_image.url,
            "unique_url": gallery_image.unique_url,
            "file_size": gallery_image.file_size,
            "project_id": gallery_image.project_id,
            "uploaded_at": gallery_image.uploaded_at,
            "image_type": gallery_image.image_type,
            "level": gallery_image.level,
            "room": gallery_image.room,
            "pk_value": gallery_image.pk_value,
            "section": gallery_image.section,
            "custom_tags": gallery_image.custom_tags.split(",") if gallery_image.custom_tags else []
        }
        
    except Exception as e:
        print(f"✗ Error subiendo imagen de galería: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading gallery image: {str(e)}")

@app.get("/api/projects/{project_id}/gallery", response_model=List[GalleryImageResponse])
def get_gallery_images(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    images = db.query(GalleryImage).filter(GalleryImage.project_id == project_id).all()
    
    result = []
    for image in images:
        image_data = {
            "id": image.id,
            "filename": image.filename,
            "url": image.url,
            "unique_url": image.unique_url,
            "file_size": image.file_size,
            "mime_type": image.mime_type,
            "project_id": image.project_id,
            "uploaded_at": image.uploaded_at,
            "image_type": image.image_type,
            "level": image.level,
            "room": image.room,
            "pk_value": image.pk_value,
            "section": image.section,
            "custom_tags": image.custom_tags.split(",") if image.custom_tags else []
        }
        result.append(image_data)
    
    return result

@app.delete("/api/projects/{project_id}/gallery/{image_id}")
def delete_gallery_image(
    project_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    image = db.query(GalleryImage).filter(
        GalleryImage.id == image_id,
        GalleryImage.project_id == project_id
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Gallery image not found")
    
    # ✅ Eliminar de Cloudinary
    try:
        url_parts = image.url.split('/')
        public_id_with_ext = '/'.join(url_parts[-3:])
        public_id = public_id_with_ext.rsplit('.', 1)[0]
        
        CloudinaryService.delete_photo(public_id)
        print(f"✓ Imagen eliminada de Cloudinary: {public_id}")
    except Exception as e:
        print(f"⚠️ No se pudo eliminar de Cloudinary: {e}")
    
    db.delete(image)
    db.commit()
    return {"message": "Gallery image deleted successfully"}

# ========================================
# RUTAS DE TAGS DE GALERÍA
# ========================================

@app.post("/api/projects/{project_id}/gallery/tags", response_model=GalleryTagResponse)
def create_gallery_tag(
    project_id: int,
    tag: GalleryTagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    existing_tag = db.query(GalleryTag).filter(
        GalleryTag.project_id == project_id,
        GalleryTag.tag_type == tag.tag_type,
        GalleryTag.tag_value == tag.tag_value
    ).first()
    
    if existing_tag:
        raise HTTPException(status_code=400, detail="Tag already exists")
    
    new_tag = GalleryTag(
        project_id=project_id,
        tag_type=tag.tag_type,
        tag_value=tag.tag_value,
        tag_color=tag.tag_color,
        created_by=current_user.id
    )
    
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    
    return new_tag

@app.get("/api/projects/{project_id}/gallery/tags", response_model=List[GalleryTagResponse])
def get_gallery_tags(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    tags = db.query(GalleryTag).filter(GalleryTag.project_id == project_id).all()
    return tags

@app.put("/api/projects/{project_id}/gallery/{image_id}/metadata")
def update_image_metadata(
    project_id: int,
    image_id: int,
    image_type: Optional[str] = None,
    level: Optional[str] = None,
    room: Optional[str] = None,
    pk_value: Optional[str] = None,
    section: Optional[str] = None,
    custom_tags: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    image = db.query(GalleryImage).filter(
        GalleryImage.id == image_id,
        GalleryImage.project_id == project_id
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Gallery image not found")
    
    if image_type is not None:
        image.image_type = image_type
    if level is not None:
        image.level = level
    if room is not None:
        image.room = room
    if pk_value is not None:
        image.pk_value = pk_value
    if section is not None:
        image.section = section
    if custom_tags is not None:
        image.custom_tags = custom_tags
    
    db.commit()
    db.refresh(image)
    
    return {
        "message": "Image metadata updated successfully",
        "image": {
            "id": image.id,
            "image_type": image.image_type,
            "level": image.level,
            "room": image.room,
            "pk_value": image.pk_value,
            "section": image.section,
            "custom_tags": image.custom_tags.split(",") if image.custom_tags else []
        }
    }

# ========================================
# RUTAS PÚBLICAS
# ========================================

@app.get("/api/public/projects/{project_id}")
def get_public_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.get("/api/public/projects/{project_id}/photos")
def get_public_photos(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    photos = db.query(Photo).filter(Photo.project_id == project_id).all()
    return photos

@app.get("/api/public/photos/{photo_id}")
def get_public_photo(photo_id: int, db: Session = Depends(get_db)):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return photo

# ========================================
# ENDPOINTS DE DEBUG PARA PRODUCCIÓN
# ========================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "cors_configured": True,
        "database": "connected"
    }

@app.get("/api/debug/cors")
async def debug_cors(request: Request):
    return {
        "origin": request.headers.get("origin"),
        "user_agent": request.headers.get("user-agent"),
        "cors_headers": {
            "allow_origin": "https://photosite360-frontend.onrender.com",
            "allow_methods": "GET,POST,PUT,DELETE,OPTIONS,PATCH"
        }
    }

# ========================================
# RUTA RAÍZ
# ========================================

@app.get("/")
def root():
    return {
        "message": "PhotoSite360 API - Server running",
        "version": "2.0.0",
        "features": [
            "Authentication",
            "Projects Management",
            "360° Photos",
            "Gallery Images",
            "Cloudinary Integration",
            "Automatic Cleanup",
            "Invitations & Permissions"
        ]
    }
# ========================================
# EJECUTAR SERVIDOR
# ========================================

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Railway usa la variable de entorno PORT
    port = int(os.getenv("PORT", 5000))
    
    print("=" * 60)
    print("🚀 INICIANDO PHOTOSITE360 BACKEND")
    print("=" * 60)
    print(f"📦 Cloudinary configurado: dryuzad8w")
    print(f"🗑️ Limpieza automática activada")
    print(f"🔐 Sistema de invitaciones activado")
    print(f"🌐 Servidor en puerto: {port}")
    print(f"🔄 CORS configurado para:")
    print(f"   - http://localhost:5173 (local)")
    print(f"   - https://photosite360-frontend.onrender.com (producción)")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)