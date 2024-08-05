from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://root:0000@8000:port/Ram")  # Cambia estos valores

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password = Column(String(255))

class Medication(Base):
    __tablename__ = "medications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    activity = Column(String(255), nullable=False)
    volume = Column(String(50), nullable=False)
    preparation_date = Column(DateTime, nullable=False)
    batch_number = Column(String(100), nullable=False)
    expiration_date = Column(DateTime, nullable=False)

Base.metadata.create_all(bind=engine)

# FastAPI app setup
app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia esto según sea necesario
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class MedicationCreate(BaseModel):
    name: str
    activity: str
    volume: str
    preparationDate: str  # Change to str to accept date in text format
    batchNumber: str
    expirationDate: str  # Change to str to accept date in text format

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoints

# Registro de usuario
@app.post("/users/", response_model=UserCreate)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(email=user.email, password=user.password)
    db.add(db_user)
    try:
        db.commit()
        db.refresh(db_user)
    except IntegrityError as e:
        db.rollback()
        if "unique constraint" in str(e.orig):
            raise HTTPException(status_code=400, detail="Email already registered")
        raise HTTPException(status_code=400, detail=f"Integrity Error: {str(e.orig)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected Error: {str(e)}")
    return {"email": db_user.email}

# Inicio de sesión
@app.post("/login/")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email, User.password == user.password).first()
    if not db_user:
        raise HTTPException(status_code=400, detail="Invalid email or password")
    return {"message": "Login successful", "email": db_user.email}

# Registro de medicamento
@app.post("/medications/")
def create_medication(medication: MedicationCreate, db: Session = Depends(get_db)):
    try:
        # Convert strings to datetime objects
        preparation_date = datetime.strptime(medication.preparationDate, "%Y-%m-%d %H:%M:%S")
        expiration_date = datetime.strptime(medication.expirationDate, "%Y-%m-%d")

        db_medication = Medication(
            name=medication.name,
            activity=medication.activity,
            volume=medication.volume,
            preparation_date=preparation_date,
            batch_number=medication.batchNumber,
            expiration_date=expiration_date
        )
        db.add(db_medication)
        db.commit()
        db.refresh(db_medication)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Date format error: {str(e)}")
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Integrity Error: {str(e.orig)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected Error: {str(e)}")
    return {"message": "Medication registered successfully", "medication": db_medication.id"}

# Obtener todos los medicamentos
@app.get("/medications/")
def read_medications(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    medications = db.query(Medication).offset(skip).limit(limit).all()
    return medications
