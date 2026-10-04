import os
import requests
from flask import Flask, request, jsonify
from PIL import Image
from moviepy import VideoFileClip

app = Flask(__name__)

# Token Zalo Bot
BOT_TOKEN = "3190358309365122943:hCYFHLRIkeKUjgFZHcWvNstmMqmXunnCyYHDVFCcpxEUrCVrXwVRPVVKMFkOiVaD"
ZALO_BOT_API = f"https://bot-api.zaloplatforms.com/bot{BOT_TOKEN}"

# Bộ nhớ tạm lưu media theo msg_id: { msg_id: (media_url, media_type) }
MEDIA_CACHE = {}

def send_zalo_message(chat_id, text):
    """Gửi tin nhắn phản hồi"""
    url = f"{ZALO_BOT_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print("LOG SEND:", res.text)
    except Exception as e:
        print("LỖI SEND:", e)

def find_media_in_payload(data):
    """Trích xuất URL/file_id từ tin nhắn Zalo gửi về"""
    if not isinstance(data, dict):
        return None, None

    attachments = data.get("attachments", [])
    if isinstance(attachments, list) and len(attachments) > 0:
        att = attachments[0]
        att_type = att.get("type", "photo")
        payload = att.get("payload", {})
        url = payload.get("url") or payload.get("file_id") or payload.get("thumbnail")
        if url:
            return url, att_type

    if "photo" in data:
        photos = data.get("photo", [])
        if isinstance(photos, list) and photos:
            return photos[-1].get("file_id") or photos[-1].get("url"), "photo"
        elif isinstance(photos, dict):
            return photos.get("file_id") or photos.get("url"), "photo"

    if "video" in data:
        video = data.get("video", {})
        if isinstance(video, dict):
            return video.get("file_id") or video.get("url"), "video"

    return None, None

@app.route("/", methods=["GET"])
def home():
    return "Bot đang hoạt động!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    print("=== DỮ LIỆU ZALO ===")
    print(data)

    message = data.get("message") or data.get("event", {})
    if message:
        chat_id = str(
            message.get("chat", {}).get("id") 
            or data.get("sender", {}).get("id") 
            or message.get("from", {}).get("id")
        )
        msg_id = str(message.get("msg_id") or message.get("message_id") or "")
        text = (message.get("text") or "").strip()

        # 1. Nếu tin nhắn gửi lên chứa Media -> Lưu vào Cache theo ID tin nhắn
        curr_url, curr_type = find_media_in_payload(message)
        if msg_id and curr_url:
            MEDIA_CACHE[msg_id] = (curr_url, curr_type)

        # 2. Xử lý khi nhận lệnh !sticker
        if "!sticker" in text.lower():
            target_url, target_type = None, None

            # Kiểm tra xem người dùng có thao tác Trả lời (Reply) hay không
            quote = message.get("quote") or message.get("quote_msg") or message.get("reply_to")
            
            if quote and isinstance(quote, dict):
                # Lấy ID của tin nhắn được reply
                quoted_msg_id = str(quote.get("msg_id") or quote.get("message_id") or quote.get("global_id") or "")
                
                # Tra cứu trong Cache
                if quoted_msg_id in MEDIA_CACHE:
                    target_url, target_type = MEDIA_CACHE[quoted_msg_id]
                else:
                    # Nếu Zalo gửi kèm thông tin đính kèm trong object quote
                    target_url, target_type = find_media_in_payload(quote)

            # Nếu không phải thao tác Reply hoặc không tìm thấy file
            if not target_url:
                send_zalo_message(
                    chat_id, 
                    "⚠️ Vui lòng Trả lời (Reply) trực tiếp vào tin nhắn Ảnh hoặc Video bằng lệnh '!sticker'!"
                )
                return jsonify({"status": "no_reply_media"}), 200

            try:
                # Chuyển đổi file_id thành link tải nếu cần
                if not str(target_url).startswith("http"):
                    file_res = requests.get(f"{ZALO_BOT_API}/getFile?file_id={target_url}").json()
                    file_path = file_res.get("result", {}).get("file_path")
                    if file_path:
                        target_url = f"https://bot-api.zaloplatforms.com/file/bot{BOT_TOKEN}/{file_path}"

                # Tải file về máy chủ
                res = requests.get(target_url, timeout=20)
                input_file = "temp_input"
                with open(input_file, "wb") as f:
                    f.write(res.content)

                if "video" in str(target_type):
                    send_zalo_message(chat_id, "⏳ Đang chuyển đổi Video sang GIF...")
                    output_file = "sticker.gif"
                    clip = VideoFileClip(input_file)
                    if clip.duration > 8:
                        clip = clip.subclipped(0, 8)
                    clip = clip.resized(width=360)
                    clip.write_gif(output_file, fps=10)
                    clip.close()
                    send_zalo_message(chat_id, "✅ Đã xử lý xong GIF từ Video!")
                else:
                    send_zalo_message(chat_id, "⏳ Đang chuyển đổi Ảnh sang Sticker...")
                    output_file = "sticker.png"
                    im = Image.open(input_file)
                    im.thumbnail((512, 512))
                    im.save(output_file, "PNG")
                    send_zalo_message(chat_id, "✅ Đã xử lý xong Sticker từ Ảnh!")

                # Dọn dẹp file tạm
                if os.path.exists(input_file): os.remove(input_file)
                if os.path.exists("sticker.png"): os.remove("sticker.png")
                if os.path.exists("sticker.gif"): os.remove("sticker.gif")

            except Exception as e:
                print("LỖI XỬ LÝ:", e)
                send_zalo_message(chat_id, f"❌ Lỗi tạo sticker: {str(e)}")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
