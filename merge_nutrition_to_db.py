import pandas as pd
import sqlite3
import re
import os
from collections import Counter
import numpy as np

# ==========================================
# 1. 설정
# ==========================================
CSV_FILE = "nutrition_dump.csv"
DB_FILE = "snacks.db"

NOISE_WORDS = ["케이크", "맛", "과자", "스낵", "비스킷", "쿠키", "칩", "질소", "대", "소", "봉", "팩", "기획", "세트", "번들"]

def build_auto_vocab(df, col_name, top_n=500):
    print(f"🧠 데이터에서 자주 쓰이는 단어 학습 중... (Top {top_n})")
    all_text = " ".join(df[col_name].dropna().astype(str).tolist())
    words = re.findall(r'[가-힣]{2,}', all_text)
    counts = Counter(words)
    for noise in NOISE_WORDS:
        if noise in counts:
            del counts[noise]
    top_keywords = [word for word, _ in counts.most_common(top_n)]
    print(f"   -> 학습된 주요 키워드: {top_keywords[:20]} ...")
    return top_keywords

def clean_and_sort_name(text, split_pattern=None):
    if pd.isna(text): return ""
    text = str(text)
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    if split_pattern:
        text = split_pattern.sub(r' \1 ', text)
    tokens = text.split()
    clean_tokens = []
    for t in tokens:
        if t not in NOISE_WORDS:
            clean_tokens.append(t)
    clean_tokens.sort()
    return "".join(clean_tokens)

def parse_weight(value):
    if pd.isna(value): return None
    value = str(value)
    # "100g" -> 100.0
    numbers = re.findall(r"[\d\.]+", value)
    if numbers:
        try: return float(numbers[0])
        except: return None
    return None

def run_merge():
    print(f"📂 '{CSV_FILE}' 로드 중...")
    
    if not os.path.exists(CSV_FILE):
        print("❌ CSV 파일이 없습니다.")
        return

    try:
        df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
        print(f"   -> {len(df):,}개 데이터 로드 완료!")
        
        name_col = 'FOOD_NM_KR'
        vocab = build_auto_vocab(df, name_col, top_n=700)
        vocab.sort(key=len, reverse=True)
        pattern = re.compile(f"({'|'.join(vocab)})")
        
        # 🚨 [UPDATE] 컬럼 매핑 수정
        cal_col = 'AMT_NUM1'
        prot_col = 'AMT_NUM3'
        fat_col = 'AMT_NUM4'
        carbo_col = 'AMT_NUM6'   # 탄수화물 수정 (2 -> 6)
        sugar_col = 'AMT_NUM7'
        sod_col = 'AMT_NUM13'
        
        # [NEW] 신규 컬럼
        chol_col = 'AMT_NUM23'    # 콜레스테롤
        sat_fat_col = 'AMT_NUM24' # 포화지방산
        trans_fat_col = 'AMT_NUM25' # 트랜스지방산
        
        weight_col = 'Z10500'       # 총 내용량
        std_col = 'SERVING_SIZE'    # 기준 용량

    except Exception as e:
        print(f"❌ 설정 에러: {e}")
        return

    print("⚡ 스마트 매칭 및 환산 로직 적용 중...")
    
    nut_dict = {}
    
    for _, row in df.iterrows():
        sorted_key = clean_and_sort_name(row[name_col], split_pattern=pattern)
        
        def safe_float(val):
            if pd.isna(val) or val == "": return 0.0
            val = str(val).replace(",", "")
            try: return float(val)
            except: return 0.0

        # 기본 값 추출
        cal = safe_float(row.get(cal_col))
        carbo = safe_float(row.get(carbo_col))
        prot = safe_float(row.get(prot_col))
        fat = safe_float(row.get(fat_col))
        sugar = safe_float(row.get(sugar_col))
        sod = safe_float(row.get(sod_col))
        
        chol = safe_float(row.get(chol_col))
        sat_fat = safe_float(row.get(sat_fat_col))
        trans_fat = safe_float(row.get(trans_fat_col))
        
        std_size_str = str(row.get(std_col, ""))
        total_weight = parse_weight(row.get(weight_col))
        
        # 기준 용량 (Serving Size) 파싱 -> 없으면 100g으로 가정하거나 total_weight 사용
        serving_weight = parse_weight(std_size_str)
        if not serving_weight:
             # 기준 용량이 없으면 총 내용량을 기준으로 본다 (데이터 특성상)
             serving_weight = total_weight if total_weight else 100.0

        # ⚖️ 환산 로직 (100g 넘으면 100g당, 아니면 총 내용량 기준)
        ratio = 1.0
        desc = ""
        
        if total_weight:
            if total_weight > 100:
                # 100g 당 표시
                ratio = 100.0 / serving_weight if serving_weight > 0 else 1.0
                desc = "100g 당"
            else:
                # 총 내용량 기준 표시
                ratio = total_weight / serving_weight if serving_weight > 0 else 1.0
                w_str = f"{total_weight:.0f}" if total_weight.is_integer() else f"{total_weight}"
                desc = f"총 내용량 ({w_str}g)"
        else:
            # 총 중량 정보가 없는 경우 -> 그냥 기준 용량대로 표시
            desc = f"{std_size_str} 당" if std_size_str else "1회 제공량"
            ratio = 1.0

        # 비정상적인 ratio 방지 (데이터 오류 등)
        if ratio > 50.0 or ratio < 0.01:
            ratio = 1.0
            desc = f"{std_size_str} 당 (환산 불가)"

        nut_dict[sorted_key] = {
            'CALORIE': cal * ratio,
            'CARBO': carbo * ratio,
            'PROTEIN': prot * ratio,
            'FAT': fat * ratio,
            'SUGAR': sugar * ratio,
            'SODIUM': sod * ratio,
            'CHOLESTEROL': chol * ratio,
            'SAT_FAT': sat_fat * ratio,
            'TRANS_FAT': trans_fat * ratio,
            'DESC': desc,
            'TOTAL_WEIGHT': total_weight if total_weight else 0.0
        }
        
    print(f"   -> 사전 준비 완료 ({len(nut_dict):,}개)")

    # DB 업데이트
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 컬럼 생성 (추가된 항목 포함)
    new_cols = ['CHOLESTEROL', 'SAT_FAT', 'TRANS_FAT', 'TOTAL_WEIGHT'] # 신규 컬럼 추가
    base_cols = ['CALORIE', 'CARBO', 'PROTEIN', 'FAT', 'SUGAR', 'SODIUM', 'SERVING_DESC']
    
    all_cols = base_cols + new_cols
    
    for col in all_cols:
        try: cursor.execute(f"ALTER TABLE snacks ADD COLUMN {col} TEXT")
        except: pass

    updated_count = 0
    missing_count = 0
    
    cursor.execute("SELECT rowid, PRDLST_NM FROM snacks")
    db_products = cursor.fetchall()
    
    print("\n🔗 스마트 매칭 및 업데이트 시작...")
    
    for row_id, db_name in db_products:
        target_key = clean_and_sort_name(db_name, split_pattern=pattern)
        
        info = nut_dict.get(target_key)
        
        if info:
            # 포맷팅 (소수점 정리)
            cal = str(int(round(info['CALORIE'])))
            carbo = str(round(info['CARBO'], 1))
            pro = str(round(info['PROTEIN'], 1))
            fat = str(round(info['FAT'], 1))
            sug = str(round(info['SUGAR'], 1))
            sod = str(int(round(info['SODIUM'])))
            
            chol = str(round(info['CHOLESTEROL'], 1))
            sat = str(round(info['SAT_FAT'], 1))
            trans = str(round(info['TRANS_FAT'], 1))
            
            desc = info['DESC']
            w = str(round(info['TOTAL_WEIGHT'], 1))

            if cal != "0":
                cursor.execute("""
                    UPDATE snacks 
                    SET CALORIE=?, CARBO=?, PROTEIN=?, FAT=?, SUGAR=?, SODIUM=?, 
                        CHOLESTEROL=?, SAT_FAT=?, TRANS_FAT=?, SERVING_DESC=?, TOTAL_WEIGHT=?
                    WHERE rowid=?
                """, (cal, carbo, pro, fat, sug, sod, chol, sat, trans, desc, w, row_id))
                updated_count += 1
                
                if updated_count % 100 == 0:
                    print(f"   [{updated_count}] {db_name} -> {cal}kcal ({desc})")
        else:
            missing_count += 1

    conn.commit()
    conn.close()
    
    print("="*40)
    print(f"🎉 완료! {updated_count}개 업데이트 성공.")
    print(f"❓ 정보 없음: {missing_count}개")

if __name__ == "__main__":
    run_merge()