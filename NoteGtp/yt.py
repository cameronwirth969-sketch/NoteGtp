# app.py - YouTube Transcript Extractor (Robust Invidious Fallback)
# ✅ Handles 404s, HTML responses, instance failures gracefully
# ✅ Correct Invidious API endpoint usage

import os
import re
import logging
import requests
from flask import Flask, request, render_template_string
from youtube_transcript_api import YouTubeTranscriptApi, RequestBlocked

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# =============================================================================
# INVIDIOUS: Reliable instances + correct API usage
# =============================================================================
# Test these instances: https://instances.invidious.io (look for "API: ✅")
INVIDIOUS_INSTANCES = [
    "https://yewtu.be",           # Very reliable, US
    "https://inv.nadeko.net",     # EU, stable
    "https://invidious.fdn.fr",   # France, good uptime
    "https://inv.tux.pizza",      # US, fast
    "https://vid.puffyan.us",     # US, reliable
    "https://invidious.slipfox.xyz", # US, backup
]

def fetch_via_invidious(video_id, language=None):
    """
    Fetch transcript via Invidious API.
    Endpoint: GET /api/v1/captions/{video_id}/{lang}
    Returns: plain text transcript or None if failed
    """
    # Language codes to try (Invidious uses standard codes)
    languages = []
    if language:
        languages.append(language)
    # Fallbacks
    languages.extend(['en', 'en-US', 'en-GB'])
    
    for instance in INVIDIOUS_INSTANCES:
        for lang in languages:
            try:
                # ✅ Correct endpoint: /api/v1/captions/{video_id}/{lang}
                url = f"{instance}/api/v1/captions/{video_id}/{lang}"
                headers = {
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                resp = requests.get(url, headers=headers, timeout=12)
                
                # ✅ Check status BEFORE parsing JSON
                if resp.status_code == 404:
                    continue  # No captions in this language on this instance
                if resp.status_code != 200:
                    continue  # Server error, try next
                
                # ✅ Only parse JSON if we got 200 OK
                try:
                    data = resp.json()
                except ValueError:
                    continue  # Not JSON, skip
                
                # Invidious returns: [{"text": "...", "start": 0.0, "dur": 1.5}, ...]
                if isinstance(data, list) and len(data) > 0 and 'text' in data[0]:
                    text_lines = [item['text'] for item in data if isinstance(item, dict) and 'text' in item]
                    if text_lines:
                        logger.info(f"✅ Invidious success: {instance} ({lang})")
                        return "\n".join(text_lines)
                        
            except requests.RequestException:
                continue  # Network error, try next instance/lang
            except Exception:
                continue  # Any other error, keep trying
    
    logger.warning(f"⚠️ Invidious fallback failed for {video_id}")
    return None

# =============================================================================
# FRONTEND (minimal, clean)
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
        body { font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; background: #f8fafc; color: #1e293b; }
        .card { background: #fff; padding: 2rem; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
        h1 { margin: 0 0 1.5rem; font-size: 1.6rem; text-align: center; }
        label { display: block; margin: 1rem 0 0.5rem; font-weight: 600; }
        input, select { width: 100%; padding: 0.85rem; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 1rem; }
        input:focus, select:focus { outline: none; border-color: #3b82f6; }
        button { width: 100%; margin-top: 1.5rem; padding: 1rem; background: #3b82f6; color: white; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; }
        button:hover { background: #2563eb; }
        #result { margin-top: 1.5rem; padding: 1.25rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; white-space: pre-wrap; line-height: 1.7; min-height: 80px; display: none; }
        .error { color: #dc2626; font-weight: 500; }
        .loader { display: none; margin-top: 1rem; text-align: center; color: #64748b; }
        .copy-btn { margin-top: 0.75rem; padding: 0.5rem 1rem; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer; display: none; width: auto; }
        .footer { text-align: center; margin-top: 2rem; color: #64748b; font-size: 0.85rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📺 YouTube Transcript Extractor</h1>
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
    <div class="footer">Free • No login • Works on cloud hosts</div>
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
                // ✅ Handle non-JSON responses safely
                const contentType = res.headers.get('content-type');
                if (!contentType || !contentType.includes('application/json')) {
                    const text = await res.text();
                    throw new Error(`Server returned ${res.status}: ${text.substring(0, 100)}`);
                }
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
                resultDiv.innerHTML = `<span class="error">❌ ${err.message}</span>`;
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
# BACKEND ROUTES
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

        # 🎯 STRATEGY 1: Official YouTube API (works on residential IPs)
        try:
            logger.info(f"🔹 Trying official API for {video_id}")
            ytt_api = YouTubeTranscriptApi()
            langs = [language, 'en'] if language else ['en']
            fetched = ytt_api.fetch(video_id, languages=langs)
            text = "\n".join([s.text for s in fetched])
            logger.info(f"✅ Official API: {len(fetched)} snippets")
            return {'success': True, 'transcript': text}
        except RequestBlocked:
            logger.info(f"⚠️ Official API blocked (cloud IP), trying Invidious...")
        except Exception as e:
            logger.warning(f"⚠️ Official API error: {type(e).__name__}, trying fallback...")

        # 🎯 STRATEGY 2: Invidious fallback (works on cloud IPs)
        logger.info(f"🔹 Trying Invidious fallback for {video_id}")
        text = fetch_via_invidious(video_id, language)
        
        if text:
            return {'success': True, 'transcript': text}
        
        # ❌ All methods failed
        return {
            'success': False,
            'error': "Could not fetch transcript. Possible reasons:\n• Video has no captions enabled\n• All services temporarily unavailable\n• Video is age-restricted or region-blocked\n\nTry a different video or test locally."
        }, 503

    except Exception as e:
        logger.error(f"💥 Server error: {e}", exc_info=True)
        return {'success': False, 'error': f"Internal error: {str(e)}"}, 500

# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting server on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
