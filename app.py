import subprocess
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

app = FastAPI()

@app.post("/generate-reel")
async def generate_reel(payload: dict):
    image_url = payload.get("image_url")
    if not image_url:
        raise HTTPException(status_code=400, detail="Missing image_url field")

    input_jpg = "temp_input.jpg"
    output_mp4 = "output_reel.mp4"

    try:
        # Pobieranie obrazu z weryfikacją nagłówka
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()

        # Zabezpieczenie: sprawdzenie czy pobrano obraz, a nie stronę HTML
        content_type = response.headers.get("Content-Type", "")
        if "image" not in content_type and "octet-stream" not in content_type:
            raise HTTPException(
                status_code=400, 
                detail=f"URL did not return an image. Received Content-Type: {content_type}"
            )

        with open(input_jpg, "wb") as f:
            f.write(response.content)

        # Komenda FFmpeg
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", input_jpg,
            "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,zoompan=z='min(zoom+0.0015,1.15)':d=125:fps=25:s=720x1280:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "stillimage",
            "-t", "5",
            "-pix_fmt", "yuv420p",
            output_mp4
        ]

        # Wywołanie z zabezpieczeniem przed deadlockiem i sztywnym limit czasu 30s
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=True
        )

        return FileResponse(output_mp4, media_type="video/mp4")

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="FFmpeg execution timed out after 30s")
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"FFmpeg error: {e.stderr[-500:]}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
