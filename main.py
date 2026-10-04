import os
import requests
from flask import Flask, request, jsonify
from moviepy import VideoFileClip

app = Flask(__name__)

# Token Bot của bạn (lấy từ Bot Creator)
BOT_TOKEN = "3190358309365122943:zpTuopVRPXUkLTfSffkfkmHdeELRaTBzsZkFaePvtlwxnFotobiFKNOJbfRuAlAa"
ZALO_BOT_API = f"https://bot.zaloplatforms.com/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    """Gửi tin nhắn phản hồi tới nhóm hoặc cá nhân"""
    url = f"{ZALO_BOT_API}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)

@app.route("/", methods=["GET"])
def home():
    return "Zalo Bot Manager đang chạy!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    """Nhận sự kiện tin nhắn từ nhóm chat Zalo"""
    data = request.json
    print("Dữ liệu nhận từ Zalo:", data)

    if data and "message" in data:
        msg = data["message"]
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "")

        # Kiểm tra lệnh !sticker
        if text.strip() == "!sticker":
            send_message(chat_id, "⏳ Bạn hãy gửi kèm 1 video để bot tạo Sticker GIF nhé!")

        # Kiểm tra nếu người dùng gửi video
        elif "video" in data["message"]:
            video_file_id = msg["video"].get("file_id")
            send_message(chat_id, "⏳ Đang xử lý chuyển đổi video sang GIF...")

            try:
                # Lấy link tải video
                file_info = requests.get(f"{ZALO_BOT_API}/getFile?file_id={video_file_id}").json()
                file_path = file_info.get("result", {}).get("file_path")

                if file_path:
                    video_url = f"https://bot.zaloplatforms.com/file/bot{BOT_TOKEN}/{file_path}"
                    local_video = "temp_video.mp4"
                    local_gif = "output.gif"

                    # 1. Tải video
                    res = requests.get(video_url)
                    with open(local_video, "wb") as f:
                        f.write(res.content)

                    # 2. Chuyển đổi sang GIF
                    clip = VideoFileClip(local_video).resized(width=480)
                    clip.write_gif(local_gif, fps=15)

                    # 3. Gửi thông báo hoàn tất
                    send_message(chat_id, "✅ Đã xử lý GIF thành công!")

                    # Xóa file tạm
                    if os.path.exists(local_video): os.remove(local_video)
                    if os.path.exists(local_gif): os.remove(local_gif)

            except Exception as e:
                send_message(chat_id, f"❌ Có lỗi xảy ra: {str(e)}")

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
