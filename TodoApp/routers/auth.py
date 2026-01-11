
from datetime import timedelta, datetime, timezone # ใช้จัดการเรื่องเวลา (อายุของ token)
from typing import Annotated # ใช้กำหนด type hint แบบพิเศษ (FastAPI dependency)
from fastapi import APIRouter, Depends # APIRouter ใช้แยก route ออกเป็นโมดูล
                                        # Depends ใช้สำหรับ Dependency Injection
from pydantic import BaseModel # BaseModel ใช้สร้าง schema สำหรับรับข้อมูลจาก request
from sqlalchemy.orm import Session # Session สำหรับติดต่อฐานข้อมูลด้วย SQLAlchemy
from starlette import status # ใช้กำหนด HTTP status code
from database import SessionLocal # สร้าง session ของฐานข้อมูล
from models import Users # Model ตาราง Users
from passlib.context import CryptContext # ใช้เข้ารหัสและตรวจสอบรหัสผ่าน
from fastapi.security import OAuth2PasswordRequestForm # ใช้รับข้อมูล login (username, password) แบบ OAuth2
from jose import jwt # ใช้สร้างและถอดรหัส JWT

router = APIRouter() # สร้าง router สำหรับ auth

SECRET_KEY = "add30ad7d74809732d22a7b24152714a97bc2d6410f346b8a78853c32db5f72d" # คีย์ลับสำหรับเข้ารหัส JWT (ควรเก็บใน .env)

ALGORITHM = "HS256" # อัลกอริทึมที่ใช้เข้ารหัส JWT

# กำหนดวิธี hash รหัสผ่านด้วย bcrypt
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Schema สำหรับรับข้อมูลตอนสมัครสมาชิก
class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str

# ฟังก์ชันเชื่อมต่อฐานข้อมูล
def get_db():
    db = SessionLocal()
    try:
        yield db        # ส่ง session ให้ endpoint ใช้งาน
    finally:
        db.close()      # ปิดการเชื่อมต่อเมื่อเสร็จงาน

# สร้าง dependency ของ database
db_dependency = Annotated[Session, Depends(get_db)]

# ตรวจสอบ username และ password
def authenticate_user(username: str, password: str, db):
    # ค้นหาผู้ใช้จาก username
    user = db.query(Users).filter(Users.username == username).first()

    # ถ้าไม่พบ user
    if not user:
        return False

    # ตรวจสอบรหัสผ่านกับ hashed_password
    if not bcrypt_context.verify(password, user.hashed_password):
        return False

    # ถ้าถูกต้อง ส่งข้อมูล user กลับ
    return user


# สร้าง JWT access token
def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    # ข้อมูลที่จะเข้ารหัสใน token
    encode = {"sub": username, "id": user_id}

    # เวลาหมดอายุของ token
    expire = datetime.now(timezone.utc) + expires_delta
    encode.update({"exp": expire})

    # เข้ารหัส JWT
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


# Endpoint สมัครสมาชิก
@router.post("/auth", status_code=status.HTTP_201_CREATED)
async def create_user(
        db: db_dependency,
        create_user_request: CreateUserRequest
    ):

    # สร้าง object Users จากข้อมูลที่รับมา
    create_user_model = Users(
        email=create_user_request.email,
        username=create_user_request.username,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        role=create_user_request.role,

        # hash รหัสผ่านก่อนเก็บลงฐานข้อมูล
        hashed_password=bcrypt_context.hash(create_user_request.password),
        is_active=True
    )

    # เพิ่มข้อมูลลง database
    db.add(create_user_model)
    db.commit()


# Endpoint login เพื่อรับ token
@router.post("/token")
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: db_dependency
    ):

    # ตรวจสอบ username และ password
    user = authenticate_user(form_data.username, form_data.password, db)

    # ถ้า login ไม่ผ่าน
    if not user:
        return "failed Authentication"

    # สร้าง access token (หมดอายุ 20 นาที)
    token = create_access_token(
        user.username,
        user.id,
        timedelta(minutes=20)
    )

    # ส่ง token กลับไปให้ client
    return token
