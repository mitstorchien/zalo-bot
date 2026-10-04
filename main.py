import os
import requests
from flask import Flask, request, jsonify
from PIL import Image
from moviepy import VideoFileClip

app = Flask(__name__)

# Lấy Zalo Access Token từ Environment Variable (hoặc điền trực tiếp token của bạn vào đây)
ZALO_ACCESS_TOKEN = os.getenv("ZALO_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN_HERE")

def send_zalo_message(user_id, text=None, image_url=None):
    url = "https://openapi.zalo.me/v2.0/oa/message"
    headers = {
        "access_token": ZALO_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "recipient": {"user_id": user_id},
        "message": {}
    }
    if text:
        payload["message"]["text"] = text
    if image_url:
        payload["message"]["attachment"] = {
            "type": "template",
            "payload": {
                "template_type": "media",
                "elements": [{
                    "media_type": "image",
                    "url": image_url
                }]
            }
        }
    
    res = requests.post(url, headers=headers, json=payload)
    return res.json()

def extract_media_info(msg_data, event_data):
    """Trích xuất URL media và loại media (image/video) từ tin nhắn trực tiếp hoặc quote"""
    # 1. Trọng tâm: Kiểm tra tin nhắn quote/reply
    quote = msg_data.get("quote") or msg_data.get("quote_msg") or event_data.get("quote")
    if quote:
        attachments = quote.get("attachments", [])
        if attachments:
            att = attachments[0]
            att_type = att.get("type", "")
            payload = att.get("payload", {})
            media_url = payload.get("url") or payload.get("thumbnail")
            if media_url:
                return media_url, att_type

    # 2. Kiểm tra attachment trực tiếp trong tin nhắn hiện tại
    attachments = msg_data.get("attachments", [])
    if attachments:
        att = attachments[0]
        att_type = att.get("type", "")
        payload = att.get("payload", {})
        media_url = payload.get("url") or payload.get("thumbnail")
        if media_url:
            return media_url, att_type

    # 3. Kiểm tra trường link/url trực tiếp
    media_url = msg_data.get("url") or msg_data.get("thumb")
    if media_url:
        return media_url, "image"

    return None, None

def convert_image_to_sticker(img_path, out_path):
    with Image.open(img_path) as img:
        img = img.convert("RGBA")
        img.thumbnail((512, 512))
        img.save(out_path, "PNG")

def convert_video_to_sticker(video_path, out_path):
    clip = VideoFileClip(video_path)
    if clip.duration > 3:
        clip = clip.subclipped(0, 3)
    clip = clip.resized(height=512) if clip.h > clip.w else clip.resized(width=512)
    clip.write_gif(out_path, fps=10)
    clip.close()

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Bot is running!", 200

    data = request.json or {}
    event_name = data.get("event_name", "")

    if event_name in ["user_send_text", "user_send_image", "user_send_video", "user_send_gif"]:
        user_id = data.get("sender", {}).get("id")
        message_obj = data.get("message", {})
        text = message_obj.get("text", "").strip()

        if text.lower() == "!sticker":
            media_url, media_type = extract_media_info(message_obj, data)

            if not media_url:
                send_zalo_message(
                    user_id, 
                    "⚠️ Không tìm thấy Ảnh/Video!\n\nHướng dẫn:\n1. Trả lời (Reply) tin nhắn Ảnh/Video bằng chữ '!sticker'\n2. Hoặc gửi Ảnh/Video kèm chú thích '!sticker'"
                )
                return jsonify({"status": "no_media"}), 200

            try:
                # Tải file media về server
                res = requests.get(media_url, stream=True)
                input_file = "input_temp"
                with open(input_file, "wb") as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        f.write(chunk)

                output_file = "sticker_output.png" if "image" in media_type else "sticker_output.gif"

                if "image" in media_type:
                    convert_image_to_sticker(input_file, output_file)
                else:
                    convert_video_to_sticker(input_file, output_file)

                # Thông báo xử lý hoàn tất
                send_zalo_message(user_id, "✅ Đã chuyển đổi thành sticker thành công!")

                # Dọn dẹp file tạm
                if os.path.exists(input_file): os.remove(input_file)
                if os.path.exists(output_file): os.remove(output_file)

            except Exception as e:
                print(f"Lỗi xử lý: {e}")
                send_zalo_message(user_id, f"❌ Có lỗi xảy ra trong quá trình tạo sticker: {str(e)}")
        
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
    
