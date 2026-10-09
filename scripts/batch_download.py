#!/usr/bin/env python3
"""从 video_urls.json 批量下载视频（直链，带 UA/Referer）"""
import json, os, sys, requests, time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.douyin.com/',
}

def download(url, out_path):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with requests.get(url, headers=HEADERS, stream=True, timeout=90) as r:
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        done = 0
        with open(out_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    done += len(chunk)
        print(f'  {os.path.basename(out_path)}: {done/1024/1024:.1f} MB')
    return done

if __name__ == '__main__':
    js_path = sys.argv[1] if len(sys.argv) > 1 else r'<ARCHIVE_ROOT>\distill_tools\video_urls.json'
    out_dir = sys.argv[2] if len(sys.argv) > 2 else r'<ARCHIVE_ROOT>\AI测试蒸馏\raw'
    data = json.load(open(js_path, encoding='utf-8'))
    for vid, info in data.items():
        if not info.get('url0'):
            print(f'{vid}: 无直链')
            continue
        out_path = os.path.join(out_dir, f'{vid}.mp4')
        if os.path.exists(out_path) and os.path.getsize(out_path) > 100000:
            print(f'{vid}: 已存在，跳过')
            continue
        try:
            n = download(info['url0'], out_path)
            print(f'{vid} {info.get("author","")} {info.get("desc","")[:40]} -> {n/1024/1024:.1f}MB')
        except Exception as e:
            print(f'{vid} 下载失败: {e}')
            time.sleep(1)
