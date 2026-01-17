# ใช้สำหรับกำหนด type ของ dependency (FastAPI)
from typing import Annotated

# BaseModel ใช้สร้าง schema รับ–ส่งข้อมูล
# Field ใช้กำหนดเงื่อนไข validation ของข้อมูล
from pydantic import BaseModel, Field

# Session สำหรับเชื่อมต่อฐานข้อมูลด้วย SQLAlchemy
from sqlalchemy.orm import Session

# APIRouter ใช้แยก route เป็นโมดูล
# Depends ใช้สำหรับ dependency injection
# HTTPException ใช้โยน error กลับ client
# Path ใช้ validate path parameter
from fastapi import APIRouter, Depends, HTTPException, Path

# ใช้กำหนด HTTP status code
import starlette.status as status

# Model ตาราง Todos
from models import Todos

# engine ใช้สร้างตาราง (ถ้าจำเป็น)
# SessionLocal ใช้สร้าง session database
from database import engine, SessionLocal

# router สำหรับ auth (ยังไม่ได้ใช้งานในไฟล์นี้)
from routers import auth


# สร้าง router สำหรับ todo
router = APIRouter()


# ฟังก์ชันเชื่อมต่อฐานข้อมูล
def get_db():
    db = SessionLocal()
    try:
        yield db      # ส่ง session ให้ endpoint ใช้งาน
    finally:
        db.close()    # ปิด session หลังใช้งานเสร็จ


# สร้าง dependency สำหรับ database
db_dependency = Annotated[Session, Depends(get_db)]


# Schema สำหรับรับข้อมูล Todo จาก request body
class TodoRequest(BaseModel):
    # หัวข้อ ต้องยาวอย่างน้อย 3 ตัวอักษร
    title: str = Field(min_length=3)

    # รายละเอียด ต้องยาว 3–100 ตัวอักษร
    description: str = Field(min_length=3, max_length=100)

    # ลำดับความสำคัญ ต้องอยู่ระหว่าง 1–5
    priority: int = Field(gt=0, lt=6)

    # สถานะเสร็จหรือยัง
    complete: bool


# ดึง todo ทั้งหมด
@router.get("/", status_code=status.HTTP_200_OK)
async def read_all(db: db_dependency):
    # query ข้อมูล todos ทั้งหมดจาก database
    return db.query(Todos).all()


# ดึง todo ตาม id
@router.get("/todo/{todo_id}", status_code=status.HTTP_200_OK)
async def read_todo(
        db: db_dependency,
        todo_id: int = Path(gt=0)   # todo_id ต้องมากกว่า 0
    ):

    # ค้นหา todo ตาม id
    todo_model = db.query(Todos).filter(Todos.id == todo_id).first()

    # ถ้าพบ ส่งข้อมูลกลับ
    if todo_model is not None:
        return todo_model

    # ถ้าไม่พบ ส่ง error 404
    raise HTTPException(status_code=404, detail="Todo not found.")


# เพิ่ม todo ใหม่
@router.post("/todo", status_code=status.HTTP_201_CREATED)
async def create_todo(
        db: db_dependency,
        todo_request: TodoRequest
    ):

    # แปลงข้อมูลจาก Pydantic → SQLAlchemy model
    todo_model = Todos(**todo_request.model_dump())

    # เพิ่มข้อมูลลง database
    db.add(todo_model)
    db.commit()


# แก้ไข todo ตาม id
@router.put("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_todo(
        db: db_dependency,
        todo_id: int,
        todo_request: TodoRequest
    ):

    # ค้นหา todo ที่ต้องการแก้ไข
    todo_model = db.query(Todos).filter(Todos.id == todo_id).first()

    # ถ้าไม่พบ todo
    if todo_model is None:
        raise HTTPException(status_code=404, detail="Todo not found.")

    # อัปเดตข้อมูลทีละฟิลด์
    todo_model.title = todo_request.title
    todo_model.description = todo_request.description
    todo_model.priority = todo_request.priority
    todo_model.complete = todo_request.complete

    # บันทึกการแก้ไข
    db.add(todo_model)
    db.commit()


# ลบ todo ตาม id
@router.delete("/todo/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
        db: db_dependency,
        todo_id: int = Path(gt=0)
    ):

    # ค้นหา todo ก่อนลบ
    todo_model = db.query(Todos).filter(Todos.id == todo_id).first()

    # ถ้าไม่พบ
    if todo_model is None:
        raise HTTPException(status_code=404, detail="Todo not found.")

    # ลบข้อมูลจาก database
    db.query(Todos).filter(Todos.id == todo_id).delete()
    db.commit()
