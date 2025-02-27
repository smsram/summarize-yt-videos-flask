from flask import Flask, request, jsonify
import os
import re
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from flask_cors import CORS
import yt_dlp

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Configure Gemini API Key (Use environment variable in production)
genai.configure(api_key="AIzaSyAFKX0_vAawMqcc8-B1Wbmq96xqPQ6p5xs")

def extract_video_id(url):
    """Extracts YouTube video ID from a valid link."""
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def generate_subtitles(video_url):
    """Gets subtitles from YouTube."""
    video_id = extract_video_id(video_url)
    if not video_id:
        return "Invalid YouTube URL!"

    # Step 1: Try to get official YouTube captions
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        subtitles = "\n".join([item["text"] for item in transcript])
        return subtitles
    except:
        return "No subtitles found!"

def summarize_text(text):
    """Summarizes subtitles using Gemini API."""
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = "Here is an extracted transcript of a video. Summarize it briefly under 400 lines you may respond with points :\n\n" + text
    response = model.generate_content(prompt)
    return response.text if response else "Failed to summarize."

@app.route('/summarize', methods=['POST'])
def summarize_video():
    data = request.json
    video_url = data.get("url")

    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    subtitles = generate_subtitles(video_url)
    if subtitles == "No subtitles found!":
        return jsonify({"error": "No subtitles available for this video."}), 400

    summary = summarize_text(subtitles)
    return jsonify({"subtitles": subtitles, "summary": summary})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
