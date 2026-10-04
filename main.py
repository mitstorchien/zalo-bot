import os
import requests
from flask import Flask, request, jsonify
from PIL import Image
from moviepy import VideoFileClip

app = Flask(__name__)

# Token Zalo Bot của bạn
BOT_TOKEN = "3190358309365122943:hCYFHLRIkeKUjgFZHcWvNstmMqmXunnCyYHDVFCcpxEUrCVrXwVRPVVKMFkOiVaD"
ZALO_BOT_API = f"https://bot-api.zaloplatforms.com/bot{BOT_TOKEN}"

# Bộ nhớ tạm lưu trữ tin nhắn chứa Media: { msg_id: (media_url, media_type) }
MEDIA_CACHE = {}

def send_zalo_message(chat_id, text):
    """Gửi tin nhắn phản hồi"""
    url = f"{ZALO_BOT_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print("KẾT QUẢ GỬI TIN NHẮN:", res.text)
    except Exception as e:
        print("LỖI GỬI TIN NHẮN:", e)

def extract_media_from_msg(msg):
    """Trích xuất media từ tin nhắn đơn"""
    if not isinstance(msg, dict):
        return None, None

    # Tìm photo
    if "photo" in msg:
        photos = msg.get("photo", [])
        if isinstance(photos, list) and photos:
            url = photos[-1].get("file_id") or photos[-1].get("url") or photos[-1].get("href")
            return url, "photo"
        elif isinstance(photos, dict):
            url = photos.get("file_id") or photos.get("url") or photos.get("href")
            return url, "photo"

    # Tìm video
    if "video" in msg:
        video = msg.get("video", {})
        if isinstance(video, dict):
            url = video.get("file_id") or video.get("url") or video.get("href")
            return url, "video"

    # Tìm trong attachments
    attachments = msg.get("attachments", [])
    if isinstance(attachments, list):
        for att in attachments:
            att_type = att.get("type", "")
            payload = att.get("payload", {})
            url = payload.get("file_id") or payload.get("url") or payload.get("thumbnail")
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
        msg_id = message.get("msg_id") or message.get("message_id")
        text = message.get("text", "").strip()

        # 1. Lưu media của tin nhắn hiện tại vào Cache (nếu có)
        url, mtype = extract_media_from_msg(message)
        if msg_id and url:
            MEDIA_CACHE[str(msg_id)] = (url, mtype)

        # 2. Xử lý lệnh !sticker
        if "!sticker" in text.lower():
            media_url, media_type = None, None

            # Kiểm tra xem có phải tin nhắn Reply không
            quote = message.get("quote") or message.get("quote_msg") or message.get("reply_to_message")
            if quote and isinstance(quote, dict):
                quoted_msg_id = quote.get("msg_id") or quote.get("message_id")
                # Thử lấy từ cache trước
                if quoted_msg_id and str(quoted_msg_id) in MEDIA_CACHE:
                    media_url, media_type = MEDIA_CACHE[str(quoted_msg_id)]
                else:
                    # Lấy trực tiếp từ đối tượng quote nếu Zalo có gửi kèm
                    media_url, media_type = extract_media_from_msg(quote)

            # Nếu không tìm thấy qua Reply, lấy media từ chính tin nhắn gửi kèm !sticker
            if not media_url:
                media_url, media_type = url, mtype

            # Báo lỗi nếu vẫn không tìm thấy
            if not media_url:
                send_zalo_message(
                    chat_id, 
                    "⚠️ Vui lòng Trả lời (Reply) trực tiếp vào tin nhắn Ảnh hoặc Video bằng lệnh '!sticker'!"
                )
                return jsonify({"status": "no_media"}), 200

            # Tiến hành xử lý tạo Sticker / GIF
            try:
                # Nếu media_url là file_id, gọi API Zalo để lấy link tải thực tế
                if not str(media_url).startswith("http"):
                    file_res = requests.get(f"{ZALO_BOT_API}/getFile?file_id={media_url}").json()
                    file_path = file_res.get("result", {}).get("file_path")
                    if file_path:
                        media_url = f"https://bot-api.zaloplatforms.com/file/bot{BOT_TOKEN}/{file_path}"

                res = requests.get(media_url, timeout=20)
                input_file = "temp_input"
                with open(input_file, "wb") as f:
                    f.write(res.content)

                if "photo" in str(media_type) or "image" in str(media_type):
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

                # Dọn dẹp file tạm
                if os.path.exists(input_file): os.remove(input_file)
                if os.path.exists("sticker.png"): os.remove("sticker.png")
                if os.path.exists("sticker.gif"): os.remove("sticker.gif")

            except Exception as e:
                print("LỖI XỬ LÝ MEDIA:", e)
                send_zalo_message(chat_id, f"❌ Có lỗi khi tạo sticker: {str(e)}")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
