#!/usr/bin/env python3
"""本地转录兜底：批量转写 raw/*.mp3（SenseVoice + llama.cpp，无需飞书额度）

用法：
  python batch_transcribe_local.py <ARCHIVE_ROOT>

前置（一次性）：
  1. 下载 FunASR llama.cpp 运行时到 <ARCHIVE_ROOT>/distill_tools/funasr-runtime/：
     - llama-funasr-sensevoice.exe（GitHub release runtime-llamacpp-v0.1.9，windows-x64-vulkan.zip）
     - sensevoice-small-q8.gguf（~242MB，HF: FunAudioLLM/SenseVoiceSmall-GGUF，国内镜像 hf-mirror.com）
     - fsmn-vad.gguf（~1.6MB，HF: FunAudioLLM/fsmn-vad-GGUF）
  2. 本机已有 mp3（batch_extract_audio.py 产出）

输出：
  <ARCHIVE_ROOT>/minutes/local_<视频ID>.txt（纯文本转写，无妙记摘要/关键词）
"""
import os, sys, glob, subprocess, time

def find_runtime(root):
    """优先环境变量 FUNASR_RUNTIME，其次常见布局"""
    env = os.environ.get('FUNASR_RUNTIME')
    if env and os.path.isdir(env):
        return env
    for cand in (
        os.path.join(root, 'distill_tools', 'funasr-runtime'),
        os.path.join(os.path.dirname(root.rstrip('\\/')), 'distill_tools', 'funasr-runtime'),
    ):
        if os.path.isdir(cand):
            return cand
    return os.path.join(root, 'distill_tools', 'funasr-runtime')

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    rt = find_runtime(root)
    exe = os.path.join(rt, 'llama-funasr-sensevoice.exe')
    model = os.path.join(rt, 'sensevoice-small-q8.gguf')
    vad = os.path.join(rt, 'fsmn-vad.gguf')
    for missing in (exe, model, vad):
        if not os.path.exists(missing):
            print(f'缺少: {missing}\n请先按脚本头部说明下载 FunASR llama.cpp 运行时')
            sys.exit(1)
    raw = os.path.join(root, 'raw')
    out_dir = os.path.join(root, 'minutes')
    os.makedirs(out_dir, exist_ok=True)
    mp3s = sorted(glob.glob(os.path.join(raw, '*.mp3')))
    ok = fail = skip = 0
    for src in mp3s:
        vid = os.path.basename(src)[:-4]
        out = os.path.join(out_dir, f'local_{vid}.txt')
        if os.path.exists(out) and os.path.getsize(out) > 50:
            print(f'{vid}: 已有，跳过')
            skip += 1
            continue
        t0 = time.time()
        try:
            r = subprocess.run([exe, '-m', model, '--vad', vad, '-a', src],
                               capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=1800)
            text = r.stdout.strip()
            if len(text) < 20:
                raise RuntimeError('输出过短，可能无声/纯音乐: ' + (r.stderr or '')[:120])
            with open(out, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f'{vid}: {len(text)}字, {time.time()-t0:.1f}s')
            ok += 1
        except Exception as e:
            print(f'{vid}: 失败 {e}')
            fail += 1
    print(f'DONE 成功{ok} 跳过{skip} 失败{fail}')

if __name__ == '__main__':
    main()
