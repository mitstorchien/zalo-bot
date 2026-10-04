import os
import requests
from flask import Flask, request, jsonify
from PIL import Image
from moviepy import VideoFileClip

app = Flask(__name__)

BOT_TOKEN = "3190358309365122943:hCYFHLRIkeKUjgFZHcWvNstmMqmXunnCyYHDVFCcpxEUrCVrXwVRPVVKMFkOiVaD"
ZALO_BOT_API = f"https://bot-api.zaloplatforms.com/bot{BOT_TOKEN}"

# Bộ nhớ tạm để lưu tin nhắn media
MEDIA_CACHE = {}

def send_zalo_message(chat_id, text):
    url = f"{ZALO_BOT_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print("LOG SEND:", res.text)
    except Exception as e:
        print("LỖI SEND:", e)

def extract_media(msg_dict):
    """Trích xuất link media từ dict tin nhắn"""
    if not isinstance(msg_dict, dict):
        return None, None
        
    # Check trong attachments
    attachments = msg_dict.get("attachments", [])
    if isinstance(attachments, list) and len(attachments) > 0:
        att = attachments[0]
        payload = att.get("payload", {})
        url = payload.get("url") or payload.get("thumbnail") or payload.get("file_id")
        att_type = att.get("type", "photo")
        if url:
            return url, att_type

    # Check photo/video trực tiếp
    if "photo" in msg_dict:
        photos = msg_dict.get("photo", [])
        if isinstance(photos, list) and photos:
            url = photos[-1].get("file_id") or photos[-1].get("url")
            return url, "photo"
    if "video" in msg_dict:
        video = msg_dict.get("video", {})
        url = video.get("file_id") or video.get("url")
        return url, "video"

    return None, None

@app.route("/", methods=["GET"])
def home():
    return "Bot đang chạy!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    print("=== ZALO PAYLOAD ===")
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

        # 1. Trích xuất media từ tin nhắn hiện tại và lưu cache
        curr_url, curr_type = extract_media(message)
        if msg_id and curr_url:
            MEDIA_CACHE[str(msg_id)] = (curr_url, curr_type)

        # 2. Xử lý lệnh !sticker
        if "!sticker" in text.lower():
            media_url, media_type = None, None

            # BẮT ĐẦU TÌM TRONG QUOTE/REPLY
            quote = message.get("quote") or message.get("quote_msg") or message.get("reply_to")
            if quote and isinstance(quote, dict):
                # Cách A: Lấy trực tiếp từ quote object
                media_url, media_type = extract_media(quote)
                
                # Cách B: Tra cứu ID tin nhắn quote trong CACHE
                if not media_url:
                    q_id = quote.get("msg_id") or quote.get("message_id") or quote.get("global_id")
                    if q_id and str(q_id) in MEDIA_CACHE:
                        media_url, media_type = MEDIA_CACHE[str(q_id)]

            # Nếu không reply, dùng media đính kèm trực tiếp
            if not media_url:
                media_url, media_type = curr_url, curr_type

            if not media_url:
                send_zalo_message(
                    chat_id, 
                    "⚠️ Vui lòng Trả lời (Reply) trực tiếp vào tin nhắn Ảnh hoặc Video bằng lệnh '!sticker'!"
                )
                return jsonify({"status": "no_media"}), 200

            # 3. Tiến hành xử lý Media sang GIF/Sticker
            try:
                if not str(media_url).startswith("http"):
                    file_res = requests.get(f"{ZALO_BOT_API}/getFile?file_id={media_url}").json()
                    file_path = file_res.get("result", {}).get("file_path")
                    if file_path:
                        media_url = f"https://bot-api.zaloplatforms.com/file/bot{BOT_TOKEN}/{file_path}"

                res = requests.get(media_url, timeout=20)
                input_file = "temp_input"
                with open(input_file, "wb") as f:
                    f.write(res.content)

                if "video" in str(media_type):
                    send_zalo_message(chat_id, "⏳ Đang chuyển đổi Video sang GIF...")
                    output_file = "sticker.gif"
                    clip = VideoFileClip(input_file)
                    if clip.duration > 8:
                        clip = clip.subclipped(0, 8)
                    clip = clip.resized(width=360)
                    clip.write_gif(output_file, fps=10)
                    clip.close()
                    send_zalo_message(chat_id, "✅ Đã xử lý xong GIF từ video!")
                else:
                    send_zalo_message(chat_id, "⏳ Đang chuyển đổi Ảnh sang Sticker...")
                    output_file = "sticker.png"
                    im = Image.open(input_file)
                    im.thumbnail((512, 512))
                    im.save(output_file, "PNG")
                    send_zalo_message(chat_id, "✅ Đã xử lý xong Sticker từ ảnh!")

                if os.path.exists(input_file): os.remove(input_file)
                if os.path.exists("sticker.png"): os.remove("sticker.png")
                if os.path.exists("sticker.gif"): os.remove("sticker.gif")

            except Exception as e:
                print("LỖI XỬ LÝ MEDIA:", e)
                send_zalo_message(chat_id, f"❌ Có lỗi khi tạo sticker: {str(e)}")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
