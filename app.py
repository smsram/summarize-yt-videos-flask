from flask import Flask, request, jsonify
import os
import re
import google.generativeai as genai
import speech_recognition as sr
from youtube_transcript_api import YouTubeTranscriptApi
from flask_cors import CORS
import yt_dlp

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Configure Gemini API Key (Use environment variable in production)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_video_id(url):
    """Extracts YouTube video ID from a valid link."""
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def download_audio(video_url):
    """Downloads YouTube video audio as MP3 using yt-dlp."""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'temp_audio.mp3',
            'quiet': True,
            'noplaylist': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        return "temp_audio.mp3"
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None

def generate_subtitles(video_url):
    """Gets subtitles from YouTube or generates them using SpeechRecognition."""
    video_id = extract_video_id(video_url)
    if not video_id:
        return "Invalid YouTube URL!"

    # Step 1: Try to get official YouTube captions
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        subtitles = "\n".join([item["text"] for item in transcript])
        return subtitles
    except:
        print("No subtitles found! Generating subtitles using SpeechRecognition...")

    # Step 2: Download audio & transcribe using Google Speech Recognition
    audio_path = download_audio(video_url)
    if not audio_path:
        return "Failed to download audio."

    recognizer = sr.Recognizer()
    subtitles = ""

    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
        subtitles = recognizer.recognize_google(audio_data)
    except sr.UnknownValueError:
        subtitles = "Speech recognition failed: Could not understand audio."
    except sr.RequestError:
        subtitles = "Speech recognition failed: API request error."
    finally:
        # Cleanup: Delete audio file after processing
        if os.path.exists(audio_path):
            os.remove(audio_path)

    return subtitles

def summarize_text(text):
    """Summarizes subtitles using Gemini API."""
    if not text or text.strip() == "":
        return "No transcript available to summarize."

    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"Summarize this YouTube video transcript in short points:\n\n{text}"
    
    try:
        response = model.generate_content(prompt)
        return response.text if hasattr(response, "text") else "Gemini API failed to generate a summary."
    except Exception as e:
        return f"Error summarizing: {str(e)}"

@app.route('/summarize', methods=['POST'])
def summarize_video():
    data = request.json
    video_url = data.get("url")

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    subtitles = generate_subtitles(video_url)
    summary = summarize_text(subtitles)

    return jsonify({"subtitles": subtitles, "summary": summary})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
