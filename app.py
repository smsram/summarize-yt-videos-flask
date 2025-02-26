from flask import Flask, request, jsonify
import os
import re
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Configure Gemini API Key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_video_id(url):
    """Extracts YouTube video ID from a valid link."""
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_youtube_subtitles(video_url):
    """Fetches subtitles from YouTube API."""
    video_id = extract_video_id(video_url)
    if not video_id:
        return "Invalid YouTube URL!"

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        subtitles = "\n".join([item["text"] for item in transcript])
        return subtitles
    except:
        return "No subtitles found!"

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

    subtitles = get_youtube_subtitles(video_url)
    summary = summarize_text(subtitles)

    return jsonify({"subtitles": subtitles, "summary": summary})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
