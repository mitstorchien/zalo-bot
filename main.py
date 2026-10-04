import os
import requests
from flask import Flask, request, jsonify
from PIL import Image
from moviepy import VideoFileClip

app = Flask(__name__)

# Token Zalo Bot của bạn
BOT_TOKEN = "3190358309365122943:hCYFHLRIkeKUjgFZHcWvNstmMqmXunnCyYHDVFCcpxEUrCVrXwVRPVVKMFkOiVaD"
ZALO_BOT_API = f"https://bot-api.zaloplatforms.com/bot{BOT_TOKEN}"

def send_zalo_message(chat_id, text):
    """Gửi tin nhắn phản hồi"""
    url = f"{ZALO_BOT_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print("KẾT QUẢ GỬI TIN NHẮN:", res.text)
    except Exception as e:
        print("LỖI GỬI TIN NHẮN:", e)

def find_media_in_dict(data):
    """Hàm tìm kiếm URL media linh hoạt trong JSON Zalo gửi về"""
    if not isinstance(data, dict):
        return None, None

    # Tìm photo
    if "photo" in data or data.get("type") == "photo":
        photos = data.get("photo", [])
        if isinstance(photos, list) and len(photos) > 0:
            url = photos[-1].get("url") or photos[-1].get("href")
            if url: return url, "photo"
        elif isinstance(photos, dict):
            url = photos.get("url") or photos.get("href")
            if url: return url, "photo"

    # Tìm video
    if "video" in data or data.get("type") == "video":
        video = data.get("video", {})
        if isinstance(video, dict):
            url = video.get("url") or video.get("href") or video.get("file_id")
            if url: return url, "video"

    # Tìm trong attachments
    attachments = data.get("attachments", [])
    if isinstance(attachments, list):
        for att in attachments:
            att_type = att.get("type", "")
            payload = att.get("payload", {})
            url = payload.get("url") or payload.get("thumbnail") or payload.get("file_id")
            if url:
                return url, att_type

    return None, None

@app.route("/", methods=["GET"])
def home():
    return "Bot đang chạy bình thường!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    print("=== DỮ LIỆU NHẬN TỪ ZALO ===")
    print(data)

    message = data.get("message") or data.get("event", {})
    if message:
        chat_id = (
            message.get("chat", {}).get("id") 
            or data.get("sender", {}).get("id") 
            or message.get("from", {}).get("id")
        )
        text = message.get("text", "").strip()

        if "!sticker" in text.lower():
            media_url, media_type = None, None

            # 1. Trích xuất trực tiếp từ tin nhắn
            media_url, media_type = find_media_in_dict(message)

            # 2. Nếu không thấy, trích xuất từ phần Reply (Quote)
            if not media_url:
                quote = message.get("quote") or message.get("quote_msg")
                if quote:
                    media_url, media_type = find_media_in_dict(quote)

            # Nếu vẫn không thấy media
            if not media_url:
                send_zalo_message(
                    chat_id, 
                    "⚠️ Không tìm thấy Ảnh/Video!\n\nHướng dẫn:\n1️⃣ Trả lời (Reply) tin nhắn Ảnh/Video bằng chữ '!sticker'\n2️⃣ Gửi Ảnh/Video kèm chú thích '!sticker'"
                )
                return jsonify({"status": "no_media"}), 200

            # Tiến hành xử lý Media
            try:
                # Nếu media_url dạng file_id của Zalo API
                if not media_url.startswith("http"):
                    file_res = requests.get(f"{ZALO_BOT_API}/getFile?file_id={media_url}").json()
                    file_path = file_res.get("result", {}).get("file_path")
                    if file_path:
                        media_url = f"https://bot-api.zaloplatforms.com/file/bot{BOT_TOKEN}/{file_path}"

                # Tải file về
                res = requests.get(media_url, timeout=15)
                input_file = "temp_input"
                with open(input_file, "wb") as f:
                    f.write(res.content)

                if "photo" in media_type or "image" in media_type:
                    send_zalo_message(chat_id, "⏳ Đang chuyển đổi Ảnh sang Sticker...")
                    output_file = "sticker.png"
                    im = Image.open(input_file)
                    im.thumbnail((512, 512))
                    im.save(output_file, "PNG")
                    send_zalo_message(chat_id, "✅ Đã xử lý xong Sticker từ ảnh!")
                else:
                    send_zalo_message(chat_id, "⏳ Đang chuyển đổi Video sang GIF...")
                    output_file = "sticker.gif"
                    clip = VideoFileClip(input_file)
                    if clip.duration > 8:
                        clip = clip.subclipped(0, 8)
                    clip = clip.resized(width=360)
                    clip.write_gif(output_file, fps=10)
                    clip.close()
                    send_zalo_message(chat_id, "✅ Đã xử lý xong GIF từ video!")

                # Dọn dẹp
                if os.path.exists(input_file): os.remove(input_file)
                if os.path.exists("sticker.png"): os.remove("sticker.png")
                if os.path.exists("sticker.gif"): os.remove("sticker.gif")

            except Exception as e:
                print("LỖI XỬ LÝ MEDIA:", e)
                send_zalo_message(chat_id, f"❌ Có lỗi khi tạo sticker: {str(e)}")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
