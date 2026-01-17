# ใช้สำหรับโยน error HTTP กลับไปยัง client
from fastapi.exceptions import HTTPException

# ใช้จัดการเรื่องเวลา (อายุของ token)
from datetime import timedelta, datetime, timezone

# ใช้สำหรับ type hint ของ dependency
from typing import Annotated

# APIRouter ใช้แยก route ออกเป็นโมดูล
# Depends ใช้ dependency injection
from fastapi import APIRouter, Depends

# ใช้สร้าง schema สำหรับรับ–ส่งข้อมูล
from pydantic import BaseModel

# Session สำหรับเชื่อมต่อฐานข้อมูลด้วย SQLAlchemy
from sqlalchemy.orm import Session

# ใช้กำหนด HTTP status code
from starlette import status

# ใช้สร้าง session ฐานข้อมูล
from database import SessionLocal

# Model ตาราง Users
from models import Users

# ใช้ hash และตรวจสอบรหัสผ่าน
from passlib.context import CryptContext

# OAuth2PasswordRequestForm ใช้รับ username/password ตอน login
# OAuth2PasswordBearer ใช้ดึง token จาก Authorization Header
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

# ใช้สร้าง / ตรวจสอบ JWT
from jose import jwt, JWTError


# สร้าง router สำหรับ auth
# prefix="/auth" → ทุก endpoint จะขึ้นต้นด้วย /auth
# tags ใช้จัดกลุ่มใน Swagger UI
router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)



# Secret key สำหรับเข้ารหัส JWT (ควรเก็บใน .env)
SECRET_KEY = "dfa06fee632f336a6e6a8924a1c8a0ffe55d9caf0d41b959875b229db6b12d82"

# อัลกอริทึมที่ใช้เข้ารหัส
ALGORITHM = "HS256"



# ตั้งค่า bcrypt สำหรับ hash password
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# กำหนดรูปแบบ OAuth2 Bearer Token
# tokenUrl="auth/token" คือ endpoint ที่ใช้ขอ token
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")



# Schema สำหรับรับข้อมูลสมัครสมาชิก
class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str


# Schema สำหรับ response ตอน login
class Token(BaseModel):
    access_token: str
    token_type: str


# ฟังก์ชันสร้าง database session
def get_db():
    db = SessionLocal()
    try:
        yield db       # ส่ง session ให้ endpoint
    finally:
        db.close()     # ปิด session หลังใช้งาน


# Dependency สำหรับ database
db_dependency = Annotated[Session, Depends(get_db)]



# ตรวจสอบ username และ password
def authenticate_user(username: str, password: str, db):
    # ค้นหาผู้ใช้จาก username
    user = db.query(Users).filter(Users.username == username).first()

    # ถ้าไม่พบ user
    if not user:
        return False

    # ตรวจสอบรหัสผ่านกับค่าที่ hash ไว้
    if not bcrypt_context.verify(password, user.hashed_password):
        return False

    # ถ้าถูกต้อง ส่งข้อมูล user กลับ
    return user


# สร้าง JWT access token
def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    # payload ที่จะใส่ใน token
    encode = {
        "sub": username,  # subject (username)
        "id": user_id     # user id
    }

    # เวลาหมดอายุของ token
    expire = datetime.now(timezone.utc) + expires_delta
    encode.update({"exp": expire})

    # เข้ารหัส JWT
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


# ใช้ดึงข้อมูล user ปัจจุบันจาก token
async def get_current_user(
        token: Annotated[str, Depends(oauth2_bearer)]
    ):
    try:
        # ถอดรหัส JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # ดึงข้อมูลจาก payload
        username: str = payload.get("sub")
        user_id: int = payload.get("id")

        # ถ้าข้อมูลไม่ครบ
        if username is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user."
            )

        # ส่งข้อมูล user กลับ
        return {"username": username, "id": user_id}

    # ถ้า token ไม่ถูกต้องหรือหมดอายุ
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate user."
        )


# Endpoint สมัครสมาชิก
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(
        db: db_dependency,
        create_user_request: CreateUserRequest
    ):

    # สร้าง object Users
    create_user_model = Users(
        email=create_user_request.email,
        username=create_user_request.username,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        role=create_user_request.role,

        # hash password ก่อนเก็บ
        hashed_password=bcrypt_context.hash(create_user_request.password),
        is_active=True
    )

    # บันทึกลง database
    db.add(create_user_model)
    db.commit()


# Endpoint login เพื่อรับ JWT
@router.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: db_dependency
    ):

    # ตรวจสอบ username/password
    user = authenticate_user(form_data.username, form_data.password, db)

    # ถ้า login ไม่ผ่าน
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate user."
        )

    # สร้าง token (อายุ 20 นาที)
    token = create_access_token(
        user.username,
        user.id,
        timedelta(minutes=20)
    )

    # ส่ง token กลับ
    return {
        "access_token": token,
        "token_type": "bearer"
    }
