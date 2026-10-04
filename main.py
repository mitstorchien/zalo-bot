import os
from zlapi import ZaloAPI
from moviepy import VideoFileClip

# Điền Token Zalo Bot của bạn
TOKEN = "3190358309365122943:zpTuopVRPXUKLTfSffkfkmHdeELRaTBzsZkFaePvtlwxnFotobiFKNOJbfRuAlAa"

class GifBot(ZaloAPI):
    def __init__(self, token):
        # Khởi tạo ZaloAPI với token
        super().__init__(token, "")

    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        # Kiểm tra nội dung tin nhắn có phải !sticker không
        if isinstance(message, str) and message.strip() == "!sticker":
            self.send("⏳ Đang xử lý tạo GIF...", thread_id=thread_id, thread_type=thread_type)
            
            # Kiểm tra nếu có file/video đính kèm
            if message_object and hasattr(message_object, 'attachUrl') and message_object.attachUrl:
                try:
                    video_url = message_object.attachUrl
                    video_path = "temp_video.mp4"
                    gif_path = "output.gif"

                    # 1. Tải video về
                    import requests
                    res = requests.get(video_url)
                    with open(video_path, "wb") as f:
                        f.write(res.content)

                    # 2. Xử lý chuyển đổi video sang GIF
                    clip = VideoFileClip(video_path).resized(width=480)
                    clip.write_gif(gif_path, fps=15)

                    # 3. Gửi GIF lại Zalo
                    self.sendLocalFiles(gif_path, thread_id=thread_id, thread_type=thread_type)
                    self.send("✅ Đã tạo sticker GIF thành công!", thread_id=thread_id, thread_type=thread_type)

                    # 4. Xóa file tạm
                    if os.path.exists(video_path): os.remove(video_path)
                    if os.path.exists(gif_path): os.remove(gif_path)

                except Exception as e:
                    self.send(f"❌ Lỗi xử lý: {str(e)}", thread_id=thread_id, thread_type=thread_type)

if __name__ == "__main__":
    bot = GifBot(TOKEN)
    bot.listen()
