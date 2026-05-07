from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.db import supabase
from datetime import datetime

router = APIRouter(prefix="/patients", tags=["patients"])

class PatientCreate(BaseModel):
    name: str
    phone: str
    pin: str

# 1. 환자 최초 등록
@router.post("/register")
def register_patient(data: PatientCreate):
    # 중복 가입 방지
    existing = supabase.table("patients").select("id").eq("phone", data.phone).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="이미 등록된 전화번호입니다.")

    new_patient = {
        "name": data.name,
        "phone": data.phone,
        "pin": data.pin,
        "reserved_at": None,
        "reserved_doctor_id": None
    }
    res = supabase.table("patients").insert(new_patient).execute()
    return {"status": "success", "message": "환자 등록 성공!", "data": res.data}

@router.get("/check-reservation")
def check_reservation(
    phone: str = Query(..., description="환자 휴대폰 번호"),
    pin: str = Query(..., description="PIN 번호")
):
    try:
        # [1] 환자 인증
        p_res = supabase.table("patients").select("id", "name").eq("phone", phone).eq("pin", pin).execute()
        
        if not p_res.data:
            raise HTTPException(status_code=401, detail="인증 실패: 정보를 확인해주세요.")
        
        patient_id = p_res.data[0]['id']
        patient_name = p_res.data[0]['name']

        # doctor_id(name, department) -> doctor_id 외래키를 타고 doctors 테이블의 정보를 가져옴
        a_res = supabase.table("appointments") \
            .select("reserved_at, doctors(name, department)") \
            .eq("patient_id", patient_id) \
            .execute()

        if not a_res.data:
            return {
                "status": "success",
                "message": f"{patient_name}님, 예약 내역이 없습니다."
            }

        appointment = a_res.data[0]
        doctor_info = appointment.get("doctors", {})

        return {
            "status": "success",
            "data": {
                "환자명": patient_name,
                "진료과": doctor_info.get("department", "정보 없음"),
                "의사명": doctor_info.get("name", "정보 없음"),
                "예약시간": appointment.get("reserved_at")
            }
        }

    except Exception as e:
        print(f"조회 상세 에러: {e}")
        raise HTTPException(status_code=500, detail="정보를 불러오는 중 오류가 발생했습니다.")