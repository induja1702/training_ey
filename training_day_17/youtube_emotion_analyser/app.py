import asyncio

from youtube_downloader import download_video
from hume_client import analyze_video
from hume_client import save_json

# https://www.youtube.com/shorts/Y20Zcm9JFSc
YOUTUBE_URL = input("Enter YouTube URL: ")

video_file = download_video(YOUTUBE_URL)



results = asyncio.run(
    analyze_video(video_file)
)
print(results, type(results))
save_json(results)


