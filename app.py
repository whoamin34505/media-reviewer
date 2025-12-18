import random
import shutil
from pathlib import Path
import json
from datetime import datetime
from flask import Flask, render_template, send_file, redirect, url_for
from PIL import Image
import pillow_heif

from config import PHOTO_DIR, TRASH_DIR, ALLOWED_EXTENSIONS

pillow_heif.register_heif_opener()

app = Flask(__name__)

PHOTO_DIR.mkdir(exist_ok=True)
TRASH_DIR.mkdir(exist_ok=True)

TRASH_LOG_FILE = Path("trash_log.json")
if not TRASH_LOG_FILE.exists():
    TRASH_LOG_FILE.write_text("[]")

def load_trash_log():
    if TRASH_LOG_FILE.exists() and TRASH_LOG_FILE.stat().st_size > 0:
        try:
            return json.loads(TRASH_LOG_FILE.read_text())
        except json.JSONDecodeError:
            print("[WARNING] Лог повреждён, создаём новый.")
            return []
    else:
        return []



def save_trash_log(log):
    TRASH_LOG_FILE.write_text(json.dumps(log, indent=4))

def scan_photos():
    return [
        p for p in PHOTO_DIR.rglob("*")
        if p.suffix.lower() in ALLOWED_EXTENSIONS and p.is_file()
    ]


@app.route("/")
def index():
    photos = scan_photos()
    if not photos:
        return "<h2>Фотографий больше нет</h2>"

    photo = random.choice(photos)
    return render_template("index.html", photo_path=photo.name)


@app.route("/photo/<filename>")
def get_photo(filename):
    path = PHOTO_DIR / filename

    if path.suffix.lower() == ".heic":
        img = Image.open(path)
        temp_path = Path("temp.jpg")
        img.save(temp_path, "JPEG")
        return send_file(temp_path, mimetype="image/jpeg")

    return send_file(path)


@app.route("/keep/<filename>")
def keep_photo(filename):
    return redirect(url_for("index"))


@app.route("/delete/<filename>")
def delete_photo(filename):
    src = PHOTO_DIR / filename
    dst = TRASH_DIR / filename

    if src.exists():
        shutil.move(src, dst)

        log = load_trash_log()
        log.append({
            "filename": filename,
            "original_path": str(PHOTO_DIR / filename),
            "deleted_at": datetime.now().isoformat()
        })
        save_trash_log(log)

    return redirect(url_for("index"))

@app.route("/trash")
def view_trash():
    log = load_trash_log()
    return render_template("trash.html", log=log)

@app.route("/restore/<filename>")
def restore_photo(filename):
    log = load_trash_log()
    item = next((x for x in log if x["filename"] == filename), None)
    if item:
        src = TRASH_DIR / filename
        dst = Path(item["original_path"])
        if src.exists():
            shutil.move(src, dst)
            log = [x for x in log if x["filename"] != filename]
            save_trash_log(log)
    return redirect(url_for("view_trash"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

