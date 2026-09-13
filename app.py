import os
import glob
import uuid

from flask import Flask, request, jsonify, send_file, render_template_string
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

COOKIE_FILE_PATH = "/tmp/youtube_cookies.txt"

# ---------------------------------------------------------
# Optional YouTube cookies
# ---------------------------------------------------------

cookies_env = os.environ.get("YOUTUBE_COOKIES")

if cookies_env:
    cookies_env = cookies_env.replace("\\r\\n", "\n")
    cookies_env = cookies_env.replace("\\n", "\n")

    with open(
        COOKIE_FILE_PATH,
        "w",
        encoding="utf-8",
        newline="\n"
    ) as f:
        f.write(cookies_env)


# ---------------------------------------------------------
# Web UI
# ---------------------------------------------------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

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
            font-family:
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;

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

            box-shadow:
                0 10px 25px rgba(0, 0, 0, 0.4);
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

        input:focus,
        select:focus {
            outline: none;

            border-color: var(--accent);
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
            background:
                rgba(248, 113, 113, 0.1);

            color: var(--error);

            border:
                1px solid var(--error);
        }

        .success {
            background:
                rgba(74, 222, 128, 0.1);

            color: var(--success);

            border:
                1px solid var(--success);
        }

        .info {
            background:
                rgba(99, 102, 241, 0.1);

            color: var(--accent);

            border:
                1px solid var(--accent);
        }

        @media (max-width: 500px) {
            .grid {
                grid-template-columns: 1fr;
            }

            .card {
                padding: 1.5rem;
            }
        }
    </style>
</head>

<body>

<div class="card">

    <h1>Media Downloader</h1>

    <div class="form-group">

        <label for="url">
            Paste Video Link
        </label>

        <input
            type="url"
            id="url"
            placeholder="https://www.youtube.com/watch?v=..."
            autocomplete="off"
            required
        >

    </div>

    <div class="grid">

        <div class="form-group">

            <label for="format">
                Format
            </label>

            <select
                id="format"
                onchange="toggleQuality()"
            >

                <option value="mp4">
                    MP4 (Video)
                </option>

                <option value="mp3">
                    MP3 (Audio)
                </option>

            </select>

        </div>

        <div
            class="form-group"
            id="qualityWrapper"
        >

            <label for="quality">
                Quality
            </label>

            <select id="quality">

                <option value="max">
                    Best Available
                </option>

                <option value="1080">
                    1080p
                </option>

                <option value="720">
                    720p
                </option>

                <option value="480">
                    480p
                </option>

            </select>

        </div>

    </div>

    <button
        id="dlBtn"
        onclick="startDownload()"
    >
        Download
    </button>

    <div id="status"></div>

</div>

<script>

function toggleQuality() {

    const format =
        document.getElementById("format").value;

    document.getElementById(
        "qualityWrapper"
    ).style.display =
        format === "mp3"
            ? "none"
            : "block";
}


function setStatus(message, type) {

    const status =
        document.getElementById("status");

    status.style.display = "block";

    status.className = type;

    status.textContent = message;
}


async function startDownload() {

    const url =
        document.getElementById("url")
            .value
            .trim();

    const format =
        document.getElementById("format")
            .value;

    const quality =
        document.getElementById("quality")
            .value;

    const button =
        document.getElementById("dlBtn");


    if (!url) {

        setStatus(
            "Please enter a valid video URL.",
            "error"
        );

        return;
    }


    button.disabled = true;

    setStatus(
        "Downloading and converting media... Please wait.",
        "info"
    );


    try {

        const response =
            await fetch("/download", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    url: url,
                    format: format,
                    quality: quality
                })

            });


        if (!response.ok) {

            let message =
                "Failed to download media.";

            try {

                const data =
                    await response.json();

                if (data.error) {
                    message = data.error;
                }

            } catch (_) {}

            throw new Error(message);
        }


        const blob =
            await response.blob();


        const downloadUrl =
            window.URL.createObjectURL(blob);


        const link =
            document.createElement("a");

        link.href = downloadUrl;

        link.download =
            format === "mp3"
                ? "download.mp3"
                : "download.mp4";


        document.body.appendChild(link);

        link.click();

        link.remove();


        setTimeout(() => {
            window.URL.revokeObjectURL(
                downloadUrl
            );
        }, 1000);


        setStatus(
            "Download started successfully!",
            "success"
        );

    } catch (error) {

        setStatus(
            "Error: " + error.message,
            "error"
        );

    } finally {

        button.disabled = false;
    }
}


toggleQuality();

</script>

</body>
</html>
"""


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def cleanup_downloads():
    """Remove old files from the temporary download folder."""

    for path in glob.glob(
        os.path.join(DOWNLOAD_DIR, "*")
    ):
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass


def get_cookie_options():
    """Use cookies only when a Netscape cookie file is present."""

    if not os.path.isfile(COOKIE_FILE_PATH):
        return {}

    try:

        if os.path.getsize(COOKIE_FILE_PATH) == 0:
            return {}

        with open(
            COOKIE_FILE_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            first_line = f.readline().strip()

        if first_line in (
            "# Netscape HTTP Cookie File",
            "# HTTP Cookie File"
        ):

            return {
                "cookiefile": COOKIE_FILE_PATH
            }

    except Exception:
        pass

    return {}


def build_options(fmt, quality, output_template):
    """Create yt-dlp configuration."""

    headers = {
        "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/153.0.0.0 Safari/537.36",

        "Accept-Language":
            "en-US,en;q=0.9",

        "Accept":
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
    }


    options = {

        "outtmpl":
            output_template,

        "http_headers":
            headers,

        "noplaylist":
            True,

        "quiet":
            True,

        "no_warnings":
            True,

        "retries":
            3,

        "fragment_retries":
            3,

        "socket_timeout":
            30,

        "continuedl":
            True,

        "overwrites":
            True,

        "restrictfilenames":
            True,

        "windowsfilenames":
            True
    }


    # Do NOT force player_client here.
    #
    # yt-dlp will choose the appropriate YouTube
    # extraction clients for the installed version.

    options.update(
        get_cookie_options()
    )


    if fmt == "mp3":

        options["format"] = (
            "bestaudio/best"
        )

        options["postprocessors"] = [

            {
                "key":
                    "FFmpegExtractAudio",

                "preferredcodec":
                    "mp3",

                "preferredquality":
                    "192"
            }

        ]

    else:

        if quality == "max":

            options["format"] = (
                "bestvideo[ext=mp4]+"
                "bestaudio[ext=m4a]/"
                "best[ext=mp4]/"
                "best"
            )

        else:

            options["format"] = (
                f"bestvideo[height<={quality}]"
                "[ext=mp4]+"
                "bestaudio[ext=m4a]/"
                f"best[height<={quality}]"
                "[ext=mp4]/"
                f"best[height<={quality}]/"
                "best"
            )

        options["merge_output_format"] = "mp4"


    return options


def find_output_file():

    files = []

    for path in glob.glob(
        os.path.join(DOWNLOAD_DIR, "*")
    ):

        if os.path.isfile(path):

            try:

                if os.path.getsize(path) > 0:
                    files.append(path)

            except Exception:
                pass


    if not files:
        return None


    return max(
        files,
        key=os.path.getmtime
    )


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

@app.route("/")
def home():

    return render_template_string(
        HTML_TEMPLATE
    )


@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({
        "status": "ok",
        "yt_dlp": yt_dlp.version.__version__
    })


@app.route(
    "/download",
    methods=["POST"]
)
def download():

    data =
        request.get_json(
            silent=True
        ) or {}

    url = str(
        data.get("url", "")
    ).strip()

    fmt = data.get(
        "format",
        "mp4"
    )

    quality = data.get(
        "quality",
        "max"
    )


    if not url:

        return jsonify({
            "error":
                "No URL provided."
        }), 400


    if fmt not in (
        "mp4",
        "mp3"
    ):

        return jsonify({
            "error":
                "Invalid format."
        }), 400


    if quality not in (
        "max",
        "1080",
        "720",
        "480"
    ):

        return jsonify({
            "error":
                "Invalid quality."
        }), 400


    cleanup_downloads()


    unique_id = uuid.uuid4().hex

    output_template = os.path.join(
        DOWNLOAD_DIR,
        f"%(title).120s_%(id)s_{unique_id}.%(ext)s"
    )


    ydl_opts = build_options(
        fmt,
        quality,
        output_template
    )


    try:

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.extract_info(
                url,
                download=True
            )


        filename =
            find_output_file()


        if not filename:

            return jsonify({
                "error":
                    "The download completed, "
                    "but no output file was found."
            }), 500


        if fmt == "mp3":

            mimetype = "audio/mpeg"

        else:

            mimetype = "video/mp4"


        return send_file(
            filename,
            mimetype=mimetype,
            as_attachment=True,
            download_name=(
                "download.mp3"
                if fmt == "mp3"
                else "download.mp4"
            )
        )


    except Exception as error:

        message = str(error)


        if (
            "Sign in to confirm"
            in message
        ):

            message = (
                "YouTube requires authentication "
                "for this video. A fresh YouTube "
                "cookies file may be required."
            )


        elif (
            "HTTP Error 429"
            in message
        ):

            message = (
                "YouTube temporarily "
                "rate-limited this server. "
                "Please try again later."
            )


        elif (
            "Video unavailable"
            in message
        ):

            message = (
                "This video is unavailable, "
                "private, or cannot be accessed."
            )


        return jsonify({
            "error": message
        }), 500


# ---------------------------------------------------------
# Local development
# ---------------------------------------------------------

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

