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

# 환자의 예약 정보 조회
@router.get("/check-reservation")
def check_reservation(
    phone: str = Query(..., description="환자 휴대폰 번호 (숫자만 입력 가능)"),
    pin: str = Query(..., description="PIN 번호")
):
    try:
        # [1] 입력받은 번호를 DB 형식으로 변환
        try:
            formatted_phone = format_phone_number(phone)
        except ValueError as e:
            # 11자리가 아니면 에러 반환
            raise HTTPException(status_code=400, detail=str(e))

        # [2] 변환된 전화번호와 pin번호로 환자 인증
        p_res = supabase.table("patients") \
            .select("id", "name") \
            .eq("phone", formatted_phone) \
            .eq("pin", pin) \
            .execute()
        
        if not p_res.data:
            raise HTTPException(status_code=401, detail="인증 실패: 정보를 확인해주세요.")
        
        patient_id = p_res.data[0]['id']
        patient_name = p_res.data[0]['name']

        # [3] appointments 조회 + doctors 정보 조인
        a_res = supabase.table("appointments") \
            .select("reserved_at, doctors(name, department)") \
            .eq("patient_id", patient_id) \
            .execute()

        if not a_res.data:
            return {
                "status": "success",
                "message": f"{patient_name}님, 현재 예약된 내역이 없습니다."
            }

        appointment = a_res.data[0]
        doctor_info = appointment.get("doctors", {})

        return {
            "status": "success",
            "data": {
                "환자명": patient_name,
                "진료과": doctor_info.get("department"),
                "의사명": doctor_info.get("name"),
                "예약시간": appointment.get("reserved_at")
            }
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"조회 에러: {e}")
        raise HTTPException(status_code=500, detail="서버 내부 오류")