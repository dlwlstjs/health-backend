from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta, time
from app.db import supabase

router = APIRouter(prefix="", tags=["appointments"])

def calculate_slots(doctor, existing_appointments):
    
    # 의사 1명의 하루 가용 슬롯을 계산하는 로직
    slots = []
    # 문자열로 들어온 시간(09:00:00)을 파이썬 시간 객체로 변환
    curr = datetime.strptime(doctor['work_start'], "%H:%M:%S").time()
    end = datetime.strptime(doctor['work_end'], "%H:%M:%S").time()
    
    # datetime으로 변환해서 계산 편하게 하기 (날짜는 오늘로 가정)
    now = datetime.combine(datetime.today(), curr)
    day_end = datetime.combine(datetime.today(), end)
    lunch_start = time(12, 0)
    lunch_end = time(13, 0)

    patient_count = 0
    
    while now + timedelta(minutes=doctor['consult_time']) <= day_end:
        # 점심시간 통과
        if lunch_start <= now.time() < lunch_end:
            now = datetime.combine(datetime.today(), lunch_end)
            patient_count = 0
            continue
            
        # 5명 진료 후 10분 휴식
        if patient_count == 5:
            now += timedelta(minutes=10)
            patient_count = 0
            continue
        
        # 이미 예약된 시간인지 확인 (단순 예시)
        time_str = now.strftime("%H:%M")
        if time_str not in existing_appointments:
            slots.append({"doctor_name": doctor['name'], "time": time_str})

        now += timedelta(minutes=doctor['consult_time'])
        patient_count += 1
        
    return slots

@router.get("/recommend")
def get_recommendation(dept: str = None):
    # 1. DB에서 의사 정보 가져오기
    query = supabase.table("doctors").select("*")
    if dept:
        query = query.eq("department", dept)
    doctors = query.execute().data

    # 2. 모든 의사의 가용 슬롯 계산
    all_available_slots = []
    for doc in doctors:
        # 실제로는 해당 날짜의 예약 내역도 가져와서 넘겨줘야 함
        slots = calculate_slots(doc, []) 
        all_available_slots.extend(slots)

    # 3. 이 데이터를 OpenAI에게 넘겨서 "가장 빠른 순"으로 문장 만들기
    # (이 부분에 OpenAI API 호출 로직 추가)
    
    return {"available_slots": all_available_slots[:10]} # 일단 상위 10개만 반환