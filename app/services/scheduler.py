# app/services/scheduler.py
from datetime import datetime, timedelta
from app.services.scheduler import get_doctor_available_slots

def get_doctor_available_slots(doctor, existing_appointments, target_date_str):

    consult_time = doctor.get('consult_time', 5) 
    work_start = datetime.strptime(f"{target_date_str} {doctor['work_start']}", "%Y-%m-%d %H:%M")
    work_end = datetime.strptime(f"{target_date_str} {doctor['work_end']}", "%Y-%m-%d %H:%M")
    lunch_start = datetime.strptime(f"{target_date_str} 12:00", "%Y-%m-%d %H:%M")
    lunch_end = datetime.strptime(f"{target_date_str} 13:00", "%Y-%m-%d %H:%M")

    # 기존 예약된 시간만 추출
    booked_times = {
        datetime.strptime(appo['reserved_at'], "%Y-%m-%d %H:%M").strftime("%H:%M") 
        for appo in existing_appointments
    }

    current_time = work_start
    continuous_count = 0 
    available_slots = []

    while current_time + timedelta(minutes=consult_time) <= work_end:
        # 1. 점심시간 체크
        if lunch_start <= current_time < lunch_end:
            current_time = lunch_end
            continuous_count = 0 
            continue

        # 2. 예약 여부 확인
        time_str = current_time.strftime("%H:%M")
        
        # 비어있는 시간이라면 리스트에 추가
        if time_str not in booked_times:
            available_slots.append(time_str)
        
        # 3. 진료 진행
        current_time += timedelta(minutes=consult_time)
        continuous_count += 1

        # 4. 5명 채우면 30분 강제 휴식
        if continuous_count >= 5:
            current_time += timedelta(minutes=30)
            continuous_count = 0 

    return available_slots