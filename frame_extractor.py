import cv2
import os
import smtplib
import zipfile
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# ─── CONFIG ───────────────────────────────────────────
# IMPORTANT: Credentials are now read from environment variables instead of
# being hard-coded. Set these before running the script (see README.md).
#
#   export VIDEO_PATH="/home/svdgsinstallationpc3/Videos/Screencasts/B_09.mp4"
#   export SENDER_EMAIL="your_email@gmail.com"
#   export SENDER_PASSWORD="your_gmail_app_password"
#   export RECEIVER_EMAIL="receiver_email@gmail.com"
#
# Or create a `.env` file (see README) and load it with python-dotenv.

video_path = os.environ.get("VIDEO_PATH", "/home/svdgsinstallationpc3/Videos/Screencasts/B_09.mp4")
output_folder = "task"
zip_path = "frames.zip"

SENDER_EMAIL    = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD")
RECEIVER_EMAIL  = os.environ.get("RECEIVER_EMAIL")

if not SENDER_EMAIL or not SENDER_PASSWORD or not RECEIVER_EMAIL:
    raise EnvironmentError(
        "Missing required environment variables. Please set SENDER_EMAIL, "
        "SENDER_PASSWORD, and RECEIVER_EMAIL before running this script. "
        "See README.md for setup instructions."
    )
# ──────────────────────────────────────────────────────

if not os.path.exists(video_path):
    raise FileNotFoundError(f"Video not found: {video_path}")

os.makedirs(output_folder, exist_ok=True)

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("Error: Video not found")
    exit()

fps = int(cap.get(cv2.CAP_PROP_FPS))
if fps <= 1 or fps > 100:
    fps = 2

print("FPS:", fps)

frame_count = 0
saved_count = 0
saved_files = []

# ─── FRAME EXTRACTION ─────────────────────────────
while True:
    ret, frame = cap.read()
    if not ret:
        break

    if frame_count % fps == 0:
        frame_filename = os.path.join(output_folder, f"frame_{saved_count:06d}.jpg")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(frame_filename, gray)
        saved_files.append(frame_filename)
        print(f"Saved: {frame_filename}")
        saved_count += 1

    frame_count += 1

cap.release()
print(f"\nTotal frames: {frame_count}")
print(f"Saved frames: {saved_count}")

# ─── CREATE ZIP ────────────────────────────────────────
print("\nZIP bana raha hai...")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
    for frame_path in saved_files:
        zipf.write(frame_path, os.path.basename(frame_path))

zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
print(f"ZIP size: {zip_size_mb:.2f} MB")

# ─── IF ZIP IS OVER 25 MB ──────────────────
MAX_SIZE_MB = 24

if zip_size_mb > MAX_SIZE_MB:
    print(f"ZIP size is large ({zip_size_mb:.1f} MB), send in part...")

    # divided in part
    part_files = []
    part_num = 0
    current_part_files = []
    current_size = 0

    for frame_path in saved_files:
        file_size = os.path.getsize(frame_path) / (1024 * 1024)

        if current_size + file_size > MAX_SIZE_MB and current_part_files:
            part_zip = f"frames_part{part_num + 1}.zip"
            with zipfile.ZipFile(part_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                for fp in current_part_files:
                    zipf.write(fp, os.path.basename(fp))
            part_files.append(part_zip)
            part_num += 1
            current_part_files = []
            current_size = 0

        current_part_files.append(frame_path)
        current_size += file_size

    # Last part
    if current_part_files:
        part_zip = f"frames_part{part_num + 1}.zip"
        with zipfile.ZipFile(part_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            for fp in current_part_files:
                zipf.write(fp, os.path.basename(fp))
        part_files.append(part_zip)

    print(f"Created {len(part_files)} parts")

else:
    part_files = [zip_path]
    print("ZIP size is ok, send in an email")

# ── SEND EMAIL ─────────────────────────────────────
print("\nSending email...")

try:
    for i, part_zip in enumerate(part_files):
        msg = MIMEMultipart()
        msg["From"]    = SENDER_EMAIL
        msg["To"]      = RECEIVER_EMAIL
        msg["Subject"] = f"Video Frames - Part {i+1}/{len(part_files)} ({saved_count} total frames)"

        body = (
            f"Part {i+1} of {len(part_files)}\n"
            f"Total frames extracted: {saved_count}\n"
            f"Video: {os.path.basename(video_path)}"
        )
        msg.attach(MIMEText(body, "plain"))

        with open(part_zip, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(part_zip)}"
            )
            msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

        print(f"✅ Part {i+1}/{len(part_files)} bheji: {part_zip}")

    print(f"\n✅ All email are send successfully: {RECEIVER_EMAIL}")

except Exception as e:
    print(f"❌ failed email sending: {e}")
