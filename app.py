import json
import os
import threading
import time
from flask import Flask, Response, jsonify, render_template_string, request, send_file
import yt_dlp

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

tasks = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>StreamFetch - High Speed Downloader</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root {
            --bg: #07090e;
            --card-bg: rgba(15, 18, 28, 0.75);
            --accent: #00f2fe;
            --accent-purple: #4facfe;
            --whatsapp-color: #25d366;
            --text: #f8fafc;
            --text-dim: #94a3b8;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }

        body {
            background-color: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            padding: 20px 15px;
            background-image: 
                radial-gradient(circle at 50% 0%, rgba(0, 242, 254, 0.12) 0%, transparent 50%),
                radial-gradient(circle at 100% 100%, rgba(79, 172, 254, 0.08) 0%, transparent 40%);
        }

        .container { width: 100%; max-width: 620px; text-align: center; margin: auto 0; }

        .logo {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            font-size: clamp(1.8rem, 5vw, 2.4rem);
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent), var(--accent-purple));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 6px;
        }

        .tagline { color: var(--text-dim); font-size: clamp(0.85rem, 3vw, 0.95rem); margin-bottom: 25px; }

        .glass-card {
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 24px;
            padding: clamp(20px, 5vw, 32px);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
        }

        .input-group {
            display: flex;
            gap: 8px;
            background: rgba(255, 255, 255, 0.03);
            padding: 6px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        input[type="text"] {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            padding: 12px 14px;
            color: var(--text);
            font-size: 0.95rem;
            min-width: 0;
        }

        .btn-search {
            background: linear-gradient(135deg, var(--accent), var(--accent-purple));
            color: #000;
            border: none;
            border-radius: 12px;
            padding: 0 20px;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            white-space: nowrap;
        }

        #preview-box { display: none; margin-top: 22px; animation: slideUp 0.35s ease; }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .media-info {
            display: flex;
            gap: 14px;
            text-align: left;
            margin-bottom: 18px;
            align-items: center;
            background: rgba(255, 255, 255, 0.03);
            padding: 12px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        .thumbnail { width: 110px; height: 70px; border-radius: 10px; object-fit: cover; flex-shrink: 0; }

        .media-details h4 {
            font-size: clamp(0.85rem, 2.5vw, 0.95rem);
            color: var(--text);
            line-height: 1.35;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .quality-select {
            width: 100%;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text);
            padding: 10px;
            border-radius: 12px;
            margin-bottom: 12px;
            outline: none;
            font-weight: 600;
        }

        .options-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

        .btn-option {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: var(--text);
            padding: 14px;
            border-radius: 14px;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-option:hover { background: rgba(255, 255, 255, 0.08); border-color: var(--accent); }

        #progress-box { display: none; margin-top: 22px; text-align: left; }

        .progress-header { display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 8px; font-weight: 600; }

        .progress-bar-bg { width: 100%; height: 10px; background: rgba(255, 255, 255, 0.08); border-radius: 10px; overflow: hidden; }

        .progress-bar-fill {
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, var(--accent), var(--accent-purple));
            transition: width 0.2s linear;
        }

        .stats { display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--text-dim); margin-top: 8px; }

        #download-btn {
            display: none;
            margin-top: 18px;
            background: #00ff66;
            color: #000;
            text-decoration: none;
            padding: 14px;
            border-radius: 14px;
            font-weight: 800;
            align-items: center;
            justify-content: center;
            gap: 8px;
            box-shadow: 0 10px 20px rgba(0, 255, 102, 0.2);
        }

        .status-msg { font-size: 0.85rem; color: var(--text-dim); margin-top: 12px; }

        footer { margin-top: 30px; font-size: 0.85rem; color: var(--text-dim); }
        footer strong { color: var(--accent); }

        .whatsapp-widget { position: fixed; bottom: 20px; right: 20px; z-index: 999; }
        .whatsapp-btn {
            width: 58px; height: 58px; background-color: var(--whatsapp-color); border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 8px 24px rgba(37, 211, 102, 0.4); text-decoration: none;
        }
        .whatsapp-btn svg { width: 32px; height: 32px; fill: #ffffff; }

        @media (max-width: 480px) {
            .input-group { flex-direction: column; background: transparent; border: none; padding: 0; }
            input[type="text"] { background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 14px; padding: 14px; }
            .btn-search { padding: 14px; border-radius: 14px; }
            .options-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>

    <div class="container">
        <div class="logo"><i data-lucide="zap"></i> StreamFetch</div>
        <p class="tagline">Descărcare Ultra-Rapidă Multi-Thread</p>

        <div class="glass-card">
            <div class="input-group">
                <input type="text" id="video-url" placeholder="Lipește link-ul video aici...">
                <button class="btn-search" onclick="fetchInfo()">
                    <i data-lucide="search"></i> Caută
                </button>
            </div>

            <p class="status-msg" id="status-text"></p>

            <div id="preview-box">
                <div class="media-info">
                    <img id="thumb" class="thumbnail" src="" alt="Thumbnail">
                    <div class="media-details">
                        <h4 id="title">Titlu Video</h4>
                    </div>
                </div>

                <select id="quality-select" class="quality-select">
                    <option value="best">Calitate Maximă (Auto Fast)</option>
                    <option value="720">720p (Rapid)</option>
                    <option value="480">480p (Ultra Rapid)</option>
                </select>

                <div class="options-grid">
                    <button class="btn-option" onclick="startDownload('mp4')">
                        <i data-lucide="video"></i> MP4 Video
                    </button>
                    <button class="btn-option" onclick="startDownload('mp3')">
                        <i data-lucide="music"></i> MP3 Audio
                    </button>
                </div>
            </div>

            <div id="progress-box">
                <div class="progress-header">
                    <span id="status-label">Se descarcă ultra-rapid...</span>
                    <span id="percent-label">0%</span>
                </div>
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" id="progress-fill"></div>
                </div>
                <div class="stats">
                    <span id="speed-label">0 MB/s</span>
                    <span id="size-label">0 MB / 0 MB</span>
                </div>
            </div>

            <a id="download-btn" href="" download>
                <i data-lucide="download"></i> Salvează Fișierul în Dispozitiv
            </a>
        </div>

        <footer>
            Creat de <strong>Liviu și Pop</strong>
        </footer>
    </div>

    <div class="whatsapp-widget">
        <a href="https://wa.me/40741647168" target="_blank" class="whatsapp-btn" title="WhatsApp Contact">
            <svg viewBox="0 0 32 32">
                <path d="M16 2a13 13 0 0 0-11 20l-2 6 6-2a13 13 0 1 0 7-24zm0 24a11 11 0 0 1-5.5-1.5l-.4-.2-3.7 1 1-3.6-.3-.4A11 11 0 1 1 16 26zm6-8c-.3-.2-2-1-2.3-1.1-.3-.1-.5-.2-.7.2s-.8 1-1 1.2c-.2.2-.4.2-.7 0a9 9 0 0 1-4.4-3.8c-.3-.6.3-.5.9-1.6.1-.2 0-.4 0-.5s-.7-1.7-1-2.3c-.3-.6-.6-.5-.8-.5h-.7c-.2 0-.7.1-1 .5a4 4 0 0 0-1.3 3c0 1.8 1.3 3.5 1.5 3.7s2.6 4 6.3 5.6c2.5 1.1 3.5 1 4.8.8a4 4 0 0 0 2.7-1.9 3 3 0 0 0 .2-1.9c-.2-.2-.5-.3-.8-.5z"/>
            </svg>
        </a>
    </div>

    <script>
        lucide.createIcons();
        let currentUrl = "";

        async function fetchInfo() {
            const urlInput = document.getElementById('video-url');
            const url = urlInput.value.trim();
            const statusText = document.getElementById('status-text');
            const previewBox = document.getElementById('preview-box');

            if (!url) return;
            currentUrl = url;

            previewBox.style.display = 'none';
            document.getElementById('progress-box').style.display = 'none';
            document.getElementById('download-btn').style.display = 'none';
            statusText.innerText = "Se caută informațiile clipului...";

            try {
                const res = await fetch('/info', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });

                const data = await res.json();
                if (data.error) {
                    statusText.innerText = "Eroare: " + data.error;
                    return;
                }

                document.getElementById('title').innerText = data.title;
                document.getElementById('thumb').src = data.thumbnail;
                statusText.innerText = "";
                previewBox.style.display = 'block';

            } catch (err) {
                statusText.innerText = "S-a produs o eroare la conectare.";
            }
        }

        async function startDownload(type) {
            const quality = document.getElementById('quality-select').value;
            document.getElementById('preview-box').style.display = 'none';
            document.getElementById('progress-box').style.display = 'block';

            const res = await fetch('/start-task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: currentUrl, type: type, quality: quality })
            });

            const data = await res.json();
            const taskId = data.task_id;

            const eventSource = new EventSource(`/progress/${taskId}`);

            eventSource.onmessage = function(e) {
                const info = JSON.parse(e.data);

                if (info.status === 'downloading') {
                    document.getElementById('percent-label').innerText = info.percent + "%";
                    document.getElementById('progress-fill').style.width = info.percent + "%";
                    document.getElementById('speed-label').innerText = info.speed;
                    document.getElementById('size-label').innerText = info.downloaded + " / " + info.total;
                } 
                else if (info.status === 'finished') {
                    eventSource.close();
                    document.getElementById('status-label').innerText = "Gata!";
                    document.getElementById('percent-label').innerText = "100%";
                    document.getElementById('progress-fill').style.width = "100%";

                    const downloadBtn = document.getElementById('download-btn');
                    downloadBtn.href = `/get-file/${encodeURIComponent(info.filename)}`;
                    downloadBtn.style.display = 'flex';
                }
                else if (info.status === 'error') {
                    eventSource.close();
                    alert("Eroare la descărcare: " + info.message);
                }
            };
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/info', methods=['POST'])
def get_info():
    data = request.get_json()
    url = data.get('url')
    
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                'title': info.get('title', 'Video fără titlu'),
                'thumbnail': info.get('thumbnail', '')
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_download(task_id, url, file_type, quality):
    tasks[task_id] = {'status': 'downloading', 'percent': 0, 'speed': '0 MB/s', 'downloaded': '0 MB', 'total': '0 MB'}

    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            speed = d.get('speed', 0) or 0
            
            percent = round((downloaded / total * 100), 1) if total > 0 else 0
            
            tasks[task_id].update({
                'status': 'downloading',
                'percent': percent,
                'speed': f"{round(speed / 1024 / 1024, 2)} MB/s",
                'downloaded': f"{round(downloaded / 1024 / 1024, 1)} MB",
                'total': f"{round(total / 1024 / 1024, 1)} MB"
            })
        elif d['status'] == 'finished':
            tasks[task_id]['status'] = 'finished'
            tasks[task_id]['filename'] = os.path.basename(d['filename'])

    out_filename = f"media_{task_id}"
    
    # Optimizare Multi-Thread & Format Viteza
    format_str = 'best[ext=mp4]/best'
    if quality == '720':
        format_str = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]'
    elif quality == '480':
        format_str = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]'

    ydl_opts = {
        'format': format_str if file_type == 'mp4' else 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, f"{out_filename}.%(ext)s"),
        'progress_hooks': [progress_hook],
        'concurrent_fragment_downloads': 10,  # Multi-thread paralel
        'buffersize': 1024 * 64,               # Buffer mărit 64KB
        'quiet': True
    }

    # Dacă aria2c este instalat pe sistem, îl folosește automat pentru viteze maxime
    if os.path.exists('/data/data/com.termux/files/usr/bin/aria2c') or os.path.exists('/usr/bin/aria2c'):
        ydl_opts['external_downloader'] = 'aria2c'
        ydl_opts['external_downloader_args'] = ['-x16', '-s16', '-k1M']

    if file_type == 'mp3':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if file_type == 'mp3':
                filename = os.path.splitext(filename)[0] + '.mp3'
            tasks[task_id]['filename'] = os.path.basename(filename)
            tasks[task_id]['status'] = 'finished'
    except Exception as e:
        tasks[task_id] = {'status': 'error', 'message': str(e)}

@app.route('/start-task', methods=['POST'])
def start_task():
    data = request.get_json()
    task_id = os.urandom(4).hex()
    
    thread = threading.Thread(target=run_download, args=(task_id, data['url'], data['type'], data.get('quality', 'best')))
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/progress/<task_id>')
def progress(task_id):
    def event_stream():
        while True:
            task = tasks.get(task_id, {})
            yield f"data: {json.dumps(task)}\n\n"
            if task.get('status') in ['finished', 'error']:
                break
            time.sleep(0.3)

    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/get-file/<filename>')
def get_file(filename):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    print("Server activ la adresa: http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)