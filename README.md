# douyin-group-video-distiller

抖音群视频自动蒸馏 Skill —— 把抖音群聊里分享的视频，全链路处理为「取链接 → 下载 → 转录 → 按内容自动分类 → 蒸馏成结构化卡片」。

## 特性

- **批量取链接**：进入抖音网页版群聊天窗口后，自动捕获 `multi/aweme/detail` 批量接口，一次性拿到群内全部视频 ID（无需逐张点击卡片）；单条 `aweme/detail` 接口直接返回标题 / 作者 / 无水印直链 / 图集信息。
- **无水印下载**：直链分段下载（带 UA / Referer），自动跳过已存在文件。
- **飞书妙记转录**：视频转小体积 MP3 后走飞书妙记链路（drive 上传 → minutes 生成 → vc 读取产物），得到逐字稿、摘要、关键词。
- **6 类自动分类**：技术干货 / 开源GitHub / 行业资讯 / 对标案例 / 观点认知 / 其他，按「强信号词 → 内容特征 → 裁定优先级」判定（见 `references/classification.md`）。
- **核心资产留存**：关键画面抽帧、提示词 OCR、项目地址核实，统一归档进 `assets/` 并写入蒸馏卡（必填节）。
- **蒸馏卡 + 归档总览**：每视频一张结构化卡片，每类 ≥3 条时自动生成「共性总结」；README 汇总表一览全群内容。

## 安装

将本 Skill 目录放入 Agent 技能根目录（例如豆包的 `.user_skills/`）：

```
.user_skills/
└── douyin-group-video-distiller/
    ├── SKILL.md
    ├── references/classification.md
    └── scripts/            # 批处理脚本（下载 / 转音频）
```

## 依赖

- 已登录的**抖音网页版**会话（用于读取群消息与接口）
- **lark-cli**（飞书云空间 + 妙记转录链路）
- Python 3 + `requests` + `imageio-ffmpeg`（系统无 ffmpeg 时自动取内置）

## 使用

对话中说出触发词即可，例如：

- 「处理 AI测试群」
- 「把群里的视频下载转录归档」
- 「蒸馏今天的群视频」

执行流程（详见 `SKILL.md`）：

```
阶段1 取链接   → 抖音网页版消息浮层 → 进群 → 抓 multi/aweme/detail 批量接口拿全部视频 ID
阶段2 下载     → 无水印直链下载到 raw/<视频ID>.mp4，转 mp3
阶段3 转录     → 飞书妙记：drive +upload → minutes +upload → vc +notes
阶段4 分类     → references/classification.md 规则（6 类）
阶段5 蒸馏     → distilled/<视频ID>.md 卡片 + README.md 归档总览 + assets/ 核心资产
```

## 目录产物

```
<ARCHIVE_ROOT>/
├── raw/              原始视频 mp4 + mp3
├── minutes/          妙记转录（逐字稿/摘要/关键词）
├── frames/           抽帧图片（OCR 用）
├── assets/           核心资产（<作者>_<内容描述>.jpg）
├── distilled/        蒸馏卡 + README 归档总览
└── distill_tools/    数据与脚本
```

## 免责声明

- 本 Skill 需要**你自己的抖音账号登录态**与飞书授权，不含任何凭据。
- 下载与转录的视频仅用于个人学习 / 存档，请遵守相关法律法规与平台条款，勿对外传播。
- 转录为空 / 纯音频 / 无画面流的视频会如实标注，蒸馏依据可用元数据。

## License

MIT
