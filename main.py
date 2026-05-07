from fastapi import FastAPI
from pydantic import BaseModel
from app.routers import appointments, doctors, patients  # 1. 라우터 파일 임포트

# 데이터 모델 정의
class AppointmentRequest(BaseModel):
    patient_id: str
    doctor_id: str
    date: str
    time: str

# 인스턴스 생성
app = FastAPI()

#라우터 등록
app.include_router(appointments.router)
app.include_router(doctors.router)
app.include_router(patients.router)

@app.get("/")
def home():
    return {"status": "success", "message": "FastAPI 서버가 정상 작동 중입니다."}