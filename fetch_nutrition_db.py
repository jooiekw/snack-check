import requests
import pandas as pd
import time
import json

import streamlit as st

# ==========================================
# 1. 설정
# ==========================================
try:
    API_KEY = st.secrets["public_api_key"]
except:
    API_KEY = "016da8c44b7744f8b3df"
    
SERVICE_ID = "FoodNtrCpntDbInfo02"
BASE_URL = "http://apis.data.go.kr/1471000/FoodNtrCpntDbInfo02/getFoodNtrCpntDbInq02"

def fetch_all_data():
    all_data = []
    page = 1
    batch_size = 500 # 한 번에 가져올 개수 (API 최대치 500 제한)

    print("🚀 API 전체 데이터 다운로드를 시작합니다...")

    while True:
        params = {
            'serviceKey': API_KEY,
            'pageNo': str(page),
            'numOfRows': str(batch_size),
            'type': 'json'
        }

        try:
            response = requests.get(BASE_URL, params=params, timeout=10)
            
            # JSON 파싱
            try:
                data = response.json()
            except:
                print(f"⚠️ {page}페이지: JSON 파싱 에러 (건너뜀)")
                page += 1
                continue

            # 데이터 추출
            if 'body' in data and 'items' in data['body']:
                items = data['body']['items']
                
                if not items: # 데이터가 없으면 끝
                    print("✅ 모든 데이터를 가져왔습니다.")
                    break
                
                # 리스트에 추가
                all_data.extend(items)
                print(f"   [{page}페이지] {len(items)}개 로드 완료 (누적 {len(all_data)}개)")
                
                page += 1
                time.sleep(0.1) # 서버 부하 방지
            else:
                print("⚠️ 응답 구조가 이상합니다. (body/items 없음)")
                print(data) # 에러 로그 확인용
                break

        except Exception as e:
            print(f"❌ 통신 에러: {e}")
            break

    # 2. DataFrame 변환 및 저장
    if all_data:
        df = pd.DataFrame(all_data)
        
        # CSV로 저장 (한글 깨짐 방지 utf-8-sig)
        file_name = "nutrition_dump.csv"
        df.to_csv(file_name, index=False, encoding="utf-8-sig")
        
        print("\n" + "="*40)
        print(f"🎉 저장 완료: {file_name}")
        print(f"총 데이터 개수: {len(df)}개")
        print("="*40)
        
        # 3. 데이터 맛보기 (로그 출력)
        print("\n🔎 데이터 구조 미리보기 (상위 3개):")
        print(df.head(3))
        print("\n🔎 컬럼 목록:")
        print(df.columns.tolist())
    else:
        print("❌ 저장할 데이터가 없습니다.")

if __name__ == "__main__":
    fetch_all_data()