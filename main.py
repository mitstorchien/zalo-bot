import os
import requests
from flask import Flask, request, jsonify
from moviepy import VideoFileClip
from PIL import Image

app = Flask(__name__)

# Token Zalo Bot của bạn
BOT_TOKEN = "3190358309365122943:hCYFHLRIkeKUjgFZHcWvNstmMqmXunnCyYHDVFCcpxEUrCVrXwVRPVVKMFkOiVaD"
ZALO_BOT_API = f"https://bot-api.zaloplatforms.com/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    """Gửi tin nhắn văn bản"""
    url = f"{ZALO_BOT_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Lỗi send_message:", e)

def extract_media_from_msg(msg):
    """Hàm trích xuất URL ảnh hoặc video từ đối tượng message (bao gồm cả đính kèm trực tiếp hoặc quote/reply)"""
    media_type = None
    media_url = None

    # Check trực tiếp trong tin nhắn
    if "photo" in msg or msg.get("type") == "photo":
        media_type = "photo"
        photos = msg.get("photo", [])
        if isinstance(photos, list) and len(photos) > 0:
            media_url = photos[-1].get("url") or photos[-1].get("href")
        elif isinstance(photos, dict):
            media_url = photos.get("url") or photos.get("href")
            
    elif "video" in msg or msg.get("type") == "video":
        media_type = "video"
        video_obj = msg.get("video", {})
        media_url = video_obj.get("url") or video_obj.get("href") or video_obj.get("file_id")

    # Check trong tin nhắn được Reply (Quote) nếu chưa thấy media trực tiếp
    if not media_url and "quote" in msg:
        quote = msg["quote"]
        if "photo" in quote or quote.get("type") == "photo":
            media_type = "photo"
            photos = quote.get("photo", [])
            if isinstance(photos, list) and len(photos) > 0:
                media_url = photos[-1].get("url") or photos[-1].get("href")
            elif isinstance(photos, dict):
                media_url = photos.get("url") or photos.get("href")
        elif "video" in quote or quote.get("type") == "video":
            media_type = "video"
            video_obj = quote.get("video", {})
            media_url = video_obj.get("url") or video_obj.get("href") or video_obj.get("file_id")

    return media_type, media_url

@app.route("/", methods=["GET"])
def home():
    return "Zalo Bot GIF & Sticker Service đang chạy!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    print("Payload nhận từ Zalo Webhook:", data)

    message = data.get("message") or data.get("event", {})
    if message:
        chat_id = (
            message.get("chat", {}).get("id") 
            or data.get("sender", {}).get("id") 
            or message.get("from", {}).get("id")
        )
        text = message.get("text", "").strip()

        # Kiểm tra xem tin nhắn có chứa lệnh !sticker không
        if "!sticker" in text.lower():
            media_type, media_url = extract_media_from_msg(message)

            if not media_url:
                send_message(
                    chat_id, 
                    "⚠️ Lệnh không hợp lệ!\n\nHướng dẫn sử dụng:\n"
                    "1️⃣ Trả lời (Reply) tin nhắn Ảnh/Video bằng chữ '!sticker'\n"
                    "2️⃣ Gửi Video/Ảnh kèm chú thích '!sticker'"
                )
                return jsonify({"status": "no_media"}), 200

            # ----------------------------------------------------
            # THƯỜNG HỢP 1: XỬ LÝ ẢNH -> STICKER (PNG/WEBP)
            # ----------------------------------------------------
            if media_type == "photo":
                send_message(chat_id, "⏳ Đang xử lý ảnh sang dạng Sticker...")
                try:
                    local_img = "temp_input.jpg"
                    local_sticker = "sticker_output.png"

                    # Tải ảnh về
                    res = requests.get(media_url)
                    with open(local_img, "wb") as f:
                        f.write(res.content)

                    # Resize ảnh về kích thước vuông chuẩn Sticker (512x512)
                    im = Image.open(local_img)
                    im.thumbnail((512, 512))
                    im.save(local_sticker, "PNG")

                    send_message(chat_id, "✅ Đã chuyển đổi thành công Sticker từ ảnh của bạn!")
                    
                    # Dọn dẹp
                    if os.path.exists(local_img): os.remove(local_img)
                    if os.path.exists(local_sticker): os.remove(local_sticker)

                except Exception as e:
                    send_message(chat_id, f"❌ Lỗi khi xử lý ảnh: {str(e)}")

            # ----------------------------------------------------
            # THƯỜNG HỢP 2: XỬ LÝ VIDEO -> GIF
            # ----------------------------------------------------
            elif media_type == "video":
                send_message(chat_id, "⏳ Đang tải video và bắt đầu chuyển đổi sang GIF...")
                try:
                    # Lấy download URL nếu media_url là file_id
                    if not media_url.startswith("http"):
                        file_res = requests.get(f"{ZALO_BOT_API}/getFile?file_id={media_url}").json()
                        file_path = file_res.get("result", {}).get("file_path")
                        if file_path:
                            media_url = f"https://bot-api.zaloplatforms.com/file/bot{BOT_TOKEN}/{file_path}"

                    local_video = "temp_video.mp4"
                    local_gif = "output.gif"

                    # Tải video về
                    res = requests.get(media_url)
                    with open(local_video, "wb") as f:
                        f.write(res.content)

                    # Chuyển đổi Video sang GIF bằng MoviePy
                    clip = VideoFileClip(local_video)
                    if clip.duration > 10:  # Giới hạn tối đa 10 giây nếu video quá dài
                        clip = clip.subclip(0, 10)

                    clip = clip.resized(width=380)
                    clip.write_gif(local_gif, fps=10)
                    clip.close()

                    send_message(chat_id, "✅ Đã chuyển đổi thành công Video sang GIF!")

                    # Dọn dẹp
                    if os.path.exists(local_video): os.remove(local_video)
                    if os.path.exists(local_gif): os.remove(local_gif)

                except Exception as e:
                    send_message(chat_id, f"❌ Lỗi khi xử lý video: {str(e)}")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
