"""
Flask web application for Slippa.

Routes:
    /              → Dashboard (paste YouTube URL or upload file)
    /batch         → Batch processing (multiple URLs)
    /history       → Job history
    /settings      → Settings page
    /process       → POST: starts processing a video
    /batch-process → POST: starts batch processing
    /status/<id>   → GET: returns processing status (JSON)
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
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify,
    send_from_directory, redirect, url_for
)

from slippa.downloader import download_video
from slippa.transcriber import transcribe_audio
from slippa.clipper import find_clips
from slippa.cutter import cut_clips
from slippa import uploader
from config import settings as config

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
)

# In-memory job stores
jobs = {}
upload_jobs = {}

CLIPS_BASE_DIR = "clips"
DOWNLOADS_DIR = "downloads"


def _process_video(job_id: str, source: str):
    """Background thread: runs the full pipeline for one video."""
    job = jobs[job_id]
    settings = config.load_settings()

    try:
        # Step 1: Download
        job["status"] = "downloading"
        job["progress"] = "Downloading video..."

        if source.startswith(("http://", "https://", "www.")):
            video_path = download_video(source, output_dir=settings["download_dir"])
        else:
            video_path = source

        job["video_title"] = os.path.splitext(os.path.basename(video_path))[0]
        job["source"] = source
        job["progress"] = f"Downloaded: {job['video_title']}"

        # Step 2: Transcribe
        job["status"] = "transcribing"
        job["progress"] = f"Transcribing with Whisper ({settings['whisper_model']})..."

        segments = transcribe_audio(video_path, model_size=settings["whisper_model"])
        job["progress"] = f"Transcribed {len(segments)} segments"

        # Step 3: Find clips
        job["status"] = "analyzing"
        job["progress"] = "Analyzing transcript for best clips..."

        clips = find_clips(
            segments,
            min_duration=settings["min_clip_duration"],
            max_duration=settings["max_clip_duration"],
            max_clips=settings["max_clips"],
        )
        job["progress"] = f"Found {len(clips)} clips"

        if not clips:
            job["status"] = "done"
            job["progress"] = "No clips found in this video."
            job["clips"] = []
            return

        # Step 4: Cut clips
        job["status"] = "cutting"
        job["progress"] = "Cutting clips with ffmpeg..."

        clip_output_dir = os.path.join(settings["clips_dir"], job_id)
        clip_paths = cut_clips(video_path, clips, output_dir=clip_output_dir)

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


# ---- Page Routes ----

@app.route("/")
def index():
    return render_template("index.html", page="home")


@app.route("/batch")
def batch_page():
    return render_template("batch.html", page="batch")


@app.route("/history")
def history_page():
    # Sort jobs by time (newest first)
    sorted_jobs = sorted(
        jobs.items(),
        key=lambda x: x[1].get("created_at", ""),
        reverse=True,
    )
    return render_template("history.html", page="history", jobs=sorted_jobs)


@app.route("/settings")
def settings_page():
    current = config.load_settings()
    return render_template(
        "settings.html",
        page="settings",
        settings=current,
        whisper_models=config.WHISPER_MODELS,
    )


@app.route("/settings", methods=["POST"])
def save_settings_route():
    new_settings = {
        "whisper_model": request.form.get("whisper_model", "base"),
        "min_clip_duration": int(request.form.get("min_clip_duration", 15)),
        "max_clip_duration": int(request.form.get("max_clip_duration", 90)),
        "target_clip_duration": int(request.form.get("target_clip_duration", 45)),
        "max_clips": int(request.form.get("max_clips", 10)),
        "default_privacy": request.form.get("default_privacy", "private"),
    }
    current = config.load_settings()
    current.update(new_settings)
    config.save_settings(current)
    return redirect(url_for("settings_page"))


# ---- Processing Routes ----

@app.route("/process", methods=["POST"])
def process():
    source = request.form.get("source", "").strip()
    if not source:
        return jsonify({"error": "No source provided"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "starting",
        "progress": "Starting...",
        "clips": [],
        "video_title": "",
        "source": source,
        "error": None,
        "created_at": datetime.now().isoformat(),
    }

    thread = threading.Thread(target=_process_video, args=(job_id, source))
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/batch-process", methods=["POST"])
def batch_process():
    """Process multiple URLs at once."""
    urls_text = request.form.get("urls", "").strip()
    if not urls_text:
        return jsonify({"error": "No URLs provided"}), 400

    urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
    if not urls:
        return jsonify({"error": "No valid URLs found"}), 400

    job_ids = []
    for url in urls:
        job_id = str(uuid.uuid4())[:8]
        jobs[job_id] = {
            "status": "queued",
            "progress": "Queued...",
            "clips": [],
            "video_title": "",
            "source": url,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "batch": True,
        }
        job_ids.append(job_id)

    # Process sequentially in a background thread to avoid overload
    def _batch_runner(ids):
        for jid in ids:
            _process_video(jid, jobs[jid]["source"])

    thread = threading.Thread(target=_batch_runner, args=(job_ids,))
    thread.daemon = True
    thread.start()

    return jsonify({"job_ids": job_ids})


@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route("/results/<job_id>")
def results(job_id):
    job = jobs.get(job_id)
    if not job:
        return redirect(url_for("index"))
    return render_template("results.html", job_id=job_id, job=job, page="home")


@app.route("/clips/<job_id>/<filename>")
def serve_clip(job_id, filename):
    clip_dir = os.path.join(os.getcwd(), CLIPS_BASE_DIR, job_id)
    return send_from_directory(clip_dir, filename)


@app.route("/download/<job_id>/<filename>")
def download_clip(job_id, filename):
    clip_dir = os.path.join(os.getcwd(), CLIPS_BASE_DIR, job_id)
    return send_from_directory(clip_dir, filename, as_attachment=True)


# ---- YouTube Upload Routes ----

@app.route("/youtube/status")
def youtube_status():
    return jsonify({
        "configured": uploader.is_configured(),
        "authenticated": uploader.is_authenticated(),
    })


@app.route("/youtube/auth")
def youtube_auth():
    try:
        auth_url = uploader.get_auth_url()
        return redirect(auth_url)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/oauth/callback")
def oauth_callback():
    try:
        uploader.handle_oauth_callback(request.url)
        return render_template("auth_success.html")
    except Exception as e:
        return jsonify({"error": f"Authentication failed: {str(e)}"}), 400


@app.route("/upload", methods=["POST"])
def upload_clip_to_youtube():
    data = request.get_json()
    job_id = data.get("job_id")
    filename = data.get("filename")
    title = data.get("title", filename)
    description = data.get("description", "Generated by Slippa")
    privacy = data.get("privacy", config.get("default_privacy"))

    if not job_id or not filename:
        return jsonify({"error": "Missing job_id or filename"}), 400

    if not uploader.is_authenticated():
        return jsonify({"error": "Not authenticated.", "need_auth": True}), 401

    clip_path = os.path.join(os.getcwd(), CLIPS_BASE_DIR, job_id, filename)
    if not os.path.exists(clip_path):
        return jsonify({"error": "Clip file not found"}), 404

    upload_id = f"{job_id}_{filename}"
    upload_jobs[upload_id] = {"status": "uploading", "progress": "Starting...", "result": None}

    def _do_upload():
        try:
            result = uploader.upload_video(
                file_path=clip_path, title=title,
                description=description, privacy_status=privacy,
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
    job = upload_jobs.get(upload_id)
    if not job:
        return jsonify({"error": "Upload not found"}), 404
    return jsonify(job)


# ---- Server ----

def run_web():
    yt_status = "✅ configured" if uploader.is_configured() else "❌ no client_secrets.json"
    print(f"\n🌐 Slippa Web UI running at: http://localhost:5000")
    print(f"📤 YouTube upload: {yt_status}\n")
    app.run(debug=True, port=5000, use_reloader=False)


if __name__ == "__main__":
    run_web()
