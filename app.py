import os
import subprocess
import uuid
import requests
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

app = FastAPI()

def cleanup_files(*file_paths):
    for path in file_paths:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

@app.post("/generate-reel")
def generate_reel(payload: dict, background_tasks: BackgroundTasks):
    image_url = payload.get("image_url")
    if not image_url:
        raise HTTPException(status_code=400, detail="Missing image_url field")

    session_id = str(uuid.uuid4())
    input_jpg = f"/tmp/{session_id}_input.jpg"
    output_mp4 = f"/tmp/{session_id}_output.mp4"

    try:
        res = requests.get(image_url, timeout=15)
        res.raise_for_status()
        with open(input_jpg, "wb") as f:
            f.write(res.content)

ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-loop", "1",
    "-i", input_jpg,
    "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,zoompan=z='min(zoom+0.0015,1.15)':d=150:s=720x1280:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-tune", "stillimage",
    "-t", "5",
    "-pix_fmt", "yuv420p",
    output_mp4
]

        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        background_tasks.add_task(cleanup_files, input_jpg, output_mp4)

        return FileResponse(
            path=output_mp4,
            media_type="video/mp4",
            filename=f"reel_{session_id}.mp4"
        )

    except Exception as e:
        cleanup_files(input_jpg, output_mp4)
        raise HTTPException(status_code=500, detail=str(e))
