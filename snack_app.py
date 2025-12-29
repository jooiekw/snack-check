# Version: 1.1.0
# Last Updated: 2025-12-29
# Author: Jooie Kwon
import streamlit as st
import pandas as pd
import sqlite3
import random
import numpy as np
import os
from datetime import datetime

# ==========================================
# 1. 설정 및 상수 정의
# ==========================================
st.set_page_config(page_title="Snack Check", page_icon="🔍", layout="centered")

ALLERGENS = [
    "밀", "대두", "우유", "계란", "새우", "땅콩", "쇠고기", "돼지고기", "토마토", "게", "조개", "오징어",
    "호두", "잣", "메밀", "복숭아", "닭고기", "고등어", "아황산류", "굴", "전복", "홍합"
]

HEALTH_WARNINGS = [
    "팜유", "쇼트닝", "가공유지", "마가린", "경화유", 
    "물엿", "설탕", "액상과당", "기타과당", "식용색소", "타르색소", "합성향료", 
    "산도조절제", "유화제", "L-글루탐산나트륨", "향미증진제", "아질산나트륨", "소르빈산", "안식향산", "변성전분"
]

SWEETENERS = [
    "아스파탐", "수크랄로스", "아세설팜칼륨", "사카린", "스테비아", "에리스리톨", "말티톨", "알룰로스"
]

CATEGORY_DISPLAY_MAP = {
    "과자": "🍪 과자",
    "스낵과자": "🍟 스낵",
    "캔디류": "🍬 캔디",
    "초콜릿가공품": "🍫 초콜릿",
    "떡류": "🍡 떡",
    "빵류": "🍞 빵",
    "기타가공품": "🍱 기타",
    "복합조미식품": "🧂 조미공",
    "즉석섭취식품": "🍙 즉석",
    "곡류가공품": "🌾 곡물",
    "두류가공품": "🥜 콩가공",
    "수산물가공품": "🐟 어묵/포",
    "식육가공품": "🍖 육가공",
    "알가공품": "🥚 알가공",
    "유가공품": "🧀 치즈/유",
    "음료류": "🥤 음료",
    "면류": "🍜 면",
    "유탕면": "🍜 라면",
}

# ==========================================
# 2. 데이터 로드 함수
# ==========================================
@st.cache_data
def load_data():
    try:
        conn = sqlite3.connect("snacks.db")
        df = pd.read_sql("SELECT * FROM snacks", conn)
        conn.close()
        
        # 🔢 [NEW] 숫자형 변환
        numeric_cols = ['CALORIE', 'CARBO', 'PROTEIN', 'FAT', 'SUGAR', 'SODIUM', 'CHOLESTEROL', 'SAT_FAT', 'TRANS_FAT', 'TOTAL_WEIGHT']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # 정렬을 위해 0을 NaN으로 치환 (정보 없음 처리를 위해)
                # 단, TOTAL_WEIGHT는 0일 수도 있으나 보통 없으면 NaN이어야 함
                if col != 'TOTAL_WEIGHT':
                    df[col] = df[col].replace(0, np.nan)
        
        return df
    except Exception:
        return pd.DataFrame()

# ==========================================
# 3. 메인 앱 로직
# ==========================================
def main():
    if 'page_limit' not in st.session_state:
        st.session_state.page_limit = 20

    df = load_data()

    LAYOUT_RATIO = [1, 3, 1] 

    # --- [헤더 영역] ---
    st.markdown("<br>", unsafe_allow_html=True)
    _, head_col, _ = st.columns(LAYOUT_RATIO)
    
    with head_col:
        st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
        st.title("🔍 Snack Check")
        st.caption("내가 먹는 간식, 성분 알고 먹기")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- [컨트롤 영역] ---
    _, ctrl_col, _ = st.columns(LAYOUT_RATIO) 

    with ctrl_col:
        # 1. 카테고리 Pills
        raw_categories = sorted(df['PRDLST_DCNM'].unique().tolist())
        pill_options = ["🌈 전체 보기"]
        for cat in raw_categories:
            display_name = CATEGORY_DISPLAY_MAP.get(cat, f"🍴 {cat}")
            pill_options.append(display_name)
        
        try:
            selected_pill = st.pills("카테고리", pill_options, default="🌈 전체 보기", label_visibility="collapsed")
        except AttributeError:
            selected_pill = st.radio("카테고리", pill_options, horizontal=True)

        st.write("") 

        # 2. 검색, 정렬
        row1_col1, row1_col2 = st.columns([2, 1])
        with row1_col1:
            search_query = st.text_input("제품명 검색", placeholder="예: 몽쉘, 제로", label_visibility="collapsed")
        with row1_col2:
            sort_options = [
                "랜덤 추천순", "가나다순", "제조사순", 
                "🔥 칼로리 낮은 순", "🔥 칼로리 높은 순",
                "💪 단백질 높은 순", "🍬 당류 낮은 순",
                "🧂 나트륨 낮은 순", "💧 지방 낮은 순"
            ]
            sort_option = st.selectbox("정렬", sort_options, label_visibility="collapsed")

        # 3. 주요 브랜드 필터
        st.write("")
        only_major = st.checkbox("주요 브랜드만 보기 (농심, 롯데, 오리온 등)", value=True)

        # 4. 추가 필터 (알레르기)
        with st.expander("🔎 상세 필터 (알레르기 제외 설정)", expanded=False):
            st.caption("체크한 성분이 **포함된** 제품을 결과에서 제외합니다.")
            excluded_allergens = st.multiselect(
                "제외할 알레르기 성분", 
                options=ALLERGENS,
                default=[],
                help="선택한 성분이 원재료에 포함되어 있다면 리스트에서 숨깁니다."
            )



    # --- [커스텀 CSS] (모바일 최적화) ---
    st.markdown("""
    <style>
    /* 기본 리스트 아이템 스타일 */
    .snack-item {
        display: flex; 
        align-items: center; 
        padding: 10px 0;
        border-bottom: 1px solid #eee;
    }
    .snack-emoji {
        font-size: 40px; 
        min-width: 60px; 
        text-align: center;
        margin-right: 15px;
    }
    .snack-info {
        flex-grow: 1;
    }
    .snack-title {
        font-size: 18px; 
        font-weight: bold; 
        margin-bottom: 2px;
        line-height: 1.3;
    }
    .snack-meta {
        font-size: 13px; 
        color: #666; 
        margin-bottom: 4px;
    }
    .snack-badges {
        font-size: 0.85em;
        line-height: 1.6;
    }

    /* 모바일용 미디어 쿼리 (화면 폭 600px 이하) */
    @media (max-width: 600px) {
        .snack-emoji {
            font-size: 28px !important;  /* 이모지 크기 축소 */
            min-width: 45px !important;
            margin-right: 10px !important;
        }
        .snack-title {
            font-size: 16px !important;  /* 제목 크기 축소 */
        }
        .snack-meta {
            font-size: 12px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # --- [필터링 로직] ---
    filtered_df = df.copy()

    # 1. 카테고리 필터
    if selected_pill != "🌈 전체 보기":
        # display name에서 원본 이름 찾기 (단순화: 텍스트 포함 여부로)
        # Pills 로직이 단순하므로 display map 역매핑하거나, 순회하며 찾음
        target_cat = None
        for cat in raw_categories:
            d_name = CATEGORY_DISPLAY_MAP.get(cat, f"🍴 {cat}")
            if d_name == selected_pill:
                target_cat = cat
                break
        if target_cat:
            filtered_df = filtered_df[filtered_df['PRDLST_DCNM'] == target_cat]

    # 2. 검색 필터
    if search_query:
        filtered_df = filtered_df[filtered_df['PRDLST_NM'].str.contains(search_query, na=False)]

    # 3. 주요 브랜드 필터
    if only_major:
        major_brands = ["농심", "롯데", "오리온", "해태", "크라운", "삼양", "빙그레", "청우", "오뚜기", "동서", "팔도", "서울우유", "매일", "남양", "동원", "하림", "진주"]
        filtered_df = filtered_df[filtered_df['BSSH_NM'].str.contains('|'.join(major_brands), na=False)]

    # 4. 알레르기 제외 필터
    if excluded_allergens:
        # 선택된 알레르기 성분이 '하나라도' 들어있으면 제외
        pattern = '|'.join(excluded_allergens)
        # ~ (not) 연산자 사용
        filtered_df = filtered_df[~filtered_df['RAWMTRL_NM'].str.contains(pattern, na=False)]

    # --- [정렬 로직] ---
    # na_position='last' 로 정보 없음(NaN) 데이터를 항상 뒤로 보냄
    if sort_option == "랜덤 추천순":
        filtered_df = filtered_df.sample(frac=1)
    elif sort_option == "가나다순":
        filtered_df = filtered_df.sort_values(by="PRDLST_NM")
    elif sort_option == "제조사순":
        filtered_df = filtered_df.sort_values(by="BSSH_NM")
    elif sort_option == "🔥 칼로리 낮은 순":
        filtered_df = filtered_df.sort_values(by="CALORIE", ascending=True, na_position='last')
    elif sort_option == "🔥 칼로리 높은 순":
        filtered_df = filtered_df.sort_values(by="CALORIE", ascending=False, na_position='last')
    elif sort_option == "💪 단백질 높은 순":
        filtered_df = filtered_df.sort_values(by="PROTEIN", ascending=False, na_position='last')
    elif sort_option == "🍬 당류 낮은 순":
        filtered_df = filtered_df.sort_values(by="SUGAR", ascending=True, na_position='last')
    elif sort_option == "🧂 나트륨 낮은 순":
        filtered_df = filtered_df.sort_values(by="SODIUM", ascending=True, na_position='last')
    elif sort_option == "💧 지방 낮은 순":
        filtered_df = filtered_df.sort_values(by="FAT", ascending=True, na_position='last')

    # --- [결과 표시] ---
    _, main_col, _ = st.columns(LAYOUT_RATIO)
    
    with main_col:
        # 페이지네이션
        if st.session_state.page_limit < len(filtered_df):
            display_df = filtered_df.iloc[:st.session_state.page_limit]
            has_more = True
        else:
            display_df = filtered_df
            has_more = False

        if display_df.empty:
            st.warning("조건에 맞는 제품이 없습니다. (필터를 조정해보세요) 😅")
        else:
            if not df.empty and not search_query:
                 st.caption(f"총 {len(filtered_df):,}개의 제품 중 {len(display_df)}개를 표시합니다.")

            for _, row in display_df.iterrows():
                name = row['PRDLST_NM']
                category = row['PRDLST_DCNM']
                maker = row['BSSH_NM']
                raw_materials = row['RAWMTRL_NM'] or ""
                
                # 영양성분 안전하게 가져오기
                def get_val(val):
                    if pd.isna(val): return 0
                    return val

                cal = get_val(row.get('CALORIE'))
                carbo = get_val(row.get('CARBO'))
                prot = get_val(row.get('PROTEIN'))
                fat = get_val(row.get('FAT'))
                sugar = get_val(row.get('SUGAR'))
                sodium = get_val(row.get('SODIUM'))
                chol = get_val(row.get('CHOLESTEROL'))
                sat_fat = get_val(row.get('SAT_FAT'))
                trans_fat = get_val(row.get('TRANS_FAT'))
                total_weight = row.get('TOTAL_WEIGHT')
                desc = row.get('SERVING_DESC') 

                # 데이터 존재 여부 확인 (칼로리가 없거나 0이면 정보 없음 취급)
                has_nutrition = cal > 0

                found_allergens = [k for k in ALLERGENS if k in raw_materials]
                found_warnings = [k for k in HEALTH_WARNINGS if k in raw_materials]
                found_sweeteners = [k for k in SWEETENERS if k in raw_materials]

                with st.container():
                    # [Mobile Optimized Layout] -> Flexbox 사용 (HTML/CSS)
                    display_cat = CATEGORY_DISPLAY_MAP.get(category, category)
                    emoji = display_cat[0] if display_cat[0] in ["🍪", "🍟", "🍬", "🍫", "🍜", "🍞", "🧀", "🥤", "🍡", "🐟"] else "🍴"
                    
                    badges_html_list = []
                    # [NEW] 영양성분 뱃지
                    if has_nutrition:
                        badges_html_list.append(f"🔥 <b>{int(cal)} kcal</b> <span style='font-size:0.9em; color:#666;'>({desc})</span>")
                    else:
                        # 정보 없음 뱃지 (회색)
                        badges_html_list.append(f"<span style='background-color:#eee; color:#888; padding:2px 6px; border-radius:4px;'>⚪ 공공데이터 정보 없음</span>")

                    # 알레르기/주의 뱃지
                    if found_allergens:
                        badges_html_list.append(f"🚨 <b>알레르기:</b> <span style='color:#d63031'>{', '.join(found_allergens)}</span>")
                    if found_warnings:
                        badges_html_list.append(f"⚠️ <b>주의성분:</b> <span style='color:#e17055'>{', '.join(found_warnings)}</span>")
                    if found_sweeteners:
                        badges_html_list.append(f"🍬 <b>대체당(주의) ⚠️:</b> <span style='color:#0984e3'>{', '.join(found_sweeteners)}</span>")
                    
                    badges_str = " | ".join(badges_html_list)

                    st.markdown(f"""
                    <div class="snack-item">
                        <div class="snack-emoji">{emoji}</div>
                        <div class="snack-info">
                            <div class="snack-title">{name}</div>
                            <div class="snack-meta">{display_cat} | {maker}</div>
                            <div class="snack-badges">{badges_str}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Expander
                    with st.expander(f"📝 '{name}' 원재료 및 영양정보 보기"):
                        # [NEW] 영양성분 표 (데이터 있을 때만)
                        if has_nutrition:
                            # 총 내용량 표시
                            weight_info = f" | 📦 <b>총 내용량: {total_weight}g</b>" if total_weight and total_weight > 0 else ""

                            st.markdown(f"""
                            <div style='background-color:#f8f9fa; padding:15px; border-radius:8px; margin-bottom:10px; font-size:14px; line-height:1.6;'>
                                <div style='color:#555; font-size:0.9em; margin-bottom:5px;'>
                                    📊 <b>영양성분 기준: {desc}</b>{weight_info}
                                </div>
                                <div style='display:flex; justify-content:space-between; flex-wrap:wrap;'>
                                    <span style='flex:1; min-width:80px;'>🔥 열량: <b>{int(cal)} kcal</b></span>
                                    <span style='flex:1; min-width:80px;'>🍞 탄수화물: <b>{carbo}g</b></span>
                                    <span style='flex:1; min-width:80px;'>🍬 당류: <b>{sugar}g</b></span>
                                </div>
                                <div style='display:flex; justify-content:space-between; flex-wrap:wrap; margin-top:5px; border-top:1px dashed #ddd; padding-top:5px;'>
                                    <span style='flex:1; min-width:80px;'>💪 단백질: <b>{prot}g</b></span>
                                    <span style='flex:1; min-width:80px;'>💧 지방: <b>{fat}g</b></span>
                                    <span style='flex:1; min-width:80px;'>🧂 나트륨: <b>{int(sodium)}mg</b></span>
                                </div>
                                <div style='display:flex; justify-content:space-between; flex-wrap:wrap; margin-top:5px; border-top:1px dashed #ddd; padding-top:5px;'>
                                    <span style='flex:1; min-width:80px;'>🩸 콜레스테롤: <b>{float(chol):.1f}mg</b></span>
                                    <span style='flex:1; min-width:80px;'>🧈 포화지방: <b>{float(sat_fat):.1f}g</b></span>
                                    <span style='flex:1; min-width:80px;'>⚠️ 트랜스지방: <b>{float(trans_fat):.1f}g</b></span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.info("ℹ️ 식약처 공공데이터에서 해당 제품의 상세 영양성분 정보를 찾을 수 없습니다.")

                        highlighted = raw_materials
                        for k in found_allergens:
                            highlighted = highlighted.replace(k, f"<strong style='color:#d63031; background-color:#ffeaea;'>{k}</strong>")
                        for k in found_warnings:
                            highlighted = highlighted.replace(k, f"<strong style='color:#e17055; background-color:#fff0e6;'>{k}</strong>")
                        for k in found_sweeteners:
                            highlighted = highlighted.replace(k, f"<strong style='color:#0984e3; background-color:#e6f3ff;'>{k}</strong>")
                        st.markdown(highlighted, unsafe_allow_html=True)
                    
                    st.divider()

        if has_more:
            if st.button("더 보기 (More)", use_container_width=True):
                st.session_state.page_limit += 20
                st.rerun()

        # 데이터 업데이트 날짜 확인
        try:
            db_mtime = os.path.getmtime("snacks.db")
            last_updated = datetime.fromtimestamp(db_mtime).strftime('%Y-%m-%d')
        except:
            last_updated = "-"

        st.markdown(f"""
            <br><br>
            <div style='text-align:center; color:#ccc; font-size:0.8em;'>
                데이터 출처: 식품의약품안전처 공공데이터 <br>
                created by: Jooie Kwon | Last Updated: {last_updated}
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()