import os
import glob
from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

COOKIE_FILE_PATH = "/tmp/youtube_cookies.txt"

# Write cookies from Render Environment Variable if present
cookies_env = os.environ.get("YOUTUBE_COOKIES")

if cookies_env:
    # Make sure escaped newlines become real newlines
    cookies_env = cookies_env.replace("\\r\\n", "\n").replace("\\n", "\n")

    with open(COOKIE_FILE_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(cookies_env)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Universal Media Downloader</title>

  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --accent: #6366f1;
      --accent-hover: #4f46e5;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --border: #334155;
      --error: #f87171;
      --success: #4ade80;
    }

    * {
      box-sizing: border-box;
    }

    body {
      font-family: system-ui, -apple-system, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
      padding: 20px;
    }

    .card {
      background-color: var(--card-bg);
      padding: 2rem;
      border-radius: 12px;
      width: 100%;
      max-width: 480px;
      border: 1px solid var(--border);
      box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    }

    h1 {
      margin: 0 0 1.5rem 0;
      font-size: 1.5rem;
      text-align: center;
    }

    .form-group {
      margin-bottom: 1.2rem;
    }

    label {
      display: block;
      margin-bottom: 0.5rem;
      font-size: 0.85rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
    }

    input,
    select {
      width: 100%;
      padding: 12px;
      border-radius: 6px;
      border: 1px solid var(--border);
      background-color: var(--bg);
      color: var(--text);
      font-size: 1rem;
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    button {
      width: 100%;
      padding: 14px;
      background-color: var(--accent);
      color: white;
      border: none;
      border-radius: 6px;
      font-weight: bold;
      font-size: 1rem;
      cursor: pointer;
      margin-top: 0.5rem;
    }

    button:hover {
      background-color: var(--accent-hover);
    }

    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    #status {
      margin-top: 1rem;
      padding: 10px;
      border-radius: 6px;
      font-size: 0.9rem;
      text-align: center;
      display: none;
      word-break: break-word;
    }

    .error {
      background: rgba(248, 113, 113, 0.1);
      color: var(--error);
      border: 1px solid var(--error);
    }

    .success {
      background: rgba(74, 222, 128, 0.1);
      color: var(--success);
      border: 1px solid var(--success);
    }

    .info {
      background: rgba(99, 102, 241, 0.1);
      color: var(--accent);
      border: 1px solid var(--accent);
    }
  </style>
</head>

<body>

  <div class="card">
    <h1>Media Downloader</h1>

    <div class="form-group">
      <label for="url">Paste Video Link</label>
      <input
        type="url"
        id="url"
        placeholder="https://www.youtube.com/watch?v=..."
        required
      >
    </div>

    <div class="grid">

      <div class="form-group">
        <label for="format">Format</label>

        <select id="format" onchange="toggleQuality()">
          <option value="mp4">MP4 (Video)</option>
          <option value="mp3">MP3 (Audio)</option>
        </select>
      </div>

      <div class="form-group" id="qualityWrapper">
        <label for="quality">Quality</label>

        <select id="quality">
          <option value="max">Best Available</option>
          <option value="1080">1080p</option>
          <option value="720">720p</option>
          <option value="480">480p</option>
        </select>
      </div>

    </div>

    <button id="dlBtn" onclick="startDownload()">
      Download
    </button>

    <div id="status"></div>
  </div>

  <script>

    function toggleQuality() {
      const fmt = document.getElementById('format').value;

      document.getElementById('qualityWrapper').style.display =
        (fmt === 'mp3') ? 'none' : 'block';
    }

    function setStatus(msg, type) {
      const status = document.getElementById('status');

      status.style.display = 'block';
      status.className = type;
      status.textContent = msg;
    }

    async function startDownload() {

      const url =
        document.getElementById('url').value.trim();

      const format =
        document.getElementById('format').value;

      const quality =
        document.getElementById('quality').value;

      const btn =
        document.getElementById('dlBtn');

      if (!url) {
        setStatus(
          'Please enter a valid video URL.',
          'error'
        );
        return;
      }

      btn.disabled = true;

      setStatus(
        'Downloading and converting media... Please wait.',
        'info'
      );

      try {

        const response = await fetch('/download', {
          method: 'POST',

          headers: {
            'Content-Type': 'application/json'
          },

          body: JSON.stringify({
            url,
            format,
            quality
          })
        });

        if (!response.ok) {

          let errorMessage =
            'Failed to extract media.';

          try {
            const errData =
              await response.json();

            if (errData.error) {
              errorMessage = errData.error;
            }
          } catch (_) {}

          throw new Error(errorMessage);
        }

        const blob =
          await response.blob();

        const downloadUrl =
          window.URL.createObjectURL(blob);

        const a =
          document.createElement('a');

        a.href = downloadUrl;

        a.download =
          `download.${format}`;

        document.body.appendChild(a);

        a.click();

        a.remove();

        window.URL.revokeObjectURL(
          downloadUrl
        );

        setStatus(
          'Download started successfully!',
          'success'
        );

      } catch (err) {

        setStatus(
          `Error: ${err.message}`,
          'error'
        );

      } finally {

        btn.disabled = false;
      }
    }

    toggleQuality();

  </script>

</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)


def build_ydl_options(fmt, quality):
    """
    Build yt-dlp options.

    Important:
    We intentionally do NOT force a specific YouTube
    player_client list. yt-dlp should select the clients
    appropriate for the current extractor version.
    """

    output_template = os.path.join(
        DOWNLOAD_DIR,
        "%(title).150s [%(id)s].%(ext)s"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

   base_opts = {
    'outtmpl': out_template,
    'http_headers': headers,
    'nocheckcertificate': True,
    'quiet': True,
    'no_warnings': True,
}

    # Only use cookies if a valid-looking Netscape cookie
    # file was supplied.
    if (
        os.path.exists(COOKIE_FILE_PATH)
        and os.path.getsize(COOKIE_FILE_PATH) > 0
    ):
        try:
            with open(
                COOKIE_FILE_PATH,
                "r",
                encoding="utf-8"
            ) as f:
                first_line = f.readline().strip()

            if first_line in (
                "# HTTP Cookie File",
                "# Netscape HTTP Cookie File"
            ):
                base_opts["cookiefile"] = COOKIE_FILE_PATH

        except Exception:
            pass

    if fmt == "mp3":

        return {
            **base_opts,

            "format": (
                "bestaudio/best"
            ),

            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

    if quality == "max":

        format_string = (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
            "bestvideo+bestaudio/"
            "best"
        )

    else:

        format_string = (
            f"bestvideo[height<={quality}][ext=mp4]+"
            f"bestaudio[ext=m4a]/"
            f"bestvideo[height<={quality}]+"
            f"bestaudio/"
            f"best[height<={quality}]"
        )

    return {
        **base_opts,

        "format": format_string,

        "merge_output_format": "mp4",
    }


@app.route("/download", methods=["POST"])
def download():

    data = request.get_json(silent=True) or {}

    url = str(data.get("url", "")).strip()
    fmt = data.get("format", "mp4")
    quality = data.get("quality", "max")

    if not url:
        return jsonify({
            "error": "No URL provided."
        }), 400

    if fmt not in ("mp4", "mp3"):
        return jsonify({
            "error": "Invalid format."
        }), 400

    if quality not in (
        "max",
        "1080",
        "720",
        "480"
    ):
        return jsonify({
            "error": "Invalid quality."
        }), 400

    # Remove old files before starting.
    for file in glob.glob(
        os.path.join(DOWNLOAD_DIR, "*")
    ):
        try:
            os.remove(file)
        except Exception:
            pass

    ydl_opts = build_ydl_options(
        fmt,
        quality
    )

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            if not info:
                raise Exception(
                    "yt-dlp returned no video information."
                )

            requested_downloads = (
                info.get("requested_downloads")
                or []
            )

            # Find the actual downloaded file.
            possible_files = []

            for item in requested_downloads:

                filepath = item.get("filepath")

                if filepath:
                    possible_files.append(
                        filepath
                    )

            # yt-dlp's prepared filename is also useful.
            prepared_filename = (
                ydl.prepare_filename(info)
            )

            possible_files.append(
                prepared_filename
            )

            # MP3 postprocessor changes the extension.
            if fmt == "mp3":

                possible_files.append(
                    os.path.splitext(
                        prepared_filename
                    )[0] + ".mp3"
                )

            # MP4 merge can change the final extension.
            if fmt == "mp4":

                possible_files.append(
                    os.path.splitext(
                        prepared_filename
                    )[0] + ".mp4"
                )

            filename = None

            for path in possible_files:

                if (
                    path
                    and os.path.isfile(path)
                    and os.path.getsize(path) > 0
                ):
                    filename = path
                    break

            # Last-resort search.
            if not filename:

                files = [
                    os.path.join(
                        DOWNLOAD_DIR,
                        f
                    )
                    for f in os.listdir(
                        DOWNLOAD_DIR
                    )
                ]

                files = [
                    f for f in files
                    if os.path.isfile(f)
                    and os.path.getsize(f) > 0
                ]

                if files:
                    filename = max(
                        files,
                        key=os.path.getmtime
                    )

            if not filename:

                raise Exception(
                    "Download completed but the output file "
                    "could not be found."
                )

            return send_file(
                filename,
                as_attachment=True
            )

    except Exception as e:

        error = str(e)

        # Give the browser a cleaner error.
        if "Sign in to confirm" in error:
            error = (
                "YouTube requires authentication for this video. "
                "Try again with a fresh YouTube cookies file."
            )

        elif "HTTP Error 429" in error:
            error = (
                "YouTube temporarily rate-limited this server. "
                "Please try again later."
            )

        elif "Video unavailable" in error:
            error = (
                "This video is unavailable or cannot be accessed."
            )

        return jsonify({
            "error": error
        }), 500


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )

