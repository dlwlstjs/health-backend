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
    # 중복 가입 방지 (휴대폰 번호 기준)
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

# 2. 본인 예약 정보 확인 (Phone + PIN 동시 일치)
@router.get("/check-reservation")
def check_reservation(
    phone: str = Query(..., description="휴대폰 번호"),
    pin: str = Query(..., description="4자리 PIN")
):
    res = supabase.table("patients") \
        .select("name, reserved_at, reserved_doctor_id") \
        .eq("phone", phone) \
        .eq("pin", pin) \
        .execute()

    if not res.data:
        raise HTTPException(status_code=401, detail="휴대폰 번호 또는 PIN 번호가 일치하지 않습니다.")

    patient_info = res.data[0]
    
    if not patient_info['reserved_at']:
        return {"name": patient_info['name'], "has_reservation": False, "message": "예약 내역이 없습니다."}

    return {
        "status": "success",
        "name": patient_info['name'],
        "reserved_at": patient_info['reserved_at'],
        "doctor_id": patient_info['reserved_doctor_id']
    }

# 3. 예약 취소 API (본인 확인 후 예약 삭제)
@router.delete("/cancel-reservation")
def cancel_reservation(
    phone: str = Query(..., description="휴대폰 번호"), 
    pin: str = Query(..., description="PIN 번호")
):
    # [1] 본인 확인
    res = supabase.table("patients") \
        .select("id") \
        .eq("phone", phone) \
        .eq("pin", pin) \
        .execute()

    if not res.data:
        raise HTTPException(status_code=401, detail="인증 실패: 정보를 다시 확인해주세요.")

    patient_id = res.data[0]['id']

    # [2] appointments 테이블에서 데이터 삭제
    delete_res = supabase.table("appointments") \
        .delete() \
        .eq("patient_id", patient_id) \
        .execute()

    # [3] patients 테이블의 reserved_at 초기화
    supabase.table("patients") \
        .update({
            "reserved_at": None,
            "reserved_doctor_id": None
        }) \
        .eq("id", patient_id) \
        .execute()

    return {
        "status": "success", 
        "message": "예약이 데이터베이스에서 완전히 삭제되었습니다."
    }