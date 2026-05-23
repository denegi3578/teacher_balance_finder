import os
import json
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px


# =========================
# 기본 설정
# =========================

st.set_page_config(
    page_title="Teacher Balance Simulator",
    layout="wide"
)

st.title("Teacher Balance Simulator")
st.subheader("시·도별 교원 1인당 학생 수 불균형 분석 및 신규 교원 충원 효과 시뮬레이터")

st.write(
    "이 프로그램은 교육통계 데이터를 바탕으로 시·도별 교원 1인당 학생 수를 분석하고, "
    "신규 교원이나 추가 정원이 확보되었을 때 어느 지역에 우선 배정하면 좋을지 가상으로 시뮬레이션합니다. "
    "기존 교사를 강제로 이동시키는 것이 아니라, 새롭게 확보되는 교원 자원을 어떻게 배분할지 판단하는 참고 도구입니다."
)


# =========================
# 데이터 불러오기
# =========================

def read_csv_safely(file_name):
    try:
        return pd.read_csv(file_name, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(file_name, encoding="cp949")


@st.cache_data
def load_data():
    balance = read_csv_safely("teacher_balance.csv")
    recommend = read_csv_safely("priority_recommendation.csv")
    return balance, recommend


try:
    balance, recommend = load_data()
except FileNotFoundError as e:
    st.error(f"필수 CSV 파일을 찾을 수 없습니다: {e}")
    st.stop()


required_balance_cols = [
    "year",
    "region",
    "school_level",
    "student_count",
    "teacher_count",
    "students_per_teacher",
    "national_avg",
    "gap_from_avg",
    "priority_score"
]

required_recommend_cols = [
    "year",
    "school_level",
    "priority_rank",
    "region",
    "students_per_teacher",
    "national_avg",
    "priority_score",
    "recommendation"
]

missing_balance = [c for c in required_balance_cols if c not in balance.columns]
missing_recommend = [c for c in required_recommend_cols if c not in recommend.columns]

if missing_balance:
    st.error(f"teacher_balance.csv에 다음 컬럼이 없습니다: {missing_balance}")
    st.stop()

if missing_recommend:
    st.error(f"priority_recommendation.csv에 다음 컬럼이 없습니다: {missing_recommend}")
    st.stop()


# 숫자형 변환
numeric_cols = [
    "year",
    "student_count",
    "teacher_count",
    "students_per_teacher",
    "national_avg",
    "gap_from_avg",
    "priority_score"
]

for col in numeric_cols:
    balance[col] = pd.to_numeric(balance[col], errors="coerce")

recommend["year"] = pd.to_numeric(recommend["year"], errors="coerce")
recommend["priority_rank"] = pd.to_numeric(recommend["priority_rank"], errors="coerce")
recommend["students_per_teacher"] = pd.to_numeric(recommend["students_per_teacher"], errors="coerce")
recommend["national_avg"] = pd.to_numeric(recommend["national_avg"], errors="coerce")
recommend["priority_score"] = pd.to_numeric(recommend["priority_score"], errors="coerce")

# 전국 행이 있으면 제외
balance = balance[~balance["region"].astype(str).str.contains("전국", na=False)].copy()
recommend = recommend[~recommend["region"].astype(str).str.contains("전국", na=False)].copy()

balance = balance.dropna(subset=["year", "region", "school_level"])
recommend = recommend.dropna(subset=["year", "region", "school_level"])


# =========================
# 사이드바 입력
# =========================

st.sidebar.header("분석 조건 선택")

years = sorted(balance["year"].dropna().astype(int).unique())
selected_year = st.sidebar.selectbox("분석 연도 선택", years, index=len(years) - 1)

school_levels = sorted(balance["school_level"].dropna().unique())
selected_level = st.sidebar.selectbox("학교급 선택", school_levels)

filtered = balance[
    (balance["year"].astype(int) == int(selected_year)) &
    (balance["school_level"] == selected_level)
].copy()

if filtered.empty:
    st.warning("해당 조건의 데이터가 없습니다.")
    st.stop()

filtered = filtered.sort_values("students_per_teacher", ascending=False).reset_index(drop=True)

selected_recommend = recommend[
    (recommend["year"].astype(int) == int(selected_year)) &
    (recommend["school_level"] == selected_level)
].copy()


# =========================
# 핵심 지표 카드
# =========================

st.divider()
st.header("1. 핵심 지표 요약")

national_avg = float(filtered["national_avg"].iloc[0])
max_row = filtered.loc[filtered["students_per_teacher"].idxmax()]
min_row = filtered.loc[filtered["students_per_teacher"].idxmin()]
gap_value = max_row["students_per_teacher"] - min_row["students_per_teacher"]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("전국 평균", f"{national_avg:.2f}명")

with col2:
    st.metric("교원 부담 최고 지역", f"{max_row['region']}", f"{max_row['students_per_teacher']:.2f}명")

with col3:
    st.metric("교원 부담 최저 지역", f"{min_row['region']}", f"{min_row['students_per_teacher']:.2f}명")

with col4:
    st.metric("지역 간 격차", f"{gap_value:.2f}명")


# =========================
# 막대그래프
# =========================

st.divider()
st.header(f"2. {selected_year}년 {selected_level} 시·도별 교원 1인당 학생 수")

fig_bar = px.bar(
    filtered,
    x="region",
    y="students_per_teacher",
    color="students_per_teacher",
    color_continuous_scale="Reds",
    title=f"{selected_year}년 {selected_level} 시·도별 교원 1인당 학생 수",
    labels={
        "region": "시·도",
        "students_per_teacher": "교원 1인당 학생 수"
    },
    hover_data={
        "student_count": True,
        "teacher_count": True,
        "national_avg": ":.2f",
        "priority_score": ":.1f"
    }
)

fig_bar.add_hline(
    y=national_avg,
    line_dash="dash",
    annotation_text=f"전국 평균 {national_avg:.2f}명",
    annotation_position="top left"
)

st.plotly_chart(fig_bar, use_container_width=True)

st.write(
    "막대가 전국 평균선보다 높을수록 교원 1명이 담당하는 학생 수가 많은 지역입니다. "
    "이는 해당 지역의 교원 부담이 상대적으로 클 수 있음을 의미합니다."
)


# =========================
# 지도 시각화
# =========================

st.divider()
st.header("3. 대한민국 시·도별 교원 1인당 학생 수 지도")

region_name_map = {
    "서울": "Seoul",
    "서울특별시": "Seoul",
    "부산": "Busan",
    "부산광역시": "Busan",
    "대구": "Daegu",
    "대구광역시": "Daegu",
    "인천": "Incheon",
    "인천광역시": "Incheon",
    "광주": "Gwangju",
    "광주광역시": "Gwangju",
    "대전": "Daejeon",
    "대전광역시": "Daejeon",
    "울산": "Ulsan",
    "울산광역시": "Ulsan",
    "세종": "Sejong",
    "세종특별자치시": "Sejong",
    "경기": "Gyeonggi-do",
    "경기도": "Gyeonggi-do",
    "강원": "Gangwon-do",
    "강원도": "Gangwon-do",
    "강원특별자치도": "Gangwon-do",
    "충북": "Chungcheongbuk-do",
    "충청북도": "Chungcheongbuk-do",
    "충남": "Chungcheongnam-do",
    "충청남도": "Chungcheongnam-do",
    "전북": "Jeollabuk-do",
    "전라북도": "Jeollabuk-do",
    "전북특별자치도": "Jeollabuk-do",
    "전남": "Jeollanam-do",
    "전라남도": "Jeollanam-do",
    "경북": "Gyeongsangbuk-do",
    "경상북도": "Gyeongsangbuk-do",
    "경남": "Gyeongsangnam-do",
    "경상남도": "Gyeongsangnam-do",
    "제주": "Jeju-do",
    "제주도": "Jeju-do",
    "제주특별자치도": "Jeju-do",
}

geojson_path = "korea_sido.geojson"

if os.path.exists(geojson_path):
    try:
        with open(geojson_path, "r", encoding="utf-8") as f:
            korea_geojson = json.load(f)

        map_df = filtered.copy()
        map_df["geo_name"] = map_df["region"].map(region_name_map)

        if map_df["geo_name"].isna().any():
            missing_regions = map_df[map_df["geo_name"].isna()]["region"].unique()
            st.warning(f"지도 지역명 매핑이 안 된 지역이 있습니다: {missing_regions}")

        fig_map = px.choropleth(
            map_df,
            geojson=korea_geojson,
            locations="geo_name",
            featureidkey="properties.NAME_1",
            color="students_per_teacher",
            hover_name="region",
            hover_data={
                "students_per_teacher": ":.2f",
                "national_avg": ":.2f",
                "priority_score": ":.1f",
                "geo_name": False
            },
            color_continuous_scale="Reds",
            title=f"{selected_year}년 {selected_level} 시·도별 교원 1인당 학생 수 지도",
            labels={
                "students_per_teacher": "교원 1인당 학생 수"
            }
        )

        fig_map.update_geos(
            fitbounds="locations",
            visible=False
        )

        fig_map.update_layout(
            margin={"r": 0, "t": 50, "l": 0, "b": 0}
        )

        st.plotly_chart(fig_map, use_container_width=True)

        st.write(
            "지도에서 색이 진할수록 교원 1인당 학생 수가 높은 지역입니다. "
            "표나 막대그래프만으로는 보기 어려운 지역적 분포를 공간적으로 확인할 수 있습니다."
        )

    except Exception as e:
        st.warning(f"지도 시각화 중 오류가 발생했습니다: {e}")
else:
    st.warning(
        "korea_sido.geojson 파일이 없어 지도 시각화를 건너뜁니다. "
        "GitHub 저장소에 korea_sido.geojson 파일을 추가하면 지도가 표시됩니다."
    )


# =========================
# TOP 10 표
# =========================

st.divider()
st.header("4. 교원 부담 지역 비교")

high = filtered.sort_values("priority_score", ascending=False).head(10)
low = filtered.sort_values("priority_score", ascending=True).head(10)

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("교원 부담 높은 지역 TOP 10")
    st.dataframe(
        high[[
            "region",
            "student_count",
            "teacher_count",
            "students_per_teacher",
            "national_avg",
            "gap_from_avg",
            "priority_score"
        ]].rename(columns={
            "region": "지역",
            "student_count": "학생 수",
            "teacher_count": "교원 수",
            "students_per_teacher": "교원 1인당 학생 수",
            "national_avg": "전국 평균",
            "gap_from_avg": "평균 대비 차이",
            "priority_score": "우선점수(%)"
        }),
        use_container_width=True
    )

with col_right:
    st.subheader("상대적으로 여유 있는 지역 TOP 10")
    st.dataframe(
        low[[
            "region",
            "student_count",
            "teacher_count",
            "students_per_teacher",
            "national_avg",
            "gap_from_avg",
            "priority_score"
        ]].rename(columns={
            "region": "지역",
            "student_count": "학생 수",
            "teacher_count": "교원 수",
            "students_per_teacher": "교원 1인당 학생 수",
            "national_avg": "전국 평균",
            "gap_from_avg": "평균 대비 차이",
            "priority_score": "우선점수(%)"
        }),
        use_container_width=True
    )


# =========================
# 우선순위 추천
# =========================

st.divider()
st.header("5. 신규 교원 배치 지원 우선순위")

if selected_recommend.empty:
    st.warning("해당 조건의 추천 데이터가 없습니다.")
else:
    selected_recommend = selected_recommend.sort_values("priority_rank")

    st.dataframe(
        selected_recommend[[
            "priority_rank",
            "region",
            "students_per_teacher",
            "national_avg",
            "priority_score",
            "recommendation"
        ]].rename(columns={
            "priority_rank": "순위",
            "region": "지역",
            "students_per_teacher": "교원 1인당 학생 수",
            "national_avg": "전국 평균",
            "priority_score": "우선점수(%)",
            "recommendation": "추천 내용"
        }),
        use_container_width=True
    )

    st.subheader("주요 추천 결과")

    for _, row in selected_recommend.head(5).iterrows():
        st.success(
            f"{int(row['priority_rank'])}순위: {row['region']} "
            f"→ 교원 1인당 학생 수 {row['students_per_teacher']:.2f}명, "
            f"전국 평균 대비 {row['priority_score']:.1f}% 높음. "
            f"{row['recommendation']}"
        )


# =========================
# 신규 교원 충원 효과 시뮬레이터
# =========================

st.divider()
st.header("6. 신규 교원 충원 효과 시뮬레이터")

st.write(
    "이 기능은 기존 교사를 다른 지역으로 이동시키는 것이 아니라, "
    "새로 확보되는 신규 교원이나 추가 정원을 어느 지역에 우선 배정할지 가정하여 "
    "교원 1인당 학생 수가 얼마나 개선되는지 계산합니다."
)

additional_teachers = st.slider(
    "추가 확보 가능한 신규 교원 수를 선택하세요",
    min_value=0,
    max_value=5000,
    value=500,
    step=50
)

allocation_method = st.selectbox(
    "신규 교원 배정 방식 선택",
    [
        "평균 초과분 비례 배정",
        "우선순위 높은 지역부터 집중 배정",
        "과밀 지역 균등 배정"
    ]
)

target_df = filtered[filtered["students_per_teacher"] > filtered["national_avg"]].copy()

if target_df.empty:
    st.info("전국 평균보다 교원 1인당 학생 수가 높은 지역이 없어 추가 배정 대상이 없습니다.")
else:
    target_df = target_df.sort_values("priority_score", ascending=False).reset_index(drop=True)
    target_df["extra_teachers"] = 0

    def allocate_by_largest_remainder(df, total, weight_col):
        if total <= 0 or df[weight_col].sum() <= 0:
            return np.zeros(len(df), dtype=int)

        raw = total * df[weight_col] / df[weight_col].sum()
        base = np.floor(raw).astype(int)
        remainder = int(total - base.sum())

        fractions = raw - base
        order = np.argsort(-fractions.values)

        allocation = base.values.copy()
        for idx in order[:remainder]:
            allocation[idx] += 1

        return allocation

    if additional_teachers > 0:
        if allocation_method == "평균 초과분 비례 배정":
            target_df["excess_load"] = (
                target_df["student_count"] - target_df["national_avg"] * target_df["teacher_count"]
            ).clip(lower=0)

            target_df["extra_teachers"] = allocate_by_largest_remainder(
                target_df,
                additional_teachers,
                "excess_load"
            )

        elif allocation_method == "우선순위 높은 지역부터 집중 배정":
            # 전국 평균 수준에 가까워질 때까지 높은 순위 지역부터 배정
            remaining = additional_teachers
            allocations = []

            for _, row in target_df.iterrows():
                if remaining <= 0:
                    allocations.append(0)
                    continue

                needed_to_avg = int(np.ceil(row["student_count"] / row["national_avg"] - row["teacher_count"]))
                needed_to_avg = max(needed_to_avg, 0)

                give = min(remaining, needed_to_avg)
                allocations.append(give)
                remaining -= give

            # 평균 초과 지역을 모두 보정하고도 남으면 우선순위 순서로 1명씩 추가 배정
            i = 0
            while remaining > 0 and len(allocations) > 0:
                allocations[i % len(allocations)] += 1
                remaining -= 1
                i += 1

            target_df["extra_teachers"] = allocations

        elif allocation_method == "과밀 지역 균등 배정":
            base = additional_teachers // len(target_df)
            remain = additional_teachers % len(target_df)

            allocations = np.array([base] * len(target_df))
            if remain > 0:
                allocations[:remain] += 1

            target_df["extra_teachers"] = allocations

    target_df["new_teacher_count"] = target_df["teacher_count"] + target_df["extra_teachers"]

    target_df["after_students_per_teacher"] = (
        target_df["student_count"] / target_df["new_teacher_count"]
    )

    target_df["improvement"] = (
        target_df["students_per_teacher"] - target_df["after_students_per_teacher"]
    )

    target_df["before_gap"] = (
        target_df["students_per_teacher"] - target_df["national_avg"]
    )

    target_df["after_gap"] = (
        target_df["after_students_per_teacher"] - target_df["national_avg"]
    )

    result_df = target_df[[
        "region",
        "student_count",
        "teacher_count",
        "extra_teachers",
        "new_teacher_count",
        "students_per_teacher",
        "after_students_per_teacher",
        "improvement",
        "national_avg",
        "before_gap",
        "after_gap"
    ]].copy()

    result_df = result_df.sort_values("improvement", ascending=False).reset_index(drop=True)

    st.subheader("신규 교원 배정 시뮬레이션 결과")

    st.dataframe(
        result_df.rename(columns={
            "region": "지역",
            "student_count": "학생 수",
            "teacher_count": "기존 교원 수",
            "extra_teachers": "추가 배정 교원 수",
            "new_teacher_count": "배정 후 교원 수",
            "students_per_teacher": "기존 교원 1인당 학생 수",
            "after_students_per_teacher": "개선 후 교원 1인당 학생 수",
            "improvement": "개선량",
            "national_avg": "전국 평균",
            "before_gap": "기존 평균 초과분",
            "after_gap": "개선 후 평균 초과분"
        }),
        use_container_width=True
    )

    before_max = target_df["students_per_teacher"].max()
    after_max = target_df["after_students_per_teacher"].max()

    before_avg_gap = target_df["before_gap"].mean()
    after_avg_gap = target_df["after_gap"].mean()
    gap_reduction = before_avg_gap - after_avg_gap

    before_total_gap = target_df["before_gap"].clip(lower=0).sum()
    after_total_gap = target_df["after_gap"].clip(lower=0).sum()

    if before_total_gap > 0:
        gap_reduction_rate = (before_total_gap - after_total_gap) / before_total_gap * 100
    else:
        gap_reduction_rate = 0

    col_a, col_b, col_c, col_d = st.columns(4)

    with col_a:
        st.metric(
            "최대 교원 부담 변화",
            f"{after_max:.2f}명",
            delta=f"{after_max - before_max:.2f}명"
        )

    with col_b:
        st.metric(
            "평균 초과분 감소",
            f"{gap_reduction:.2f}명"
        )

    with col_c:
        st.metric(
            "초과 부담 감소율",
            f"{gap_reduction_rate:.1f}%"
        )

    with col_d:
        st.metric(
            "추가 배정 교원 수",
            f"{int(target_df['extra_teachers'].sum())}명"
        )

    compare_df = result_df[[
        "region",
        "students_per_teacher",
        "after_students_per_teacher"
    ]].copy()

    compare_df = compare_df.rename(columns={
        "students_per_teacher": "기존",
        "after_students_per_teacher": "개선 후"
    })

    compare_long = compare_df.melt(
        id_vars="region",
        value_vars=["기존", "개선 후"],
        var_name="구분",
        value_name="교원 1인당 학생 수"
    )

    fig_sim = px.bar(
        compare_long,
        x="region",
        y="교원 1인당 학생 수",
        color="구분",
        barmode="group",
        title="신규 교원 배정 전후 교원 1인당 학생 수 비교",
        labels={
            "region": "지역",
            "교원 1인당 학생 수": "교원 1인당 학생 수"
        }
    )

    fig_sim.add_hline(
        y=national_avg,
        line_dash="dash",
        annotation_text="전국 평균",
        annotation_position="top left"
    )

    st.plotly_chart(fig_sim, use_container_width=True)

    st.write(
        "이 시뮬레이션은 실제 교원 인사 발령을 의미하지 않습니다. "
        "신규 교원 정원, 기간제 교원, 추가 충원 인원 등이 확보되었을 때 "
        "어느 지역에 우선 배정하면 지표가 얼마나 완화될 수 있는지 확인하기 위한 가상 분석입니다."
    )


# =========================
# 지표 해석
# =========================

st.divider()
st.header("7. 지표 해석 및 한계")

st.write(
    "교원 1인당 학생 수는 학생 수를 교원 수로 나눈 값입니다. "
    "이 값이 높을수록 교원 1명이 담당하는 학생 수가 많아 상대적으로 교육 부담이 클 수 있습니다. "
    "본 프로그램은 같은 연도와 같은 학교급의 전국 평균을 기준으로 각 시·도가 평균보다 얼마나 높은지 계산하고, "
    "그 차이가 큰 지역을 신규 교원 배치 지원 우선순위가 높은 지역으로 제시했습니다."
)

st.write(
    "다만 실제 교원 배치는 단순히 교원 1인당 학생 수만으로 결정될 수 없습니다. "
    "교과별 수요, 학교별 정원, 지역별 생활 여건, 교육청 인사 규정, 농어촌·도서벽지 조건 등 다양한 요소가 함께 고려되어야 합니다. "
    "따라서 본 프로그램은 실제 인사 결정을 직접 대체하는 것이 아니라, 신규 교원 충원이나 추가 정원 배정을 검토할 때 활용할 수 있는 기초 참고 도구입니다."
)