import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Teacher Balance Finder",
    layout="wide"
)

st.title("Teacher Balance Finder")
st.subheader("시·도별 교원 1인당 학생 수 불균형 분석 및 교원 배치 지원 우선순위 추천 프로그램")

st.write(
    "이 프로그램은 교육통계 데이터를 바탕으로 시·도별 교원 1인당 학생 수를 분석하고, "
    "전국 평균보다 교원 1인당 학생 수가 높은 지역을 찾아 교원 배치 지원 우선순위를 제시합니다. "
    "단순히 학생 수나 교원 수만 보는 것이 아니라, 교원 1명이 담당하는 학생 수를 기준으로 "
    "지역 간 교육환경의 불균형을 확인하는 데 목적이 있습니다."
)

def read_csv_safely(file_name):
    try:
        return pd.read_csv(file_name, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(file_name, encoding="cp949")

balance = read_csv_safely("teacher_balance.csv")
recommend = read_csv_safely("priority_recommendation.csv")

# 숫자형 변환
num_cols = [
    "student_count",
    "teacher_count",
    "students_per_teacher",
    "national_avg",
    "gap_from_avg",
    "priority_score"
]

for col in num_cols:
    if col in balance.columns:
        balance[col] = pd.to_numeric(balance[col], errors="coerce")

if "priority_score" in recommend.columns:
    recommend["priority_score"] = pd.to_numeric(recommend["priority_score"], errors="coerce")

st.divider()

# 선택 옵션
years = sorted(balance["year"].dropna().unique())
selected_year = st.selectbox("분석 연도 선택", years, index=len(years)-1)

school_levels = sorted(balance["school_level"].dropna().unique())
selected_level = st.selectbox("학교급 선택", school_levels)

filtered = balance[
    (balance["year"] == selected_year) &
    (balance["school_level"] == selected_level)
].copy()

filtered = filtered.sort_values("students_per_teacher", ascending=False)

st.header(f"1. {selected_year}년 {selected_level} 시·도별 교원 1인당 학생 수")

if filtered.empty:
    st.warning("해당 조건의 데이터가 없습니다.")
else:
    avg_value = filtered["national_avg"].iloc[0]

    fig = px.bar(
        filtered,
        x="region",
        y="students_per_teacher",
        title=f"{selected_year}년 {selected_level} 시·도별 교원 1인당 학생 수",
        labels={
            "region": "시·도",
            "students_per_teacher": "교원 1인당 학생 수"
        }
    )

    fig.add_hline(
        y=avg_value,
        line_dash="dash",
        annotation_text=f"전국 평균 {avg_value:.2f}명",
        annotation_position="top left"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.write(
        f"{selected_level} 기준 전국 평균은 약 {avg_value:.2f}명입니다. "
        "막대가 평균선보다 높을수록 교원 1명이 담당하는 학생 수가 상대적으로 많은 지역입니다."
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.header("2. 교원 부담 높은 지역 TOP 10")
        high = filtered.sort_values("priority_score", ascending=False).head(10)
        st.dataframe(
            high[[
                "region",
                "student_count",
                "teacher_count",
                "students_per_teacher",
                "national_avg",
                "priority_score"
            ]],
            use_container_width=True
        )

    with col2:
        st.header("3. 상대적으로 여유 있는 지역 TOP 10")
        low = filtered.sort_values("priority_score", ascending=True).head(10)
        st.dataframe(
            low[[
                "region",
                "student_count",
                "teacher_count",
                "students_per_teacher",
                "national_avg",
                "priority_score"
            ]],
            use_container_width=True
        )

    st.divider()

    st.header("4. 교원 배치 지원 우선순위 추천")

    selected_recommend = recommend[
        (recommend["year"] == selected_year) &
        (recommend["school_level"] == selected_level)
    ].copy()

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
            ]],
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

st.divider()

st.header("5. 지표 해석")

st.write(
    "교원 1인당 학생 수는 학생 수를 교원 수로 나눈 값입니다. "
    "이 값이 높을수록 교원 1명이 담당하는 학생 수가 많아 상대적으로 교육 부담이 클 수 있습니다. "
    "본 프로그램에서는 같은 연도와 같은 학교급의 전국 평균을 기준으로 각 시·도가 평균보다 얼마나 높은지 계산하고, "
    "그 차이가 큰 지역을 교원 배치 지원 우선순위가 높은 지역으로 제시했습니다. "
    "다만 실제 교원 배치는 지역별 교과 수요, 학급 수, 학교 규모, 농어촌·도서벽지 조건 등 다양한 정책 요소를 함께 고려해야 하므로, "
    "본 프로그램의 결과는 교원 배치 정책을 판단하기 위한 기초 참고 자료로 해석해야 합니다."
)