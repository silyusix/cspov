import os
import subprocess

# 配置路径
video_dir = r"D:\hlae\videos"
audio_root = r"D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\bin\win64\untitled_rec"
ffmpeg_path = r"D:\hlae\ffmpeg\bin\ffmpeg.exe"
output_file = r"D:\hlae\videos\final_full_movie.mp4"

# 创建临时工作目录
temp_dir = os.path.join(video_dir, "temp_segments")
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

segments = []

print("--- 开始音画同步处理 ---")

# 假设文件从 1 到 42
for i in range(1, 43):
    v_file = os.path.join(video_dir, f"{i}.mp4")
    # take 文件夹是从 0000 开始计数的
    take_folder = f"take{i-1:04d}"
    a_file = os.path.join(audio_root, take_folder, "audio.wav")
    
    if os.path.exists(v_file) and os.path.exists(a_file):
        temp_v = os.path.join(temp_dir, f"seg_{i:03d}.mp4")
        print(f"正在处理第 {i} 段: {v_file} + {a_file}")
        
        # 将音频压入视频，视频流直接复制(无损)，音频压成AAC
        cmd = [
            ffmpeg_path, "-y",
            "-i", v_file,
            "-i", a_file,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            temp_v
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        segments.append(temp_v)
    else:
        print(f"警告：找不到第 {i} 段的文件，已跳过。")

if not segments:
    print("错误：没有找到任何可合成的文件！")
    exit()

print("\n--- 开始最终合并 ---")

# 创建 concat 列表文件
list_file = os.path.join(temp_dir, "list.txt")
with open(list_file, "w") as f:
    for seg in segments:
        # ffmpeg concat 要求路径使用正斜杠
        f.write(f"file '{seg.replace('\\', '/')}'\n")

# 执行最终合并
merge_cmd = [
    ffmpeg_path, "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", list_file,
    "-c", "copy",
    output_file
]

subprocess.run(merge_cmd)

print(f"\n恭喜！全场视频已合成完毕！")
print(f"成品路径: {output_file}")
print("提示：temp_segments 文件夹里的临时文件您可以检查后手动删除，原始 1.mp4 等文件已为您保留。")
