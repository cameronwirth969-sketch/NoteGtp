import re
import logging
from flask import Flask, request, render_template_string
from youtube_transcript_api import YouTubeTranscriptApi

# Suppress noisy library logs
logging.getLogger("youtube_transcript_api").setLevel(logging.WARNING)

app = Flask(__name__)

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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: #333; min-height: 100vh;
        }
        .card { 
            background: #fff; padding: 2rem; border-radius: 16px; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.2); 
        }
        h1 { margin: 0 0 1.5rem; font-size: 1.8rem; text-align: center; color: #444; }
        label { display: block; margin: 1rem 0 0.5rem; font-weight: 600; color: #555; }
        input, select { 
            width: 100%; padding: 0.85rem; border: 2px solid #e1e5eb; 
            border-radius: 8px; font-size: 1rem; transition: border-color 0.2s;
        }
        input:focus, select:focus { outline: none; border-color: #667eea; }
        button { 
            width: 100%; margin-top: 1.5rem; padding: 1rem; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; border: none; border-radius: 8px; 
            font-size: 1rem; font-weight: 600; cursor: pointer; 
            transition: transform 0.1s, box-shadow 0.2s;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102,126,234,0.4); }
        button:active { transform: translateY(0); }
        #result { 
            margin-top: 1.5rem; padding: 1.25rem; background: #f8fafc; 
            border: 1px solid #e2e8f0; border-radius: 10px; 
            white-space: pre-wrap; line-height: 1.7; min-height: 80px; 
            display: none; font-size: 0.95rem;
        }
        .error { color: #dc2626; font-weight: 500; }
        .loader { display: none; margin-top: 1rem; text-align: center; font-style: italic; color: #666; }
        .copy-btn { 
            margin-top: 0.75rem; padding: 0.5rem 1rem; 
            background: #10b981; color: white; border: none; 
            border-radius: 6px; cursor: pointer; font-size: 0.9rem; 
            display: none; width: auto;
        }
        .copy-btn:hover { background: #059669; }
        .footer { text-align: center; margin-top: 2rem; color: rgba(255,255,255,0.85); font-size: 0.9rem; }
        .footer a { color: #fff; text-decoration: none; font-weight: 500; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📺 YouTube Transcript Extractor</h1>
        <form id="form">
            <label for="url">YouTube URL or Video ID</label>
            <input type="text" id="url" placeholder="https://youtu.be/dQw4w9WgXcQ" required>
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
    <div class="footer">Built with Flask • <a href="https://github.com/jdepoix/youtube-transcript-api" target="_blank">youtube-transcript-api</a></div>
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
                if (data.success) resultDiv.textContent = data.transcript;
                else { resultDiv.innerHTML = `<span class="error">❌ ${data.error}</span>`; copyBtn.style.display = 'none'; }
            } catch (err) {
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<span class="error">❌ Connection error: ${err.message}</span>`;
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

def extract_video_id(url):
    patterns = [r'(?:v=|/v/|youtu\.be/|embed/|shorts/|live/)([0-9A-Za-z_-]{11})', r'^([0-9A-Za-z_-]{11})$']
    for pattern in patterns:
        match = re.search(pattern, url)
        if match: return match.group(1)
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

        ytt_api = YouTubeTranscriptApi()
        languages = [language, 'en'] if language else ['en']
        fetched_transcript = ytt_api.fetch(video_id, languages=languages)
        plain_text = "\n".join([snippet.text for snippet in fetched_transcript])
        
        return {'success': True, 'transcript': plain_text}
    
    except Exception as e:
        error_msg = str(e)
        if 'Could not retrieve a transcript' in error_msg:
            error_msg = "No transcript available. This video may not have captions enabled."
        elif 'Video unavailable' in error_msg:
            error_msg = "This video is private, deleted, or region-restricted."
        return {'success': False, 'error': error_msg}, 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
