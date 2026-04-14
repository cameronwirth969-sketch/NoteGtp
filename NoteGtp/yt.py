# app.py - YouTube Transcript Extractor with Invidious Fallback
# ✅ Works locally (official API) AND on cloud hosts (Invidious fallback)
# ✅ 100% free, no proxies, no auth

import os
import re
import logging
import requests
from flask import Flask, request, render_template_string, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, RequestBlocked

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# =============================================================================
# INVIDIOUS INSTANCES (public, free, CORS-enabled)
# =============================================================================
INVIDIOUS_INSTANCES = [
    "https://inv.nadeko.net",
    "https://invidious.snopyta.org",
    "https://yewtu.be",
    "https://invidious.fdn.fr",
    "https://inv.tux.pizza",
    "https://vid.puffyan.us",
]

# =============================================================================
# FRONTEND
# =============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Transcript Extractor</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            max-width: 800px; margin: 2rem auto; padding: 0 1rem; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
            color: #e6e6e6; min-height: 100vh;
        }
        .card { background: #0f3460; padding: 2rem; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); border: 1px solid #1a4780; }
        h1 { margin: 0 0 1.5rem; font-size: 1.8rem; text-align: center; color: #fff; }
        label { display: block; margin: 1rem 0 0.5rem; font-weight: 600; color: #c5c5c5; }
        input, select { width: 100%; padding: 0.85rem; border: 2px solid #1a4780; border-radius: 8px; font-size: 1rem; background: #0a1929; color: #fff; }
        input:focus, select:focus { outline: none; border-color: #4ecca3; }
        button { width: 100%; margin-top: 1.5rem; padding: 1rem; background: linear-gradient(135deg, #4ecca3 0%, #45b393 100%); color: #0a1929; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(78,204,163,0.4); }
        #result { margin-top: 1.5rem; padding: 1.25rem; background: #0a1929; border: 1px solid #1a4780; border-radius: 10px; white-space: pre-wrap; line-height: 1.7; min-height: 80px; display: none; font-size: 0.95rem; }
        .error { color: #ff6b6b; font-weight: 500; }
        .loader { display: none; margin-top: 1rem; text-align: center; font-style: italic; color: #aaa; }
        .copy-btn { margin-top: 0.75rem; padding: 0.5rem 1rem; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem; display: none; width: auto; }
        .footer { text-align: center; margin-top: 2rem; color: rgba(255,255,255,0.7); font-size: 0.85rem; }
        .badge { display: inline-block; padding: 0.25rem 0.5rem; background: #4ecca3; color: #0a1929; border-radius: 4px; font-size: 0.75rem; font-weight: 600; margin-left: 0.5rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📺 YouTube Transcript Extractor <span class="badge">FREE</span></h1>
        <form id="form">
            <label for="url">YouTube URL or Video ID</label>
            <input type="text" id="url" placeholder="https://youtu.be/jNQXAC9IVRw" value="https://youtu.be/jNQXAC9IVRw" required>
            <label for="language">Preferred Language</label>
            <select id="language">
                <option value="">Auto (try English first)</option>
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="pt">Portuguese</option>
                <option value="ja">Japanese</option>
                <option value="ko">Korean</option>
                <option value="zh-Hans">Chinese (Simplified)</option>
            </select>
            <button type="submit">✨ Extract Transcript</button>
        </form>
        <div class="loader" id="loader">⏳ Fetching transcript...</div>
        <div id="result"></div>
        <button class="copy-btn" id="copyBtn" onclick="copyText()">📋 Copy to Clipboard</button>
    </div>
    <div class="footer">
        Built with Flask • Uses <a href="https://github.com/iv-org/invidious" target="_blank">Invidious</a> fallback for cloud hosting
    </div>
    <script>
        document.getElementById('form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = document.getElementById('url').value.trim();
            const language = document.getElementById('language').value;
            const resultDiv = document.getElementById('result');
            const loader = document.getElementById('loader');
            const copyBtn = document.getElementById('copyBtn');
            resultDiv.style.display = 'none';
            copyBtn.style.display = 'none';
            loader.style.display = 'block';
            try {
                const res = await fetch('/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url, language })
                });
                const data = await res.json();
                resultDiv.style.display = 'block';
                copyBtn.style.display = 'block';
                if (data.success) {
                    resultDiv.textContent = data.transcript;
                } else {
                    resultDiv.innerHTML = `<span class="error">❌ ${data.error}</span>`;
                    copyBtn.style.display = 'none';
                }
            } catch (err) {
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<span class="error">❌ Network error: ${err.message}</span>`;
                copyBtn.style.display = 'none';
            } finally { loader.style.display = 'none'; }
        });
        function copyText() {
            const text = document.getElementById('result').textContent;
            if (!text) return;
            navigator.clipboard.writeText(text).then(() => {
                const btn = document.getElementById('copyBtn');
                btn.textContent = '✅ Copied!';
                setTimeout(() => btn.textContent = '📋 Copy to Clipboard', 2000);
            });
        }
    </script>
</body>
</html>
"""

# =============================================================================
# BACKEND
# =============================================================================

def extract_video_id(url):
    patterns = [
        r'(?:v=|/v/|youtu\.be/|embed/|shorts/|live/)([0-9A-Za-z_-]{11})',
        r'^([0-9A-Za-z_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def fetch_via_invidious(video_id, language=None):
    """Fetch transcript via Invidious API fallback."""
    languages = [language, 'en'] if language else ['en', 'en-US', 'en-GB']
    
    for instance in INVIDIOUS_INSTANCES:
        for lang in languages:
            try:
                url = f"{instance}/api/v1/captions/{video_id}"
                params = {'lang': lang} if lang else {}
                headers = {'Accept': 'application/json'}
                
                resp = requests.get(url, params=params, headers=headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    # Invidious returns list of {text, start, dur}
                    if isinstance(data, list) and len(data) > 0:
                        return "\n".join([item['text'] for item in data if 'text' in item])
            except Exception:
                continue  # Try next instance/language
    return None

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/extract', methods=['POST'])
def extract():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        language = data.get('language', '').strip()
        video_id = extract_video_id(url)
        
        if not video_id or len(video_id) != 11:
            return {'success': False, 'error': 'Invalid YouTube URL or Video ID'}, 400

        # 🎯 STRATEGY 1: Try official API first (works locally)
        try:
            logger.info(f"🔹 Trying official YouTube API for {video_id}")
            ytt_api = YouTubeTranscriptApi()
            languages = [language, 'en'] if language else ['en']
            fetched = ytt_api.fetch(video_id, languages=languages)
            text = "\n".join([s.text for s in fetched])
            logger.info(f"✅ Official API succeeded: {len(fetched)} snippets")
            return {'success': True, 'transcript': text}
        except RequestBlocked:
            logger.info(f"⚠️ Official API blocked (cloud IP), falling back to Invidious...")
        except Exception as e:
            logger.warning(f"⚠️ Official API failed: {e}, trying fallback...")

        # 🎯 STRATEGY 2: Invidious fallback (works on cloud hosts)
        logger.info(f"🔹 Trying Invidious fallback for {video_id}")
        text = fetch_via_invidious(video_id, language)
        
        if text:
            logger.info(f"✅ Invidious fallback succeeded")
            return {'success': True, 'transcript': text}
        
        # ❌ All methods failed
        return {
            'success': False,
            'error': "Could not fetch transcript. This video may have captions disabled, or all services are temporarily unavailable. Try again later or test locally."
        }, 503

    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}", exc_info=True)
        return {'success': False, 'error': f"Server error: {str(e)}"}, 500

# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting server on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
