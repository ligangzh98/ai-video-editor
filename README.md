# TechGuide Video Editor

面向 YouTube 口播与教程的**本地剪辑工具包**：用 Python 脚本处理剪切、转录与质检，用 [HyperFrames](https://github.com/hyperframes/hyperframes) 合成动效叠层并渲染 4K 成片；也可导出 **FCPXML** 在 Final Cut Pro 里继续精修。

本仓库核心是 **`youtube-edit/`**——一套可在 [Claude Code](https://claude.ai/code) 或 Cursor 中通过 Agent Skill 驱动的端到端工作流；也可在终端里直接调用 `scripts/` 下的脚本。

> **素材与成片不进 Git。** `videos/`、各类音视频文件已在 `.gitignore` 中排除；克隆后需自备原始素材与共享资源目录。

---

## 能做什么

| 能力 | 说明 |
|------|------|
| **剪切阶段** | 从重拍、口误、打板中自动出 `cut-list.json` 与 `PAPER-CUT.md`，帧精确应用到平剪 |
| **转录** | [VoiceMagic](https://voicemagic.demo2easy.com) 词级 ASR（含幻觉修复、长文件分窗等） |
| **动效与分镜** | `storyboard.json` → `compose.py` → HyperFrames 页面 → 4K MP4 |
| **长片节奏** | 结巴扫描、空档检查、节拍对齐、分段渲染与组装 |
| **双机位教程** | 脸 + 录屏音画同步（`sync-tracks.py`） |
| **Final Cut 交付** | 双轨分段 FCPXML、透明叠层 MOV；见 [`youtube-edit/FCP.md`](youtube-edit/FCP.md) |
| **频道学习** | `teardown.py` 测量参考片的节奏与叠层密度 |

视觉风格（浅色玻璃卡、关键词绿、金额黄等）写在 `compose.py` 的 CSS 中，并在 [`youtube-edit/SKILL.md`](youtube-edit/SKILL.md) 里作为可迭代的「门派规则」维护。

---

## 仓库结构

```
TechGuide-Video-Editor/
├── README.md                 # 本文件
├── youtube-edit/             # 剪辑 Skill 与全部脚本
│   ├── SKILL.md              # 完整流程、检查点、转录与剪辑规则（主文档）
│   ├── FORMATS.md            # 叠层格式库与 storyboard 字段
│   ├── FCP.md                # FCPXML 交付规范
│   ├── formats/              # 可插拔格式模块（如 AI 聊天窗）
│   └── scripts/              # Python / Node 工具链 + tests/
└── videos/                   # 本地项目工作区（不提交）
    ├── <project>/            # 单条视频：raw、public、storyboard、输出等
    └── _shared/              # 可选：跨项目 sfx、img、缩略图
```

在仓库根目录约定：

```bash
SK="youtube-edit"                    # 或本目录的绝对路径
W="videos/<project>"                 # 一条视频一个文件夹
```

装进 Claude Code 后，Skill 路径通常为 `.claude/skills/youtube-edit`；**在本仓库内请始终用并列的 `youtube-edit/`**，不要到 `.claude/skills/` 里找脚本。

---

## 环境要求

| 依赖 | 用途 |
|------|------|
| **Node.js 22+** | HyperFrames CLI（`npx hyperframes`） |
| **Google Chrome** | 无头截图、渲染 |
| **FFmpeg / ffprobe** | 编解码、探针、响度与色彩 |
| **Python 3** + **numpy** | 剪切、对齐、静音与边缘分析 |
| **auto-editor** | 语音块检测（剪切阶段） |
| **VoiceMagic** | 词级转录（`VOICEMAGIC_MCP_TOKEN` 或 `~/.cursor/mcp.json` 中的 MCP 配置） |

可选：`yt-dlp`、本地 GSAP 副本（见 `SKILL.md` 安装表）、Epidemic Sound 连接器。

### 快速检查

```bash
node -v
npx hyperframes doctor
ffmpeg -version
python3 -c "import numpy"
auto-editor --version
```

### 运行测试

```bash
cd youtube-edit/scripts && python3 -m unittest tests
```

测试使用合成媒体；未安装 ffmpeg 时部分媒体测试会自动跳过。修改脚本后应跑通并以 `OK` 结束。

---

## 转录：[VoiceMagic](https://voicemagic.demo2easy.com/)

本仓库的剪切、节拍对齐与叠层锚词都依赖**词级时间戳**。[VoiceMagic](https://voicemagic.demo2easy.com/) 是配套的 AI 语音工作台：在同一套流程里提供**语音转文字**（ASR）与**声音克隆**（TTS），面向内容创作、播客后期与产品配音。除网页与微信小程序外，也可通过 **MCP** 接到 Cursor、Claude Code、Codex 等客户端，在对话里查额度、提交转写、看任务进度，无需反复切浏览器。

与本项目相关的要点：

| 项目 | 说明 |
|------|------|
| **在本仓库中的角色** | `transcribe-api.py` / `voicemagic_asr.py` 调用 VoiceMagic ASR，产出 `transcript.json`（`words[]` 含 `text`、`start`、`end`），供 `paper-cut.py`、`phrase-times.py`、`beat-check.py` 等使用 |
| **接入方式** | 环境变量 `VOICEMAGIC_MCP_TOKEN`（或 `VOICEMAGIC_TOKEN`）；未设置时脚本会读取 `~/.cursor/mcp.json` 里 `voicemagic` 的 MCP 令牌 |
| **令牌** | 登录官网 → **我的 → MCP 令牌**，创建以 `vmpat_` 开头的令牌，按 [MCP 文档](https://voicemagic.demo2easy.com/) 配置 Streamable HTTP |
| **输出格式** | 纯文本、SRT，或**字词级时间戳**（本剪辑流默认需要后者；与网页 ASR 一致，通常需有效会员额度） |
| **引擎** | `transcribe-api.py --engine` 默认为 `auto`，也可显式指定本地或其它引擎 |
| **安全** | 不要把令牌写入仓库或 Skill 文件；上传前脚本会用 ffmpeg 将音频转为 MP3 再请求（与 VoiceMagic Skill 一致） |

更细的转录规则（长文件分窗、幻觉修复、`retranscribe-holes.py` 等）见 [`youtube-edit/SKILL.md` → 转录](youtube-edit/SKILL.md)。

---

## 三条主路线

详情与命令见 [`youtube-edit/SKILL.md`](youtube-edit/SKILL.md) 的「路线表」。

1. **只剪切** — 原始素材 → `PAPER-CUT.md` + `cut-list.json`（检查点 A）  
2. **整片渲染** — 平剪 → `storyboard.json` → HyperFrames → `verify-render.py`（检查点 B + 成片）  
3. **FCP** — 剪切照跑 → 交付媒体 + 双轨 FCPXML；一般不渲整条 4K  

典型剪切链（节选）：

```bash
python3 "$SK/scripts/transcribe-api.py" --audio "$W/audio-raw.wav" --out "$W/transcript-raw.json"
python3 "$SK/scripts/paper-cut.py" --transcript "$W/transcript-raw.json" --duration <秒> --out-dir "$W" --speech "$W/speech.v1"
python3 "$SK/scripts/apply-cut.py" --input "$W/raw/<clip>.MP4" --cut-list "$W/cut-list.json" --out "$W/public/input-video.mp4"
```

典型渲染链（节选）：

```bash
python3 "$SK/scripts/compose.py" --spec "$W/storyboard.json" --out "$W/public" --shared videos/_shared
npx hyperframes check "$W/public"
python3 "$SK/scripts/beat-check.py" --index "$W/public/index.html" --transcript "$W/transcript.json"
npx hyperframes render "$W/public" --resolution 4k --video-bitrate 45M --gpu -o "$W/output-4k-raw.mp4"
python3 "$SK/scripts/verify-render.py" --render "$W/output-4k.mp4" --index "$W/public/index.html"
```

---

## 在 AI 助手里使用

将 `youtube-edit/` 安装为 Agent Skill 后，可对助手说例如：

- 「剪这个钩子 / 加字幕动画 / 渲 4K」
- 「出 FCPXML，不要渲染」
- 「把多段 SD 卡素材拼起来再剪」

助手应先读 `SKILL.md`，写分镜或叠层前读 `FORMATS.md`，走 Final Cut 时读 `FCP.md`。

---

## 脚本索引

`youtube-edit/scripts/` 包含 30+ 个工具，覆盖：入库拼接（`ingest.py`）、转录与洞补（`transcribe-api.py`、`retranscribe-holes.py`）、剪切与修边（`paper-cut.py`、`hand-cut.py`、`edge-audit.py`、`dead-air.py` 等）、分镜合成（`compose.py`、`beat-check.py`、`snap-beats.py`）、B-roll 规范化（`broll-conform.py`）、成片组装（`assemble.py`）、FCP 预检（`check-fcpxml.py`）等。

完整表格见 [`youtube-edit/SKILL.md` → 脚本](youtube-edit/SKILL.md)。

---

## 许可与致谢

部分 Node 脚本改编自 MIT 许可的 HyperFrames starter kit（见文件头注释）。字体与第三方素材**不随仓库分发**；叠层音效可从 HyperFrames `media-use` skill 或自备素材库获取，见 `SKILL.md`「寻找素材」。

---

## 进一步阅读

- **[`youtube-edit/SKILL.md`](youtube-edit/SKILL.md)** — 安装、路线、转录陷阱、检查点、渲染参数  
- **[`youtube-edit/FORMATS.md`](youtube-edit/FORMATS.md)** — 叠层类型与 `storyboard.json` 约定  
- **[`youtube-edit/FCP.md`](youtube-edit/FCP.md)** — FCPXML 双轨交付与透明叠层  
