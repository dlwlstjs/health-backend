import json
import os
from datetime import datetime
import openai

from app.db import supabase  # ✅ 단일 DB 연결
from app.routers.appointments import (
    register_appointment as register_appo_api,
    cancel_appointment as cancel_appo_api
)
from app.routers.patients import (
    register_patient as register_patient_api,
    check_reservation as check_reservation_api
)
from app.services.scheduler import get_doctor_available_slots


# ✅ OpenAI 클라이언트
client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


# =========================
# 1. AI Tool 정의
# =========================
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_booking_advice",
            "description": "진료과별 의사 목록과 예약 가능한 시간을 조회합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "department": {"type": "string"},
                    "date": {"type": "string"}
                },
                "required": ["department", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "register_full_process",
            "description": "신규 환자 등록 + 예약",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "pin": {"type": "string"},
                    "doctor_id": {"type": "string"},
                    "reserved_at": {"type": "string"}
                },
                "required": ["name", "phone", "pin", "doctor_id", "reserved_at"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_my_reservation",
            "description": "예약 조회",
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
            "name": "cancel_my_reservation",
            "description": "예약 취소",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string"},
                    "pin": {"type": "string"}
                },
                "required": ["phone", "pin"]
            }
        }
    }
]


# =========================
# 2. 실제 실행 함수들
# =========================

def fetch_booking_advice(department: str, date: str):
    docs_res = supabase.table("doctors").select("*").eq("department", department).execute()

    results = []
    for doc in docs_res.data:
        appo_res = supabase.table("appointments") \
            .select("reserved_at") \
            .eq("doctor_id", doc['id']) \
            .like("reserved_at", f"{date}%") \
            .execute()

        slots = get_doctor_available_slots(doc, appo_res.data, date)

        results.append({
            "doctor_id": doc['id'],
            "doctor_name": doc['name'],
            "available_slots": slots,
            "special_note": doc.get('special_note', '')
        })

    return results


def register_full_process(name, phone, pin, doctor_id, reserved_at):
    register_patient_api(name=name, phone=phone, pin=pin)
    return register_appo_api(phone=phone, doctor_id=doctor_id, reserved_at=reserved_at)


def check_my_reservation(phone, pin):
    return check_reservation_api(phone=phone, pin=pin)


def cancel_my_reservation(phone, pin):
    return cancel_appo_api(phone=phone, pin=pin)


# =========================
# 3. 메인 챗봇 함수
# =========================

def ask_chatbot(user_message: str):
    print("🔥 함수 진입:", user_message)

    current_date = datetime.now().strftime("%Y-%m-%d")

    messages = [
        {
            "role": "system",
            "content": (
                f"너는 병원 예약 비서야. 오늘은 {current_date}야.\n"
                "병원 운영시간은 09:00~18:00, 점심 11:30~13:00\n"
                "예약, 조회, 취소를 도와줘."
            )
        },
        {"role": "user", "content": user_message}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools
        )

        msg = response.choices[0].message

        # 🔥 tool 호출 있는 경우
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            messages.append(msg)

            for tool in msg.tool_calls:
                args = json.loads(tool.function.arguments)
                func_name = tool.function.name

                if func_name == "get_booking_advice":
                    res = fetch_booking_advice(args['department'], args['date'])
                elif func_name == "register_full_process":
                    res = register_full_process(
                        args['name'], args['phone'], args['pin'],
                        args['doctor_id'], args['reserved_at']
                    )
                elif func_name == "check_my_reservation":
                    res = check_my_reservation(args['phone'], args['pin'])
                elif func_name == "cancel_my_reservation":
                    res = cancel_my_reservation(args['phone'], args['pin'])

                messages.append({
                    "tool_call_id": tool.id,
                    "role": "tool",
                    "name": func_name,
                    "content": json.dumps(res, ensure_ascii=False)
                })

            final = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )

            return final.choices[0].message.content

        # 🔥 일반 응답
        return msg.content

    except Exception as e:
        print("🔥 챗봇 에러:", e)
        return "서버 처리 중 오류가 발생했어요 😢"