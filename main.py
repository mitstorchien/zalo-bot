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
    """Tìm kiếm URL/Link/File trong mọi tầng của JSON Zalo gửi về"""
    if not data:
        return None, None
    
    if isinstance(data, str):
        if data.startswith("http://") or data.startswith("https://"):
            if any(ext in data.lower() for ext in ['.mp4', '.mov', 'video']):
                return data, "video"
            return data, "photo"
        return None, None

    if isinstance(data, dict):
        quote = data.get("quote") or data.get("quote_msg") or data.get("reply_to") or data.get("source")
        if quote and quote != data:
            url, mtype = find_media_in_dict(quote)
            if url: return url, mtype

        for key in ["url", "href", "src", "download_url", "file_url", "preview_url", "thumbnail"]:
            val = data.get(key)
            if isinstance(val, str) and val.startswith("http"):
                msg_type = data.get("type") or data.get("msg_type") or "photo"
                return val, str(msg_type)

        for key, val in data.items():
            if key in ["chat", "sender", "from"]:
                continue
            url, mtype = find_media_in_dict(val)
            if url: return url, mtype

    elif isinstance(data, list):
        for item in data:
            url, mtype = find_media_in_dict(item)
            if url: return url, mtype

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
            media_url, media_type = find_media_in_dict(message)

            # Nếu không thấy media
            if not media_url:
                send_zalo_message(
                    chat_id, 
                    "⚠️ Vui lòng Trả lời (Reply) trực tiếp vào tin nhắn Ảnh hoặc Video bằng lệnh '!sticker'!"
                )
                return jsonify({"status": "no_media"}), 200

            # Tiến hành xử lý Media
            try:
                if not media_url.startswith("http"):
                    file_res = requests.get(f"{ZALO_BOT_API}/getFile?file_id={media_url}").json()
                    file_path = file_res.get("result", {}).get("file_path")
                    if file_path:
                        media_url = f"https://bot-api.zaloplatforms.com/file/bot{BOT_TOKEN}/{file_path}"

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
    
