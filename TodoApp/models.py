# นำเข้า Base ซึ่งเป็นคลาสหลักของ SQLAlchemy
# ใช้สำหรับสร้างตารางจาก ORM model
from database import Base

# นำเข้า Column และชนิดข้อมูลของคอลัมน์
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey

# สร้างคลาส Todos ซึ่งเป็น ORM Model
# คลาสนี้จะถูก map กับตารางในฐานข้อมูล
class Todos(Base):
    # ชื่อตารางในฐานข้อมูล
    __tablename__ = 'todos'

    # คอลัมน์ id เป็น primary key
    id = Column(Integer, primary_key=True, index=True)

    # คอลัมน์ title เป็น String
    title = Column(String)

    # คอลัมน์ description เป็น String
    description = Column(String)

    # คอลัมน์ priority เป็น Integer
    complete = Column(Boolean, default=False)