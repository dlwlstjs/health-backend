from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.db import supabase

router = APIRouter(prefix="/doctors", tags=["doctors"])

# 의사 데이터 모델 (docs에서 입력할 때 쓰임)
class DoctorCreate(BaseModel):
    name: str
    department: str
    consult_time: int
    off_days: Optional[List[str]] = []
    work_start: str = "09:00:00"
    work_end: str = "18:00:00"
    special_note: Optional[List[str]] = []

# 의사 등록 API
@router.post("/")
def create_doctor(doc: DoctorCreate):
    try:
        res = supabase.table("doctors").insert({
            "name": doc.name,
            "department": doc.department,
            "off_days": doc.off_days,
            "work_start": doc.work_start,
            "work_end": doc.work_end,
            "special_note": doc.special_note,
            "consult_time": doc.consult_time
        }).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 의사 목록 조회 API (확인용)
@router.get("/")
def get_doctors():
    res = supabase.table("doctors").select("*").execute()
    return res.data