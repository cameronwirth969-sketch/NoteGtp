# app.py - Minimal, Bulletproof YouTube Transcript Extractor
# ✅ Always returns valid JSON
# ✅ Uses only Invidious (works on cloud hosts)
# ✅ No complex fallback logic

import os
import re
import logging
import requests
from flask import Flask, request, jsonify, render_template_string

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Reliable Invidious instances (API-enabled)
INVIDIOUS = [
    "https://yewtu.be",
    "https://inv.nadeko.net", 
    "https://invidious.fdn.fr",
    "https://inv.tux.pizza",
]

# =============================================================================
# FRONTEND (minimal)
# =============================================================================
HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>YT Transcript</title><style>
body{font-family:system-ui,sans-serif;max-width:700px;margin:2rem auto;padding:1rem;background:#f8fafc}
.card{background:#fff;padding:1.5rem;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1)}
h1{text-align:center;margin:0 0 1.5rem}
input,select{width:100%;padding:0.75rem;margin:0.5rem 0;border:2px solid #e2e8f0;border-radius:8px;font-size:1rem}
button{width:100%;padding:0.75rem;margin-top:1rem;background:#3b82f6;color:#fff;border:none;border-radius:8px;font-size:1rem;font-weight:600;cursor:pointer}
button:hover{background:#2563eb}
#result{margin-top:1rem;padding:1rem;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;white-space:pre-wrap;display:none}
.error{color:#dc2626;font-weight:500}
.loader{display:none;margin-top:1rem;text-align:center;color:#64748b}
.copy-btn{margin-top:0.5rem;padding:0.4rem 0.8rem;background:#10b981;color:#fff;border:none;border-radius:6px;cursor:pointer;display:none}
</style></head><body>
<div class="card">
<h1>📺 YouTube Transcript</h1>
<form id="f"><input id="url" placeholder="YouTube URL or ID" value="https://youtu.be/jNQXAC9IVRw" required>
<select id="lang"><option value="">Auto (English first)</option><option value="en">English</option><option value="es">Spanish</option><option value="fr">French</option><option value="de">German</option></select>
<button type="submit">Extract</button></form>
<div class="loader" id="ld">Fetching...</div><div id="result"></div><button class="copy-btn" id="cp" onclick="navigator.clipboard.writeText(document.getElementById('result').textContent).then(()=>{cp.textContent='✅ Copied!';setTimeout(()=>cp.textContent='📋 Copy',1500)})">📋 Copy</button>
</div><script>
f.addEventListener('submit',async e=>{e.preventDefault();const url=document.getElementById('url').value.trim(),lang=document.getElementById('lang').value,r=document.getElementById('result'),l=document.getElementById('ld'),c=document.getElementById('cp');r.style.display='none';c.style.display='none';l.style.display='block';try{const res=await fetch('/extract',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url,lang})});if(!res.headers.get('content-type')?.includes('application/json')){const t=await res.text();throw new Error(`Server returned ${res.status}: ${t.substring(0,80)}`)}const d=await res.json();r.style.display='block';c.style.display='block';if(d.success)r.textContent=d.transcript;else{r.innerHTML='<span class="error">❌ '+d.error+'</span>';c.style.display='none'}}catch(err){r.style.display='block';r.innerHTML='<span class="error">❌ '+err.message+'</span>';c.style.display='none'}finally{l.style.display='none'}});
</script></body></html>"""

# =============================================================================
# BACKEND
# =============================================================================

def get_video_id(url):
    """Extract 11-char YouTube video ID."""
    for p in [r'(?:v=|/v/|youtu\.be/|embed/|shorts/)([0-9A-Za-z_-]{11})', r'^([0-9A-Za-z_-]{11})$']:
        m = re.search(p, url)
        if m: return m.group(1)
    return None

def get_transcript_invidious(vid, lang=None):
    """Fetch transcript via Invidious API. Returns plain text or None."""
    langs = [lang, 'en', 'en-US'] if lang else ['en', 'en-US', 'en-GB']
    for inst in INVIDIOUS:
        for l in langs:
            try:
                # Correct endpoint: /api/v1/captions/{video_id}/{lang}
                r = requests.get(f"{inst}/api/v1/captions/{vid}/{l}", 
                               headers={'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0'}, 
                               timeout=10)
                if r.status_code != 200: continue
                data = r.json()  # Only parse if status is 200
                if isinstance(data, list) and data and 'text' in data[0]:
                    return "\n".join(item['text'] for item in data if isinstance(item, dict) and 'text' in item)
            except: continue  # Skip any error, try next
    return None

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/extract', methods=['POST'])
def extract():
    """ALWAYS returns JSON with proper Content-Type header."""
    try:
        # Ensure we return JSON
        data = request.get_json(silent=True) or {}
        url = data.get('url', '').strip()
        lang = data.get('lang', '').strip() or data.get('language', '').strip()  # Support both keys
        vid = get_video_id(url)
        
        if not vid or len(vid) != 11:
            return jsonify(success=False, error="Invalid YouTube URL or Video ID"), 400
        
        logger.info(f"Fetching transcript for {vid}")
        text = get_transcript_invidious(vid, lang)
        
        if text:
            logger.info(f"✅ Success: {len(text.splitlines())} lines")
            return jsonify(success=True, transcript=text)
        
        return jsonify(success=False, error="No transcript found. Video may have captions disabled, or service is temporarily unavailable."), 404
        
    except Exception as e:
        # 🛡️ CATCH ALL: Always return valid JSON, never HTML
        logger.error(f"💥 Error: {e}", exc_info=True)
        return jsonify(success=False, error=f"Server error: {str(e)[:200]}"), 500

# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
