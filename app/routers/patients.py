from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.db import supabase
from datetime import datetime

router = APIRouter(prefix="/patients", tags=["patients"])

class PatientCreate(BaseModel):
    name: str
    phone: str
    pin: str

def format_phone_number(phone: str) -> str:
    # 1. 숫자만 추출
    clean_number = "".join(filter(str.isdigit, phone))
    
    if len(clean_number) != 11:
        raise ValueError("전화번호는 하이픈 제외 11자리 숫자여야 합니다.")
        
    # 3. 포맷팅하여 반환
    return f"{clean_number[:3]}-{clean_number[3:7]}-{clean_number[7:]}"

# 1. 환자 최초 등록
@router.post("/register")
def register_patient(data: PatientCreate):
    try:
        # [1] 번호 변환 시도
        formatted_phone = format_phone_number(data.phone)
    except ValueError as e:
        # 11자리가 아닐 경우 400 에러 발생
        raise HTTPException(status_code=400, detail=str(e))
    
    # [2] 중복 가입 방지
    existing = supabase.table("patients").select("id").eq("phone", formatted_phone).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="이미 등록된 전화번호입니다.")

    # [3] 데이터 저장
    new_patient = {
        "name": data.name,
        "phone": formatted_phone,
        "pin": data.pin
    }
    res = supabase.table("patients").insert(new_patient).execute()
    
    return {
        "status": "success", 
        "message": "환자 등록 성공!", 
        "data": {"name": data.name, "phone": formatted_phone}
    }

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