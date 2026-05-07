import openai
import json
import os
from datetime import datetime
from supabase import create_client, Client
from app.services.scheduler import get_doctor_available_slots
from app.routers.patients import format_phone_number

# Supabase 설정
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# OpenAI 클라이언트 설정
client = openai.OpenAI(api_key="YOUR_OPENAI_API_KEY")

# 1. AI가 사용할 도구(Tools) 정의
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_booking_advice",
            "description": "진료과별 의사 목록과 예약 가능 시간을 조회합니다. (휴식/점심시간 제외)",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {"type": "string", "description": "진료과 (예: 내과)"},
                    "date": {"type": "string", "description": "날짜 (YYYY-MM-DD)"}
                },
                "required": ["department", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "register_appointment",
            "description": "환자 정보를 등록(신규일 경우)하고 예약을 확정합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "환자 이름"},
                    "phone": {"type": "string", "description": "휴대폰 번호"},
                    "pin": {"type": "string", "description": "비밀번호 4자리"},
                    "doctor_id": {"type": "string", "description": "의사 UUID"},
                    "reserved_at": {"type": "string", "description": "예약 일시 (YYYY-MM-DD HH:MM)"}
                },
                "required": ["name", "phone", "pin", "doctor_id", "reserved_at"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_user_appointment",
            "description": "전화번호와 비밀번호를 통해 예약 내역을 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string"},
                    "pin": {"type": "string"}
                },
                "required": ["phone", "pin"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "특정 예약을 취소(삭제)합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string", "description": "삭제할 예약의 UUID"}
                },
                "required": ["appointment_id"]
            }
        }
    }
]

# 2. 실행 함수들
def fetch_booking_advice(department: str, date: str):
    docs_res = supabase.table("doctors").select("*").eq("department", department).execute()
    results = []
    for doc in docs_res.data:
        appo_res = supabase.table("appointments").select("reserved_at").eq("doctor_id", doc['id']).like("reserved_at", f"{date}%").execute()
        slots = get_doctor_available_slots(doc, appo_res.data, date)
        results.append({"doctor_id": doc['id'], "doctor_name": doc['name'], "available_slots": slots, "special_note": doc.get('special_note', '')})
    return results

def process_register_appointment(name, phone, pin, doctor_id, reserved_at):
    clean_phone = format_phone_number(phone)
    p_res = supabase.table("patients").select("id").eq("phone", clean_phone).execute()
    
    if not p_res.data:
        p_insert = supabase.table("patients").insert({"name": name, "phone": clean_phone, "pin": pin}).execute()
        patient_id = p_insert.data[0]['id']
    else:
        patient_id = p_res.data[0]['id']

    res = supabase.table("appointments").insert({"patient_id": patient_id, "doctor_id": doctor_id, "reserved_at": reserved_at, "status": "confirmed"}).execute()
    return {"status": "success", "message": f"{name}님, {reserved_at} 예약 완료."} if res.data else {"status": "error"}

def fetch_user_appointments(phone, pin):
    clean_phone = format_phone_number(phone)
    p_res = supabase.table("patients").select("id, name").eq("phone", clean_phone).eq("pin", pin).execute()
    if not p_res.data: return {"error": "본인 확인 실패."}
    
    a_res = supabase.table("appointments").select("id, reserved_at, doctors(name, department)").eq("patient_id", p_res.data[0]['id']).execute()
    return {"name": p_res.data[0]['name'], "list": a_res.data}

def delete_appointment_data(appointment_id):
    res = supabase.table("appointments").delete().eq("id", appointment_id).execute()
    return {"status": "success"} if res.data else {"status": "error"}

# 3. 메인 챗봇 함수
def ask_chatbot(user_message: str):
    current_date = datetime.now().strftime("%Y-%m-%d")
    weekday_info = datetime.now().strftime("%A")

    messages = [
        {
            "role": "system", 
            "content": (
                f"너는 병원 예약 비서야. 오늘은 {current_date}이고 {weekday_info}요일이야. "
                "의사는 5명 진료마다 30분씩 의무 휴식을 가져야 해. "
                "병원은 9:00~18:00까지 하고, 11:30분부터 13:00까지는 점심시간이며, "
                "병원은 평일만 문을 열어. "
                "사용자가 예약을 원하면 먼저 시간을 조회해서 가능한 시간만 제안하고, "
                "사용자가 확정하면 예약을 등록해줘."
            )
        },
        {"role": "user", "content": user_message}
    ]

    response = client.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
    msg = response.choices[0].message
    
    if msg.tool_calls:
        messages.append(msg)
        for tool in msg.tool_calls:
            args = json.loads(tool.function.arguments)
            if tool.function.name == "get_booking_advice":
                res = fetch_booking_advice(args['department'], args['date'])
            elif tool.function.name == "register_appointment":
                res = process_register_appointment(args['name'], args['phone'], args['pin'], args['doctor_id'], args['reserved_at'])
            elif tool.function.name == "check_user_appointment":
                res = fetch_user_appointments(args['phone'], args['pin'])
            elif tool.function.name == "cancel_appointment":
                res = delete_appointment_data(args['appointment_id'])
            
            messages.append({"tool_call_id": tool.id, "role": "tool", "name": tool.function.name, "content": json.dumps(res, ensure_ascii=False)})
        
        final = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
        return final.choices[0].message.content
    return msg.content