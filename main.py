import os
import requests
from zlapi import ZaloAPI
from moviepy import VideoFileClip

# Điền thông tin đăng nhập Zalo (Cookie và IMEI lấy từ trình duyệt)
COOKIES = {
    # Thay thế bằng cookies Zalo của bạn (hoặc dạng dict/json)
}
IMEI = "điền_imei_trình_duyệt_của_bạn"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class GifBot(ZaloAPI):
    def __init__(self, cookies, imei, user_agent):
        super().__init__(phone="", password="", cookies=cookies, imei=imei, user_agent=user_agent)

    def onMessage(self, mid, author_id, message, message_object, thread_id, thread_type):
        if isinstance(message, str) and message.strip() == "!sticker":
            self.send("⏳ Đang xử lý tạo GIF...", thread_id=thread_id, thread_type=thread_type)
            
            if message_object and hasattr(message_object, 'attachUrl') and message_object.attachUrl:
                try:
                    video_url = message_object.attachUrl
                    video_path = "temp_video.mp4"
                    gif_path = "output.gif"

                    res = requests.get(video_url)
                    with open(video_path, "wb") as f:
                        f.write(res.content)

                    clip = VideoFileClip(video_path).resized(width=480)
                    clip.write_gif(gif_path, fps=15)

                    self.sendLocalFiles(gif_path, thread_id=thread_id, thread_type=thread_type)
                    self.send("✅ Đã tạo sticker GIF thành công!", thread_id=thread_id, thread_type=thread_type)

                    if os.path.exists(video_path): os.remove(video_path)
                    if os.path.exists(gif_path): os.remove(gif_path)

                except Exception as e:
                    self.send(f"❌ Lỗi xử lý: {str(e)}", thread_id=thread_id, thread_type=thread_type)

if __name__ == "__main__":
    # Khởi tạo bot bằng Cookies & IMEI
    bot = GifBot(COOKIES, IMEI, USER_AGENT)
    bot.listen()
    
