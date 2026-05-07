from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.db import supabase

router = APIRouter(prefix="/appointments", tags=["appointments"])

# 예약 생성을 위한 데이터 모델
class AppointmentCreate(BaseModel):
    phone: str       # 환자 휴대폰 번호
    pin: str         # 환자 PIN 번호
    doctor_id: int   # 예약할 의사 ID
    reserved_at: str  # 예) "2026-05-07 14:30"

@router.post("/register")
def register_appointment(data: AppointmentCreate):
    # [1] 환자 본인 확인
    patient_res = supabase.table("patients") \
        .select("id", "name") \
        .eq("phone", data.phone) \
        .eq("pin", data.pin) \
        .execute()

    if not patient_res.data:
        raise HTTPException(status_code=401, detail="환자 인증에 실패했습니다. 번호와 PIN을 확인해주세요.")

    patient_id = patient_res.data[0]['id']
    patient_name = patient_res.data[0]['name']

    # [2] 중복 예약 방지 체크 (해당 의사의 해당 시간에 이미 예약이 있는지)
    existing_check = supabase.table("appointments") \
        .select("id") \
        .eq("doctor_id", data.doctor_id) \
        .eq("appointment_date", data.date) \
        .eq("appointment_time", data.time) \
        .execute()
    
    if existing_check.data:
        raise HTTPException(status_code=400, detail="이미 예약이 완료된 시간대입니다.")

    try:
        # [3] appointments 테이블에 예약 기록 추가
        new_appointment = {
            "patient_id": patient_id,
            "doctor_id": data.doctor_id,
            "appointment_date": data.date,
            "appointment_time": data.time,
            "status": "confirmed"
        }
        supabase.table("appointments").insert(new_appointment).execute()

        # [4] patients 테이블의 예약 정보 업데이트 (Update reserved_at)
        reserved_at_combined = f"{data.date} {data.time}"
        supabase.table("patients").update({
            "reserved_at": reserved_at_combined,
            "reserved_doctor_id": data.doctor_id
        }).eq("id", patient_id).execute()

        return {
            "status": "success",
            "message": f"{patient_name}님, {reserved_at_combined}에 예약이 확정되었습니다."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예약 처리 중 오류 발생: {str(e)}")