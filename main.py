import os
import requests
from flask import Flask, request, jsonify
from PIL import Image
from moviepy import VideoFileClip

app = Flask(__name__)

# Token Zalo Bot
BOT_TOKEN = "3190358309365122943:hCYFHLRIkeKUjgFZHcWvNstmMqmXunnCyYHDVFCcpxEUrCVrXwVRPVVKMFkOiVaD"
ZALO_BOT_API = f"https://bot-api.zaloplatforms.com/bot{BOT_TOKEN}"

# Bộ nhớ tạm
LAST_USER_MEDIA = {}

def send_zalo_message(chat_id, text):
    """Gửi tin nhắn phản hồi"""
    url = f"{ZALO_BOT_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print("LOG SEND:", res.text)
    except Exception as e:
        print("LỖI SEND:", e)

def extract_media_from_payload(payload):
    """Quét toàn bộ payload để tìm link/file_id media bất kể cấu trúc Zalo gửi về"""
    if not isinstance(payload, dict):
        return None, None

    # 1. Quét trường photo/video trực tiếp
    if "photo" in payload:
        p = payload["photo"]
        if isinstance(p, list) and len(p) > 0:
            return p[-1].get("file_id") or p[-1].get("url"), "photo"
        elif isinstance(p, dict):
            return p.get("file_id") or p.get("url"), "photo"

    if "video" in payload:
        v = payload["video"]
        if isinstance(v, dict):
            return v.get("file_id") or v.get("url"), "video"

    # 2. Quét trường attachments
    atts = payload.get("attachments", [])
    if isinstance(atts, list) and len(atts) > 0:
        att = atts[0]
        att_type = att.get("type", "photo")
        p_data = att.get("payload", {})
        url = p_data.get("url") or p_data.get("file_id") or p_data.get("thumbnail")
        if url:
            return url, att_type

    # 3. Quét trường message con nếu có
    if "message" in payload and isinstance(payload["message"], dict):
        return extract_media_from_payload(payload["message"])

    return None, None

@app.route("/", methods=["GET"])
def home():
    return "Bot đang hoạt động!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    print("=== DỮ LIỆU ZALO WEBHOOK RECEIVE ===")
    print(data)

    message = data.get("message") or data.get("event") or data
    
    # Lấy Chat ID
    chat_id = None
    if isinstance(message, dict):
        chat_id = str(
            message.get("chat", {}).get("id") 
            or data.get("sender", {}).get("id") 
            or message.get("from", {}).get("id")
            or data.get("recipient", {}).get("id")
        )

    if chat_id:
        text = ""
        if isinstance(message, dict):
            text = (message.get("text") or "").strip().lower()

        # Tự động quét và lưu Media nếu có trong payload
        media_url, media_type = extract_media_from_payload(data)
        if media_url:
            LAST_USER_MEDIA[chat_id] = (media_url, media_type)
            print(f"✅ ĐÃ LƯU MEDIA CHO CHAT_ID {chat_id}: {media_url}")

        # Xử lý lệnh "s" hoặc "!sticker"
        if text in ["s", "!s", "!sticker"]:
            target_url, target_type = LAST_USER_MEDIA.get(chat_id, (None, None))

            if not target_url:
                send_zalo_message(
                    chat_id, 
                    "⚠️ Chưa nhận được Ảnh/Video nào!\n\nHãy gửi 1 Ảnh hoặc Video mới lên trước, sau đó nhắn chữ 's'."
                )
                return jsonify({"status": "no_media"}), 200

            try:
                # Chuyển file_id thành URL tải nếu cần
                if not str(target_url).startswith("http"):
                    file_res = requests.get(f"{ZALO_BOT_API}/getFile?file_id={target_url}").json()
                    file_path = file_res.get("result", {}).get("file_path")
                    if file_path:
                        target_url = f"https://bot-api.zaloplatforms.com/file/bot{BOT_TOKEN}/{file_path}"

                res = requests.get(target_url, timeout=20)
                input_file = "temp_input"
                with open(input_file, "wb") as f:
                    f.write(res.content)

                if "video" in str(target_type):
                    send_zalo_message(chat_id, "⏳ Đang chuyển Video sang GIF...")
                    output_file = "sticker.gif"
                    clip = VideoFileClip(input_file)
                    if clip.duration > 8:
                        clip = clip.subclipped(0, 8)
                    clip = clip.resized(width=360)
                    clip.write_gif(output_file, fps=10)
                    clip.close()
                    send_zalo_message(chat_id, "✅ Đã xử lý xong GIF!")
                else:
                    send_zalo_message(chat_id, "⏳ Đang chuyển Ảnh sang Sticker...")
                    output_file = "sticker.png"
                    im = Image.open(input_file)
                    im.thumbnail((512, 512))
                    im.save(output_file, "PNG")
                    send_zalo_message(chat_id, "✅ Đã xử lý xong Sticker!")

                # Dọn dẹp file
                if os.path.exists(input_file): os.remove(input_file)
                if os.path.exists("sticker.png"): os.remove("sticker.png")
                if os.path.exists("sticker.gif"): os.remove("sticker.gif")

            except Exception as e:
                print("LỖI XỬ LÝ:", e)
                send_zalo_message(chat_id, f"❌ Lỗi tạo sticker: {str(e)}")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
