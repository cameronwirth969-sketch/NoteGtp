import re
from flask import Flask, request, render_template_string
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)

# Embedded HTML/CSS/JS
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Transcript Extractor</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; background: #f4f4f9; color: #333; }
        .card { background: #fff; padding: 1.5rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { margin-top: 0; font-size: 1.5rem; }
        label { display: block; margin: 0.5rem 0 0.25rem; font-weight: 500; }
        input { width: 100%; padding: 0.75rem; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 1rem; }
        button { margin-top: 1rem; padding: 0.75rem 1.5rem; background: #2563eb; color: #fff; border: none; border-radius: 6px; font-size: 1rem; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #1d4ed8; }
        #result { margin-top: 1.5rem; padding: 1rem; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; white-space: pre-wrap; line-height: 1.6; min-height: 60px; display: none; }
        .error { color: #dc2626; font-weight: 500; }
        .loader { display: none; margin-top: 1rem; font-style: italic; color: #666; }
        .copy-btn { margin-top: 0.5rem; padding: 0.4rem 0.8rem; background: #10b981; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; display: none; }
        select { width: 100%; padding: 0.75rem; border: 1px solid #ccc; border-radius: 6px; margin: 0.5rem 0; box-sizing: border-box; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📺 YouTube Transcript Extractor</h1>
        <form id="form">
            <label for="url">Paste YouTube URL or Video ID</label>
            <input type="text" id="url" placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ" required>
            
            <label for="language">Preferred Language (optional)</label>
            <select id="language">
                <option value="">Auto-detect</option>
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="pt">Portuguese</option>
                <option value="ja">Japanese</option>
                <option value="ko">Korean</option>
                <option value="zh-Hans">Chinese (Simplified)</option>
            </select>
            
            <button type="submit">Extract Transcript</button>
        </form>
        <div class="loader" id="loader">Fetching transcript...</div>
        <div id="result"></div>
        <button class="copy-btn" id="copyBtn" onclick="copyText()">📋 Copy to Clipboard</button>
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
            } finally {
                loader.style.display = 'none';
            }
        });

        function copyText() {
            const text = document.getElementById('result').textContent;
            navigator.clipboard.writeText(text).then(() => {
                document.getElementById('copyBtn').textContent = '✅ Copied!';
                setTimeout(() => document.getElementById('copyBtn').textContent = '📋 Copy to Clipboard', 2000);
            });
        }
    </script>
</body>
</html>
"""

def extract_video_id(url):
    """Extracts 11-character YouTube video ID from various URL formats."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/|embed/|shorts/)([0-9A-Za-z_-]{11})',
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
        
        if not video_id:
            return {'success': False, 'error': 'Invalid YouTube URL or Video ID'}, 400

        # ✅ CORRECT API USAGE (v0.6.0+): Instantiate first
        ytt_api = YouTubeTranscriptApi()
        
        # Build language list with fallback
        languages = [language, 'en'] if language else ['en']
        
        # Fetch transcript with language preference
        fetched_transcript = ytt_api.fetch(video_id, languages=languages)
        
        # Extract plain text from FetchedTranscript object
        # Each snippet has .text, .start, .duration attributes
        plain_text = "\n".join([snippet.text for snippet in fetched_transcript])
        
        return {'success': True, 'transcript': plain_text}
    
    except Exception as e:
        error_msg = str(e)
        # Friendly error messages for common issues
        if 'Could not retrieve a transcript' in error_msg:
            error_msg = "No transcript available for this video. Try another video or check if captions are enabled."
        elif 'RequestBlocked' in error_msg or 'IpBlocked' in error_msg:
            error_msg = "YouTube blocked the request. Try again later or use a proxy."
        return {'success': False, 'error': error_msg}, 500

if __name__ == '__main__':
    print("🌐 Starting local server: http://localhost:5000")
    print("Press Ctrl+C to stop.")
    app.run(debug=True, port=5000)