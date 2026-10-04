import os
import requests
from flask import Flask, request, jsonify
from moviepy import VideoFileClip

app = Flask(__name__)

# Token Zalo OA của bạn
ACCESS_TOKEN = "3190358309365122943:zpTuopVRPXUkLTfSffkfkmHdeELRaTBzsZkFaePvtlwxnFotobiFKNOJbfRuAlAa"
ZALO_API_URL = "https://openapi.zalo.me/v2.0/oa/message"

def send_zalo_message(user_id, text):
    """Hàm gửi tin nhắn phản hồi qua Zalo OA API"""
    headers = {
        "access_token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "recipient": {"user_id": user_id},
        "message": {"text": text}
    }
    requests.post(ZALO_API_URL, headers=headers, json=payload)

@app.route("/", methods=["GET"])
def home():
    return "Zalo OA Bot đang chạy!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    """Nhận sự kiện (Webhook) từ Zalo OA khi có người nhắn tin hoặc gửi video"""
    data = request.json
    print("Nhận dữ liệu Webhook:", data)

    if data and "event_name" in data:
        event = data["event_name"]
        sender_id = data.get("sender", {}).get("id")

        # Khi người dùng gửi tin nhắn
        if event == "user_send_text":
            text = data.get("message", {}).get("text", "")
            if text == "!sticker":
                send_zalo_message(sender_id, "⏳ Vui lòng gửi kèm một video để tạo Sticker GIF!")

        # Khi người dùng gửi video
        elif event == "user_send_video":
            send_zalo_message(sender_id, "⏳ Đang tải và chuyển đổi video sang GIF...")
            video_url = data.get("message", {}).get("attachments", [{}])[0].get("payload", {}).get("url")

            if video_url:
                try:
                    video_path = "temp_video.mp4"
                    gif_path = "output.gif"

                    # 1. Tải video
                    res = requests.get(video_url)
                    with open(video_path, "wb") as f:
                        f.write(res.content)

                    # 2. Convert video thành GIF
                    clip = VideoFileClip(video_path).resized(width=480)
                    clip.write_gif(gif_path, fps=15)

                    # 3. Thông báo tạo thành công
                    send_zalo_message(sender_id, "✅ Đã tạo GIF thành công! (Lưu ý: Cần đăng ký Zalo OA Media API để gửi trực tiếp tệp GIF).")

                    if os.path.exists(video_path): os.remove(video_path)
                    if os.path.exists(gif_path): os.remove(gif_path)

                except Exception as e:
                    send_zalo_message(sender_id, f"❌ Lỗi xử lý: {str(e)}")

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
