from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.db import supabase

router = APIRouter(prefix="/appointments", tags=["appointments"])

class AppointmentCreate(BaseModel):
    phone: str
    pin: str
    doctor_id: str
    reserved_at: str # "2026-05-07 14:30"

@router.post("/register")
def register_appointment(data: AppointmentCreate):
    # [1] 환자 인증 및 UUID 확보
    patient_res = supabase.table("patients").select("id").eq("phone", data.phone).eq("pin", data.pin).execute()
    if not patient_res.data:
        raise HTTPException(status_code=401, detail="인증 실패")

    p_id = patient_res.data[0]['id']

    # [2] 중복 예약 체크
    existing = supabase.table("appointments") \
        .select("id") \
        .eq("doctor_id", data.doctor_id) \
        .eq("reserved_at", data.reserved_at) \
        .execute()
    
    if existing.data:
        raise HTTPException(status_code=400, detail="이미 예약된 시간대입니다.")

    # [3] 데이터 삽입
    supabase.table("appointments").insert({
        "patient_id": p_id,
        "doctor_id": data.doctor_id,
        "reserved_at": data.reserved_at
    }).execute()

    # [4] 환자 테이블 상태 업데이트
    supabase.table("patients").update({
        "reserved_at": data.reserved_at,
        "reserved_doctor_id": data.doctor_id
    }).eq("id", p_id).execute()

    return {"status": "success", "message": "예약 완료"}

@router.delete("/cancel")
def cancel_appointment(
    phone: str = Query(..., description="환자 휴대폰 번호"),
    pin: str = Query(..., description="PIN 번호")
):
    # [1] 환자 인증 (Phone + PIN)
    patient_res = supabase.table("patients") \
        .select("id") \
        .eq("phone", phone) \
        .eq("pin", pin) \
        .execute()

    if not patient_res.data:
        raise HTTPException(status_code=401, detail="인증 실패: 정보를 확인해주세요.")

    patient_id = patient_res.data[0]['id']

    # [2] 실제 예약 데이터 존재 여부 확인
    appointment_check = supabase.table("appointments") \
        .select("id") \
        .eq("patient_id", patient_id) \
        .execute()
    
    if not appointment_check.data:
        raise HTTPException(status_code=404, detail="취소할 예약 내역이 없습니다.")

    try:
        # [3] appointments 테이블에서 데이터 삭제
        supabase.table("appointments") \
            .delete() \
            .eq("patient_id", patient_id) \
            .execute()

        # [4] patients 테이블의 예약 정보 초기화
        supabase.table("patients").update({
            "reserved_at": None,
            "reserved_doctor_id": None
        }).eq("id", patient_id).execute()

        return {"status": "success", "message": "예약이 성공적으로 삭제 및 초기화되었습니다."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"취소 처리 중 오류 발생: {str(e)}")