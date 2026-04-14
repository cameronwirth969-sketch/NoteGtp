# app.py - YouTube Transcript Extractor with FULL DEBUG MODE
# ✅ Works on Render, Railway, Fly.io, or locally
# ✅ Shows REAL errors (not masked messages)

import os
import re
import logging
import traceback
from flask import Flask, request, render_template_string, jsonify
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# =============================================================================
# FRONTEND: Embedded HTML with Debug Panel
# =============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Transcript Extractor (Debug)</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            max-width: 900px; margin: 2rem auto; padding: 0 1rem; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
            color: #e6e6e6; min-height: 100vh;
        }
        .card { 
            background: #0f3460; padding: 2rem; border-radius: 16px; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.3); border: 1px solid #1a4780;
        }
        h1 { margin: 0 0 1.5rem; font-size: 1.8rem; text-align: center; color: #fff; }
        label { display: block; margin: 1rem 0 0.5rem; font-weight: 600; color: #c5c5c5; }
        input, select { 
            width: 100%; padding: 0.85rem; border: 2px solid #1a4780; 
            border-radius: 8px; font-size: 1rem; background: #0a1929; color: #fff;
            transition: border-color 0.2s;
        }
        input:focus, select:focus { outline: none; border-color: #4ecca3; }
        button { 
            width: 100%; margin-top: 1.5rem; padding: 1rem; 
            background: linear-gradient(135deg, #4ecca3 0%, #45b393 100%); 
            color: #0a1929; border: none; border-radius: 8px; 
            font-size: 1rem; font-weight: 600; cursor: pointer; 
            transition: transform 0.1s, box-shadow 0.2s;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(78,204,163,0.4); }
        button:active { transform: translateY(0); }
        #result { 
            margin-top: 1.5rem; padding: 1.25rem; background: #0a1929; 
            border: 1px solid #1a4780; border-radius: 10px; 
            white-space: pre-wrap; line-height: 1.7; min-height: 80px; 
            display: none; font-size: 0.95rem; color: #e6e6e6;
        }
        .error { color: #ff6b6b; font-weight: 500; }
        .loader { display: none; margin-top: 1rem; text-align: center; font-style: italic; color: #aaa; }
        .copy-btn { 
            margin-top: 0.75rem; padding: 0.5rem 1rem; 
            background: #10b981; color: white; border: none; 
            border-radius: 6px; cursor: pointer; font-size: 0.9rem; 
            display: none; width: auto;
        }
        .copy-btn:hover { background: #059669; }
        .footer { text-align: center; margin-top: 2rem; color: rgba(255,255,255,0.7); font-size: 0.85rem; }
        .footer a { color: #4ecca3; text-decoration: none; font-weight: 500; }
        
        /* Debug panel */
        .debug-panel {
            margin-top: 2rem; padding: 1rem; background: #0a1929; 
            border: 1px dashed #4ecca3; border-radius: 8px; font-size: 0.85rem;
        }
        .debug-panel h3 { color: #4ecca3; margin-bottom: 0.5rem; }
        .debug-panel pre { 
            background: #05131f; padding: 0.75rem; border-radius: 4px; 
            overflow-x: auto; color: #ff6b6b; font-size: 0.8rem;
        }
        .status-dot { 
            display: inline-block; width: 10px; height: 10px; 
            border-radius: 50%; margin-right: 5px; 
        }
        .status-ok { background: #4ecca3; }
        .status-err { background: #ff6b6b; }
    </style>
</head>
<body>
    <div class="card">
        <h1>📺 YouTube Transcript Extractor <span style="font-size:0.9em; color:#4ecca3;">[DEBUG]</span></h1>
        
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
        
        <!-- Debug Panel -->
        <div class="debug-panel">
            <h3>🔧 Debug Info</h3>
            <div id="debug-status">
                <span class="status-dot status-err"></span> Waiting for request...
            </div>
            <pre id="debug-output" style="display:none;"></pre>
            <button onclick="testConnection()" style="margin-top:0.5rem; width:auto; padding:0.4rem 0.8rem; font-size:0.85rem;">
                🌐 Test API Connection
            </button>
        </div>
    </div>
    
    <div class="footer">
        Built with Flask • <a href="https://github.com/jdepoix/youtube-transcript-api" target="_blank">youtube-transcript-api</a>
    </div>

    <script>
        function updateDebug(status, message, raw = null) {
            const dot = document.querySelector('#debug-status .status-dot');
            const statusEl = document.getElementById('debug-status');
            const output = document.getElementById('debug-output');
            
            if (status === 'ok') {
                dot.className = 'status-dot status-ok';
                statusEl.innerHTML = `<span class="status-dot status-ok"></span> ${message}`;
            } else {
                dot.className = 'status-dot status-err';
                statusEl.innerHTML = `<span class="status-dot status-err"></span> ${message}`;
            }
            
            if (raw) {
                output.style.display = 'block';
                output.textContent = raw;
            } else {
                output.style.display = 'none';
            }
        }

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
            updateDebug('wait', 'Processing request...');

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
                    updateDebug('ok', `✅ Success! ${data.snippet_count || '?'} snippets`);
                } else {
                    resultDiv.innerHTML = `<span class="error">❌ ${data.error}</span>`;
                    copyBtn.style.display = 'none';
                    updateDebug('err', 'Request failed', data.debug_trace || data.error);
                }
            } catch (err) {
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = `<span class="error">❌ Network error: ${err.message}</span>`;
                copyBtn.style.display = 'none';
                updateDebug('err', 'Network error', err.stack || err.message);
            } finally {
                loader.style.display = 'none';
            }
        });

        async function testConnection() {
            updateDebug('wait', 'Testing API connection...');
            try {
                const res = await fetch('/debug/test');
                const data = await res.json();
                if (data.ok) {
                    updateDebug('ok', '✅ API connection works!', JSON.stringify(data, null, 2));
                } else {
                    updateDebug('err', '❌ Connection test failed', JSON.stringify(data, null, 2));
                }
            } catch (err) {
                updateDebug('err', 'Network error', err.stack || err.message);
            }
        }

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
# BACKEND: Routes & Logic
# =============================================================================

def extract_video_id(url):
    """Extract 11-character YouTube video ID from URL or raw ID."""
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
    """Extract transcript with FULL DEBUG output."""
    debug_trace = []
    
    def log(msg):
        debug_trace.append(msg)
        logger.info(msg)
    
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        language = data.get('language', '').strip()
        
        log(f"📥 Request received: url={url}, language={language or 'auto'}")
        
        video_id = extract_video_id(url)
        if not video_id or len(video_id) != 11:
            log(f"❌ Invalid video ID extracted: {video_id}")
            return {
                'success': False, 
                'error': f'Invalid YouTube URL or Video ID (got: "{video_id}")',
                'debug_trace': '\n'.join(debug_trace)
            }, 400
        
        log(f"✅ Video ID: {video_id}")
        log(f"🌐 Fetching from YouTube API...")
        
        # Initialize API
        ytt_api = YouTubeTranscriptApi()
        log(f"✅ YouTubeTranscriptApi initialized")
        
        # Build language list
        languages = [language, 'en'] if language else ['en']
        log(f"🔤 Language priority: {languages}")
        
        # List available transcripts first (debug info)
        try:
            transcript_list = ytt_api.list(video_id)
            available = []
            for t in transcript_list:
                available.append({
                    'language': t.language,
                    'code': t.language_code,
                    'auto': t.is_generated,
                    'translatable': t.is_translatable
                })
            log(f"📋 Available transcripts: {available}")
        except Exception as list_err:
            log(f"⚠️ Could not list transcripts: {list_err}")
        
        # Fetch the actual transcript
        fetched_transcript = ytt_api.fetch(video_id, languages=languages)
        log(f"✅ Fetched {len(fetched_transcript)} transcript snippets")
        
        # Convert to plain text
        plain_text = "\n".join([snippet.text for snippet in fetched_transcript])
        log(f"✅ Converted to plain text ({len(plain_text)} chars)")
        
        return {
            'success': True, 
            'transcript': plain_text,
            'snippet_count': len(fetched_transcript),
            'debug_trace': '\n'.join(debug_trace)
        }
    
    except TranscriptsDisabled as e:
        msg = f"🚫 Transcripts disabled for this video: {e}"
        log(msg)
        return {
            'success': False,
            'error': "This video has transcripts disabled by the uploader.",
            'debug_trace': '\n'.join(debug_trace) + f"\n{msg}"
        }, 400
        
    except NoTranscriptFound as e:
        msg = f"🔍 No transcript found in requested languages: {e}"
        log(msg)
        return {
            'success': False,
            'error': "No transcript available in selected language(s). Try 'Auto' or check if captions exist on YouTube.",
            'debug_trace': '\n'.join(debug_trace) + f"\n{msg}"
        }, 404
        
    except VideoUnavailable as e:
        msg = f"🔒 Video unavailable: {e}"
        log(msg)
        return {
            'success': False,
            'error': "This video is private, deleted, age-restricted, or region-blocked.",
            'debug_trace': '\n'.join(debug_trace) + f"\n{msg}"
        }, 404
        
    except Exception as e:
        msg = f"💥 Unexpected error: {type(e).__name__}: {e}"
        log(msg)
        log(f"📄 Full traceback:\n{traceback.format_exc()}")
        return {
            'success': False,
            'error': f"{type(e).__name__}: {e}",
            'debug_trace': '\n'.join(debug_trace) + f"\n{msg}\n\n{traceback.format_exc()}"
        }, 500

@app.route('/debug/test')
def debug_test():
    """Endpoint to test basic API connectivity."""
    try:
        # Simple connectivity test
        import requests
        resp = requests.get('https://www.youtube.com/watch?v=jNQXAC9IVRw', timeout=10)
        return {
            'ok': True,
            'youtube_status': resp.status_code,
            'youtube_headers': dict(resp.headers),
            'message': '✅ Can reach YouTube'
        }
    except Exception as e:
        return {
            'ok': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }

# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting server on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
