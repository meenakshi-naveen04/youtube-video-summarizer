from urllib.parse import urlparse, parse_qs
from flask import Flask, request, jsonify, render_template
from transformers import pipeline
from youtube_transcript_api import YouTubeTranscriptApi
import whisper
import os
import subprocess
from pydub import AudioSegment
import traceback

app = Flask(__name__)

# Load AI Models
whisper_model = whisper.load_model("base")
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def extract_video_id(youtube_url):
    """Extracts YouTube video ID from the URL."""
    try:
        parsed_url = urlparse(youtube_url)
        if "youtube.com" in parsed_url.netloc:
            return parse_qs(parsed_url.query).get("v", [None])[0]
        elif "youtu.be" in parsed_url.netloc:
            return parsed_url.path.lstrip("/")
        return None
    except Exception:
        return None

def get_youtube_transcript(video_id):
    """Fetches transcript from YouTube API if available."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry["text"] for entry in transcript]) if transcript else None
    except Exception:
        return None  # Return None if transcript is not available

def download_audio(youtube_url, output_path="audio.mp3"):
    """Downloads audio from YouTube using yt-dlp."""
    command = [
        "yt-dlp", "-f", "bestaudio", "--extract-audio",
        "--audio-format", "mp3", "--output", output_path, youtube_url
    ]
    
    print("🎵 Downloading audio...")
    subprocess.run(command, capture_output=True)
    
    if os.path.exists(output_path):
        print("✅ Download complete!")
        return output_path
    else:
        return None

def convert_audio_to_wav(input_audio, output_audio="audio.wav"):
    """Converts MP3 to WAV format for transcription."""
    try:
        audio = AudioSegment.from_file(input_audio)
        audio.export(output_audio, format="wav")
        return output_audio
    except Exception as e:
        return None

def transcribe_audio(audio_file):
    """Transcribes audio using OpenAI's Whisper model."""
    try:
        print("🎙 Transcribing audio...")
        result = whisper_model.transcribe(audio_file)
        return result["text"]
    except Exception as e:
        return None

def chunk_text(text, max_words=900):
    """Splits text into manageable chunks for summarization."""
    words = text.split()
    return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

def summarize_text(text, max_length=150, min_length=50):
    """Summarizes text using DistilBART."""
    chunks = chunk_text(text)
    summaries = []
    
    for chunk in chunks:
        try:
            summary = summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)
            summaries.append(summary[0]['summary_text'])
        except Exception as e:
            print(f"Error in summarization: {e}")
            continue  # Skip problematic chunks

    return " ".join(summaries) if summaries else None

def process_youtube_video(youtube_url):
    """Processes the YouTube video and returns a summary."""
    try:
        video_id = extract_video_id(youtube_url)
        if not video_id:
            return "Error: Invalid YouTube URL"

        # Step 1: Check if a transcript is available
        transcript = get_youtube_transcript(video_id)

        if transcript:
            print("📜 Using YouTube transcript...")
            return summarize_text(transcript)
        
        # Step 2: If no transcript, process audio
        print("🔉 No transcript found, processing audio...")
        input_audio = download_audio(youtube_url)
        if not input_audio:
            return "Error: Failed to download audio"

        output_audio = convert_audio_to_wav(input_audio)
        if not output_audio:
            return "Error: Failed to convert audio"

        transcript = transcribe_audio(output_audio)
        if not transcript:
            return "Error: Failed to transcribe audio"

        summary = summarize_text(transcript)

        # Cleanup temporary files
        for file in ["audio.mp3", "audio.wav"]:
            if os.path.exists(file):
                os.remove(file)

        return summary if summary else "Error: Summarization failed"

    except Exception as e:
        return f"Error: {str(e)}"

# Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/summarize", methods=["POST"])
def summarize():
    try:
        data = request.get_json(force=True)
        youtube_url = data.get("youtube_url", "").strip()
        max_length = int(data.get("max_length", 150))  # Default: 150
        min_length = int(data.get("min_length", 50))   # Default: 50

        if not youtube_url:
            return jsonify({"error": "No YouTube URL provided"}), 400

        print("🎥 Processing:", youtube_url)

        summary = process_youtube_video(youtube_url)

        if "Error" in summary:
            return jsonify({"error": summary}), 500

        return jsonify({"summary": summary})

    except Exception as e:
        print("🔥 SERVER ERROR:", traceback.format_exc())
        return jsonify({"error": f"Server error: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
