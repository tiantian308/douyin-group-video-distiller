#!/usr/bin/env python3
"""批量把 raw 下所有 mp4 转成 mp3（16000Hz 64k，跳过已有）"""
import os, subprocess, glob
import imageio_ffmpeg

ff = imageio_ffmpeg.get_ffmpeg_exe()
raw = r'<ARCHIVE_ROOT>\AI测试蒸馏\raw'
mp4s = sorted(glob.glob(os.path.join(raw, '*.mp4')))
for src in mp4s:
    vid = os.path.basename(src)[:-4]
    out = os.path.join(raw, f'{vid}.mp3')
    if os.path.exists(out) and os.path.getsize(out) > 50000:
        print(f'{vid}: 已有mp3，跳过')
        continue
    try:
        subprocess.run([ff, '-y', '-i', src, '-vn', '-ac', '1', '-ar', '16000', '-b:a', '64k', out], capture_output=True, check=True)
        print(f'{vid}: {os.path.getsize(out)/1024/1024:.2f} MB')
    except Exception as e:
        print(f'{vid}: 失败 {e}')
