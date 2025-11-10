from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
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

# Configuración
SECRET_KEY = "tu_clave_secreta_super_segura_cambiala_en_produccion"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configuración de Cloudinary
cloudinary.config(
    cloud_name="dryuzad8w",
    api_key="281976991233177",
    api_secret="oVv51LHUFYrmmux8oFuU0t-836s",
    secure=True
)

# Base de datos
import os
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./photosite360.db")

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

# ✅ NUEVOS MODELOS PARA GALERÍA
class GalleryImage(Base):
    __tablename__ = "gallery_images"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    url = Column(String)  # URL de Cloudinary
    unique_url = Column(String, unique=True)  # URL única para compartir
    file_size = Column(Integer)
    mime_type = Column(String)
    project_id = Column(Integer, ForeignKey("projects.id"))
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    
    # Metadatos estructurados para el nuevo sistema de etiquetas
    image_type = Column(String, default="edification")  # 'edification' o 'linear'
    level = Column(String, nullable=True)    # P00, P01, etc.
    room = Column(String, nullable=True)     # Salon, Cocina, etc.  
    pk_value = Column(String, nullable=True) # 0+000, 1+250, etc.
    section = Column(String, nullable=True)  # Tramo-A, etc.
    custom_tags = Column(String, nullable=True)  # JSON string de tags personalizados
    
    project = relationship("Project")
    uploader = relationship("User")

class GalleryTag(Base):
    __tablename__ = "gallery_tags"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    tag_type = Column(String)  # 'level', 'room', 'pk', 'section', 'custom'
    tag_value = Column(String)
    tag_color = Column(String, default='#3b82f6')
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    project = relationship("Project")
    creator = relationship("User")

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

# CORS - CONFIGURACIÓN COMPLETA QUE SÍ FUNCIONA
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware adicional para CORS
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
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

# ✅ MODELOS PYDANTIC PARA GALERÍA (DEFINIDOS ANTES DE USARSE)
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

# Rutas de autenticación
@app.post("/api/auth/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": db_user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name
    }

# Rutas de proyectos
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
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

# Rutas de fotos
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
    
    db.delete(photo)
    db.commit()
    return {"message": "Photo deleted successfully"}

# ✅ ENDPOINTS PARA GALERÍA DE IMÁGENES NORMALES
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
        
        # Leer archivo
        contents = await file.read()
        
        # Subir a Cloudinary
        upload_result = cloudinary.uploader.upload(
            contents,
            folder=f"photosite360/gallery/project_{project_id}",
            public_id=f"gallery_{datetime.utcnow().timestamp()}_{file.filename}",
            resource_type="image"
        )
        
        cloudinary_url = upload_result['secure_url']
        print(f"✓ Imagen subida exitosamente: {cloudinary_url}")
        
        # Generar URL única
        unique_url = f"gallery_{project_id}_{datetime.utcnow().timestamp()}_{file.filename}"
        
        # Procesar custom_tags si existen
        processed_custom_tags = None
        if custom_tags:
            try:
                tags_list = [tag.strip() for tag in custom_tags.split(",") if tag.strip()]
                processed_custom_tags = ",".join(tags_list)
            except:
                processed_custom_tags = custom_tags
        
        # Crear registro en BD
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
    
    # Convertir custom_tags de string a lista
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
    
    # Opcional: Eliminar también de Cloudinary
    try:
        public_id = image.url.split('/')[-1].split('.')[0]
        cloudinary.uploader.destroy(public_id)
        print(f"✓ Imagen eliminada de Cloudinary: {public_id}")
    except Exception as e:
        print(f"⚠️ No se pudo eliminar de Cloudinary: {e}")
    
    db.delete(image)
    db.commit()
    return {"message": "Gallery image deleted successfully"}

# Endpoints para etiquetas de galería
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
    
    # Verificar si ya existe
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
    
    # Actualizar campos proporcionados
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

# RUTAS PÚBLICAS
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

# Ruta raíz
@app.get("/")
def root():
    return {"message": "PhotoSite360 API - Server running"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)