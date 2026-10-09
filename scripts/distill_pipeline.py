#!/usr/bin/env python3
"""蒸馏流水线：转录+元数据 → 自动分类 → 蒸馏卡骨架（省 token 版）

用法：
  python distill_pipeline.py <ARCHIVE_ROOT> [--write-cards]

输入：
  <ARCHIVE_ROOT>/distill_tools/video_urls.json   (desc/author/url0)
  <ARCHIVE_ROOT>/minutes/artifact-<vid>-*/transcript.txt (可选，无则用标题判定)
输出：
  <ARCHIVE_ROOT>/distill_tools/classification.json  (每条: 主类别/标签/依据/建议)
  --write-cards 时生成 <ARCHIVE_ROOT>/distilled/<vid>.md 骨架
"""
import json, os, re, sys, glob

# —— 强信号词表（与 references/classification.md 一致）——
SIGNALS = {
    '技术干货': ['教程','干货','实操','原理','避坑','保姆级','手把手','代码讲解','架构','算法',
              'prompt工程','prompt','rag','微调','工作流','教你','如何','步骤','剪映','剪辑',
              '桌面版','使用技巧','ai学习','效果','学会','芯片','参数','传感器','离线',
              '产出','生成','接入','制作'],
    '开源GitHub': ['github','仓库','repo','开源项目','开源','star','commit','api','sdk',
                 'langchain','autogpt','huggingface','项目地址','skill','技能'],
    '行业资讯': ['发布','官宣','最新','首发','融资','监管','政策','报告','白皮书','增长数据',
              '财报','革命','来了','新出','宣布','突破'],
    '对标案例': ['账号拆解','涨粉','gmv','投流','roi','带货','爆款','人设','对标','起号',
              '变现模式','佣金','橱窗'],
    '观点认知': ['我认为','本质','底层逻辑','认知','方法论','思维方式','长期主义','复盘',
              '意识到','突然','觉得','token是','比喻','骗钱','套件','私改','别买'],
}
PRIORITY = ['技术干货', '开源GitHub', '行业资讯', '对标案例', '观点认知']
# 动作/操作类词：命中开源GitHub时若同时命中动作词 → 按「技术干货 > 开源GitHub」优先（内容主体是教学/实操）
ACTION_WORDS = ['教程','教你','实操','避坑','步骤','使用技巧','手把手','产出','接入','制作']
LABEL_STOP = {'ai','aigc','抖音','科技','干货','分享','deepseek','skill','github','git','剪辑教程'}

def load_transcripts(root):
    """返回 {vid: transcript_text}；只取正文前 1200 字符 + Keywords 行（省 token）"""
    out = {}
    d = os.path.join(root, 'minutes')
    if not os.path.isdir(d):
        return out
    for folder in glob.glob(os.path.join(d, 'artifact-*')):
        m = re.search(r'artifact-(\d+)', os.path.basename(folder))
        if not m:
            continue
        t = os.path.join(folder, 'transcript.txt')
        if os.path.exists(t):
            try:
                txt = open(t, encoding='utf-8').read()
                # 截取：头部 Keywords + 正文前 1200 字符
                head = txt[:1600]
                out[m.group(1)] = head
            except Exception:
                pass
    return out

def classify(desc, author, transcript):
    text = (transcript or '') + '\n' + (desc or '')
    text_l = text.lower()
    scores = {}
    hits = {}
    for cat, words in SIGNALS.items():
        s = 0
        hit_words = []
        for w in words:
            if w in text_l:
                s += 1
                hit_words.append(w)
        if s:
            scores[cat] = s
            hits[cat] = hit_words
    if not scores:
        main = '其他'
        basis = '无强信号词命中'
    else:
        # 内容主体裁定：开源GitHub 命中 + 存在动作/操作词 → 优先技术干货（内容主体是教学/实操）
        if '开源GitHub' in scores and any(w in text_l for w in ACTION_WORDS) and scores.get('技术干货', 0) >= 1:
            main = '技术干货'
            basis = (hits.get('技术干货') or [])[:3] + (hits.get('开源GitHub') or [])[:2]
        else:
            main = max(scores, key=lambda c: (scores[c], -PRIORITY.index(c)))
            basis = hits[main][:4]
    # 标签：desc 里的 #话题（去停用词），最多 2 个
    tags = re.findall(r'#([\u4e00-\u9fa5A-Za-z0-9]+)', desc or '')
    tags = [t for t in tags if t.lower() not in LABEL_STOP][:2]
    return main, tags, basis, scores

def build_card(vid, info, main, tags, basis, transcript, root):
    title = (info.get('desc') or '').split('#')[0].strip()[:40]
    author = info.get('author') or ''
    lines = [f'# 蒸馏卡片 · {author}《{title}》\n']
    lines.append('| 字段 | 值 |')
    lines.append('|---|---|')
    lines.append(f'| 视频 ID | `{vid}` |')
    lines.append(f'| 链接 | https://www.douyin.com/video/{vid} |')
    lines.append(f'| 主类别 | {main} |')
    lines.append(f'| 标签 | {", ".join(tags) if tags else "无"} |')
    lines.append(f'| 来源 | 抖音群分享 · {author} |')
    lines.append('| 分类依据 | ' + ('、'.join(basis) if basis else '无强信号，按内容特征') + ' |')
    lines.append('\n## 核心资产（必填）')
    lines.append('- 核心图片：`assets/<作者>_<内容描述>.jpg`（待抽帧/确认；纯音频流写"无（纯音频流）"）')
    lines.append('- 提示词：待提取/确认（未展示则写"视频中未展示，待获取"）')
    lines.append('- 项目地址：待核实（无则写"无"）')
    lines.append('\n## 一句话结论')
    lines.append('> 待人工/AI 润色（<30字，聚焦"对你有什么用"）')
    lines.append('\n## 核心要点')
    if transcript:
        kws = re.search(r'Keywords:\s*(.+)', transcript)
        if kws:
            lines.append(f'- 关键词：{kws.group(1).strip()}')
    lines.append('- 要点1 / 要点2 / 要点3（≤30字，可执行优先）')
    lines.append('\n## 可执行清单')
    lines.append('- [ ] 待补充（如无，写"无直接动作，属认知积累"）')
    lines.append('\n## 关联提示')
    lines.append('- 待补充（无关联写"无"）\n')
    return '\n'.join(lines)

def resolve_tools_dir(root):
    """distill_tools 可能在 <root>/distill_tools 或 <root>/../distill_tools"""
    for cand in (os.path.join(root, 'distill_tools'), os.path.join(os.path.dirname(root.rstrip('\\/')), 'distill_tools')):
        if os.path.isdir(cand):
            return cand
    return os.path.join(root, 'distill_tools')

def main():
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    write_cards = '--write-cards' in sys.argv
    tools_dir = resolve_tools_dir(root)
    meta = json.load(open(os.path.join(tools_dir, 'video_urls.json'), encoding='utf-8'))
    trans = load_transcripts(root)
    results = {}
    for vid, info in meta.items():
        main, tags, basis, scores = classify(info.get('desc',''), info.get('author',''), trans.get(vid))
        results[vid] = {
            'author': info.get('author',''),
            'desc': (info.get('desc') or '')[:60],
            'main': main,
            'tags': tags,
            'basis': basis,
            'scores': scores,
        }
        print(f"{vid} | {results[vid]['author']} | {main} | {','.join(tags)} | 依据:{','.join(basis) if basis else '特征裁定'}")
        if write_cards:
            card = build_card(vid, info, main, tags, basis, trans.get(vid), root)
            out = os.path.join(root, 'distilled', f'{vid}.md')
            with open(out, 'w', encoding='utf-8') as f:
                f.write(card)
    out_path = os.path.join(tools_dir, 'classification.json')
    json.dump(results, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('WROTE', out_path)

if __name__ == '__main__':
    main()
