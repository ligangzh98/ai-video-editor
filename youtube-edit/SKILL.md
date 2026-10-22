---
name: youtube-edit
description: 在 Claude Code 里端到端剪辑 YouTube 视频。吃进一段原始相机素材（带重拍的也算）或一段平剪，完成剪切、动画叠层、切出镜头、素材或 AI B-roll、运镜、少数配得上的声音，然后用 HyperFrames 在本地渲出带色彩标签的 4K MP4。只要用户丢来一个视频文件或 SD 卡素材并说「剪这个/剪一下/加字幕/加动画/剪这个钩子/加 B-roll/渲 4K/拼成片/把各段拼起来」，或点名要剪某个视频文件，就用本 skill。覆盖剪切阶段、分镜、长视频节奏、运镜、声音、组装与交付。格式规格在同目录 `FORMATS.md`，Final Cut 在 `FCP.md`；写分镜或出 XML 之前先读对应文件。
---

# YouTube 剪辑师

把原始素材或平剪变成成片：剪切、动画叠层、切出镜头、运镜、声音，以及带色彩标签的 4K MP4。一切通过 HyperFrames（Chrome + FFmpeg）在你自己的机器上跑：渲片零成本，素材不出电脑。

**这是门派风格。** 这是一个真实频道的剪辑 skill，所以它有主张：浅色玻璃卡片、系统无衬线粗体标题、关键词用绿色、钱用黄色、点睛句用橙色、运镜锚在画面顶部，画面上没有东西发声就保持安静。这些是写给你——创作者——的默认值。颜色与字体栈写在 `scripts/compose.py` 的 CSS 里（`:root` 与 `body`）。你改风格时，Claude 会同步更新本文件对应章节和合成器里的颜色变量。

**这个 skill 持续学习。** 下面每条规则都来自真实视频上的真实意见。当你给出一条值得留下的意见（「字太小了」「这段没声音」）时，说一句 **「把这个存进 skill」**：Claude 会把它写进本文件对应章节的一条大白话规则，下一次剪辑从这条规则出发。见「让 skill 保持是你的」。

命令在你的项目文件夹下运行。`W="videos/<project>"`（一条视频一个工作文件夹）。`SK` 指向本 skill 目录，脚本在 `$SK/scripts/`：

- **本仓库：** skill 就在与 `videos/` 并列的 `youtube-edit/`。在仓库根目录用 `SK="youtube-edit"`（或绝对路径）。
- **装进 Claude Code 之后：** 才是 `SK=".claude/skills/youtube-edit"`。不要在本仓库里去 `.claude/skills/` 找脚本。

## 安装检查（首次使用，以及每次更新后）

首次使用时 Claude 逐行检查，缺什么装什么（需要管理员权限的会先问你），然后跑测试。更新 HyperFrames 或移动 skill 之后再检查一遍。

| 需要 | 检查 | 缺了怎么装 |
|---|---|---|
| Node.js 22 或更新 | `node -v` | nodejs.org，或 `brew install node` |
| HyperFrames CLI | `npx hyperframes --version`，然后 `npx hyperframes doctor` | 通过 npx 获取；`doctor` 会列出它还想要什么 |
| FFmpeg 和 ffprobe | `ffmpeg -version` | `brew install ffmpeg`（Mac）、`winget install ffmpeg`（Windows）、包管理器（Linux） |
| Python 3 + numpy | `python3 -c "import numpy"` | `python3 -m pip install numpy` |
| auto-editor | `auto-editor --version` | `pip install auto-editor` 或 `brew install auto-editor` |
| Google Chrome | 快照、页面抓取和无头截图都在它里面跑 | google.com/chrome |
| GSAP | compose.py 回退到 CDN 时会打印提示（那样首次渲染需要联网） | 可选的本地副本：`mkdir -p "$SK/assets/vendor" && curl -sL https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js -o "$SK/assets/vendor/gsap.min.js"` |
| yt-dlp（可选） | `yt-dlp --version` | `brew install yt-dlp` 或 `pip install yt-dlp` |
| VoiceMagic（转录，必需） | `VOICEMAGIC_MCP_TOKEN` 已设置，或 `~/.cursor/mcp.json` 里配置了 voicemagic MCP | 在 [VoiceMagic](https://voicemagic.demo2easy.com) **我的 → MCP 令牌** 创建 `vmpat_…`；字词级 ASR 需有效会员（与网页一致） |

然后在 scripts 文件夹下（不是 `tests/` 里面）：`cd "$SK/scripts" && python3 -m unittest tests`。测试用合成媒体，必须以 `OK` 结尾（没有 ffmpeg 时媒体测试会自动跳过）。动过任何脚本后都要跑。

- **随包附带：** 脚本与 `formats/`。**不附带任何字体文件、声音、图片、logo 或素材。** 叠层文字用系统无衬线（`compose.py` 里的 `ui-sans-serif` 栈）。你的素材放在一个共享文件夹里，compose.py 用 `--shared DIR` 拷贝（`DIR/sfx/`、`DIR/img/`、`DIR/img/thumbs/`）：声音来自你的 Epidemic Sound 账号（它的连接器）或免费的 HyperFrames 音效库（`npx hyperframes skills update media-use` 会把 19 个音效放进 media-use skill 的 `audio/assets/sfx/`，Pixabay Content License，无需署名）；logo 来自品牌自己的媒体资料包或官网（见「寻找素材」）。
- **可选连接器：** Epidemic Sound。
- 需要 numpy 的脚本：`sync-tracks.py`、`tighten-cut.py`、`sliver.py`、`edge-audit.py`、`dead-air.py`。需要 Node 的：`stutter-scan.py`（它跑 `find-cut-candidates.mjs`）和剪辑审查页（`build-edl-review.mjs`）。
- **`silence-check.py` 不在 `$SK/scripts/`。** 保留段静音检查是每条片子工作目录里的脚本（261007），规则见「转录」里「工作目录里长出来的检查」。不要在 skill 包里找这个文件。

## 路线表

| 输入 | 路线 |
|---|---|
| 你自己剪的平剪（没有预录的缩放、字幕或转场；4K 优先） | 流水线（Pipeline） |
| 中文视频（本用户的默认） | 任何路线；转录与语言规则见「转录（VoiceMagic）」 |
| 一段原始素材，1–3 分钟（一个钩子、一个段落开场） | 剪切阶段 → `storyboard.json` → `compose.py` → `snap-beats.py` → 渲染 |
| 一条视频的多段原始素材 | `ingest.py`（排序并拼成 `source.mp4`）→ 在 `source.mp4` 上跑同样的流程 |
| 一段长口播（超过 3 分钟） | 剪切阶段 + `stutter-scan.py` + 检查点 A 的 `CUT-REVIEW.html` → 长视频章法下的分镜 → `gap-scan.py` + `beat-check.py` → 分段渲染 |
| 两个文件录的教程（脸 + 屏幕） | `sync-tracks.py` → 对脸的文件跑剪切阶段 → 屏幕做全屏 `clip` 切出 |
| 一条完整视频（钩子 + 开场 + 段落 + 教程） | `assemble.py` → 一个 4K 母版，响度对齐，带章节表 |
| 要 FCPXML 进 Final Cut 继续剪，不要渲染 | 剪切阶段照跑 → 原始双文件 + 双轨分段 FCPXML；细则见 [`FCP.md`](FCP.md) |
| Shorts（9:16） | 不是默认流程；见「Shorts」 |
| 一个你想学习的频道 | `teardown.py`；见「拆解」 |

**先选一条路，再往下读。** 三条路的交付物不一样，不要串：

| 路 | 什么时候 | 做到哪停 |
|---|---|---|
| 只剪切 | 还在决定留哪一遍 | `PAPER-CUT.md` + `cut-list.json`；检查点 A |
| 整片渲染 | 要一条 HyperFrames 4K MP4 | 检查点 B 的分镜和静帧 → 渲染 → `verify-render.py` |
| FCP | 要进 Final Cut，不渲整条成片 | 剪切照跑 → 双轨 XML。接线读 [`FCP.md`](FCP.md)。不要整片 `verify-render.py`，也不要默认 `beat-check` |

一条视频两个检查点，其余按上面那条路走。**A，剪切：** `PAPER-CUT.md`（长片再加 `CUT-REVIEW.html`）；你用大白话回答（「录音棚那句留前面那遍」）。**B，方案（只在整片渲染这条路）：** `storyboard.json` + `snaps/sheet.png`，每个卡片时刻一张静帧，然后渲染，对文件跑 `verify-render.py`。FCP 这条路没有检查点 B 的成片渲染。

**钩子闸门**（每个钩子，在检查点 B）：
- 前 3 秒说服别人看到最后。第一帧是有意义的画面，而不是还在稳住的镜头。
- 静音也要成立：第一个叠层自己把承诺说清楚。第一个说出口的词必须幸存：不要有声音、卡片入场或剪切落在它上面。
- 承诺要有兑现时间：分镜里的 `"loops": [{"question": "...", "planted": 2.1, "payoff": 412.0}]`，在组装好的母版里检查。同时只开一个主环，最多一个副环；一个回来却什么都没解决的物件是回响（callback），不是闭环。承诺的功课要在任何行动号召之前收掉。

## 转录（VoiceMagic）

**转录一律走 VoiceMagic ASR（`transcribe-api.py` → 与 MCP `voicemagic_transcribe_audio` 相同，`output_format=words`）。视频语言默认是中文。凡是拿不准素材语言，先问用户再继续——绝不要自作主张换成别的语言。**

**令牌：** 环境变量 `VOICEMAGIC_MCP_TOKEN`（或 `VOICEMAGIC_TOKEN`）；未设置时脚本会读 `~/.cursor/mcp.json` 里 `voicemagic` 的 `x-voicemagic-mcp-token`。不要把令牌写进仓库或 skill 文件。上传前脚本会用 ffmpeg 把非 MP3 转成 MP3 再请求（与 voicemagic skill 一致）。

```bash
# 剪切阶段（原始素材时间）：
python3 "$SK/scripts/transcribe-api.py" --audio "$W/audio-raw.wav" --out "$W/transcript-raw.json"
# 流水线 / 重转录（平剪时间）：
python3 "$SK/scripts/transcribe-api.py" --audio "$W/audio.wav" --out "$W/transcript.json"
```

- **引擎：** VoiceMagic `engine` 默认 `auto`（`transcribe-api.py --engine`）；可显式 `local` 或 `qwen-audio-3.1-asr-flash-filetrans`。产物是词级 `transcript.json`，paper-cut / phrase-times / beat-check 都能读中文（CJK 感知匹配）。
- **FCP 交付要留一份转录副本（与 `.fcpxml` 同目录）：** 用 `transcribe-api.py` 拿到的词级稿（`{"words":[{"text","start","end"},…]}`）不要只留在 `videos/<p>/` 工作区——**同时写入即将交付或已交付的 FCP XML 所在文件夹**（例如 `…/fcp/xml/261007-ai剪辑-双轨-v1.fcpxml` 旁边的 `…/fcp/xml/`），方便以后调叠层、对锚词、重跑 `phrase-times` / `beat-check` 而不用翻仓库路径。多段原始素材按 **XML 里的资产名** 分文件：`transcript-1-录像.json`、`transcript-2-录像.json` …（与 `make-fcpxml.py` 读的 `transcript-<take>.json` 同名）；可选再存一份 MCP/ASR 原始 JSON 为 `transcript-<take>-asr-verbose.json` 供 `--from-json` 离线重导。`make-fcpxml.py` 重跑 XML 时优先从该目录读或跑完转录后 `cp` 进去，保持 **XML + 动画 + 转录** 同包可搬。
- **语言默认 `zh`。** 只有用户明确要求时才传其他语言（`--language`）。
- **配额与格式：** 字词级时间戳需有效会员（与网页 ASR 一致）；长任务前确认今日额度。约 3 分钟以上的长原始素材按 auto-editor 语音块开窗转录（见下）。
- **长静音头和文件尾巴会炸解码：** 全文件转录会整段丢语音，或在结尾幻觉出根本不存在的句子（「之后再录一条…」）。开头有十几秒静音就够触发：按 auto-editor 语音块开窗转录、词时间加窗口偏移再合并（不止 3 分钟以上的素材才用）。两轮解码结论打架时按频谱的语音块间隙结构裁决；尾巴可疑就单截尾段重解码核对。
- **合并窗口解码的两个坑（真实事故）：** ① 无停顿重拍会被并成一句，词表只剩一遍且词时间是假的——**词间出现 >1 秒的大间隙就要单解该区间**（「设|备」曾被假时间劈开，单解发现是连续句；「你录一条」三连重拍则被并句藏了两遍）；② 平剪重转录在跳剪接缝处会**回声重复短语**——先分清真重拍和回声：回声串语法不通（「并且对你本地的不管是手机」），真重拍是完整的整句重复。
- **半截烂头要靠子窗口逐段复核（听感投诉后补的课）：** 「并且不会挑」「但是配」「去在程序中」这类半句烂头会被合并解码**完全藏进句子**，词表都看不见；「并且对你本地的设备没有任何的要求」这种整句重说第 2 遍也只显示一遍。对每个保留段的边界做 2 秒级子窗口解码，半截烂头和重说才现形；同时 **hand-cut 的「延到语音块尾」会吞进下一遍重说的头**——保留段末词后面紧跟重说时，手工把尾收在真句尾。
- **平剪二审扫「6 字以上短语重复」：** 3 字级扫描会被滑窗自匹配淹没；6 字以上、两次出现隔开 ≥1 个词的才看。真重拍=同一短语不同结尾（留后遍）；两句不同的话共享短语（「这一串就是它的一个完整的配置」/「你可以点击复制这串配置」）是内容，别删——自动判重说有过误伤，拿不准就听语义。
- 数字、同音字（「世界」→「十几」）拿不准时：屏幕文案用最保守读法，把几种读法的分歧写进 `PAPER-CUT.md`，绝不硬猜。
- `--from-json` 离线重转一份保存下来的响应；`--dry-run` 查看将要发送的请求。纯文本的 API 响应（没有 `words[]`）会被故意拒收：没有词级时间戳，就无法剪。

- **幻觉不必只发生在静音头——它能把整段开场白盖掉（261007 真实事故，丢了大半段）：** ASR 在文件开头把真人话音整段幻听成一句样板（「请不吝点赞订阅转发打赏支持明镜与点点栏目」），而且是**把它铺在真话上面**，不是替掉静音。转录里开头因此只有这句、重复几遍；`paper-cut` 读到「同一句说了三遍」就判成重拍、留最后一遍——删掉的正好是真开场白所在的区间。此后的每一道检查全绿：若只扫**保留段里有没有可疑静音**（261007 工作目录里的 `silence-check.py`，不是 skill 包里的脚本），没人查**被剪掉的段底下有没有真话**。症状出现在成片上：开头是样板句，稿子的钩子句整段不见了。
  - **判据是电平，不是文本。** 真话所在的那 90 秒 RMS 是 3000-6000，模板句所在处 <200。中文 ASR 逐字出词，幻觉句的词会散落在几秒的静音上（词组时长 1-8 秒），所以按文本匹配句子永远匹配不上。
  - **修法：** `scripts/retranscribe-holes.py --audio W/audio.wav --transcript W/transcript.json [--head-until T]`。它按电平判每个词（`--frac` 词跨度里超阈值的比例），两件事一起做：①「有声但转录是空的」区间按小窗重转（`--win/--step`）；②「整片压在静音上的词」当幻觉删掉（`--phantom-run/--phantom-span`，顿号标点不算）。**开头被整段盖住的**——幻觉句是铺在真话上的，电平分不开——只有 `--head-until T` 能把 [0, T] 整体重转，这是唯一有效的修法。跑完必须从 `paper-cut.py` 重跑整条剪切链。
- **剪切链跑完还要做一次「丢了多少真话」的对账：** 把每条 `removed` 区间按声音量一遍，凡 `>0.3s` 且 `RMS > 800` 的都要看清楚是什么——它们要么是重拍/打板（该剪），要么就是被幻觉或词表错误连带剪掉的真话。261007 上这一步查出 1-录像 77s、2-录像 358s、3-录像 41s 的真话被当成静音剪掉。**这一步没有就等着用户发现开头是样板句。**

**工作目录里长出来、下一条片照做的检查（脚本留在 `videos/<p>/`，不收进 skill 包；261003 / 261007）。** `paper-cut` 写完 `cut-list.json` 之后、`apply-cut` 之前跑。长文件按 auto-editor 语音块分窗调 `transcribe-api.py`（每窗 MP3 + 词时间加偏移合并），不要整文件硬扛一次 ASR。

- **保留段里的静音是幻觉，不是「留白」：** 房间底噪大约几十 RMS，说话是几千。一条保留段里高于约 300 RMS 的 10 ms 帧少于 3 帧，就是样板句铺在静音上——从 `kept` 里丢掉（261007 `silence-check.py`）。这和上面「被删区间里反而有真话」是一对：一个查留多了，一个查删多了。
- **划掉的重拍仍可能留在 `kept` 时间里：** `paper-cut` 会把重拍写进 `removed`，但 `kept` 区间有时仍罩住那段。成片就会两遍连着放。把所有**非静音**的 `removed` 从 `kept` 里挖掉，剩下短于约 0.35 s 的碎片丢掉（`repair-cut.py`）。
- **没有停顿的重说，句子相似度看不见：** ASR 把同一短语连说两遍并进一条保留段，或前一段结尾和后一段开头（接缝 &lt; 约 1.2 s）是同一串（至少约 4 个词）。留**后面**那遍：段内从第二遍的词起点切开，跨段则把第一段的尾巴收到重复开始之前（`dedupe-takes.py`，先打印再 `--apply`）。和「平剪后扫 6 字重复」是同一类问题，这一步在**素材时间的 cut-list** 上做，不等平剪。
- **响着的剪切边缘要分两种：** 相邻两条保留段在素材里本来就贴着（间隙 &lt; 1 帧），中间的「边缘」不是跳剪，声音连续，响着也没关系。只有真跳剪还落在声音上才要修（`edge-report.py`）。`edge-audit` 报的问题先用这个分开，避免把连续句当成坏刀。
- **脸和录屏的偏移用多个锚点核对，不要一次互相关定终身：** 在口播上隔几分钟各取一段包络，对录屏做互相关，偏移应稳定在同一值（261007 的 2-录像 / 2-录屏是 **35.290 s**，写进该片 `make-fcpxml.py` 的 `SCREEN_DELTA`）。`sync-tracks.py` 给初值，长片用 `verify-sync.py` 这种多点复核。
- **检查点 A 除了 `PAPER-CUT.md`，再出一份「保留段里实际有哪些字」：** 按 `kept` 把转录贴上去（`review-cut.py`）。走 FCP 时还可以从已生成的 fcpxml 脊柱汇总：每条 take 保留多少秒、禁用段按原因计数、前若干条划掉原文，并写明「要留那一遍就启用禁用段、禁用相邻保留段」（`write-review.py`，和 XML 放在同一交付夹）。数字从 XML 和 cut-list 来，不要手抄。

## 这样录，才好剪

- 4K、30 fps（29.97 也行）、标准色彩、画面保持「平」（不要机内缩放、字幕或转场），每个文件都带麦克风声轨，每次录制同一个构图，两端各留一秒静音。1080p 超过约 112% 缩放就发糊；4K 撑得住 200%。
- **说砸了一句？停约两秒，从这句话的第一个词整句重说。** 留最后一遍；数字、名字或价格说错了就整句重说。「Cut that」或「scratch that」可以丢掉一段。
- 不要口头打板或自言自语备注（它们是语音，会被留下）；改用拍手或竖手指。列表就按列表念，工具名大声说出来（logo 来自名字），钱说全称（「一千美元一个月」，永远不说「1K」），图示该出现的地方用手指一下，笑话之后留停顿，一个段落收在它的结束语上。
- 双文件教程：脸和屏幕同时录，都带麦克风，拍一次手，文件主名相同。

## 脚本（`scripts/`）

| 脚本 | 做什么 | 选项 |
|---|---|---|
| `ingest.py` | 探测、排序并拼接多段原始素材；`ingest.json` 把合成时间映射回（片段, 时间） | `--raw --out [--concat] [--order A,B] [--only A,B] [--name]` |
| `transcribe-api.py` | VoiceMagic ASR：音频 → 词级 JSON（内部转 MP3 再调 MCP） | `--audio --out [--language zh] [--engine auto] [--mcp-url] [--from-json] [--dry-run]` |
| `retranscribe-holes.py` | 转录被幻觉盖住时的修复：按电平判词，重转「有声但无词」的区间、删掉压在静音上的幻觉词、`--head-until` 整段重转开头 | `--audio --transcript [--head-until T] [--thr 800] [--frac 0.15] [--out] [--dry-run]`；改完从 paper-cut 重跑 |
| `sync-tracks.py` | 用音频互相关算脸文件与屏幕文件的时间偏移 | `--a cam --b screen [--write-aligned DIR] [--window 180]` |
| `paper-cut.py` | 一段原始 take 里该删什么：重说段、「cut that」、重拍（留最后一遍）、短起头、长停顿 | `--transcript --duration --out-dir --speech`；写出 `cut-list.json` + `PAPER-CUT.md` |
| `hand-cut.py` | 从你指定保留的句子重建 `cut-list.json` | `--keep A-B`（保留首词与末词的起点；`A-B!` 整段保留）`--transcript --speech --duration --out-dir` |
| `tighten-cut.py` | 按声音收紧引导头、尾巴和内部停顿 | `--audio --cut-list --out [--lead 0.07] [--tail 0.11] [--maxgap 0.30]` |
| `sliver.py` | edge-audit 放过去的东西：只有呼吸的段、带着被删词余音的头、漏进下词起音的尾巴、40 ms 以内的边缘 | `--cut-list --audio [--fix]` |
| `edge-audit.py` | 每个剪切边缘按声音检查：在声音中间开始/结束、重说段碎片 | `--audio --cut-list --transcript [--keeps FILE] [--fix] [--threshold 300]` |
| `apply-cut.py` | 一次帧精确重编码进 `public/input-video.mp4` + `cut-map.json`（每个跳剪） | `--input --cut-list --out [--fps 30] [--crf 16]`；长片自动分批编码再拼（滤镜图超约 64KB 会被命令行截断，ffmpeg 9 又移除了 `-filter_complex_script`） |
| `dead-air.py` | 平剪里句尾超过 0.40 秒（其他位置 0.45 秒）的每个停顿，按声音判定 | `W [--plan] [--keep T] [--max 0.45] [--max-sentence 0.40] [--target 0.30]` |
| `patch-cut.py` | 对剪切清单的小修 | `--cut-list` 配 `--add A-B`、`--drop T` 或 `--drop-flat A-B`（平剪时间，经 `cut-map.json` 映射回去） |
| `stutter-scan.py` | 对平剪转录做词级结巴与重拍二审 | `--transcript --out-dir` |
| `cutlist-to-edl.py` | 把剪切清单转成 EDL，供并排审查页用（`node build-edl-review.mjs`） | `--cut-list --out` |
| `phrase-times.py` | 某句话在第几秒说（首词起点、末词终点） | `--transcript "phrase" ... [--after T]` |
| `compose.py` | `storyboard.json` → `public/index.html` | `--spec --out [--shared DIR]` |
| `beat-check.py` | 每个带锚句的元素在它的词前 0.60 秒到后 0.10 秒之间入场；未锚定的卡片和过期转录都算失败 | `--index --transcript [--suggest] [--allow-stale] [--video]` |
| `snap-beats.py` | 每个节拍、节拍内每个状态各截一张图，拼进 `snaps/sheet.png` | `--project [--at T ...]` |
| `gap-scan.py` | 长视频覆盖检查：既无叠层也无运镜的空档；每 90 秒密度 | `--index [--early 15] [--body 20] [--max 30]` |
| `storyboard-md.py` | 从一份或多份分镜生成交付用 `STORYBOARD.md` | `--title --project dir:slug:title --out [--note] [--concern]` |
| `broll-conform.py` | 素材片段、生成片段或静帧 → 切出镜头（30 fps、无音轨、每 15 帧一个关键帧、BT.709）+ 三格缩略图 + 可粘贴的节拍 | `--in --out [--start] [--dur] [--4k] [--grade] [--push 1.08] [--vf FILTERS]` |
| `window-patch.py` | 只覆盖 [T0, T1] 的可渲副本，用于长渲染内部修补 | `--public --t0 --t1 --out` |
| `verify-render.py` | 检查渲染出来的文件：黑帧、尺寸、BT.709 标签、码率、时长、音画、削字 | `--render [--index] [--res] [--words --kept] [--out]`；FAIL 则退出码 1 |
| `check-fcpxml.py` | 交付前的 FCPXML 预检：asset 时间码、资产超报、帧格、结构、子元素顺序、spine 连续性 | `X.fcpxml [--no-probe] [--fps 24]`；有问题退出码 1 |
| `assemble.py` | `assembly.json` → 一个 -14 LUFS 的 4K 母版 + `ASSEMBLY.md` + `chapters.txt` | `--manifest --out [--gpu] [--keep-work]` |
| `screen-activity.py` | 录屏画面随时间的变化量（`activity.json`） | `--video --out [--fps 2]` |
| `teardown.py` | 测量任意视频；精确统计分镜；对比报告 | `--video` / `--storyboard` / `--compare`、`--out [--transcript] [--every 2]` |

`formats/claude_chat.py` 是 AI 聊天窗口（format 13b）。

## 剪切阶段（原始素材 → 平剪）

```bash
mkdir -p "$W/raw" "$W/public" && cp "<card or folder>/<clip>.MP4" "$W/raw/"     # eject the card only after the copy is confirmed
ffmpeg -y -v error -i "$W/raw/<clip>.MP4" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$W/audio-raw.wav"
python3 "$SK/scripts/transcribe-api.py" --audio "$W/audio-raw.wav" --out "$W/transcript-raw.json"
auto-editor "$W/raw/<clip>.MP4" --edit audio:-30dB --margin 0.12s,0.35s --export v1 -o "$W/speech.v1"   # speech chunks by the audio
python3 "$SK/scripts/paper-cut.py" --transcript "$W/transcript-raw.json" --duration <seconds> --out-dir "$W" --speech "$W/speech.v1"
#   read PAPER-CUT.md; fix misreads with hand-cut.py (it rewrites cut-list.json)
python3 "$SK/scripts/tighten-cut.py" --audio "$W/audio-raw.wav" --cut-list "$W/cut-list.json" --out "$W/cut-list.json"
python3 "$SK/scripts/sliver.py" --cut-list "$W/cut-list.json" --audio "$W/audio-raw.wav" --fix
python3 "$SK/scripts/edge-audit.py" --audio "$W/audio-raw.wav" --cut-list "$W/cut-list.json" --transcript "$W/transcript-raw.json" --fix
python3 "$SK/scripts/edge-audit.py" --audio "$W/audio-raw.wav" --cut-list "$W/cut-list.json" --transcript "$W/transcript-raw.json"  # 0 issues
python3 "$SK/scripts/apply-cut.py" --input "$W/raw/<clip>.MP4" --cut-list "$W/cut-list.json" --out "$W/public/input-video.mp4"
ffmpeg -y -v error -i "$W/public/input-video.mp4" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$W/audio.wav"
python3 "$SK/scripts/transcribe-api.py" --audio "$W/audio.wav" --out "$W/transcript.json"   # flat-cut time
python3 "$SK/scripts/dead-air.py" "$W" --plan
#   each proposed range: patch-cut.py --cut-list "$W/cut-list.json" --drop-flat A-B, then edge-audit to 0 issues,
#   apply-cut, re-transcribe, and dead-air again until it prints 0 pauses
```

每段素材的固定顺序：paper cut → 手工修正 → tighten-cut → sliver → edge-audit 到 0 → apply-cut → 重新转录 → dead-air → patch-cut `--drop-flat` → edge-audit → apply-cut → 重新转录 → dead-air 打印 0。`<seconds>` 来自 `ffprobe -v error -show_entries format=duration -of csv=p=0 <clip>`。edge-audit 的 `--keeps FILE` 装你 hand-cut 的 `--keep A-B` 参数；普通 paper cut 之后不用带。

**paper-cut.py** 留每句话的**最后一遍**，按声音剪掉句内的重说段，丢掉同一节拍的其他遍，认「cut that / scratch that / let me redo / start over / take two」，以及**整句就是**「重来 / 再来一遍 / 这一遍不要 / 这段不要 / 作废」这类短标记（标记句和它前一句一起删）。句子里只是提到「重录」不算标记。丢掉短起头，修剪长停顿。只多了一个开头语气词（"So, ..."）的后一遍，输给干净的前一遍。**「又 / 再」夹在重复的两字之间不是口吃：**「一 遍 又 一 遍」整句留下；紧挨着的「一 遍 一 遍」仍当 restart，留后面那遍。

**它会看走眼的地方（用 hand-cut.py 修）：** 列表被当成重说段（「candles, soap, t-shirts」）；口头打板；带错数字的重拍；一句话连着重说很多次没有停顿（ASR 会把各遍并成一句，paper cut 会留下碎片：用 `--keep` 留最后那遍干净的）；同一短语说两次但结尾不同（"is able to find the fact, is able to find the screenshot" 是重说段：留第二遍）。hand-cut 会保留没有停顿的口头重说段，所以每次 apply 之后要扫一遍平剪转录：3–4 个词的同一短语在 7 秒内出现两次的，把真的重说删掉。

**边缘：**
- **句首信 ASR，句尾信声音。** ASR 会把最后一个词拉长进停顿（有一读拉出 8.8 秒），所以静音永远不能从词间隙推断。它还会在停顿后把短语起点标早最多 0.4 秒，这就是「气口太大」的来源：tighten-cut 曾把一刀从 3:12 收到 3:02，一个词都没丢。
- **每次都用声音审计每个边缘。** 被删 take 漏出的一丝碎音能藏在转录里，放出来却是 "right. [ght] A couple hours ago"。句头要从第一个保留词向后退到安静间隙（向前搜会削词）；新文件的接缝同样检查。
- **死气口：** 句尾不超过 0.40 秒、其他位置不超过 0.45 秒；`--plan` 把每个气口压到 0.30 秒，两个新边缘都落在环境底噪上，`--keep T` 保住有意留的节拍。每个段落、每个平剪都要跑。
- **句尾最后一个词前的低谷里下刀会把那个词删掉，** 而 edge-audit 放它过。每次 apply 之后，把每个保留段的末词和平剪新转录比对；下一个词紧接着来时，要在词边界穿过语音下刀，用耳朵和转录双重检查接缝。
- **有意留的气：** 用你自己的环境底噪段（`"room_tone": true`，一段长停顿里最安静的 0.5 秒），绝不用数字静音，画面用全屏切出盖住。
- **超过约 3 分钟的原始素材：** ASR 可能整句漏掉。按 auto-editor 静音切成约 25 秒的窗口转录，每个窗口的词时间加上窗口起点偏移，再合并。

**apply-cut.py** 做一次帧精确重编码（trim/atrim + concat，每个接缝 20 ms 音频淡化，CRF 16，每 30 帧一个关键帧，30 fps，BT.709）直接进 `public/input-video.mp4`，每条边缘对齐到源帧网格（不对齐的话，24 段下来画面会比声音漂后 4 帧）。输出对照 `cut-map.json` 检查（时长差一帧以内，音画差 0.12 秒以内）；出现 DRIFT 行就不要装扮那个文件。`cut-map.json` 列出每个跳剪：切出镜头放在这些剪切点上，其余剪切点最多装扮一两个。

- **VFR 录屏是 DRIFT 的头号来源：** 屏幕录制常是变帧率（标称 60、实际 ~54 fps），帧网格对不上，输出时长和 cut-map 差出两三帧。动刀前先把 take 重编码成 30 fps CFR（流水线第 2 步的参数：`-r 30`、CRF 16、密集关键帧），DRIFT 即消失。留一个奇数帧的保留段也会 DRIFT（60→30 折不整）：段尾收进静音里一帧就好。

## 流水线（平剪 → 4K MP4）

```bash
VIDEO="/path/to/flat-cut.mp4"; mkdir -p "$W/public" "$W/snaps"
# 1. Probe + 16 kHz mono audio, then transcribe locally
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,color_transfer \
  -show_entries format=duration -of json "$VIDEO" > "$W/metadata.json"
ffmpeg -y -v error -i "$VIDEO" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$W/audio.wav"
python3 "$SK/scripts/transcribe-api.py" --audio "$W/audio.wav" --out "$W/transcript.json"
# 2. Re-encode at the SOURCE resolution with dense keyframes, or the render freezes on seek (the Cut stage did this already)
ffmpeg -y -v error -i "$VIDEO" -map 0:v:0 -map 0:a:0 -r 30 -c:v libx264 -crf 16 -preset fast -g 30 -keyint_min 30 \
  -pix_fmt yuv420p -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
  -movflags +faststart -c:a aac -b:a 256k -ar 48000 "$W/public/input-video.mp4"
# 3. Only for text behind you: the subject matte
npx hyperframes remove-background "$W/public/input-video.mp4" -o "$W/public/subject-matte.webm" --quality best
# 4. Storyboard → compose → checks → snapshots (Checkpoint B: read the sheet before rendering)
python3 "$SK/scripts/compose.py" --spec "$W/storyboard.json" --out "$W/public" --shared videos/_shared
npx hyperframes check "$W/public"
python3 "$SK/scripts/beat-check.py" --index "$W/public/index.html" --transcript "$W/transcript.json"
python3 "$SK/scripts/snap-beats.py" --project "$W"
# 5. Render 4K: the 1920x1080 composition renders at 2x. --gpu ignores CRF, so give the bitrate (45M = YouTube's 2160p
#    figure). About a minute per 30 s on a recent Mac; without a hardware encoder, drop --gpu.
PRODUCER_BROWSER_GPU_MODE=hardware NODE_OPTIONS=--max-old-space-size=8192 \
  npx hyperframes render "$W/public" --resolution 4k --video-bitrate 45M --gpu --workers 4 -o "$W/output-4k-raw.mp4"
# 6. Full BT.709 tags (the render leaves them "unknown" and QuickTime shows faces darker and redder). Lossless.
ffmpeg -y -v error -i "$W/output-4k-raw.mp4" -c copy -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -color_range tv -movflags +write_colr+faststart "$W/output-4k.mp4"
# 7. Check the FILE (exit 1 = do not deliver), then deliver
python3 "$SK/scripts/verify-render.py" --render "$W/output-4k.mp4" --index "$W/public/index.html"
mkdir -p "$HOME/Movies/YouTube Renders/<project>" && cp "$W/output-4k.mp4" "$HOME/Movies/YouTube Renders/<project>/<project>-4k.mp4"
```

**渲染前把每个卡片时刻都截图看一遍**（截图是秒级，渲染是分钟级），读 PNG；绝不假设。合成器做不出来的东西放进 `raw_html` / `raw_js`，或用下面的骨架手工搭页（手工搭页沿用合成器同一套 `font-family` 与 `:root` 颜色）。

## 合成骨架

```html
<div id="stage" data-composition-id="..." data-start="0" data-duration="D"
     data-fps="30" data-width="1920" data-height="1080">
  <div class="video-wrapper" id="video-wrap">     <!-- push-over moves (format 3b) -->
    <div id="video-zoom">                          <!-- the camera -->
      <video id="bg-video" src="input-video.mp4" playsinline data-has-audio="true"
             data-start="0" data-duration="D" data-track-index="1"></video>
      <div id="behind-layer"> ...text behind you... </div>
      <video id="fg-matte" src="subject-matte.webm" playsinline muted
             data-start="0" data-duration="D" data-track-index="2"></video>
    </div>
  </div>
  <div class="card-host clip" id="host-card-01" data-card-id="card-01" data-anchor="spoken phrase"
       data-start="..." data-duration="..." data-track-index="3"
       style="left:0;top:0;width:1920px;height:1080px;visibility:hidden;opacity:0;">...</div>
</div>
```

两层嵌套包装是故意的：`#video-wrap` 承载推移镜头（format 3b），`#video-zoom` 承载相机；两个动作放同一元素上会冲突、过不了 QA。必须跟相机走的东西（画面、身后的字、遮罩）放在 `#video-zoom` 里面；前置卡片留在外面，永远不缩放。

## 合成器（`compose.py`）与 `storyboard.json`

分镜既是审查工件**也是**唯一事实来源：给卡片重新卡点就是改一个数字再重建。

```json
{"id": "hook", "duration": 38.0, "video": "input-video.mp4", "origin": "52% 0%",
 "tag": {"n": 1, "of": 5, "label": "Thumbnails", "in": 0.2, "out": 5.3, "pos": "tr", "anchor": "-"},
 "beats": [
   {"type": "line", "id": "l1", "text": "You clicked on a thumbnail", "em": [4], "color": "cyan", "in": 8.5, "out": 11.6, "anchor": "clicked on a thumbnail"},
   {"type": "logo", "id": "yt", "src": "img/youtube.svg", "in": 11.85, "out": 14.9, "pop": 11.92, "pos": "tl", "anchor": "YouTube"},
   {"type": "list", "id": "ls", "pos": "tr", "in": 15.6, "out": 20.4, "anchor": "candles",
    "items": [["Candles", 15.9], ["Soap", 17.12, "a bar of soap"], ["T-shirts", 18.3]]}],
 "camera": [["creep", 0.3, 5.4, 1.10], ["set", 9.698, 1.0], ["punch", 18.3, 1.18], ["release", 21.0, 0.5]],
 "loops": [{"question": "Why that thumbnail?", "planted": 2.1, "payoff": 31.0}], "raw_html": "", "raw_js": ""}
```

| 键 | 是什么 |
|---|---|
| `id`、`duration`、`video` | 合成 id、时长秒数（平剪）、`public/` 里的画面文件 |
| `origin` | 相机锚点，永远在顶边：`"52% 0%"` 居中，人坐左侧用 `"38% 0%"` |
| `tag` / `tags` | 章节或进度标签；`tags` 是列表（长视频：每个段落回来一次） |
| `glass_bg`、`glass_bg_cut` | 玻璃着色落在什么上（默认浅色 `rgba(255,255,255,0.18)`；亮房间用 `"rgba(17,17,17,0.55)"`），以及全屏场景里落在色洗上的着色（默认同 `glass_bg`；保持浅色） |
| `loops`、`raw_html`、`raw_js` | 钩子的开放悬念（检查点 B 检查，合成器忽略它）；手写格式 |

每个节拍都有 `type`、`id`、`in`、`out` 和一个 `anchor`（口头短语；`"-"` 标记有意不锚定的节拍，写作 `data-unanchored`）。列表与要点项自带时间和锚句（`["Soap", 7.12, "a bar of soap"]`；默认用文字，`"-"` = 没说出口），这样 beat-check 能验证每一项。全屏节拍可加 `"transition": "zoomthrough"`（切前 0.22 秒画面推进并虚化）或 `"punch"`（返回时 2 帧 pop），以及可选的 `label`（88 px 场景标题字）。
- **`line` 逐词跟口播（FCP 叠层字幕）：** 除默认 stagger 入场外，可给 `"times": [t0, t1, …]`（秒，**相对本 MOV 起点**，与 `text` 按空格分词一一对应）；compose 按词表时刻单独 `lowerIn`，用于口播原文字幕而不是占位短句。改剪辑后必须用**最终转录**重算 `times`。
- **FCP 专用透明舞台：** `storyboard.json` 加 `"raw_html": "<style>html,body,#stage{background:transparent!important}#video-wrap{display:none!important}</style>"`（`#video-wrap` 藏起来，避免黑底占位视频进 ProRes）；`camera` 可省略。配图示例用 `imagecard`（37b），底行用带 `times` 的 `line`。

| 运镜指令 | 做什么 |
|---|---|
| `["set", t, scale]` | 跳到某个缩放；`cut-map.json` 里每个跳剪处放 `["set", t, 1.0]`（绝不把缩放带过剪切点） |
| `["creep", t0, t1, scale]` | 一个想法讲完前的缓慢推进，`power1.inOut` |
| `["punch", t, scale]` | 推近，0.32 秒 `power2.out` |
| `["release", t, dur]` / `["reveal", t]` | 回到 1.0 / 拉远揭示，卡片入场时 1.10 → 1.00 |

- 位置：`tl` = 左 70、上 96（避开桌面麦）；`tr` = 右 70、上 96。底行 100 px 字号约容 33 字（更长就拆行）；超过约 18 字的列表项需要在节拍上给 `"width"` 和 `"size"`。
- **卡片里文字一多就拆成消息气泡：** 单条超过约 12 字、或一行挤不下的，别硬塞进卡片——拆成 `chat` 消息气泡，一条一句完整的话；**每个气泡都带进场和出场动画**（`messages` 用 dict 项给 `at` 和 `out`），气泡不许凭空消失或整组一起没。
- 合成器只有两个声音：`sfx/pop.mp3`（logo pop，0.34）和 `sfx/typing.mp3`（搜索打字，0.22），从你的 `--shared` 文件夹拷入；logo 和图片放在它的 `img/` 里。
- 每次构建会打印截图时刻、每种格式的计数，同一种手法连着出现两次时打印 WARN（底行除外）。修掉它；绝不带着它交付。
- 行内图标：doc browser bolt chat money check user code video mail gear chart search shield lock robot globe cloud key alert folder eye bank chip。

**AI 聊天窗口（13b）是一个共享函数：** `formats/claude_chat.py` 的 `chat_css()` + `chat_scene(p, prompt, t_in, t_out, type_t0, type_t1, send, think_end, head, items, ..., attachments=[...], att_times=[...])`，返回 `(html, js_lines)`：图片缩略图落进输入框，prompt 随你的口播打进去，消息发出，回答行落在你说的词上。每个词是一个 nowrap span、词间是真实空格、输入框从底部往上长，所以任何 prompt 都会正常换行（不换行空格曾经让 prompt 冲出输入框）。从构建脚本调用它；绝不手搓。

## 格式库

选格式、核对像素、看已否决清单：读同目录 [`FORMATS.md`](FORMATS.md)。写 `storyboard.json` 之前读它。留在这里的硬规则：

- 同一种手法绝不连用两次（底行除外）。`compose.py` 打出 WARN 就改。
- 「合成器类型」里的反引号名字必须在 `compose.py` 里；「手工搭建」「尚未构建」没有 type，不要发明。表和分支由 `scripts/tests/test_format_table.py` 锁在 `FORMATS.md`。
- 卡片文字超过约 12 字就拆成 `chat` 气泡，每条自带进出场。
- FCP 透明叠层只用 `pills` / `chip` / `list` / `popout` / `tag` / `imagecard` / `line`。全屏色洗格式的禁令和接线在 [`FCP.md`](FCP.md)。

## 在转录里找讲解点

图解（6、7、8、27、30）是**找出来的，不是你要求的**。扫转录找枚举（「第一/第二/第三」）、许诺形状的句子（「它的原理是」「有三种」）、链式因果（「然后」「这就带来」）、阶段词汇（「漏斗顶部」「冷/热」）和清单里点名的工具（它们变成 chip）。

| 段落说…… | 格式 |
|---|---|
| A 然后 B 然后 C，每个是不同动作 | 6 流程图（快节奏用 27） |
| 只有 A 才有 B：一段攀登 | 7 台阶 |
| 多变少、少变付费 | 8 漏斗 |
| 一样变几样 | 30 流动路径 |
| 以前是 X，现在是 Y | 20b 前后对比擦除 |

节点标题用你的原话 2–4 个词；细节行是你自己观点的收紧版，绝不编造说法、数字或步骤（「大约七天」就保持「七天」）；每个节拍是引出该步骤那句的词起点；时长 = 最后一个节拍 + 约 8 秒；不说结果，不落兑现横幅。**搭建前先提案**（段落、格式、步骤标签，一条短消息说清）：一张图解占 30–40 秒画面，值得确认一轮。

## 读素材，不只是读转录

1. 找镜头切换点：`ffmpeg -v error -i in.mp4 -vf "select='gt(scene,0.12)',metadata=print:file=-" -f null -`。
2. 按镜头放置并测量脸部安全区；叠层放在你的对面。已测过的构图（把你的加进来）：
   - 你坐左侧：卡片待在 x 1000 以右。
   - 你坐中、桌前有麦（麦头约 x 500–800、y 330–500）：卡片待在 x 660 以左；`tl` 避开麦；一张 left 62 的 840 px 卡片到了 x 902，盖住了脸。
   - 特写、麦在右下：你的脸占 x 750–1150，胸在左下。卡片放右上（left 1220、宽 640 px）或左上（left 62、top 80、宽约 720 px 以内、y 220 以上）；左下什么都不放。
3. **卡片绝不盖你的脸。** 文案塞不进安全区时，改成底行而不是缩小卡片；在快照里对照你的头发检查卡片边缘。
4. 按镜头重新锚定相机（坐左侧 `38% 0%`，居中 `52% 0%`），并在每个剪切点前释放完所有运镜。
5. **画面已经说过的，不要再说一遍。** 一个大数字曾经重复了一个举到镜头前的秒表，一只失焦的手还从遮罩里穿掉了它的首位数字。叠层撤了。

## 长视频章法

- **一个持久的世界。** 长视频是相机穿行的一个空间，不是一摞互不相干的卡片。先定空间语法（左到右 = 通向结果，上 = 人物，下 = 系统）。
- **章节道具在每个边界回来**（进度标签、插槽墙或卡组）；开放悬念在钩子里就埋成看得见的未完成（空插槽、虚影堆叠），在画面上填掉，绝不说「我们待会儿回来讲」。
- **同一时刻只有一个元素全亮。** 画出来的就留下，压暗但可读（上下文 .56、用过 .33、标签亮度永不低于 90）；收掉的道具退到 0 而不是 0.3。每段落约 20 个屏上词，不出句子；一切在 2 秒内读完。
- **节奏：** 前 90 秒不允许超过 15 秒、之后 20 秒、任何时候 30 秒的无叠层无运镜空档（`gap-scan.py`）；每 90 秒约 7 个叠层 + 7 个运镜。一张卡片跨一个话题（中途长出一项）胜过五次闪现。比锚词提前 0.15–0.25 秒入场；绝不把段落均分。
- **一个手势，不是两个动作。** 同一主体上连着两个动作看着像故障：合成一个动作、一个对称缓动（`power2.inOut`）。前置缓动（`power3.out`）在可见素材上是先冲后爬。
- **全屏图形当一个画布上的相机来动：** 推近你点名的部分，拉远展示它连着什么，游走到下一处，一次一个动作（`world`、`deck`）。
- **每个元素每个时间窗只有一个 opacity 拥有者：** 同一元素 opacity 上两条 tween 会在母版里频闪。淡入子元素或包装层，二选一；让 lint 的 `overlapping_gsap_tweens` 警告拦住构建。
- **在声学层面审计音频**（停顿里的数字零电平：用环境底噪填上；接缝处的电平断崖）并逐帧校验运动（见「验证与交付」）：每道闸都过了，观众仍可能看到卡帧。
- **分段合成**（钩子、每个开场、每个主体段落）再用 `assemble.py` 拼：每段都待在重叠层预算内，一条意见只花一段的渲染。

**长视频的门规：**
- **你的脸不是默认背景。** 口播段落争取 40% 以上是全屏品牌色洗、画面上只有动画。抽象讲解（一个工具能干什么：文件、程序、输出文件夹）做成 `world` 全屏场景，绝不做成盖在你脸上的卡片。
- **花样胜过清单。** 长视频正文不用列表/要点面板：每个清单都变成手法（短语旁的药丸、`world` 循环、每个数字一个手法、流水线）。
- **每个点名的人或职业都要配上那个人的画面：** 你说完这个职业之后、工具或答案揭晓之前，接 2.6–3.4 秒全屏素材 `clip`；一两处你的 AI 镜头用在笑点落下的地方。
- **逐项点亮的板子初始是糊的：** 每张卡只露图标、模糊，到各自的词时变清晰。
- **变化按你讲的顺序演：** 「一开始是深蓝，我不喜欢」= 先深蓝，在说到「不喜欢」时切换。
- **点名的 App 要给设计出来的窗口**（13b 的空初始态），不是你真实软件的截图；**点名的网站要给真实页面**（浏览器窗口里的 2x 截图），一直停到你讲过去。
- **画面上每次点击都配轻响**（0.28）落在光标触底的那一帧；静音的点击看着像失误。
- **笑点里点名的东西给真实图片**（说「薯片」，你两边就坐两袋真薯片）：产品图来自 Open Food Facts（`cgi/search.pl?...&json=1`，把 `.400.jpg` 换成 `.full.jpg`；CC BY-SA，要署名），用 `npx hyperframes remove-background photo.jpg -o photo-cut.png` 抠出（先给铺满画面的照片 20% 留白），裁到 alpha 边界，根层级 `<img class="clip">` 放你两侧，随词带一次 pop 入场。

## 运镜

**锚点永远在顶部**（居中 `52% 0%`，坐左侧 `38% 0%`）：居中锚点的缩放会裁掉你的头。

| 动作 | 数值 |
|---|---|
| 强调推近（数字、承诺、点睛句） | 118%–125%，0.30–0.35 秒，`power2.out` |
| 一个想法讲完前的缓慢推进 | 5–10 秒内 110%–112%，`power1.inOut`；下一个剪切点释放 |
| 拉远揭示 | 卡片入场时 0.5 秒 110% → 100% |
| 归位 | 每个镜头切换回到 100%；绝不把缩放带过剪切点 |
| 预算 | 40 秒钩子 3–5 个动作；长视频每 90 秒约 7 个 |
| 上限 | 1080p 素材：最多 112%；4K：150% 随便用，刻意冲近才用 200% |

- 主打文字要补偿缩放：scale 1.12、origin 52% 时，左锚元素会左移约 105 px。
- **跳剪默认保持裸切。** 只在能量变化时装扮一处（转折、笑点落地、段落开始）：快速推近（0.12 秒 scale 1.04 → 1.00）、穿焦缩放（放大的同时 10 px 模糊出场）或微甩（12% x 位移带模糊，0.25 秒）。40 秒钩子一到两处，长视频每 10 秒最多一处，绝不断在词中间。长段纯口播时在跳剪之间切换构图（1.0 / 1.09），让每个看起来像推近而不是颠簸。
- **每个归位都落在跳切帧上。** cut-map 的时间不按帧对齐：10.34 的 `set` 落在 10.367 的帧上，而素材在 10.333 已经跳了——一刀变两刀。从低清解码测量一次跳切帧（每个剪切点 ±4 帧内的最大帧差），在 `jump/30 - 0.003` 处 set。

## 节奏

- 钩子：37 秒约 6 个叠层时刻（每分钟约 10 个叠层 + 4.5–7.5 个运镜）。卡片停留 3–7 秒；超过 7 秒需要内部运动（条目错峰、数字滚动）。入场 0.4 秒 `power2.out`，出场 0.35 秒 `power2.in`；不弹跳、不 3D 翻转，模糊永远不动画。同一时刻一个主打元素（点睛药丸可以和 logo 卡同框）。
- **钩子第一帧就要有动作。** 一个好用的范式：你自己的四段作品短视频装在玻璃卡里围在你身边（440x248，x 36 / 1444、y 128 / 400），从 0.35 秒起每 0.12 秒进一个，同时全在播，5.8 秒前出完；标题行在开场约 1 秒后落下，不压第 0 帧。这些片段是根层级静音视频。
- **反应类钩子（新闻、发布）：** 钩子全程都在动；你点名的一切在词出现的那一刻就在画面上（片段提前约 0.1 秒开播，让揭晓正好砸在词上）。报数量给咔咔蒙太奇（「超过 20 次发布」：11 张卡、每约 0.3 秒一张、一个小计数器）。事件切出：每段只用一个干净镜头（官方流会在镜头中间切机位），逐帧检查。帖子 1560 px 宽（1040 在手机上看不清），亮场景用深玻璃，大数字不压脸，标签在下一个全屏切出前撤掉。

## 声音

**默认静音。声音要挣到自己的位置：** 画面上什么东西会发出这个声音？没有任何东西物理上会响，就没有声音。一个钩子一到两个（38 秒钩子里放了八个被评为「太吵了」）。

| 声音 | 允许用在 | 音量 | 绝不用在 |
|---|---|---|---|
| 打字 | 真实打字、prompt 窗口或搜索输入，时长严格等于打字时长 | 0.22 | 任何不是键盘的东西 |
| Pop | logo 出现（4a、21） | 0.34 | 文案：不是点睛药丸、不是字幕 |
| Click | 画面上每次光标点击 | 0.28 | 任何没有光标的地方 |
| Ping / 通知音 | 手机通知，字面意义上的 | 随意 | 数字落地、揭晓、强调 |
| Cha-ching | 金钱计数落地 | 0.07 | 任何比耳语响的地方 |
| Whoosh / 嗖 | 没有任何已确认用途 | | **任何文案**：文字靠动作到场，绝不靠一扫（最常见的错误） |

**接线：** `<audio id="sfx-typing" src="sfx/typing.mp3" data-start="8.22" data-duration="1.50" data-track-index="10" data-volume="0.22"></audio>` 作为合成根的直接子元素，绝不放进 wrapper。每个 `<audio>` 都要有 `id`，否则渲染里是哑的而预览正常（`check` 报 `media_missing_id`）。重叠的声音用不同的 `data-track-index`；任何会超出 `data-duration` 的声音要裁短。

**找声音：** Epidemic Sound 连接器（`SearchSoundEffects` 按时长过滤、`DownloadSoundEffect`；音乐用 `SearchRecordings`、`DownloadRecording` 带分轨、`EditRecording` 精确到 `targetDurationMs`），先查已附加的；或免费 HyperFrames 音效库（typing、key-press、click、click-soft、pop、ping、notification、chime 等）。

**对齐可听的峰，不是文件开头：** 把瞬态前的静音裁掉（`ffmpeg -af silenceremove=start_periods=1:start_threshold=-40dB`），让峰落在它的成因两帧以内。

**混音前先归一化：** 库文件电平差可达 10 倍，同一个 `data-volume` 会让一些声音消失。每个文件峰值归一到 -3 dBFS（用 `ffmpeg -i in.mp3 -af volumedetect -f null -` 读 `max_volume`，然后 `-af "volume=<-3 减 max_volume>dB"`），`data-volume` 只管混音配比。持续音需要的比瞬态低。

**验证渲染里有每个声音：** 把渲染和未动的素材解码成 16 kHz 单声道，在语音窗上增益对齐，相减，读每个声音窗（对齐到文件自身峰）里差值的 RMS，对照两个控制窗（pop 应约 650 对约 30）。绝不要和上一版渲染对比：两次 AAC 编码的差异足以盖住一个轻音效。

**音乐：** 钩子下面放一条有点紧张感的轨（约 18 秒），其余部分铺平静的 lo-fi 床，在你的声音下闪避约 16 dB（钩子）和 19 dB（正文），然后 -1 dB 限幅，前提是语音已在 -14 LUFS（`assemble.py` 会做电平）。最简单的床是 `assemble.py` 的 `music` 键；在成片母版上压闪避床（同时留一个无音乐孪生版）：

```bash
ffmpeg -i master.mp4 -stream_loop -1 -i bed.mp3 -filter_complex \
 "[0:a]asplit=2[voice][sc];[1:a]volume=-16dB,afade=t=in:d=1[bed];[bed][sc]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[duck];[voice][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89[a]" \
 -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 256k -shortest master-music.mp4
```

## 给玻璃做动画（写任何入场之前读）

**绝不通过祖先的 `opacity` 淡入玻璃元素：** 只要任何祖先 opacity 低于 1，Chrome 就丢掉 `backdrop-filter`，整段淡入里磨砂面板都是缺的、最后才猛地出现。把宿主保持在 opacity 1，动玻璃本身的外观：

```js
tl.set('#host', { visibility:'visible', opacity:1 }, t);
tl.fromTo(glassSel,
  { backgroundColor:'rgba(255,255,255,0)', borderColor:'rgba(255,255,255,0)',
    boxShadow:'0 24px 80px rgba(0,0,0,0)', x:60 },
  { backgroundColor:'rgba(255,255,255,0.18)', borderColor:'rgba(255,255,255,0.58)',
    boxShadow:'0 24px 80px rgba(0,0,0,0.38)', x:0, duration:.42, ease:'power2.out' }, t);
tl.fromTo(contentSel, { opacity:0 }, { opacity:1, duration:.36 }, t + 0.04);   // text is safe to fade
```

模糊从第一帧就活着，但没有着色就看不见，所以整体读起来就是一次「面板、描边、文案一起到」的淡入；出场反着来。直接坐在玻璃元素里的文案要包一层内层 span 来淡。没有 backdrop-filter 的纯 opacity 淡入没问题（底行）。没到位的玻璃保持隐藏，否则会把画面糊掉。

## 白烧渲染的坑

**长渲染**
- **磁盘捕获先存每一帧：** 12 分钟 4K 要了约 714 GB 暂存。超过约 2 分钟，用单 worker 流式编码（`PRODUCER_STREAMING_ENCODE_MAX_DURATION_SECONDS=3600`、`--workers 1`；12 分钟 4K 约 35 分钟）。并行流式曾把素材涂黑一大段；`--low-memory-mode` 不是解法。
- **单会话长 4K 捕获可能卡死**在 Chrome 的截图调用里。超过约 5 分钟，分段渲染、每段一个新浏览器，保留 `--resume` 用于重试：`HF_SEGMENTED_CAPTURE=true HF_SEGMENT_FRAMES=1500 HF_SEGMENT_BROWSER_RECYCLE=1` 外加流式设置（8:53 的片子 30 分钟渲净）。
- **并行 worker 下素材变黑：** `--workers 1`，并对每次长渲染跑 `ffmpeg -i out.mp4 -vf "scale=192:-2,blackdetect=d=0.4:pix_th=0.08" -an -f null -`。
- **帧缓存会塞满临时目录**（一天 16 GB），在 `<tmpdir>/hyperframes-extract-cache-<uid>`：没有渲染在跑时删掉它，或用 `--frames-cache-dir` 挪走。组装前查磁盘余量（约 2 x 分钟数 x 0.34 GB）。失败运行留下的 `work-*` 文件夹要删；zsh 在空 glob 上会中止 `&&` 链（用 `work-*(N)`）。
- **长渲染上的一条意见花一次补丁，不是整片重渲：** `window-patch.py --public "$W/public" --t0 T0 --t1 T1 --out "$W/patch-a"`，用同样的参数渲染，然后盖到全片渲染上（`overlay` 加 `enable='between(t,T0,T1)'`）或帧精确拼接（12 ms 音频淡化）。窗口要在卡片宿主入场前开始；用首尾帧的 `psnr` 证明对齐（50 dB 以上 = 同一帧）。跨接缝保持的任何东西必须两侧静止。

**编码与文件**
- **`--gpu` 无视 CRF**（`--quality high --gpu` 在 4K 给出 14 Mb/s）：永远加 `--video-bitrate 45M`。
- **渲染会丢两个色彩标签：** 永远做 BT.709 重封装，否则人脸比相机原片偏红。
- **跳过 `assemble.py` 的下场：** 渲染保留相机电平（约 -25 LUFS）。先把人声对到 -14（一段的 `assembly.json` 就能做），再加音乐；用 `ebur128` 测文件。
- **渲染完成 ≠ 文件正确**（黑画面、丢标签、音频差一帧）：`verify-render.py` 抓这些，渲前快照抓不到。它 40 Mb/s 的下限在静止画面为主的片子上会误报（硬件编码器会打不到）；其他行都过的话，那就不是质量问题。

**合成**
- **每个带时间的元素都要 `class="clip"`**，否则它全程显示。素材上保留 `data-has-audio="true"`（`video_missing_muted` 是真问题），否则渲染没声音。
- **`input-video.mp4` 上的第二个 `<video>` 不出画：** 把那段剪成独立文件，给它高过 `.card-host`（10）的 `z-index`。**每个 `public/` 只有一个根合成：** 里面放备份会让音频翻倍。
- **GSAP 也要动的元素，style 里绝不写 CSS translate()、scale() 或 rotate()：** GSAP 会整段替换值，lint 直接失败。起始状态放 `tl.fromTo`；持久居中用单独的 CSS `translate` 属性。
- **数字滚动是挂在代理对象上、同一条时间线的一个 `onUpdate`；** 加载时把起始值写进去。
- **逐步变化的文字（打字、时钟）来自一条代理 tween，绝不用每步一个 `tl.set`，** 否则往回 seek 会留下残字：把 `{ n: 0 }` 用 `ease: 'none'` 补到长度，写 `slice(0, floor(n))`。这一类的检查方法：seek 过一个节拍、再 seek 回它内部，和全新 seek 对比。
- **重叠层有预算：** `composition_heavy_overlay_count_high` 统计每个 `filter: blur`、`radial-gradient` 和 `clip-path`，隐藏的也算；到了约 40 个，捕获前半段会涂黑（每个全屏色洗都算）。长视频分段合成；辉光优先用 `box-shadow`。
- **linter 会错两次：** 主体后面的 `text_occluded` 恰恰是目的，`text_not_painted` 会在 `background-clip:text` 上误报（它渲染正常）。重建 logo 框里两个文本块会触发 `content_overlap`（小词用 `::before` 画）；`width="1em"` 的 SVG 会渲成 16 px（给显式宽高）。

**字体、转录、快照**

- **字体：** 合成器根上 `font-family: ui-sans-serif, system-ui, sans-serif`（Mac 上通常是 San Francisco）。正文继承根字体，绝不用 CSS 变量当 `font-family`；子元素用 `font-family: inherit` 或 `font-weight`，避免单独写别的族名（曾有一整个场景渲成了 Times）。
- **快照文件名：** `snapshot --at 8.0` 写出 `frame-00-at-8s.png`（没有 ".0"），每次运行清空文件夹；按精确文件名拷贝（`snap-beats.py` 就是这么干的）。

## 寻找素材

- **工具 logo：** 品牌媒体资料包，或 `npx hyperframes capture <url>` 后从 `extracted/page.html` 里抠 `<svg>`（真矢量；当心 `fill="none"` 的路径和近黑色字标，深色板上做白色变体）。media-use skill 的 `scripts/resolve.mjs --type logo --intent "..." --project .` 是另一条路（`image`、`icon`、`bgm`、`sfx` 同理）。
- **你自己的录屏**是最强的切出：它们就是证据。**公有领域存档**做隐喻：NASA（`images-api.nasa.gov/search?q=...&media_type=video`，然后取资源清单里的 mp4）。
- **网站截图：** 显式请求 `/en` URL（裸域名可能按地理位置路由到别的语言）；Cloudflare 的「Just a moment...」页是暂态的，重试。绝不绕过机器人检测。
- **挡住机器人的页面：** 不要绕过。用真实浏览器打开页面（Claude 的浏览器工具），用 JavaScript 摘取事实（标题、日期、导航、logo `<svg>`、`@font-face` URL、主图媒体），在允许的范围内从它们的 CDN 取字体和图片，然后按真实的 1360 px 布局重建页面顶部，缩到 50% 放进 680 px 浏览器卡（先把面板调到 1360x765，用 `window.scrollTo` 滚动）。
- **拼接截图装不出滚动**（钉住的段落会重复）：一帧加漂移、滚动窗口里的整页截图（4c、4d），或你自己的录屏。
- **X 帖子：** 用 X 官方嵌入（`platform.twitter.com/embed/Tweet.html?id=<ID>&theme=light&dnt=true&lang=en`），无头 Chrome 设备缩放 6，对帖子的带边框父容器截图（3300 px 宽）。用 syndication JSON 证实文字（`cdn.syndication.twimg.com/tweet-result?id=<ID>&token=<T>`，T = `((ID/1e15)*Math.PI).toString(36).replace(/(0+|\.)/g,'')`）；帖子视频用 `yt-dlp` 下，做成 1.1 秒切出加账号药丸。未登录的 x.com 对无头 Chrome 回 403：绝不伪造 user agent 硬闯。
- **人物照片：** 直接找人要文件。**烧进字幕的素材：** 画面裁掉约 10%，顶部锚定。

## 素材 B-roll 路线

门派常规自动跑完（挑选、下载、清理、规格化）并把每个片段列进分镜。你想先过一遍候选清单的话，说一声并记在这里。

- **用在哪：** 每个你点名的人或职业，说完之后、工具或答案揭晓之前，接 2.5–3.5 秒全屏 `clip`（开场 1.5 秒也行）。
- **搜索**在小模型的分叉子代理里做：每个位置两个候选，带页面、许可、时长、分辨率、fps、体积、风险和可用秒段，写进 `$W/broll-shortlist.md`，不下载任何东西。没有下面的风险排除就用第一个。
- **许可：** Pexels 优先（YouTube 免费、无需署名、有 4K），然后 Coverr 和 Mixkit 的免费许可。绝不用 Mixkit 的 Restricted 许可、绝不选标注 AI 生成的片段、绝不碰付费档。
- **画面：** 真人、屏幕照亮的深色或情绪化房间、横屏、4K、无水印、没人看镜头、无可读的品牌 logo 或第三方 UI（认得出但读不出的编辑器没问题）。
- **下载**走 Pexels API（免费 key 放 `Authorization` 头；取 `video_files` 里 3840 宽那条）或页面下载按钮，进 `$W/broll/raw/`。
- **清理与规格化**写成每条视频一个脚本（`$W/broll/conform-stock.sh`，记录每个窗口）：`python3 "$SK/scripts/broll-conform.py" --4k --in "$W/broll/raw/<file>" --out "$W/public/broll/<job>.mp4" --start <s> --dur <slot + 1>`。可读内容用 `--vf "split[a][b];[b]crop=W:H:X:Y,boxblur=8[bb];[a][bb]overlay=X:Y"` 在源像素里糊掉（用 ffmpeg 的 `drawgrid` 找 X 和 Y）；裁切很难既去掉标签又不毁构图。
- **按实测清晰度选窗口**（有一个片段中途虚焦了）：640x360 灰度帧上每 0.5 秒的邻像素平均差；取最稳的高清晰段。渲染前每个位置先截图。

## AI B-roll 路线

用你选的图像服务和图生视频服务生成你的镜头。刻意收窄：这些镜头之所以成立，是因为人是讲述者、画面就是句子描述的场景。

- **主角是你，或者没人：** 绝不是另一个真人；路人是通用的、在背景里。画面呈现你描述的具体场景，2–5 秒，落在你的词上；观众三个词说不清它演的是什么，就剪掉。
- **绝不当证据：** 不做假仪表盘、假收入、假学员、假人群、假截图、假结果；证据是你真实的屏幕。
- 每分钟最多一个左右，绝不连着两个，每个都是带锚句的 `clip`。**上传时标注**（YouTube 的「Altered or synthetic content」：Yes）。每次生成都烧钱：报价并为每一跑拿到明确同意。

**链条：**
1. 先写镜头单，`$W/BROLL.md`：锚句、一行场景、着装（素材里那套）、运镜、时长。检查点 B 批准；之前什么也不生成。
2. 参考图：一套人脸包（视频光线下素墙前的 6–12 张：正面、四分之三、中性和微笑、一张你书桌的半身）、你空场景的照片、素材里抽两三帧（`ffmpeg -ss <t> -i "$W/public/input-video.mp4" -frames:v 1 ref-<n>.png`）。每个镜头用同一套参考，否则脸会漂。照片由你自己上传到服务；Claude 绝不用 shell 发它们。
3. 静帧，16:9，2K：「参考照片里的人，同样的脸和头发，穿着[着装]，在[具体地点][做一件事]，[时段]窗光，35mm 平视镜头，浅景深，自然皮肤质感，无文字、无 logo，16:9。」屏幕要么背对要么失焦：生成的屏幕会出假字。
4. 先检查静帧（脸、手、任何文字）再花钱生成动效：坏静帧重跑即可，坏视频是白烧。
5. 动效：图生视频，5–8 秒，关音频，提示词只写运镜和一个小动作（「缓慢推进，他打字，然后抬头看屏幕，自然动作，无剪切、无新人物」）。
6. `python3 "$SK/scripts/broll-conform.py" --in "$W/broll/raw/<shot>.mp4" --out "$W/public/broll/<shot>.mp4" --start 0.5 --dur 4 --grade`（`--start` 跳过模型的起手式，`--grade` 向你的素材靠拢），然后读它的缩略图。预算版：只用静帧，`--in <shot>.png --dur 4`，慢推（`--push 1.08`）。
7. 作为 `clip` 节拍落进分镜、对齐你的词，镜头带观点时加 `label` 或清单。

## 双文件教程（脸 + 屏幕）

教程用两个文件录：脸和屏幕同时录，都带麦克风，拍一次手对齐。`sync-tracks.py --a <face> --b <screen> --write-aligned "$W/aligned"` 对齐两条轨，对脸文件跑剪切阶段，屏幕做全屏 `clip` 切出。`screen-activity.py` 显示录屏哪儿变静止了（全脸候选）；用 `phrase-times.py` 把叠层锚到说出口的词上。

- **对完必须复核方向：** sync-tracks 会把「谁先开机」判反——`--write-aligned` 可能把该延后的那条裁了头。对齐产物再跑一遍 sync-tracks：偏移回 ≈0 才对；偏移翻倍（8.2 s 变 16.4 s）就是裁反了。真方向也可以用响度包络或波形互相关独立验证；修正动作是给晚开录的那条补头部静音（`ffmpeg` `adelay`）去贴早开录的那条，不是反过来。
- **录屏中途断掉续录（两段录屏 + 一条贯穿录音）：** 两个录屏各自对录音做同步（包络互相关，别信工具的方向）；声轨「听起来没声音」**先拉高音量再下结论**（RMS 0.0008 的音轨放大后相关系数 0.85——『全静音』判错过一次，语义锚定因此偏了 0.47 秒）。能互相关就绝不语义锚定；实在没有可听音轨才用「画面状态 ↔ 解说词语义」+ 时长对账（录音总长 = 各段之和 − 晚开 + 断点空隙 + 尾巴）收口。合成工作带时断点留黑色空隙，后半段才不漂；时间线上断点做成 `gap` 并标记，别硬拼——`gap` 允许挂连接孩子，**录音轨要一路铺过去**（用户开录的音频是全程连续的，断点下方也要有声）。

## 组装（一个母版）

```bash
python3 "$SK/scripts/assemble.py" --manifest "$W/assembly.json" \
  --out "$HOME/Movies/YouTube Renders/<project>/<project>-full-4k.mp4" --gpu
```

```json
{"project": "my-video", "width": 3840, "height": 2160, "fps": 30, "loudness": -14,
 "music": {"file": "bed.mp3", "db": -26, "fade": 2.0},
 "segments": [{"name": "Hook", "file": "~/Movies/YouTube Renders/my-video/hook-4k.mp4"},
              {"name": "1 · Thumbnails", "file": "intro-01-4k.mp4"},
              {"name": "1 · Tutorial", "file": "tutorial-01-4k.mp4", "trim": [0.0, 71.4], "chapter": false}]}
```

相对路径按清单文件所在目录解析；`trim` 是 [起点, 终点] 秒；`"chapter": false` 把某段从章节表里藏掉；`music` 可选（默认静音）；`"loudness": null` 保持电平不动。每段规格化一次（CRF 16，或 `--gpu` 时 45 Mb/s）、两遍响度归一（相机渲染来的时候约 -25 到 -33 LUFS，录屏导出约 -23：不做这步接缝会跳 10 dB），然后流复制拼接并打 BT.709 标签。母版旁边产出 `ASSEMBLY.md`（起始时间、输入响度、md5）和简介用的 `chapters.txt`。要改动就编辑清单再跑一遍：**母版绝不手工剪辑。**

## 验证与交付

- **每次渲染都跑 `verify-render.py`：** 黑帧（含单帧闪黑）、尺寸、BT.709 标签、4K 至少 40 Mb/s、时长 = `data-duration` ± 1 帧、音画差 0.12 秒以内；它写出 `VERIFY.md` 和 `render-sheet.png`。退出码 1 = 不要交付。**削字：** 转录渲染的音频并加 `--words <那句话> --kept "$W/transcript.json"`。
- **连续帧看运动：** `ffmpeg -i out.mp4 -vf "select='between(n,A,B)',scale=480:270,tile=6x7" -frames:v 1 strip.png` 覆盖每个转场窗口；找「跳一下再爬」、动作之间死停、单帧爆闪。
- **声音**按「声音」一节；**响度**用 `ebur128`（约 -14 LUFS，真峰值低于 -1）；**唇形同步**在长切上验：平坦帧在后几个段落里应与源在 `src_start + x` 一帧内对上。
- **交付**到 `~/Movies/YouTube Renders/<project>/<project>-4k.mp4`（和渲染 md5 对照），旁边放 `STORYBOARD.md`（`storyboard-md.py`：时间 / 节拍 / 画面上是什么、改了什么、你的顾虑、每条素材的页面、许可和秒段）；从原始素材剪的再加 `PAPER-CUT.md`。从 Finder（或资源管理器）打开；绝不把 MP4 从聊天下载里过一道，托管往返可能改文件。
- **汇报**文件夹、加了什么加在哪，以及**你自己的顾虑**（某卡停太久、衬衫上的词丢了、某刀藏在切出下面）。版本号继续往前走（v2、v3……）。意见用大白话回来；没有什么是锁死的。
- **把已批准的设计重新卡到同内容的新剪辑上是最便宜的修改：** 拷贝参考 `public/`，重新转录，把每个 `data-start` 和时间线时间挪到新词上，截图，渲染。

## FCPXML 交付（Final Cut）

走这条路时读同目录 [`FCP.md`](FCP.md)（含剪映音效附录）。进 Final Cut 之前：

- 剪切照跑，**不**渲整条 4K，**不**跑整片 `verify-render.py`。
- 连接片 `offset` 用宿主素材时钟，不是时间线秒。改完 XML 要删掉库里旧项目再导入。
- 动画和音效连接片不挂 `<marker>`；备注写进剪辑名。
- 透明 MOV 去掉音轨；磁盘上没有的文件不要写进 XML。
- VoiceMagic 词级 `transcript-<资产名>.json` 与 `.fcpxml` 放同一文件夹。

## 拆解（向你佩服的频道学习）

每两条视频，量一个你想学习的频道最近两条片子，对照你最近两条。拉下来做私人分析（`yt-dlp -f "bv*[height<=1080]+ba" -o "videos/_teardown/<slug>.%(ext)s" <url>`，字幕用 `--write-auto-subs --skip-download`）；下载被拒就不要强求。

```bash
python3 "$SK/scripts/teardown.py" --video videos/_teardown/<ref>.mp4 --out videos/_teardown/<ref>/ [--transcript words.json]
python3 "$SK/scripts/teardown.py" --storyboard videos/<ours>/storyboard.json --out videos/_teardown/<ours>-sb/
python3 "$SK/scripts/teardown.py" --compare videos/_teardown/*/report.json --out videos/_teardown/COMPARE.md
```

脚本测量像素能说的（硬切对照局部帧变化中位数——同构图跳剪是中位数的 4–17 倍；爆发段；最安静的 15 秒段；亮度；响度；每分钟词数）。联络表留给剩下的、要用眼睛数的：叠层时刻、入场、屏上词、运镜、露脸时长、切出类型、字幕。绝不根据波形数字声称听到了音频。把每个差距变成这里的一条规则（涉及外观的同步进本文件与 `compose.py` 颜色变量）。高密度剪辑的密度通常在卡片内部（约每秒一个新元素），不在卡片数量上；无论如何都守住「2 秒内读完」。

## Shorts（9:16）

不是默认流程。要做的话：单独的 1080x1920 合成（绝不从 16:9 居中裁），主打字号 88–110 px，卡片全宽减 48 px，字幕药丸离底约 280 px，保留词的逐字精确字幕，前三秒有一个具体的、视频一定会兑现的留下来的理由，一个主开放悬念。

## 让 skill 保持是你的

- **每次交付后：** 你的大白话意见 → 改分镜（一个数字）或格式（一条规则）→ 重建 → 截图 → 渲染。skill 存在的意义，是让下一次的第一条提示词只剩「剪一下这些开场」。
- **「把这个存进 skill」：** 把意见写成它所属章节里的一条大白话规则，有编号的带上编号。它改变外观时，同步更新本文件与 `compose.py` 的颜色变量。新规则和旧规则冲突时，替换旧的；绝不两者并存。
- **被认可的结果变成格式：** 在 `FORMATS.md` 的格式库表里加一行，附一份带数值的规格。FCP 接线写进 `FCP.md`，不要塞回 `SKILL.md`。
- **新格式从状态表开始：** 写代码前先命名每个状态（画面上是什么、在哪、尺寸、颜色）和两态之间的每次变化（什么在动、动哪个属性、什么缓动、什么时间）。按状态表搭建，每个状态截图，一轮轮修，跑回看检查（见「坑」），并在 `scripts/tests/` 下加测试。没有状态表的格式会漂移，审查时无处指认。
- **模型与 token：** 常规轮次用中档模型就很好；新格式、或本文件没覆盖的例外，配最强的。token 大头在截图和工具输出上：一个时刻一张截图，能用脚本就别手抄。
