import os
import requests
from flask import Flask, request, jsonify
from moviepy import VideoFileClip

app = Flask(__name__)

# Thông tin Token Bot từ Zalo Bot Manager
BOT_TOKEN = "3190358309365122943:zpTuopVRPXUkLTfSffkfkmHdeELRaTBzsZkFaePvtlwxnFotobiFKNOJbfRuAlAa"
ZALO_BOT_API = f"https://bot-api.zaloplatforms.com/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    """Gửi tin nhắn phản hồi tới người dùng hoặc nhóm chat"""
    url = f"{ZALO_BOT_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        print("Response sendMsg:", res.json())
    except Exception as e:
        print("Lỗi khi gửi tin nhắn:", e)

@app.route("/", methods=["GET"])
def home():
    return "Zalo Platform Bot Service đang chạy!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Payload nhận từ Zalo Webhook:", data)

    if not data:
        return jsonify({"status": "empty_payload"}), 200

    # Bắt sự kiện tin nhắn từ Webhook
    message = data.get("message") or data.get("event", {})
    if message:
        # Lấy ID cuộc trò chuyện (nhóm hoặc nhắn riêng)
        chat_id = (
            message.get("chat", {}).get("id") 
            or data.get("sender", {}).get("id") 
            or message.get("from", {}).get("id")
        )
        text = message.get("text", "")

        if chat_id:
            # 1. Trường hợp gõ lệnh !sticker
            if "!sticker" in text.lower():
                send_message(chat_id, "⏳ Đã nhận lệnh! Hãy gửi hoặc đính kèm 1 video ngắn để bot chuyển đổi sang GIF.")

            # 2. Trường hợp gửi file Video
            elif "video" in message or message.get("type") == "video":
                send_message(chat_id, "⏳ Đang tải video và bắt đầu xử lý chuyển đổi sang GIF...")
                
                video_obj = message.get("video", {})
                video_file_id = video_obj.get("file_id")

                if video_file_id:
                    try:
                        # Lấy đường dẫn file từ Zalo API
                        file_res = requests.get(f"{ZALO_BOT_API}/getFile?file_id={video_file_id}").json()
                        file_path = file_res.get("result", {}).get("file_path")

                        if file_path:
                            download_url = f"https://bot-api.zaloplatforms.com/file/bot{BOT_TOKEN}/{file_path}"
                            local_video = "temp_video.mp4"
                            local_gif = "output.gif"

                            # Tải video về Render
                            res = requests.get(download_url)
                            with open(local_video, "wb") as f:
                                f.write(res.content)

                            # Chuyển đổi video sang GIF
                            clip = VideoFileClip(local_video).resized(width=480)
                            clip.write_gif(local_gif, fps=12)

                            # Phản hồi hoàn tất
                            send_message(chat_id, "✅ Đã tạo GIF thành công!")

                            # Dọn dẹp tài nguyên tạm
                            if os.path.exists(local_video): os.remove(local_video)
                            if os.path.exists(local_gif): os.remove(local_gif)
                        else:
                            send_message(chat_id, "❌ Không thể lấy đường dẫn tải video từ Zalo.")
                    except Exception as e:
                        send_message(chat_id, f"❌ Lỗi xử lý video: {str(e)}")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
