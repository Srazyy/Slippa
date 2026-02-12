"""
Flask web application for Slippa.

This is the web UI that lets users interact with the pipeline
through a browser instead of the command line.

Routes:
    /              → Dashboard (paste YouTube URL or upload file)
    /process       → POST: starts processing a video
    /status/<id>   → GET: returns processing status (JSON, for polling)
    /results/<id>  → Results page with clip previews
    /download/<id>/<clip> → Download a specific clip
    /clips/<path>  → Serve clip video files
    /youtube/auth  → Start YouTube OAuth2 login
    /oauth/callback → Handle OAuth2 callback
    /upload        → POST: upload a clip to YouTube
    /upload-status → GET: check upload status
"""

import os
import uuid
import threading
from flask import (
    Flask, render_template, request, jsonify,
    send_from_directory, redirect, url_for
)

from slippa.downloader import download_video
from slippa.transcriber import transcribe_audio
from slippa.clipper import find_clips
from slippa.cutter import cut_clips
from slippa import uploader

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
)

# Store processing jobs in memory (simple approach for MVP)
# Key: job_id, Value: dict with status, progress, clips, error
jobs = {}

# Track upload status per clip
upload_jobs = {}

CLIPS_BASE_DIR = "clips"
DOWNLOADS_DIR = "downloads"


def _process_video(job_id: str, source: str):
    """
    Background thread function that runs the full pipeline.
    Updates the job dict as it progresses so the UI can poll for status.
    """
    job = jobs[job_id]

    try:
        # Step 1: Download (if URL)
        job["status"] = "downloading"
        job["progress"] = "Downloading video..."

        if source.startswith(("http://", "https://", "www.")):
            video_path = download_video(source, output_dir=DOWNLOADS_DIR)
        else:
            video_path = source

        job["video_title"] = os.path.splitext(os.path.basename(video_path))[0]
        job["progress"] = f"Downloaded: {job['video_title']}"

        # Step 2: Transcribe
        job["status"] = "transcribing"
        job["progress"] = "Transcribing audio with Whisper (this takes a bit)..."

        segments = transcribe_audio(video_path)
        job["progress"] = f"Transcribed {len(segments)} segments"

        # Step 3: Find clips
        job["status"] = "analyzing"
        job["progress"] = "Analyzing transcript for best clips..."

        clips = find_clips(segments)
        job["progress"] = f"Found {len(clips)} clips"

        if not clips:
            job["status"] = "done"
            job["progress"] = "No clips found in this video."
            job["clips"] = []
            return

        # Step 4: Cut clips
        job["status"] = "cutting"
        job["progress"] = "Cutting clips with ffmpeg..."

        clip_output_dir = os.path.join(CLIPS_BASE_DIR, job_id)
        clip_paths = cut_clips(video_path, clips, output_dir=clip_output_dir)

        # Build clip info for the UI
        clip_info = []
        for i, (path, clip_data) in enumerate(zip(clip_paths, clips)):
            duration = clip_data["end"] - clip_data["start"]
            clip_info.append({
                "index": i + 1,
                "filename": os.path.basename(path),
                "start": round(clip_data["start"], 1),
                "end": round(clip_data["end"], 1),
                "duration": round(duration, 1),
                "score": clip_data["score"],
                "text": clip_data.get("text", "")[:200],
                "size_kb": round(os.path.getsize(path) / 1024, 1),
            })

        job["clips"] = clip_info
        job["status"] = "done"
        job["progress"] = f"Done! {len(clip_info)} clips ready."

    except Exception as e:
        job["status"] = "error"
        job["progress"] = f"Error: {str(e)}"
        job["error"] = str(e)


@app.route("/")
def index():
    """Dashboard page."""
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    """Start processing a video."""
    source = request.form.get("source", "").strip()

    if not source:
        return jsonify({"error": "No source provided"}), 400

    # Create a new job
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "starting",
        "progress": "Starting...",
        "clips": [],
        "video_title": "",
        "error": None,
    }

    # Run pipeline in background thread
    thread = threading.Thread(target=_process_video, args=(job_id, source))
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/status/<job_id>")
def status(job_id):
    """Poll for job status."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/results/<job_id>")
def results(job_id):
    """Results page with clip previews."""
    job = jobs.get(job_id)
    if not job:
        return redirect(url_for("index"))
    return render_template("results.html", job_id=job_id, job=job)


@app.route("/clips/<job_id>/<filename>")
def serve_clip(job_id, filename):
    """Serve a clip video file for preview/download."""
    clip_dir = os.path.join(os.getcwd(), CLIPS_BASE_DIR, job_id)
    return send_from_directory(clip_dir, filename)


@app.route("/download/<job_id>/<filename>")
def download_clip(job_id, filename):
    """Download a clip file."""
    clip_dir = os.path.join(os.getcwd(), CLIPS_BASE_DIR, job_id)
    return send_from_directory(clip_dir, filename, as_attachment=True)


# ---- YouTube Upload Routes ----

@app.route("/youtube/status")
def youtube_status():
    """Check if YouTube is configured and authenticated."""
    return jsonify({
        "configured": uploader.is_configured(),
        "authenticated": uploader.is_authenticated(),
    })


@app.route("/youtube/auth")
def youtube_auth():
    """Start YouTube OAuth2 flow — redirects to Google login."""
    try:
        auth_url = uploader.get_auth_url()
        return redirect(auth_url)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/oauth/callback")
def oauth_callback():
    """Handle OAuth2 callback from Google."""
    try:
        uploader.handle_oauth_callback(request.url)
        return render_template("auth_success.html")
    except Exception as e:
        return jsonify({"error": f"Authentication failed: {str(e)}"}), 400


@app.route("/upload", methods=["POST"])
def upload_clip_to_youtube():
    """Upload a clip to YouTube."""
    data = request.get_json()
    job_id = data.get("job_id")
    filename = data.get("filename")
    title = data.get("title", filename)
    description = data.get("description", "Generated by Slippa")
    privacy = data.get("privacy", "private")

    if not job_id or not filename:
        return jsonify({"error": "Missing job_id or filename"}), 400

    if not uploader.is_authenticated():
        return jsonify({"error": "Not authenticated. Please log in first.", "need_auth": True}), 401

    clip_path = os.path.join(os.getcwd(), CLIPS_BASE_DIR, job_id, filename)
    if not os.path.exists(clip_path):
        return jsonify({"error": "Clip file not found"}), 404

    # Track this upload
    upload_id = f"{job_id}_{filename}"
    upload_jobs[upload_id] = {"status": "uploading", "progress": "Starting upload...", "result": None}

    def _do_upload():
        try:
            result = uploader.upload_video(
                file_path=clip_path,
                title=title,
                description=description,
                privacy_status=privacy,
            )
            upload_jobs[upload_id] = {"status": "done", "progress": "Uploaded!", "result": result}
        except Exception as e:
            upload_jobs[upload_id] = {"status": "error", "progress": str(e), "result": None}

    thread = threading.Thread(target=_do_upload)
    thread.daemon = True
    thread.start()

    return jsonify({"upload_id": upload_id})


@app.route("/upload-status/<upload_id>")
def upload_status(upload_id):
    """Poll upload status."""
    job = upload_jobs.get(upload_id)
    if not job:
        return jsonify({"error": "Upload not found"}), 404
    return jsonify(job)


def run_web():
    """Start the web server."""
    yt_status = "✅ configured" if uploader.is_configured() else "❌ no client_secrets.json"
    print(f"\n🌐 Slippa Web UI running at: http://localhost:5000")
    print(f"📤 YouTube upload: {yt_status}\n")
    app.run(debug=True, port=5000, use_reloader=False)


if __name__ == "__main__":
    run_web()
