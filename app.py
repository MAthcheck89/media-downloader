import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)  # Allows your GitHub frontend to talk to this backend

DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/')
def home():
    return "Backend server is running!"

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    fmt = data.get('format', 'mp4')
    quality = data.get('quality', '1080')

    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    out_template = os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s')

    if fmt == 'mp3':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out_template,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        if quality == 'max':
            fmt_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        else:
            fmt_str = f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality}][ext=mp4]/best'

        ydl_opts = {
            'format': fmt_str,
            'outtmpl': out_template,
            'merge_output_format': 'mp4',
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if fmt == 'mp3':
                filename = os.path.splitext(filename)[0] + '.mp3'

            return send_file(filename, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)