---
name: douyin-group-video-distiller
description: 处理抖音群视频的自动化蒸馏 Skill。当用户要求处理抖音 App/网页版群聊（默认「AI测试」群）里分享的视频链接、把群里的视频批量下载转录、按内容自动分类并蒸馏成结构化卡片/知识要点时使用。触发词包括：处理抖音群、AI测试群、群视频蒸馏、视频转录归档、下载群里的视频、把视频内容整理成文档、今天的群视频等。本 Skill 依赖用户已登录的抖音网页版会话与飞书妙记链路。
---

# Douyin Group Video Distiller（抖音群视频自动蒸馏器）

## 概览

把抖音群聊（默认「AI测试」群，群名可能被成员修改，以用户指定或最近活跃群为准）里分享的抖音视频，走完「取链接 → 下载 → 转录 → 自动分类 → 蒸馏归档」整条流水线，产出分门别类的结构化蒸馏卡。本 Skill 是**编排者**：它决定流程顺序、工具选择、分类标准与产出格式；实际能力由浏览器自动化（`browser-use-automation`）、`lark-cli`（飞书妙记/云空间）与本地 Python 承担。

**已打通的核心链路（2026-10 验证）**：抖音网页版登录会话下，群聊天窗口会自动请求 `multi/aweme/detail` 批量接口一次性返回群内全部视频 ID；单条 `aweme/detail` 接口直接返回标题/作者/无水印 mp4 直链；下载后用飞书妙记（MP3 上传）转录；按 `references/classification.md` 分类并蒸馏出卡片 + 归档总览。

## 工作流决策树

| 用户指令 | 执行范围 |
|---|---|
| 「处理/蒸馏 AI测试群」 | 全流程 1–5 |
| 「把群里的视频下载下来」 | 阶段 1–2，产物：本地视频清单 |
| 「把群里的视频转录了」 | 阶段 1–3，产物：转录文档 |
| 「蒸馏成干货/GitHub/对标」 | 阶段 1–5，阶段 4 只保留指定类别 |
| 「整理成文档/归档」 | 阶段 1–5 全量，产物：蒸馏卡 + 归档总览 |

未命中时：先确认用户指哪个群、哪个时间范围，再执行。

## 执行环境与工具

- 归档根目录：`<ARCHIVE_ROOT>`（执行时替换为实际工作目录），内部固定结构见「产物规范」。
- 抖音网页版：`https://www.douyin.com/jingxuan`，已登录用户会话（必要时让用户接管登录）。
- Python 运行解释器：`python`（已装 requests、imageio-ffmpeg；系统无 ffmpeg 时用 `imageio_ffmpeg.get_ffmpeg_exe()`）。
- 飞书链路：`lark-cli drive +upload` / `lark-cli minutes +upload` / `lark-cli vc +notes`。
- 分类与蒸馏唯一依据：`references/classification.md`（含核心资产留存规则）。

## 阶段 1：取链接（抖音网页版，禁用逐卡点击）

1. 打开 `https://www.douyin.com/jingxuan`，点击顶栏「消息」打开消息浮层（`aside` 内会话项 class 含 `ConversationItemwrapper`）。浮层偶发渲染空白：刷新页面或关闭重开。
2. 用 `aside.innerText` 核对会话列表，确认目标群（群名可能被改名；同名旧会话会造成误入其他群，用首屏文本与最近活跃时间确认）。
3. 点击目标群进入聊天窗口，等待其自动向 `multi/aweme/detail` 批量接口请求群内全部视频 ID。
4. 用浏览器 `network_requests()` 抓取 URL 含 `multi/aweme/detail` 的请求，解析 `aweme_ids=%5B...%5D` 得到全部视频 ID。**不要**逐张点视频卡片（极慢且浮层易空白）。
5. 对每个 ID 用单条接口补全元信息（可浏览器内 fetch，带登录 cookie，无需签名）：
   `https://www.douyin.com/aweme/v1/web/aweme/detail/?device_platform=webapp&aid=6383&channel=channel_pc_web&aweme_id=<ID>`
   取 `aweme_detail.desc`（标题）、`.author.nickname`（作者）、`.video.play_addr.url_list[0]`（无水印直链）、`.images`（图集条数）。
6. 全部元信息写入 `<ARCHIVE_ROOT>/distill_tools/video_urls.json`（字段：desc/author/url0/images），作为后续阶段唯一数据源。

## 阶段 2：下载视频

1. 复用/参考 `scripts/batch_download.py`：requests 分段下载到 `<ARCHIVE_ROOT>/raw/<视频ID>.mp4`，带 `User-Agent` + `Referer: https://www.douyin.com/`；已存在且 >100KB 的跳过。
2. 失败项记录原因（链接失效/需要登录/无直链），放入失败清单继续，不中断流水线。
3. 视频下载后立即批量转 MP3（`scripts/batch_extract_audio.py`：imageio_ffmpeg，`-ac 1 -ar 16000 -b:a 64k`）到 `raw/<视频ID>.mp3`，供妙记上传（妙记直传 mp4 超配额，必须用音频）。

## 阶段 3：转录（飞书妙记链路）

1. 对每个 `<ARCHIVE_ROOT>/raw/<视频ID>.mp3`：
   - 上传云空间：**先 `cd` 到 media 所在目录**，再 `lark-cli drive +upload --file ./<视频ID>.mp3 --format json`（lark-cli 拒绝绝对路径与 cwd 外部路径，且不继承 PowerShell 脚本内 `Set-Location`——必须在同一命令串内 `cd`）。
   - 取返回 `file_token`，`lark-cli minutes +upload --file-token <token> --format json` 得 `minute_token`。
   - 全部上传完成后统一写入 `distill_tools/minute_tokens.json`（id→token 映射）。
2. 等待妙记处理（约 50–90 秒；首次常见 "minute not ready"，继续轮询），再 `lark-cli vc +notes --minute-tokens <token> --output-dir <ARCHIVE_ROOT>/minutes --format json` 读取产物。
3. 产物落盘：`minutes/artifact-<视频ID>-<minute_token>/transcript.txt`（含逐字稿、摘要、关键词、时长）。
4. 转录为空/无有效语音（背景音乐覆盖、纯图文帖、无画面纯音频流）：保留元信息，分类阶段按「无有效语音」处理，蒸馏依据标题/话题标签并如实标注。

## 阶段 4：自动分类

1. 读取 `references/classification.md` 的完整分类规则（6 类体系 + 强信号词 + 裁定优先级）。
2. 判定输入按权重：**转录内容（50%）> 视频标题/话题（30%）> 群内附带文字（20%）**；命中任一强信号词直接判定；无强信号按内容特征裁定。
3. 一条视频只归 1 个主类别 + 最多 2 个标签；信号冲突按「技术干货 > 开源GitHub > 行业资讯 > 对标案例 > 观点认知」裁定，并在卡中标注判定依据。

## 阶段 5：蒸馏归档与交付

1. 按 `references/classification.md` 的「蒸馏产物模板」逐条产出蒸馏卡，**「核心资产」节为必填**（核心图片归档到 `<ARCHIVE_ROOT>/assets/<作者>_<内容描述>.jpg`、提示词 OCR 入卡、项目地址联网核实入卡）。
2. 产物载体（默认本地 Markdown，用户要求飞书文档时再走 `lark-doc`）：
   - 每视频一张蒸馏卡：`<ARCHIVE_ROOT>/distilled/<视频ID>.md`
   - 归档总览：`<ARCHIVE_ROOT>/README.md`（汇总表 + 类别分布 + 每类数量 ≥3 时的「共性总结」+ 核心资产留存总表）
3. 交付给用户：归档总览 + 蒸馏卡（present_files）；核心图片用图片卡片展示；汇总用表格呈现（链接 | 作者 | 内容 | 主类别 | 标签 | 蒸馏卡）。

## 产物规范

```
<ARCHIVE_ROOT>/
├── raw/               原始视频 mp4 + 转码 mp3（按 <视频ID>.<ext>）
├── minutes/           妙记转录产物（逐字稿/摘要/关键词，artifact-<ID>-<token>/transcript.txt）
├── frames/            抽帧图片（提示词/关键画面 OCR 用）
├── assets/            核心资产归档（<作者>_<内容描述>.jpg）
├── distilled/         蒸馏卡 <视频ID>.md + README.md 归档总览
└── distill_tools/     video_urls.json / minute_tokens.json / 批处理脚本
```

## 已证实死路（不要再走）

- **`lark-im` 搜抖音群**：返回 0 条，群在抖音不在飞书。
- **faster-whisper 本地转录**：模型下载过慢（数百 MB），弃用。
- **妙记直传 mp4**：`quota_exceeded 1061043`（36MB 失败），必须先转小体积 MP3。
- **`imapi.douyin.com` 消息接口重放**：`get_message_by_init` 等返回 HTML / Failed to fetch，需签名，不可重放。
- **逐张点 `.MessageItemShareAwemecontainer` 卡片取 ID**：能跑但极慢，浮层多次渲染空白，已被 multi 批量接口取代。
- **GitHub MCP `search_repositories`**：供应商持续不可用，检索改用 general_search。

## 执行依赖与边界

- 依赖：用户已登录的抖音网页版会话（浏览器自动化）、`lark-cli` 飞书链路、本地 Python（requests/imageio-ffmpeg）。
- 只处理用户指定或默认的群，不扫描全部会话；进入聊天窗前必须用 aside 文本确认群名，避免误入同名群。
- 下载的视频仅用于内部存档与学习，不对外发布；归档中保留来源链接。
- 任一阶段失败不中断整条流水线，失败项进入对应清单并如实告知用户。
- 分类基于内容本身；无法判定归「其他」并标注待确认。
- 核心资产留存规则见 `references/classification.md`（蒸馏产物模板首节）。
