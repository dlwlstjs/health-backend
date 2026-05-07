from pydantic import BaseModel

#데이터 요청
class AppointmentRequest(BaseModel):
    patient_id: str
    doctor_id: str
    date: str
    time: str