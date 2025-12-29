import requests
import streamlit as st
from urllib.parse import quote
import json

try:
    API_KEY = st.secrets["public_api_key"]
except:
    API_KEY = "016da8c44b7744f8b3df"
SERVICE_ID = "C002"

def probe_ramen_category():
    # '콘드로이친 상어연골 맥스 1400'을 검색해서 카테고리(PRDLST_DCNM)가 뭐라고 나오는지 확인
    product_name = "콘드로이친 상어연골 맥스 1400"
    encoded_name = quote(product_name)
    
    url = f"http://openapi.foodsafetykorea.go.kr/api/{API_KEY}/{SERVICE_ID}/json/1/5/PRDLST_NM={encoded_name}"
    
    print(f"🔍 '{product_name}' 검색 중...")
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if SERVICE_ID in data and 'row' in data[SERVICE_ID]:
            rows = data[SERVICE_ID]['row']
            print(f"✅ {len(rows)}개 발견!\n")
            
            seen_categories = set()
            for item in rows:
                cat = item.get('PRDLST_DCNM')
                seen_categories.add(cat)
                print(f"- 제품명: {item.get('PRDLST_NM')}")
                print(f"  카테고리: {cat}")
                print("---")
            
            print(f"\n💡 결론: API에서 사용하는 카테고리 명칭은 {seen_categories} 입니다.")
        else:
            print("❌ 검색 결과가 없습니다.")
            print(data)

    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    probe_ramen_category()
