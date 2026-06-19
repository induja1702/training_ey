import yt_dlp

def download_video(url):
    output_file = "video.mp4"

    ydl_opts = {
        "format": "mp4",
        "outtmpl": output_file
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return output_file