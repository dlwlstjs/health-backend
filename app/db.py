from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
print("--- 환경 변수 로드 체크 ---")
print(f"URL 존재 여부: {bool(os.getenv('SUPABASE_URL'))}")
print(f"KEY 존재 여부: {bool(os.getenv('SUPABASE_KEY'))}")
print("--------------------------")
#db연결 -> supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)