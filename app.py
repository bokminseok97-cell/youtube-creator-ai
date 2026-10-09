
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 기본 설정
st.set_page_config(
    page_title="AI 유튜버 매칭",
    page_icon="🎬",
    layout="wide"
)

# .env 파일에서 API 키 불러오기
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
api_key = os.getenv("YOUTUBE_API_KEY")

st.title("🎬 AI 유튜버 매칭 시스템")
st.write("제품 정보와 검색 조건을 바탕으로 실제 유튜브 채널을 검색합니다.")

st.divider()

# 1. 제품 정보
st.header("1. 제품 정보")

product_name = st.text_input("제품명")

product_description = st.text_area(
    "제품 설명",
    placeholder="제품의 특징, 성분, 장점 등을 입력하세요."
)

target_age = st.text_input(
    "타깃 연령",
    placeholder="예: 40~60대"
)

category = st.selectbox(
    "카테고리",
    ["건강", "뷰티", "식품", "라이프스타일", "운동", "기타"]
)

interest = st.text_input(
    "주요 관심사",
    placeholder="예: 항산화, 건강관리"
)

extra_keywords = st.text_input(
    "추가 검색어",
    placeholder="예: 하스카프베리, 건강식품 리뷰, 건강 식단"
)

st.divider()

# 2. 검색 조건
st.header("2. 검색 조건")

min_subscribers = st.number_input(
    "최소 구독자 수",
    min_value=0,
    value=1000,
    step=1000
)

max_subscribers = st.number_input(
    "최대 구독자 수",
    min_value=0,
    value=10000000,
    step=1000
)

# 3. 검색 실행
if st.button("유튜버 찾기", type="primary"):

    if not api_key:
        st.error(".env 파일에서 API 키를 찾지 못했습니다.")

    elif not product_name.strip():
        st.warning("제품명을 입력해주세요.")

    elif min_subscribers > max_subscribers:
        st.warning("최소 구독자 수를 최대 구독자 수 이하로 설정해주세요.")

    else:
        extra_list = [
            word.strip()
            for word in extra_keywords.split(",")
            if word.strip()
        ]

        keywords = list(dict.fromkeys([
            product_name.strip(),
            interest.strip(),
            *extra_list,
            f"{category} 유튜버",
            f"{target_age} {category}" if target_age.strip() else ""
        ]))

        keywords = [word for word in keywords if word][:5]

        try:
            youtube = build(
                "youtube",
                "v3",
                developerKey=api_key,
                cache_discovery=False
            )

            channels = {}

            with st.spinner("유튜브 채널을 검색하고 있습니다..."):
                for keyword in keywords:
                    response = youtube.search().list(
                        part="snippet",
                        q=keyword,
                        type="channel",
                        maxResults=10
                    ).execute()

                    for item in response.get("items", []):
                        channel_id = item["snippet"]["channelId"]
                        channels[channel_id] = item["snippet"]["title"]

                channel_ids = list(channels.keys())
                details = []

                for start in range(0, len(channel_ids), 50):
                    batch = channel_ids[start:start + 50]

                    response = youtube.channels().list(
                        part="snippet,statistics",
                        id=",".join(batch),
                        maxResults=50
                    ).execute()

                    details.extend(response.get("items", []))

            results = []

            for channel in details:
                snippet = channel.get("snippet", {})
                stats = channel.get("statistics", {})

                subscriber_count = (
                    int(stats["subscriberCount"])
                    if "subscriberCount" in stats
                    else None
                )

                if subscriber_count is None:
                    continue

                if not (
                    min_subscribers
                    <= subscriber_count
                    <= max_subscribers
                ):
                    continue

                results.append({
                    "채널명": snippet.get("title", ""),
                    "구독자 수": subscriber_count,
                    "총 조회수": int(stats.get("viewCount", 0)),
                    "영상 수": int(stats.get("videoCount", 0)),
                    "채널 설명": snippet.get("description", ""),
                    "채널 URL": (
                        "https://www.youtube.com/channel/"
                        + channel["id"]
                    )
                })

            st.subheader("3. 검색 결과")

            if results:
                df = pd.DataFrame(results)
                df = df.sort_values(
                    "구독자 수",
                    ascending=False
                )

                st.success(f"{len(df)}개 채널을 찾았습니다.")

                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "채널 URL": st.column_config.LinkColumn(
                            "채널 URL"
                        )
                    }
                )

                csv_data = df.to_csv(
                    index=False
                ).encode("utf-8-sig")

                st.download_button(
                    "검색 결과 CSV 다운로드",
                    data=csv_data,
                    file_name="youtube_channels.csv",
                    mime="text/csv"
                )

            else:
                st.warning(
                    "조건에 맞는 채널이 없습니다. "
                    "검색어 또는 구독자 범위를 바꿔보세요."
                )

        except HttpError as error:
            st.error("YouTube API 요청 중 오류가 발생했습니다.")
            st.code(str(error))

        except Exception as error:
            st.error("오류가 발생했습니다.")
            st.code(str(error))

