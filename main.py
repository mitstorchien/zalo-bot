from zlapi import ZaloAPI
from moviepy import VideoFileClip
import os

# Điền mã Token bạn nhận được vào đây
TOKEN = "3190358309365122943:zpTuopVRPXUKLTfSffkfkmHdeELRaTBzsZkFaePvtlwxnFotobiFKNOJbfRuAlAa"

# Khởi tạo Zalo API
client = ZaloAPI(TOKEN)

@client.onMessage
def handle_message(message):
    # Kiểm tra xem người dùng có gõ lệnh !sticker và có đính kèm video không
    if message.text == "!sticker" and message.has_video:
        message.reply("⏳ Đang xử lý sticker...")
        
        # 1. Tải video người dùng gửi về máy chủ
        video_path = message.download_video()
        gif_path = "output.gif"
        
        # 2. Xử lý chuyển đổi video sang GIF
        clip = VideoFileClip(video_path).resized(width=480)
        clip.write_gif(gif_path, fps=15)
        
        # 3. Gửi tệp GIF/Sticker ngược lại nhóm chat Zalo
        message.reply_with_file(gif_path)
        message.reply("✅ Đã tạo sticker thành công!")
        
        # Xóa file tạm sau khi dùng xong
        os.remove(video_path)
        os.remove(gif_path)

client.listen()
