from yt_client.yt_client import YouTubeCLient

keyword = "cárteles de México"
published_after = "2023-10-01T00:00:00Z"
published_before = "2023-10-31T23:59:59Z"

keyword = "cárteles de México"
published_after = "2023-10-01T00:00:00Z"
published_before = "2023-10-31T23:59:59Z"

keyword_videos = YouTubeCLient(api_key="AIzaSyANk4ZcIKiISIMDlL9ZZLvJEnigwru3-BI").get_videos_by_keyword(
    keyword=keyword,
    published_after=published_after,
    published_before=published_before
)

print(f'Got {len(keyword_videos)} videos for keyword "{keyword}"')