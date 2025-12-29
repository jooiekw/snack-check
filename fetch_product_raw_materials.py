import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
import time
import sqlite3
import streamlit as st
from urllib.parse import quote

# ==========================================
# 1. 설정 (속도 UP 🚀)
# ==========================================
try:
    API_KEY = st.secrets["public_api_key"]
except FileNotFoundError:
    # 로컬에서 secrets.toml이 없는 경우를 대비한 폴백, 혹은 안내
    print("⚠️ .streamlit/secrets.toml 파일을 찾을 수 없습니다.")
    API_KEY = "016da8c44b7744f8b3df" # (임시 폴백)
    
SERVICE_ID = "C002"
DB_FILE = "snacks.db"

# 핵심 카테고리
TARGET_CATEGORIES = ["과자", "캔디류", "초콜릿가공품", "유탕면"]

# ⚡️ 50개는 너무 느림! 1000개로 20배 고속 수집!
# (1000개 * 100회 = 10만개까지 수집 가능 -> 사실상 전체 수집)
BATCH_SIZE = 1000
MAX_LOOPS = 100 

# ==========================================
# 2. 스마트 세션 설정 (재시도 기능 탑재)
# ==========================================
def get_session():
    """
    서버가 튕겨도 3번까지는 알아서 다시 시도하는 '끈기 있는' 세션을 만듭니다.
    """
    session = requests.Session()
    retry = Retry(
        total=3,                # 최대 3번 재시도
        backoff_factor=1,       # 재시도 간격 (1초, 2초, 4초...)
        status_forcelist=[500, 502, 503, 504], # 서버 에러 시 재시도
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# ==========================================
# 3. 수집 로직
# ==========================================
def fetch_category_data(session, category):
    print(f"\n🏎️ '{category}' 고속 수집 시작 (배치크기: {BATCH_SIZE})...")
    all_rows = []
    start_idx = 1
    encoded_cat = quote(category)
    
    for i in range(MAX_LOOPS):
        end_idx = start_idx + BATCH_SIZE - 1
        url = f"http://openapi.foodsafetykorea.go.kr/api/{API_KEY}/{SERVICE_ID}/json/{start_idx}/{end_idx}/PRDLST_DCNM={encoded_cat}"
        
        try:
            # 타임아웃을 넉넉히 20초 줍니다 (50개 데이터 묶는 시간 고려)
            response = session.get(url, timeout=20)
            
            # JSON 파싱 시도
            try:
                data = response.json()
            except ValueError:
                print(f"   - ⚠️ [{start_idx}~{end_idx}] JSON 변환 실패 (HTML 에러 페이지 수신됨)")
                # 이 구간만 건너뛰고 계속 진행
                start_idx += BATCH_SIZE
                continue

            if SERVICE_ID in data and 'row' in data[SERVICE_ID]:
                rows = data[SERVICE_ID]['row']
                count = len(rows)
                
                # 진행 상황을 한 줄로 깔끔하게 출력
                print(f"   - ✅ {count}개 수집 완료 ({start_idx}~{end_idx})")
                
                for item in rows:
                    all_rows.append({
                        'PRDLST_NM': item.get('PRDLST_NM'),
                        'RAWMTRL_NM': item.get('RAWMTRL_NM'),
                        'PRDLST_DCNM': item.get('PRDLST_DCNM'),
                        'BSSH_NM': item.get('BSSH_NM')
                    })
                
                if count < BATCH_SIZE:
                    print("   - (데이터 끝 도달)")
                    break
                    
                start_idx += BATCH_SIZE
                
                # 50개나 가져왔으니 0.5초만 숨 고르기
                time.sleep(0.5) 
            
            elif 'RESULT' in data and data['RESULT']['CODE'] == 'INFO-200':
                 # 데이터가 없는 경우 (정상 종료)
                 print("   - (데이터 없음)")
                 break
            else:
                print(f"   - ❓ 알 수 없는 응답: {data}")
                break

        except Exception as e:
            print(f"   - 💥 치명적 에러: {e}")
            break
            
    return all_rows

def run():
    session = get_session() # 재시도 기능이 있는 세션 생성
    total_data = []
    
    for cat in TARGET_CATEGORIES:
        total_data.extend(fetch_category_data(session, cat))
        
    if not total_data:
        print("\n❌ 수집된 데이터가 없습니다. (키 문제일 수도 있습니다)")
        return

    df = pd.DataFrame(total_data)
    
    # 중복 제거
    initial_len = len(df)
    df.drop_duplicates(subset=['PRDLST_NM', 'BSSH_NM'], keep='first', inplace=True)
    
    print("\n" + "=" * 40)
    print(f"🎉 최종 수집 완료! 총 {len(df)}개 (중복 {initial_len - len(df)}개 제거)")
    
    # CSV 저장 (백업)
    df.to_csv("all_snacks.csv", index=False, encoding='utf-8-sig')
    
    # DB 저장
    conn = sqlite3.connect(DB_FILE)
    df.to_sql('snacks', conn, if_exists='replace', index=False)
    conn.close()
    print(f"💾 DB 저장 완료: {DB_FILE}")

if __name__ == "__main__":
    run()