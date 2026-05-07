from fastapi import FastAPI
from pydantic import BaseModel
from app.db import supabase
from app.routers import appointments, doctors, patients  # 1. router 임포트
from fastapi.middleware.cors import CORSMiddleware
from app.services.chatbot import ask_chatbot

# 데이터 모델 정의
class AppointmentRequest(BaseModel):
    patient_id: str
    doctor_id: str
    date: str
    time: str

# 인스턴스 생성
app = FastAPI()

# CORS 설정: 프론트엔드 접속 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인에서의 접속을 허용 (가장 강력함)
    allow_credentials=False, # allow_origins가 "*"일 때는 False로 하는 게 안전합니다
    allow_methods=["*"],
    allow_headers=["*"],
)

#라우터 등록
app.include_router(appointments.router)
app.include_router(doctors.router)
app.include_router(patients.router)

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    print("🔥 API 요청:", request.message)
    reply = ask_chatbot(request.message)
    return {"reply": reply}

@app.get("/")
def home():
    return {"status": "success", "message": "FastAPI 서버가 정상 작동 중입니다."}