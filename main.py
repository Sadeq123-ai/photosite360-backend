from services.email_service import EmailService
from fastapi import FastAPI, Request, Response
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request, Body, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text, text
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
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# ✅ IMPORTS DE SERVICIOS
from services.cloudinary_service import CloudinaryService

# Importaciones opcionales para coordenadas
try:
    import pandas as pd
    import openpyxl
    from utils.coordinate_transforms import CoordinateTransformer
    COORDINATES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  WARNING: Coordinate features disabled - {e}")
    COORDINATES_AVAILABLE = False

# Configuración
SECRET_KEY = "tu_clave_secreta_super_segura_cambiala_en_produccion"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200  # 30 días

# Configuración de Cloudinary
cloudinary.config(
    cloud_name="dryuzad8w",
    api_key="281976991233177",
    api_secret="oVv51LHUFYrmmux8oFuU0t-836s",
    secure=True
)

# Base de datos - DEBUG COMPLETO
print("\n" + "=" * 80)
print("DEBUG: TODAS LAS VARIABLES DE ENTORNO")
print("=" * 80)
for key, value in os.environ.items():
    if 'DATABASE' in key.upper() or 'DB' in key.upper() or 'POSTGRES' in key.upper():
        print(f"{key}: {value[:80]}..." if len(value) > 80 else f"{key}: {value}")
print("=" * 80 + "\n")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./photosite360.db")
print("\n" + "=" * 80)
print("DATABASE CONFIGURATION")
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

    # Campos para origen y rotación del mapa
    map_origin_lat = Column(Float, nullable=True)
    map_origin_lng = Column(Float, nullable=True)
    map_rotation = Column(Float, default=0.0)

    owner = relationship("User", back_populates="projects")
    photos = relationship("Photo", back_populates="project", cascade="all, delete-orphan")
    gallery_images = relationship("GalleryImage", back_populates="project", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="project", cascade="all, delete-orphan")

class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String, nullable=True)
    url = Column(String)
    project_id = Column(Integer, ForeignKey("projects.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Coordenadas geográficas WGS84
    geo_latitude = Column(Float, nullable=True)
    geo_longitude = Column(Float, nullable=True)

    # Coordenadas UTM ETRS89
    utm_easting = Column(Float, nullable=True)
    utm_northing = Column(Float, nullable=True)
    utm_zone = Column(Integer, nullable=True)
    utm_hemisphere = Column(String, nullable=True)
    utm_datum = Column(String, nullable=True)

    # Coordenadas del proyecto (sistema local)
    project_x = Column(Float, nullable=True)
    project_y = Column(Float, nullable=True)
    project_z = Column(Float, nullable=True)

    # Origen de coordenadas: 'local', 'utm', 'geo', 'manual'
    coordinate_source = Column(String, default="manual", nullable=True)

    # Tipo de objeto
    object_type = Column(String, default="360photo")

    project = relationship("Project", back_populates="photos")

class GalleryImage(Base):
    __tablename__ = "gallery_images"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    url = Column(String)
    unique_url = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Metadatos de clasificación
    image_type = Column(String, default="edification")
    level = Column(String, nullable=True)
    room = Column(String, nullable=True)
    pk_value = Column(String, nullable=True)
    section = Column(String, nullable=True)
    custom_tags = Column(String, nullable=True)

    # Coordenadas geográficas WGS84
    geo_latitude = Column(Float, nullable=True)
    geo_longitude = Column(Float, nullable=True)

    # Coordenadas UTM ETRS89
    utm_easting = Column(Float, nullable=True)
    utm_northing = Column(Float, nullable=True)
    utm_zone = Column(Integer, nullable=True)
    utm_hemisphere = Column(String, nullable=True)
    utm_datum = Column(String, nullable=True)

    # Coordenadas del proyecto
    project_x = Column(Float, nullable=True)
    project_y = Column(Float, nullable=True)
    project_z = Column(Float, nullable=True)

    # Origen de coordenadas: 'local', 'utm', 'geo', 'manual'
    coordinate_source = Column(String, default="manual", nullable=True)

    # Tipo de objeto
    object_type = Column(String, default="image")

    project = relationship("Project", back_populates="gallery_images")

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    incident_type = Column(String, default="defecto")
    severity = Column(String, default="media")
    status = Column(String, default="pendiente")
    project_id = Column(Integer, ForeignKey("projects.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Coordenadas geográficas WGS84
    geo_latitude = Column(Float, nullable=True)
    geo_longitude = Column(Float, nullable=True)

    # Coordenadas UTM ETRS89
    utm_easting = Column(Float, nullable=True)
    utm_northing = Column(Float, nullable=True)
    utm_zone = Column(Integer, nullable=True)
    utm_hemisphere = Column(String, nullable=True)
    utm_datum = Column(String, nullable=True)

    # Coordenadas del proyecto
    project_x = Column(Float, nullable=True)
    project_y = Column(Float, nullable=True)
    project_z = Column(Float, nullable=True)

    # Tipo de objeto
    object_type = Column(String, default="incident")

    project = relationship("Project", back_populates="incidents")

class Invitation(Base):
    __tablename__ = "invitations"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    token = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

# Crear tablas
Base.metadata.create_all(bind=engine)

# Función para ejecutar migraciones automáticas
def run_auto_migrations():
    """Ejecuta migraciones necesarias para agregar campos faltantes"""
    try:
        with engine.connect() as conn:
            # Verificar si coordinate_source existe en photos
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'photos' AND column_name = 'coordinate_source'
            """))

            if not result.fetchone():
                print("⚙️  Running migration: Adding coordinate_source to photos...")
                conn.execute(text("""
                    ALTER TABLE photos
                    ADD COLUMN coordinate_source VARCHAR DEFAULT 'manual'
                """))
                conn.commit()
                print("✅ Migration complete: coordinate_source added to photos")

            # Verificar si coordinate_source existe en gallery_images
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'gallery_images' AND column_name = 'coordinate_source'
            """))

            if not result.fetchone():
                print("⚙️  Running migration: Adding coordinate_source to gallery_images...")
                conn.execute(text("""
                    ALTER TABLE gallery_images
                    ADD COLUMN coordinate_source VARCHAR DEFAULT 'manual'
                """))
                conn.commit()
                print("✅ Migration complete: coordinate_source added to gallery_images")

    except Exception as e:
        print(f"⚠️  Migration warning: {e}")
        # No fallar si la migración tiene problemas, solo advertir

# Ejecutar migraciones automáticas
if DATABASE_URL.startswith("postgresql://"):
    run_auto_migrations()

# Contexto de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    username: str
    invitation_token: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    is_public: Optional[int] = 0

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_public: Optional[int] = None
    map_origin_lat: Optional[float] = None
    map_origin_lng: Optional[float] = None
    map_rotation: Optional[float] = None

class PhotoResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    url: str
    project_id: int
    created_at: datetime
    geo_latitude: Optional[float] = None
    geo_longitude: Optional[float] = None
    utm_easting: Optional[float] = None
    utm_northing: Optional[float] = None
    utm_zone: Optional[int] = None
    utm_hemisphere: Optional[str] = None
    utm_datum: Optional[str] = None
    project_x: Optional[float] = None
    project_y: Optional[float] = None
    project_z: Optional[float] = None
    object_type: Optional[str] = "360photo"

    class Config:
        from_attributes = True

class GalleryImageResponse(BaseModel):
    id: int
    filename: str
    url: str
    unique_url: Optional[str]
    file_size: Optional[int]
    mime_type: Optional[str]
    project_id: int
    uploaded_at: datetime
    image_type: str
    level: Optional[str]
    room: Optional[str]
    pk_value: Optional[str]
    section: Optional[str]
    custom_tags: List[str] = []
    geo_latitude: Optional[float] = None
    geo_longitude: Optional[float] = None
    utm_easting: Optional[float] = None
    utm_northing: Optional[float] = None
    utm_zone: Optional[int] = None
    utm_hemisphere: Optional[str] = None
    utm_datum: Optional[str] = None
    project_x: Optional[float] = None
    project_y: Optional[float] = None
    project_z: Optional[float] = None
    object_type: Optional[str] = "image"

    class Config:
        from_attributes = True

# FastAPI app
app = FastAPI(title="PhotoSite360 API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://photosite360-frontend.onrender.com",
        "https://virtuous-hope-production.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Middleware para logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Request: {request.method} {request.url}")
    print(f"Origin: {request.headers.get('origin')}")
    response = await call_next(request)
    print(f"Response: {response.status_code}")
    return response

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Utilidades
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

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except JWTException:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Endpoints
@app.get("/")
def read_root():
    return {"message": "PhotoSite360 API is running"}

@app.post("/api/auth/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Verificar invitación si es necesario
    if user.invitation_token:
        invitation = db.query(Invitation).filter(
            Invitation.token == user.invitation_token,
            Invitation.used == False,
            Invitation.expires_at > datetime.utcnow()
        ).first()

        if not invitation:
            raise HTTPException(status_code=400, detail="Invalid or expired invitation token")

        # Marcar invitación como usada
        invitation.used = True
        db.commit()

    # Verificar si el email ya existe
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Verificar si el username ya existe
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already taken")

    # Crear nuevo usuario
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        full_name=user.full_name,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {"message": "User created successfully", "user_id": db_user.id}

@app.post("/api/auth/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    print(f"[LOGIN] Intento de login: {user.email}")

    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        print(f"[LOGIN] Usuario no encontrado: {user.email}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    print(f"[LOGIN] Usuario encontrado: ID={db_user.id}, Email={db_user.email}")
    print(f"[LOGIN] Hash almacenado: {db_user.hashed_password[:50]}...")

    password_valid = verify_password(user.password, db_user.hashed_password)
    print(f"[LOGIN] Password valido?: {password_valid}")

    if not password_valid:
        print(f"[LOGIN] Password incorrecto para: {user.email}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": db_user.email})
    print(f"[LOGIN] Login exitoso para {db_user.email}")

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "username": current_user.username
    }

# Endpoints de proyectos
@app.post("/api/projects/")
def create_project(project: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_project = Project(**project.dict(), owner_id=current_user.id)
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

@app.get("/api/projects/")
def get_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    projects = db.query(Project).filter(Project.owner_id == current_user.id).all()
    return projects

@app.get("/api/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.put("/api/projects/{project_id}")
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_update.dict(exclude_unset=True)
    print(f"[PROJECT] Proyecto {project_id} actualizado: {update_data}")

    for key, value in update_data.items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)

    return project

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

# Endpoints de fotos 360
@app.post("/api/projects/{project_id}/photos/upload")
async def upload_photo(
    project_id: int,
    file: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form(""),
    # Coordenadas geográficas WGS84
    geo_latitude: Optional[float] = Form(None),
    geo_longitude: Optional[float] = Form(None),
    # Coordenadas UTM ETRS89
    utm_easting: Optional[float] = Form(None),
    utm_northing: Optional[float] = Form(None),
    utm_zone: Optional[int] = Form(None),
    utm_hemisphere: Optional[str] = Form(None),
    utm_datum: Optional[str] = Form("ETRS89"),
    # Coordenadas del proyecto
    project_x: Optional[float] = Form(None),
    project_y: Optional[float] = Form(None),
    project_z: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar que el proyecto pertenece al usuario
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Subir a Cloudinary
    print(f"Subiendo foto 360: {file.filename}")
    file_content = await file.read()
    cloudinary_response = cloudinary.uploader.upload(
        file_content,
        folder=f"photosite360/photos/project_{project_id}",
        public_id=f"photo_{datetime.utcnow().timestamp()}_{file.filename}",
        resource_type="image"
    )

    cloudinary_url = cloudinary_response.get("secure_url")
    print(f"Foto 360 subida exitosamente: {cloudinary_url}")

    # Crear registro en la base de datos
    photo = Photo(
        title=title or file.filename,
        description="",
        url=cloudinary_url,
        project_id=project_id,
        geo_latitude=geo_latitude,
        geo_longitude=geo_longitude,
        utm_easting=utm_easting,
        utm_northing=utm_northing,
        utm_zone=utm_zone,
        utm_hemisphere=utm_hemisphere,
        utm_datum=utm_datum,
        project_x=project_x,
        project_y=project_y,
        project_z=project_z,
        object_type="360photo"
    )

    db.add(photo)
    db.commit()
    db.refresh(photo)

    print(f"Foto 360 guardada con ID: {photo.id}")
    print(f"Coordenadas: WGS84({geo_latitude},{geo_longitude}), UTM({utm_easting},{utm_northing}), Proyecto({project_x},{project_y},{project_z})")

    return {
        "id": photo.id,
        "title": photo.title,
        "url": photo.url,
        "message": "Photo uploaded successfully"
    }

@app.get("/api/projects/{project_id}/photos", response_model=List[PhotoResponse])
def get_photos(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    photos = db.query(Photo).filter(Photo.project_id == project_id).all()
    return photos

@app.put("/api/projects/{project_id}/photos/{photo_id}/coordinates")
async def update_photo360_coordinates(
    project_id: int,
    photo_id: int,
    geo_latitude: Optional[float] = None,
    geo_longitude: Optional[float] = None,
    utm_easting: Optional[float] = None,
    utm_northing: Optional[float] = None,
    utm_zone: Optional[int] = None,
    utm_hemisphere: Optional[str] = None,
    utm_datum: Optional[str] = "ETRS89",
    project_x: Optional[float] = None,
    project_y: Optional[float] = None,
    project_z: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar proyecto
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get photo
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.project_id == project_id
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Update coordinates
    if geo_latitude is not None:
        photo.geo_latitude = geo_latitude
    if geo_longitude is not None:
        photo.geo_longitude = geo_longitude
    if utm_easting is not None:
        photo.utm_easting = utm_easting
    if utm_northing is not None:
        photo.utm_northing = utm_northing
    if utm_zone is not None:
        photo.utm_zone = utm_zone
    if utm_hemisphere is not None:
        photo.utm_hemisphere = utm_hemisphere
    if utm_datum is not None:
        photo.utm_datum = utm_datum
    if project_x is not None:
        photo.project_x = project_x
    if project_y is not None:
        photo.project_y = project_y
    if project_z is not None:
        photo.project_z = project_z

    db.commit()
    db.refresh(photo)

    print(f"[COORDS] Updated photo {photo_id} coordinates: UTM({utm_easting},{utm_northing}), Project({project_x},{project_y},{project_z})")

    return {"message": "Coordinates updated", "photo_id": photo_id}

@app.post("/api/projects/{project_id}/photos/{photo_id}/coordinates/upload")
async def upload_photo_coordinates_file(
    project_id: int,
    photo_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload coordinates from TXT file for a photo"""
    # Verificar proyecto
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get photo
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.project_id == project_id
    ).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    try:
        # Leer contenido del archivo TXT
        content = await file.read()
        text = content.decode('utf-8')

        # Parsear coordenadas del archivo TXT
        # Formatos soportados:
        # 1. "position = [x, y, z];" (formato Ldr Image)
        # 2. "X: valor", "Y: valor", "Z: valor"
        # 3. "Latitude: valor", "Longitude: valor"

        import re

        # Formato 1: position = [x, y, z];
        position_match = re.search(r'position\s*=\s*\[\s*([-\d.e+]+)\s*,\s*([-\d.e+]+)\s*,\s*([-\d.e+]+)\s*\]', text, re.IGNORECASE)

        if position_match:
            # Extraer X, Y, Z del formato position = [x, y, z]
            x = float(position_match.group(1))
            y = float(position_match.group(2))
            z = float(position_match.group(3))

            photo.project_x = x
            photo.project_y = y
            photo.project_z = z

            print(f"[TXT COORDS] Parsed position format: X={x}, Y={y}, Z={z}")
        else:
            # Formato 2 y 3: Intentar extraer coordenadas individuales
            x_match = re.search(r'[xX]\s*:\s*([-\d.e+]+)', text)
            y_match = re.search(r'[yY]\s*:\s*([-\d.e+]+)', text)
            z_match = re.search(r'[zZ]\s*:\s*([-\d.e+]+)', text)

            # Intentar extraer coordenadas geográficas (Latitude, Longitude)
            lat_match = re.search(r'(Latitude|Lat|latitude|lat)\s*:\s*([-\d.e+]+)', text)
            lon_match = re.search(r'(Longitude|Lon|Lng|longitude|lon|lng)\s*:\s*([-\d.e+]+)', text)

            # Actualizar coordenadas del proyecto si se encontraron
            if x_match:
                photo.project_x = float(x_match.group(1))
            if y_match:
                photo.project_y = float(y_match.group(1))
            if z_match:
                photo.project_z = float(z_match.group(1))

            # Actualizar coordenadas geográficas si se encontraron
            if lat_match:
                photo.geo_latitude = float(lat_match.group(2))
            if lon_match:
                photo.geo_longitude = float(lon_match.group(2))

        db.commit()
        db.refresh(photo)

        print(f"[TXT COORDS] Updated photo {photo_id} from file: Project({photo.project_x},{photo.project_y},{photo.project_z}), Geo({photo.geo_latitude},{photo.geo_longitude})")

        return {
            "message": "Coordinates updated from file",
            "photo_id": photo_id,
            "coordinates": {
                "project_x": photo.project_x,
                "project_y": photo.project_y,
                "project_z": photo.project_z,
                "geo_latitude": photo.geo_latitude,
                "geo_longitude": photo.geo_longitude
            }
        }
    except Exception as e:
        print(f"[ERROR] Failed to parse coordinates file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse coordinates file: {str(e)}")

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

    db.delete(photo)
    db.commit()
    return {"message": "Photo deleted successfully"}

# Endpoints de galería
@app.post("/api/projects/{project_id}/gallery/upload")
async def upload_gallery_image(
    project_id: int,
    file: UploadFile = File(...),
    image_type: str = Form("edification"),
    level: Optional[str] = Form(None),
    room: Optional[str] = Form(None),
    pk_value: Optional[str] = Form(None),
    section: Optional[str] = Form(None),
    custom_tags: Optional[str] = Form(None),
    # Coordenadas geográficas WGS84
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    geo_latitude: Optional[float] = Form(None),
    geo_longitude: Optional[float] = Form(None),
    # Coordenadas UTM ETRS89
    utm_easting: Optional[float] = Form(None),
    utm_northing: Optional[float] = Form(None),
    utm_zone: Optional[int] = Form(None),
    utm_hemisphere: Optional[str] = Form(None),
    utm_datum: Optional[str] = Form("ETRS89"),
    # Coordenadas del proyecto (locales)
    project_x: Optional[float] = Form(None),
    project_y: Optional[float] = Form(None),
    project_z: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Usar geo_latitude/geo_longitude si latitude/longitude están presentes
    if latitude is not None and geo_latitude is None:
        geo_latitude = latitude
    if longitude is not None and geo_longitude is None:
        geo_longitude = longitude

    # Verificar proyecto
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Subir a Cloudinary
    print(f"Subiendo imagen de galeria: {file.filename}")
    file_content = await file.read()
    cloudinary_response = cloudinary.uploader.upload(
        file_content,
        folder=f"photosite360/gallery/project_{project_id}",
        public_id=f"gallery_{datetime.utcnow().timestamp()}_{file.filename}",
        resource_type="image"
    )

    cloudinary_url = cloudinary_response.get("secure_url")
    print(f"Imagen subida exitosamente: {cloudinary_url}")

    # Crear URL única
    unique_url = f"gallery_{project_id}_{datetime.utcnow().timestamp()}_{file.filename}"

    # Guardar en BD
    gallery_image = GalleryImage(
        filename=file.filename,
        url=cloudinary_url,
        unique_url=unique_url,
        file_size=len(file_content),
        mime_type=file.content_type,
        project_id=project_id,
        image_type=image_type,
        level=level,
        room=room,
        pk_value=pk_value,
        section=section,
        custom_tags=custom_tags,
        geo_latitude=geo_latitude,
        geo_longitude=geo_longitude,
        utm_easting=utm_easting,
        utm_northing=utm_northing,
        utm_zone=utm_zone,
        utm_hemisphere=utm_hemisphere,
        utm_datum=utm_datum,
        project_x=project_x,
        project_y=project_y,
        project_z=project_z,
        object_type="image"
    )

    db.add(gallery_image)
    db.commit()
    db.refresh(gallery_image)

    print(f"Imagen de galeria guardada con ID: {gallery_image.id}")
    print(f"Coordenadas: WGS84({geo_latitude},{geo_longitude}), UTM({utm_easting},{utm_northing}), Proyecto({project_x},{project_y},{project_z})")

    return {
        "id": gallery_image.id,
        "filename": gallery_image.filename,
        "url": gallery_image.url,
        "message": "Image uploaded successfully"
    }

@app.put("/api/projects/{project_id}/gallery/{image_id}/coordinates")
async def update_gallery_coordinates(
    project_id: int,
    image_id: int,
    geo_latitude: Optional[float] = None,
    geo_longitude: Optional[float] = None,
    utm_easting: Optional[float] = None,
    utm_northing: Optional[float] = None,
    utm_zone: Optional[int] = None,
    utm_hemisphere: Optional[str] = None,
    utm_datum: Optional[str] = "ETRS89",
    project_x: Optional[float] = None,
    project_y: Optional[float] = None,
    project_z: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update coordinates of an existing gallery image"""
    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get image
    image = db.query(GalleryImage).filter(
        GalleryImage.id == image_id,
        GalleryImage.project_id == project_id
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Update coordinates
    if geo_latitude is not None:
        image.geo_latitude = geo_latitude
    if geo_longitude is not None:
        image.geo_longitude = geo_longitude
    if utm_easting is not None:
        image.utm_easting = utm_easting
    if utm_northing is not None:
        image.utm_northing = utm_northing
    if utm_zone is not None:
        image.utm_zone = utm_zone
    if utm_hemisphere is not None:
        image.utm_hemisphere = utm_hemisphere
    if utm_datum is not None:
        image.utm_datum = utm_datum
    if project_x is not None:
        image.project_x = project_x
    if project_y is not None:
        image.project_y = project_y
    if project_z is not None:
        image.project_z = project_z

    image.object_type = 'image'

    db.commit()
    db.refresh(image)

    print(f"[COORDS] Updated image {image_id} coordinates: UTM({utm_easting},{utm_northing}), Project({project_x},{project_y},{project_z})")

    return {"message": "Coordinates updated", "image_id": image_id}

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
            "custom_tags": image.custom_tags.split(",") if image.custom_tags else [],
            "geo_latitude": image.geo_latitude,
            "geo_longitude": image.geo_longitude,
            "utm_easting": image.utm_easting,
            "utm_northing": image.utm_northing,
            "utm_zone": image.utm_zone,
            "utm_hemisphere": image.utm_hemisphere,
            "utm_datum": image.utm_datum,
            "project_x": image.project_x,
            "project_y": image.project_y,
            "project_z": image.project_z,
            "object_type": image.object_type or "image"
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
        raise HTTPException(status_code=404, detail="Image not found")

    db.delete(image)
    db.commit()
    return {"message": "Image deleted successfully"}

# Endpoints de incidencias
@app.post("/api/projects/{project_id}/incidents")
async def create_incident(
    project_id: int,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    incident_type: str = Form("defecto"),
    severity: str = Form("media"),
    geo_latitude: Optional[float] = Form(None),
    geo_longitude: Optional[float] = Form(None),
    utm_easting: Optional[float] = Form(None),
    utm_northing: Optional[float] = Form(None),
    utm_zone: Optional[int] = Form(None),
    utm_hemisphere: Optional[str] = Form(None),
    utm_datum: Optional[str] = Form("ETRS89"),
    project_x: Optional[float] = Form(None),
    project_y: Optional[float] = Form(None),
    project_z: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar proyecto
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Crear incidencia
    incident = Incident(
        title=title,
        description=description,
        incident_type=incident_type,
        severity=severity,
        project_id=project_id,
        geo_latitude=geo_latitude,
        geo_longitude=geo_longitude,
        utm_easting=utm_easting,
        utm_northing=utm_northing,
        utm_zone=utm_zone,
        utm_hemisphere=utm_hemisphere,
        utm_datum=utm_datum,
        project_x=project_x,
        project_y=project_y,
        project_z=project_z,
        object_type="incident"
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    print(f"Incidencia creada con ID: {incident.id}")
    print(f"Coordenadas: WGS84({geo_latitude},{geo_longitude}), UTM({utm_easting},{utm_northing})")

    return incident

@app.get("/api/projects/{project_id}/incidents")
def get_incidents(
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

    incidents = db.query(Incident).filter(Incident.project_id == project_id).all()
    return incidents

@app.put("/api/projects/{project_id}/incidents/{incident_id}")
async def update_incident(
    project_id: int,
    incident_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    incident_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    geo_latitude: Optional[float] = None,
    geo_longitude: Optional[float] = None,
    utm_easting: Optional[float] = None,
    utm_northing: Optional[float] = None,
    utm_zone: Optional[int] = None,
    utm_hemisphere: Optional[str] = None,
    utm_datum: Optional[str] = None,
    project_x: Optional[float] = None,
    project_y: Optional[float] = None,
    project_z: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar proyecto
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get incident
    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.project_id == project_id
    ).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Update fields
    if title is not None:
        incident.title = title
    if description is not None:
        incident.description = description
    if incident_type is not None:
        incident.incident_type = incident_type
    if severity is not None:
        incident.severity = severity
    if status is not None:
        incident.status = status
    if geo_latitude is not None:
        incident.geo_latitude = geo_latitude
    if geo_longitude is not None:
        incident.geo_longitude = geo_longitude
    if utm_easting is not None:
        incident.utm_easting = utm_easting
    if utm_northing is not None:
        incident.utm_northing = utm_northing
    if utm_zone is not None:
        incident.utm_zone = utm_zone
    if utm_hemisphere is not None:
        incident.utm_hemisphere = utm_hemisphere
    if utm_datum is not None:
        incident.utm_datum = utm_datum
    if project_x is not None:
        incident.project_x = project_x
    if project_y is not None:
        incident.project_y = project_y
    if project_z is not None:
        incident.project_z = project_z

    incident.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(incident)

    return incident

@app.delete("/api/projects/{project_id}/incidents/{incident_id}")
def delete_incident(
    project_id: int,
    incident_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    incident = db.query(Incident).filter(
        Incident.id == incident_id,
        Incident.project_id == project_id
    ).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    db.delete(incident)
    db.commit()
    return {"message": "Incident deleted successfully"}

# Endpoints de invitaciones
@app.get("/api/invitations/pending")
def get_pending_invitations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    invitations = db.query(Invitation).filter(
        Invitation.used == False,
        Invitation.expires_at > datetime.utcnow()
    ).all()
    return invitations

# ============================================================================
# ENDPOINT DE IMPORTACIÓN DE COORDENADAS
# ============================================================================

@app.post("/api/projects/{project_id}/import-coordinates")
async def import_coordinates(
    project_id: int,
    file: UploadFile = File(...),
    coordinate_type: str = Form(...),  # 'local', 'utm', 'geo'
    object_type: str = Form("foto360"),  # 'foto360', 'imagen', 'incidencia'
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Importa coordenadas desde archivo CSV/Excel/TXT

    Formato esperado del archivo:
    - Columnas: nombre_imagen, x, y, z (pueden variar nombres)
    - Separador: ; , tab (autodetección)

    coordinate_type:
      - 'local': Coordenadas locales del proyecto (X, Y, Z)
      - 'utm': Coordenadas UTM ETRS89 (Easting, Northing, Z)
      - 'geo': Coordenadas geográficas WGS84 (Latitud, Longitud, altitud)
    """
    if not COORDINATES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Coordinate import feature temporarily unavailable. Please contact support."
        )

    import io

    # Verificar proyecto
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        # Leer archivo
        content = await file.read()
        filename = file.filename.lower()

        # Parsear según extensión
        if filename.endswith('.csv') or filename.endswith('.txt'):
            # Intentar detectar separador
            text_content = content.decode('utf-8-sig')  # utf-8-sig ignora BOM

            # Detectar separador
            if ';' in text_content.split('\n')[0]:
                df = pd.read_csv(io.StringIO(text_content), sep=';')
            elif ',' in text_content.split('\n')[0]:
                df = pd.read_csv(io.StringIO(text_content), sep=',')
            else:
                df = pd.read_csv(io.StringIO(text_content), sep='\t')

        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = pd.read_excel(io.BytesIO(content))

        else:
            raise HTTPException(status_code=400, detail="Formato de archivo no soportado. Use CSV, TXT o Excel")

        # Normalizar nombres de columnas (quitar espacios, minúsculas)
        df.columns = df.columns.str.strip().str.lower()

        # Mapeo flexible de nombres de columnas
        column_mappings = {
            'nombre': ['nombre_imagen', 'nombre', 'imagen', 'filename', 'file', 'name', 'photo'],
            'x': ['x', 'easting', 'longitude', 'lon', 'lng', 'project_x'],
            'y': ['y', 'northing', 'latitude', 'lat', 'project_y'],
            'z': ['z', 'altura', 'elevation', 'altitud', 'height', 'project_z', 'cota'],
            'tipo': ['tipo', 'type', 'object_type', 'categoria']
        }

        # Encontrar columnas reales
        def find_column(df_columns, possible_names):
            for col in df_columns:
                if col in possible_names:
                    return col
            return None

        nombre_col = find_column(df.columns, column_mappings['nombre'])
        x_col = find_column(df.columns, column_mappings['x'])
        y_col = find_column(df.columns, column_mappings['y'])
        z_col = find_column(df.columns, column_mappings['z'])
        tipo_col = find_column(df.columns, column_mappings['tipo'])

        if not nombre_col:
            raise HTTPException(status_code=400, detail=f"No se encontró columna de nombre de imagen. Columnas disponibles: {list(df.columns)}")

        if not x_col or not y_col:
            raise HTTPException(status_code=400, detail=f"No se encontraron columnas X e Y. Columnas disponibles: {list(df.columns)}")

        # Procesar cada fila
        imported_count = 0
        updated_count = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                nombre_imagen = str(row[nombre_col]).strip()
                x_value = float(row[x_col])
                y_value = float(row[y_col])
                z_value = float(row[z_col]) if z_col and pd.notna(row[z_col]) else 0.0
                tipo_objeto = str(row[tipo_col]).strip() if tipo_col and pd.notna(row[tipo_col]) else object_type

                # Buscar foto/imagen existente por nombre
                photo = db.query(Photo).filter(
                    Photo.project_id == project_id,
                    Photo.title.contains(nombre_imagen)
                ).first()

                gallery_image = db.query(GalleryImage).filter(
                    GalleryImage.project_id == project_id,
                    GalleryImage.filename.contains(nombre_imagen)
                ).first()

                target = photo or gallery_image

                if target:
                    # Actualizar coordenadas según tipo
                    if coordinate_type == 'local':
                        target.project_x = x_value
                        target.project_y = y_value
                        target.project_z = z_value
                        target.coordinate_source = 'local'

                    elif coordinate_type == 'utm':
                        target.utm_easting = x_value
                        target.utm_northing = y_value
                        target.project_z = z_value
                        target.coordinate_source = 'utm'
                        # También calcular coordenadas locales (si hay origen definido)
                        # TODO: implementar transformación UTM -> Local

                    elif coordinate_type == 'geo':
                        target.geo_latitude = x_value
                        target.geo_longitude = y_value
                        target.project_z = z_value
                        target.coordinate_source = 'geo'
                        # También calcular UTM y Local
                        # TODO: implementar transformación Geo -> UTM -> Local

                    target.object_type = tipo_objeto
                    updated_count += 1
                else:
                    errors.append(f"Fila {idx + 2}: Imagen '{nombre_imagen}' no encontrada en el proyecto")

            except Exception as e:
                errors.append(f"Fila {idx + 2}: Error procesando - {str(e)}")

        db.commit()

        return {
            "message": "Importación completada",
            "imported": imported_count,
            "updated": updated_count,
            "total_rows": len(df),
            "errors": errors if errors else None,
            "coordinate_type": coordinate_type
        }

    except Exception as e:
        print(f"[ERROR] Failed to import coordinates: {e}")
        raise HTTPException(status_code=400, detail=f"Error al importar coordenadas: {str(e)}")

# ============================================================================
# ENDPOINTS DE TRANSFORMACIÓN Y POSICIONAMIENTO DE PROYECTO
# ============================================================================

@app.put("/api/projects/{project_id}/positioning")
async def update_project_positioning(
    project_id: int,
    map_origin_lat: float = Body(...),
    map_origin_lng: float = Body(...),
    map_rotation: float = Body(0.0),
    recalculate_coordinates: bool = Body(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza el origen y rotación del proyecto en el mapa

    Si recalculate_coordinates=True, recalcula todas las coordenadas:
    - Si las fotos tienen coordenadas locales → calcula UTM y Geo
    - Si las fotos tienen coordenadas UTM → recalcula locales
    """
    if not COORDINATES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Coordinate transformation feature temporarily unavailable."
        )

    # Verificar proyecto
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Actualizar origen y rotación
    project.map_origin_lat = map_origin_lat
    project.map_origin_lng = map_origin_lng
    project.map_rotation = map_rotation

    if recalculate_coordinates:
        transformer = CoordinateTransformer()

        # Obtener todas las fotos del proyecto
        photos = db.query(Photo).filter(Photo.project_id == project_id).all()
        gallery_images = db.query(GalleryImage).filter(GalleryImage.project_id == project_id).all()

        all_items = photos + gallery_images
        updated_count = 0

        for item in all_items:
            try:
                # Si tiene coordenadas locales, calcular UTM y Geo
                if item.project_x is not None and item.project_y is not None and item.coordinate_source == 'local':
                    utm = transformer.local_to_utm(
                        item.project_x,
                        item.project_y,
                        item.project_z or 0,
                        map_origin_lat,
                        map_origin_lng,
                        map_rotation
                    )
                    item.utm_easting = utm['utm_easting']
                    item.utm_northing = utm['utm_northing']
                    item.utm_zone = utm['utm_zone']
                    item.utm_hemisphere = utm['utm_hemisphere']
                    item.utm_datum = utm['utm_datum']

                    # También calcular coordenadas geográficas
                    geo = transformer.utm_to_geo(
                        utm['utm_easting'],
                        utm['utm_northing'],
                        utm['utm_zone']
                    )
                    item.geo_latitude = geo['geo_latitude']
                    item.geo_longitude = geo['geo_longitude']

                    updated_count += 1

                # Si tiene coordenadas UTM, recalcular locales
                elif item.utm_easting is not None and item.utm_northing is not None:
                    local = transformer.utm_to_local(
                        item.utm_easting,
                        item.utm_northing,
                        map_origin_lat,
                        map_origin_lng,
                        map_rotation
                    )
                    item.project_x = local['project_x']
                    item.project_y = local['project_y']

                    # También calcular coordenadas geográficas si no existen
                    if item.geo_latitude is None or item.geo_longitude is None:
                        geo = transformer.utm_to_geo(
                            item.utm_easting,
                            item.utm_northing,
                            item.utm_zone or 30
                        )
                        item.geo_latitude = geo['geo_latitude']
                        item.geo_longitude = geo['geo_longitude']

                    updated_count += 1

                # Si tiene coordenadas geográficas, calcular UTM y locales
                elif item.geo_latitude is not None and item.geo_longitude is not None:
                    utm = transformer.geo_to_utm(item.geo_latitude, item.geo_longitude)
                    item.utm_easting = utm['utm_easting']
                    item.utm_northing = utm['utm_northing']
                    item.utm_zone = utm['utm_zone']
                    item.utm_hemisphere = utm['utm_hemisphere']
                    item.utm_datum = utm['utm_datum']

                    local = transformer.utm_to_local(
                        utm['utm_easting'],
                        utm['utm_northing'],
                        map_origin_lat,
                        map_origin_lng,
                        map_rotation
                    )
                    item.project_x = local['project_x']
                    item.project_y = local['project_y']

                    updated_count += 1

            except Exception as e:
                print(f"[WARNING] Error transforming coordinates for item {item.id}: {e}")

        db.commit()
        print(f"[POSITIONING] Project {project_id} positioned at ({map_origin_lat}, {map_origin_lng}) rotation={map_rotation}°. {updated_count} items updated")

        return {
            "message": "Posicionamiento actualizado",
            "origin": {"lat": map_origin_lat, "lng": map_origin_lng},
            "rotation": map_rotation,
            "coordinates_recalculated": recalculate_coordinates,
            "items_updated": updated_count
        }

    db.commit()
    return {
        "message": "Posicionamiento actualizado",
        "origin": {"lat": map_origin_lat, "lng": map_origin_lng},
        "rotation": map_rotation,
        "coordinates_recalculated": False
    }

@app.post("/api/projects/{project_id}/recalculate-coordinates")
async def recalculate_all_coordinates(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Recalcula todas las coordenadas del proyecto basándose en el origen y rotación actuales

    Útil después de mover el proyecto en el mapa
    """
    if not COORDINATES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Coordinate recalculation feature temporarily unavailable."
        )

    # Verificar proyecto
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.map_origin_lat or not project.map_origin_lng:
        raise HTTPException(
            status_code=400,
            detail="El proyecto no tiene origen definido. Configura primero el posicionamiento."
        )

    transformer = CoordinateTransformer()

    # Obtener todas las fotos del proyecto
    photos = db.query(Photo).filter(Photo.project_id == project_id).all()
    gallery_images = db.query(GalleryImage).filter(GalleryImage.project_id == project_id).all()

    all_items = photos + gallery_images
    updated_count = 0
    errors = []

    for item in all_items:
        try:
            # Prioridad: local → UTM → geo
            if item.project_x is not None and item.project_y is not None:
                # Calcular desde locales
                utm = transformer.local_to_utm(
                    item.project_x,
                    item.project_y,
                    item.project_z or 0,
                    project.map_origin_lat,
                    project.map_origin_lng,
                    project.map_rotation
                )
                geo = transformer.utm_to_geo(utm['utm_easting'], utm['utm_northing'], utm['utm_zone'])

                item.utm_easting = utm['utm_easting']
                item.utm_northing = utm['utm_northing']
                item.utm_zone = utm['utm_zone']
                item.utm_hemisphere = utm['utm_hemisphere']
                item.utm_datum = utm['utm_datum']
                item.geo_latitude = geo['geo_latitude']
                item.geo_longitude = geo['geo_longitude']

                updated_count += 1

        except Exception as e:
            errors.append(f"Item {item.id}: {str(e)}")

    db.commit()

    return {
        "message": "Coordenadas recalculadas",
        "total_items": len(all_items),
        "updated": updated_count,
        "errors": errors if errors else None
    }

print("\n" + "=" * 60)
print("INICIANDO PHOTOSITE360 BACKEND")
print("=" * 60)
print(f"Cloudinary configurado: {cloudinary.config().cloud_name}")
print("Limpieza automatica activada")
print("Sistema de invitaciones activado")
print("Servidor en puerto: 5000")
print("CORS configurado para:")
print("   - http://localhost:5173 (local)")
print("   - https://photosite360-frontend.onrender.com (produccion)")
print("=" * 60 + "\n")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
