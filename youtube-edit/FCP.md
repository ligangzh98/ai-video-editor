读这份文件的时机：用户要 FCPXML、Final Cut、透明 MOV 叠层或剪映音效进时间线时。不要为了这条路渲整条 4K。

## FCPXML 交付（Final Cut）

用户要「出 FCPXML、不用渲染」时：剪切阶段照跑、`PAPER-CUT.md` 照出，然后交付**媒体 + XML**，让 Final Cut 接手精修。FCP 里拿到的是「剪辑决定 + 全部原始余量」——时间线上是剪好的保留段，拖边缘就能回看被剪的部分。**默认不在本地渲整条 4K 成片**；画面精修、字幕样式在 FCP 里做。若用户要**门派透明叠层**（药丸、玻璃卡、配图等）仍走 `compose.py` + HyperFrames 渲 **透明 MOV**，用连接片挂进 XML（见下「Alpha 叠加素材」与「FCP 透明叠层批量包装」）——不是把 HTML 底行逐字效果直接搬进 FCP 字幕轨。

**默认：双轨分段版（已在真实 FCP 导入验证）。只交付一个项目：带标记的原片时序（裁而不删）——不要另出「纯净版/成片版」项目（用户定的：对照意义不大，FCP 里拖剪辑边缘随时能回溯被剪内容）。** 把原始的视频、音频两个文件原封不动拷进交付文件夹；XML 时间线按剪切点把素材切成段——要的段启用、不要的段 `enabled="0"` 禁用，**裁而不删**，用户后期手动调整（换保留段 = 禁用一段、启用另一段）。画面段在脊柱上，录音是挂在段下的负 lane 连接片（`audioRole="dialogue"`）：两条独立轨道，可单独静音或替换。一个项目就够。

```xml
<fcpxml version="1.9">
  <resources>
    <format id="r1" name="FFVideoFormat3840x2160p60" frameDuration="1/60s" width="3840" height="2160" colorSpace="1-1-1 (Rec. 709)"/>   <!-- 时间线帧率跟素材走 -->
    <asset id="r2" name="视频" start="0s" duration="1808/60s" hasVideo="1" hasAudio="1" videoSources="1" audioSources="1" audioChannels="1" audioRate="48000" format="r1">
      <media-rep kind="original-media" src="file:///…百分号编码…/视频.mp4"/>
    </asset>
    <asset id="r3" name="音频（录音机）" start="0s" duration="1440720/48000s" hasAudio="1" audioSources="1" audioChannels="2" audioRate="48000">
      <media-rep kind="original-media" src="file:///…百分号编码…/音频.m4a"/>
    </asset>
  </resources>
  <library location="file:///…交付文件夹/">
    <event name="<项目>">
      <project name="<项目> 剪辑（标记）">            <!-- project 上绝不写 format -->
        <sequence format="r1" duration="1808/60s" tcStart="0s" tcFormat="NDF">
          <spine>
            <!-- 一段一个剪辑头尾相接，剪切点 = 段边界；每段挂自己的配对录音。要的段 enabled="1" -->
            <asset-clip ref="r2" name="重拍 1" offset="1425/60s" start="1425/60s" duration="87/60s" format="r1" tcFormat="NDF" srcEnable="video" enabled="0">
              <asset-clip ref="r3" name="录音（录音机）" offset="1425/60s" start="935/60s" duration="87/60s" audioRole="dialogue" lane="-1"/>
              <marker start="2375/100s" duration="1/60s" value="重拍 1（禁用）" note="烂开头：「你录一条三…」"/>
            </asset-clip>
            <!-- 录音连接片对齐：offset = 画面段 start；晚开录 Δ 秒就再 +Δ（音频 start = 画面 start − Δ） -->
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
```

- **分段画时间线：** 剪切点就是段边界（静音、打板、每遍重拍、保留各一段），不要的段 `enabled="0"`、剪辑名写明状态，标记给 `value` 短标签 + `note` 详情（包括「要留这遍就启用本段、禁用保留段」）。绝不删除、绝不挪位——时间线镜像素材原貌；每段的配对录音都在，启用哪段都是完整音画。
- **坐标语义（搞错不报错、经常静默失败）：** 分两层记，别混。
  - **脊柱上的剪辑**（`spine` 里首尾相接的 `asset-clip`）：`offset` = 序列时间线位置（从 0 起算）；`start` = 该素材的入点（带 tmcd 的相机素材是拍摄时间码，不是 0）。
  - **挂在宿主下的连接片**（`lane` 正负、动画/录屏/音效）：`offset` **不是**序列秒数，而是写在**宿主本地时钟**里——这台钟从宿主的 `start` 起算，和 `marker`/`keyword` 的 `start` 同一套坐标。时间线上的真实位置 = `宿主 spine offset + (连接片 offset − 宿主 start)`（与 Apple DTD「parent timeline」、`fcp-mcp-server-main/fcpxml/parser.py` 的 `_iter_connected_elements` 一致）。**齐到宿主剪辑头：** 连接片 `offset` = 宿主的 `start`（素材侧）；晚于头 Δ 秒就写 `宿主 start + Δ`（仍用该素材的有理数秒，如 `801540/24s`）。**常见事故（FCP 11.2 实测）：** 把连接片 `offset` 写成宿主的 spine `offset`（如 `1620/24s`）而宿主 `start` 是 `801540/24s` → 事件浏览器里动画 asset 能看见，**时间线主轨上方没有任何连接片**（FCP 直接丢掉，无告警）。对照已验证工程（如 261003）：父片 `offset="2880/60s" start="2880/60s"`，动画子片 `offset="2886/60s" start="0s" lane="2"`（本地 +6 帧，不是写 `2880/60` 当子片 offset 的「时间线含义」）。
  - 标记和连接片只能挂在剪辑上（没有「时间线级」标记）。子元素顺序被 DTD 强校验：**连接片（anchor 组）必须在 marker/keyword 之前**（启用段上先铺 `lane` 连接片，再挂 `keyword`/`marker`）。
- **asset 的 `start` 必须写素材内嵌的起始时间码，否则每条启用剪辑都报「未包含相应媒体的无效编辑」：** 相机（iPhone / Blackmagic Cam / Sony Alpha 等）拍的 `.mov` 带 tmcd 轨，起始时间码常是拍摄钟点（`09:15:30:00`）而不是零。FCP 用**真实时间码**给素材定位，XML 里若写 `asset start="0s"` + 0 基的片段入点，剪辑区间就落在素材第一帧之前 → 逐条告警。查时间码：`ffprobe -v error -show_streams -of json X.mov | grep timecode`（tmcd 轨和视频轨的 tags 里都有）。修法：`asset/@start` 写该秒数（`09:15:30:00` → `33330s`），**该素材的所有 source 侧时间都加这个偏移**——脊柱剪辑的 `start`、`marker/@start`、`keyword/@start`、以及**连接片的 `offset`（对齐用，不是子片 `start` 入点）**；**序列时间线侧不加 TC**：脊柱剪辑的 `offset`、序列 `duration`。没有内嵌时间码的素材（录屏、m4a、渲染出的中间件）保持 `0s`。副作用是 FCP 里这些素材时间码从 09:xx 起——只想归零就得用 Compressor「Uncompressed 8-bit 422」+ Timing 起始时间码 00:00:00:00 且视频音频都 pass-through 重封一次，4K 素材代价太大，不推荐。
  **诊断要点：告警只报启用段、不报 `enabled="0"` 的段 → 就是这条**（禁用段不参与校验）。若告警均匀落在所有段上，那才是剪辑坐标算错。
- **资产时长绝不能多报，宁少勿多：** 音频按采样数写（`round(秒×采样率)/采样率`）；视频按**最后一帧的终点**算，不是容器时长——容器总比末帧多零点几帧（真实数据：1-录像 容器 428.360 s，但 10280 帧 @24 fps 到 428.333 s 就结束了，按容器报尾巴那段就引用了一帧不存在的画面）。**帧数只在素材帧率与序列帧率同口径时能用**：24 fps 相机（1-录像 10280 / 2-录像 38059 / 3-录像 5592 帧）直接写帧数；60 fps 录屏被 conform 进 24 fps 序列时 `nb_frames` 不是 24 fps 口径，按容器时长下取整到帧格（2-录屏 1521.967 s → `36527/24s`）。多报会被 FCP 标记——症状是整个画面或声音直接失效（真实事故：视频资产多报 0.02 秒，画面不显示、声音却正常，查了一轮才定位到）。
- **帧格：** 「此项目不在编辑帧边界上」= 有剪辑级 `offset`/`start`/`duration` 没落在序列 `frameDuration` 的整数倍上。时间线帧率跟素材走（60 fps 素材用 1/60s 序列，媒体时长天然落格）；互相关算出的音频对齐偏移天生亚毫秒（8.168 s），收进最近的帧格（490/60 s，偏 1.3 ms 无感）。交付前自检剪辑级时间值；资产时长和标记不在此约束内。
- **相机自带的音轨要关掉：** 画面段带 `srcEnable="video"`（all|audio|video），否则相机声和录音机声叠着放。
- **标记每条都要 `duration="1/60s"`**——DTD 里写的是可选，但 FCP 不渲染无 duration 的标记（实测）。短剪辑上标记图标挤成一个点：告诉用户去时间线索引 →「标记」标签看列表。
- **`<audio>` 元素不许带 `format`/`tcFormat`**——它的 ATTLIST 里没有这两个属性，带了直接验证失败；`<asset-clip>` 可以带。资产引用优先 `<media-rep kind="original-media" src="…"/>` 子元素，不是 `src` 属性。
- **`format/@name` 必须是 FCP 认识的枚举名：** 4K 30p 是 `FFVideoFormat3840x2160p30`（高度命名要带宽度，没有「2160p30」这种简写）；60 fps 媒体用 `FFVideoFormat3840x2160p60`。写错的报错很绕：在 `sequence/@format` 上报「遇到意外值」，病灶却在 `format/@name`。整张枚举表从 FCP 本体挖：`strings -a /Applications/Final\ Cut\ Pro.app/Contents/Frameworks/Flexo.framework/Versions/A/Flexo | grep -o 'FFVideoFormat[A-Za-z0-9]*' | sort -u`。
- **时间值写有理数秒**（`"824/30s"`、`"1516/100s"`），照 FCPXML DTD 注释的格式；`src` 用百分号编码的 `file://` URL；XML 和媒体一起交付，别分开移动。**同一文件夹里还要带 VoiceMagic 词级转录**（见「转录」：`transcript-<资产名>.json` 与 `.fcpxml` 并列），后续改连接片、透明叠层锚点、字幕 `times` 都直接对着这份稿，不必回 `videos/<p>/` 找旧文件。
- **校验对着 FCP 自带 DTD 逐条核属性：** `Final Cut Pro.app/Contents/Frameworks/Interchange.framework/Versions/A/Resources/FCPXMLv1_<n>.dtd` 的 ATTLIST（Apple 1.10 之后不再公开 DTD，App 里这组就是唯一权威规范；`xmllint` 解析不了它，读文本即可）。FCP 的验证遇错即停，一次只报第一处；修完再导，别以为只有一处。
- 导入时 FCP 必然问「导入到哪个资源库」——正常流程，选一个或新建即可；问是否把媒体拷进库，要自包含就拷、省空间就不拷。**FCP 不会刷新已导入的 XML：** 修连接片坐标、补动画、改 lane 后，必须删掉库里旧项目/事件再导入；覆盖同名 fcpxml 文件不够。写完 XML、`check-fcpxml.py` 全绿也不等于时间线上能看见叠层——**以用户 FCP 时间线确认为准**（浏览器有素材、时间线没有 = 优先查连接片 `offset` 是否误写成 spine 时间线秒数）。
- **交付前先跑 `scripts/check-fcpxml.py X.fcpxml`**（有问题退出码 1）。它把 FCP 只会在导入后一条条报的失败模式提前查出来：asset 时间码与素材内嵌时间码不符（「无效编辑」的头号原因）、资产超报、剪辑级帧格、anchor→marker 顺序、媒体文件存在、spine 连续。自己的 `make-fcpxml.py` 里还要有同样几条自检，并**显式按「连接片 offset ∈ 宿主素材时钟」生成**（见上）；脚本自检与本工具互为独立复核，别只留一个。

**已否决：sync-clip 双轨方案（不要重建）。** 试过两版：一版在 `sequence/@format` 上报「意外值」（病灶是 `format/@name`），一版只出声音不出画面。结构比连接片深一层、窗口语义又含糊，不值得再碰——分段 + 连接片方案已验证，照它走。

**可编辑动画三件套（动画要留在 FCP 里调时）：** 门派动画烧在渲染里不可改；要用户能持续调整的动效，给这三样，可同框、互为备份：

- **变换关键帧（运镜类）：** `adjust-transform`/`adjust-blend` 里放 `<param name="scale|position|amount">` + `<keyframeAnimation><keyframe time value>`，时间用宿主本地时间、值用 `"1 1"` 这种成对写法。**变换参数（position/scale）的关键帧只写 `time`/`value`**——`interp`/`curve` 会被 FCP 忽略并告警（「此参数元素不支持其关键帧上的插值属性」），插值交给 FCP 默认；`amount` 这类参数才认 `interp`。推近、淡入、滑入进 FCP 就是标准 Video Animation 关键帧，曲线随便改。`adjust-*` 在剪辑子元素里排在连接片和标记**之前**。
- **标题实例（文字类）：** `<title ref="…">` 作连接片挂 lane 1；ref 指向 `<effect uid=".../Titles.localized/…/X.moti" src="…">`——uid 是**字面 `.../` 开头的模板路径串**，从 `strings -a …/Flexo.framework/…/Flexo | grep "Titles.localized.*\.moti"` 挖。文字用 `<text>` 里多段 `<text-style ref>`（部分变色 = 两个 `text-style-def`）。文字位置/字体在 FCP 检查器里调，XML 只负责把内容和入场关键帧带上。
- **Alpha 叠加素材（门派外观）：** 合成页删掉背景视频、`background` 全改 `transparent`，`hyperframes render --format mov` 直出**透明底 ProRes 4444**（yuva444p12le）。时间线与 4K 成片一致时用 `--resolution landscape-4k`；要快、文件小可用 `landscape`（1080p）+ `-q draft`，FCP 里再缩放对齐——XML 侧与 4K 序列并存无硬要求。**进 FCP 的接线（261003 / 261007 在 FCP 11.2 导入验证）：**
  - 每个 MOV 在 `<resources>` 注册 `asset`：`start="0s"`、`hasVideo="1"` **`hasAudio="0"`**（渲染若带出 AAC，交付前 `ffmpeg -i in.mov -map 0:v:0 -c copy -an out.mov` 去音轨，否则与 `hasAudio="0"` 不一致时行为不可信）。
  - 事件级浏览器再挂一条无 `offset` 的 `asset-clip` + `keyword value="动画素材"`，方便精选；**真正出现在时间线上的是**挂在对应**保留段**宿主下的连接片：`lane="2"`（主轨上方，与录屏连接片同 lane 编号；别和「事件里多出来的素材条目」混淆）、子片 `start="0s"`、`duration` 用整条 MOV 帧数（可略超出宿主段，与 261003 一致）、**不要**给子片加 `format`/`srcEnable`/`adjust-transform`（除非刻意仿 FCP 导出形状）。
  - 子片 `offset` 用 **`f24s(宿主.src + 段内本地秒, 宿主.asset)`**，不要用 `f24(序列时间线秒)`。`make-fcpxml.py` 里 `anim_layers()` / 录屏 / 音效连接片同一规则。
  - 例（相机带 TC，宿主在序列 1:07.5，素材入点 `801540/24s`）：
    ```xml
    <asset-clip ref="r2" name="保留·…" offset="1620/24s" start="801540/24s" duration="118/24s" …>
      <asset-clip ref="r9" name="动画·药丸三连" offset="801540/24s" start="0s" duration="120/24s" lane="2">
        <keyword start="0s" duration="120/24s" value="动画素材"/>
      </asset-clip>
      <keyword …/><marker …/>
    </asset-clip>
    ```
  - 时间、位置、缩放、透明度仍在 FCP 调；内部文字和动画曲线烧在 MOV 里。验 alpha：`ffmpeg -vf "alphaextract,signalstats"` 看 YAVG（约 10% = 正常；`showinfo` 的 mean 会骗人）。改 XML 后须**删掉旧导入项目再导**（见下），否则连接片不刷新。
- 同框规则：XML 里默认 **alpha 素材启用**（导入即见门派外观）、标题 `enabled="0"` 备用（用户定的默认）；剪辑名和标记写清二选一与换法；换保留段时关键帧跟着段走。
- **动画素材按门派节奏铺，不是只给一条：** 每 90 秒约 7 个叠层时刻，每个时刻一个独立透明底 MOV（时间/位置/透明度在 FCP 各自可调），格式换花样、同手法绝不连用；入场用 beat-check 对着**段内本地时间的转录**校（先按锚词真实时刻调 `in`/条目 `at`，再烧进 MOV——动画时机在像素里，错了要重渲）。
- **FCP 透明叠层批量包装（长口播正文，261007 1:39–6:46 验证）：** 引子几条 + 正文按话题铺 **十几条**短 MOV（约 4.5–5.5 s/条），不是一条长合成、也**不要**整段只用 `line` 底行字。
  - **载体优先（叠在口播上、无全屏色洗）：** `pills`（胶囊分置/底行）、`chip`（点睛暗玻璃条）、`list` / `popout`（玻璃列表）、`tag`（章节角标）+ 同屏 `pills` 等。**避免** `deck` / `pipeline` / `search` / `image` 等带 `.cut` 全屏底的格式——透明 MOV 上会盖住整张脸。
  - **工程布局（可复用）：** `videos/<p>/overlay/body-storyboards.py` 里表驱动 `(时间线秒, 文件夹名, FCP 剪辑名, duration, spec)` → 写出各 `overlay/anim-b-*/storyboard.json` + `body-timeline.json` + `body-render-manifest.json`；`write-storyboards.py` 末尾调用生成器；`make-fcpxml.py` 在引子 `ANIM_INTRO` 后 **`json.load(overlay/body-timeline.json)`** 合并进 `ANIM_OVERLAYS`（每项 `(tl_start, "anim-b-foo.mov", "动画·…")`）。
  - **时间线锚点必须落在「单条保留段」内：** 分段版 XML 里 `anim_layers()` 会对**每个**与 `[tl0, tl0+dur)` 相交的宿主段各挂一条连接片——锚点跨禁用缝/多段保留 → 同一条 MOV **重复**出现在时间线上。规划前用段表算：该秒是否落在某一 `保留` 的 `[t0,t1)` 且 `tl + duration ≤ t1`（宁短 0.3 s 也别跨缝）。
  - **批量渲染：** `overlay/render-overlays.sh`（引子 + 正文）或 `overlay/render-body-only.sh`（只渲 `anim-b-*`）；每条 `compose` → `hyperframes render`（`landscape` + `-q draft` + MOV）→ `ffmpeg -map 0:v:0 -an` 去音轨。`make-fcpxml.py` 只注册磁盘上**已存在**的 MOV（缺文件则跳过，别指望 XML 占位）。
  - **批量脚本 stdin 陷阱（真实事故）：** `while read …; do render_one; done < manifest` 时，`npx hyperframes` / `python3 compose.py` 会**读走 stdin**，循环只跑第一条就结束。修法：清单先写入 `overlay/.body-render.tsv`，`done < 文件`；`compose`/`hyperframes` 加 `</dev/null`。
  - **多段时间窗（正文 + 收尾，261007 验证）：** 不必只铺一段。引子用 `ANIM_INTRO`；中段 `body-storyboards.py` → `body-timeline.json`；更晚的一截（如 **30:50–片尾**）用 **`outro-storyboards.py`**（`anim-e-*`）生成 `outro-timeline.json` / `outro-render-manifest.json`，`write-storyboards.py` 在 body 生成后 **`append` 进同一份 `body-timeline.json` 与 manifest**；`make-fcpxml.py` 仍只 `json.load(body-timeline.json)`。增量渲染：`render-body-only.sh` / **`render-outro-only.sh`**（只渲缺文件的 `anim-e-*`，末尾重跑 `make-fcpxml.py`）。
  - **时间线秒 ≠ 素材秒：** 分段版时间线含禁用缝，`tl=1850` 未必等于 `src=1850`。定 `tl_start`、对锚词、挂音效前用 **`make-fcpxml.py` 的段表**（或同等 `tiles`）做 `tl → (资产, src)`；`phrase-times.py` 给的是**素材时间**，要换算到序列再写入表。保留段很短（&lt;5 s）时整条 MOV 的 `duration` 必须收进该段，否则连接片越界或重复挂片。
  - **FCP 批量叠层默认是「话题邻近 + 分镜手填 `in`/`at`」**，不是成片 HTML 那种每条都 `beat-check` 锁词：卡片文案对齐你在讲的事，胶囊/item 常早半秒到数秒。要对齐口播：用交付夹里的 `transcript-*.json` + `phrase-times.py` 改 `tl_start` 与 spec 里的 `at`/`line.times`，再重渲 MOV；**引子里带 `times` 的 `line`** 是已按词表烧进像素的例外。
  - **叠层音效（`lane="-2"`、`audioRole="effects"`，261007 验证）：** 音效文件放在 **`…/fcp/xml/音效/`**（与 XML 同包），从用户常备库（如 **剪映素材/音效**）挑 `.mp3` **转 AAC `.m4a`** 登记进 `make-fcpxml.py` 的 `SFX_FILES`。**演示段**（录屏上真在点的）用原响度素材；**正文/收尾每条透明 MOV** 用 **`叠层-*` 拷贝**（峰值约 **0 dBFS**，YouTube 人声下可闻——ffmpeg 自合成短哔声常只有 -30 dB，几乎听不见）。在 `make-fcpxml.py` 里按 `ANIM_OVERLAYS` 的 `tl_start` 在 **多个时间窗**（如 99–406 s 与 1850 s–片尾）于 **`tl_start + ~0.32 s`** 自动追加 `SFX_CUES`，坐标与动画相同（**宿主素材时钟**，`sfx_at()` 挂在对应保留段下）。轮换哪几个文件、特殊条怎么覆盖，见附录「剪映音效库 → FCP 交付默认映射」，正文不重复那张表。重跑 XML 前确认磁盘上已有 `.m4a`。
- **锚词要锚「说出口的那遍」：** 取词表中**离动画时刻最近的那次出现**——被剪掉的残遍常含同一短语，首匹配会被它劫持（「一句话就能完成」先出现在已删的重说里、`TTS` 先出现在模型介绍段，都会把入场拉飞几秒）。beat-check 的锚词必须用词表原样：大小写照抄（`download按钮` 不是 `Download按钮`）、数字/字母分词串用旁边的中文字锚（`260708`、`TTS` 在词表里是单字 token，匹配不上）。
- **卡片文字必须能换行，出片前逐个动画抽帧核边界：** CJK 长串配 `white-space:nowrap` 必冲破固定宽卡片（真实事故：「在线 VoiceMagic:配置更快、效果更好」半个身子挂在卡外）——compose.py 里 `.list/.po/.bullets` 的条目已改可换行，别改回去；浅玻璃条目文字要带暗投影（`.po .item .t` 曾漏）。自查姿势：**抽帧叠到真实视频帧上看**，白字叠白玻璃的独立预览有「没字」假象，像素方差一测便知。校验用的词表必须出自**最终版**音轨——剪辑每动一刀旧词表就作废，拿旧词表校验会满屏假 MISS（时刻本身是对的，错的是参照系）。**窗口从第一个可见事件前 0.5–1 秒起**：空引子在 FCP 检查器里就是黑屏（用户问过「前一半黑屏正常吗」——不正常）；卡片/条目组的入场锚**第一个条目**的话，别锚中段短语，否则卡片比自己的内容还晚到；尾部留 0.1–0.3 秒收。
- **标记只留剪辑结构层：** 动画连接片和音效连接片**都不挂 `<marker>`**（剪辑名本身就写着是什么；音效的备注写进 `name`，例如 `音效·叠层弹出 · 叠层·三件事`）。挂上只会把时间线索引淹没。标记只给「重拍/打板/断录/保留/章节」这类审阅用的结构段。`make-fcpxml.py` 的 `sfx_at()` 遵守这条，不要为了备注再把 marker 加回去。
- **XML 用生成脚本产出，绝不手改：** 每条视频在工作文件夹写一个 `make-fcpxml.py`（结构、段表、三件套、自检都在里面），改版本 = 改脚本重跑；自检覆盖帧格（豁免资产时长与标记时刻）、资产不超报、anchor→marker 子元素顺序、**每条剪辑/标记/关键词的素材区间都落在 `asset [start, start+duration]` 内**（最后这条是唯一能挡住「无效编辑」告警的自检——它必须按素材内嵌时间码算，不能按 0 基算，否则自检全绿而 FCP 逐条报警）。交付文件带版本号（`-v2`），旧版删掉免得导错。
- **关键词要挂在事件级浏览器剪辑上才成精选：** `<keyword start duration value>`（value 逗号分隔多个名）写在 `<event>` 里、没有 `offset` 的 `asset-clip` 上（Apple 官方示例形式），导入后事件下才会出现关键词精选——只挂时间线剪辑不生成精选（实测）。start/duration 是宿主本地时间，标注的是剪辑里的「区段」。素材级「原始素材 / 录音 / 动画素材」+ 内容级「保留 / 重拍 / 打板」；这些浏览器剪辑同时就是事件里的媒体列表。
- **素材路径永远写绝对 `file://` URL：** `src` 只在导入那一刻被读一次，进库后 FCP 记自己的引用；相对路径不是 FCP 的文档功能，别赌。素材备份/迁移的正解：① 导入时选「将媒体拷贝到资源库」→ 库自包含，`.fcpbundle` 搬去哪都不断链；② 媒体在外时用「文件 > 重新链接媒体」批量重链；③ XML + 媒体同文件夹、还原到原路径 = 零操作。

**备选：单素材合体版。** 只要一条剪辑、要最简结构时用：把对齐后的录音烧进 30 fps CFR 工作素材（`raw/take-01-cfr.mp4` 这类），XML 里一个 asset-clip 直接修剪（`srcEnable` 不用动）。代价：音画绑死、不可独立替换，画面是重编码。其余规则同上。

**本地参考：** Apple 官方 FCPXML 文档（`developer.apple.com/documentation/professional-video-applications/fcpxml-reference`，关键词/标记专篇 `…/associating-ratings-keywords-markers-and-metadata-with-media`）是第一权威，示例就是可用写法；本地 `mcp 参考/`（gitignore 的本地目录）里两个 FCP MCP 项目——遇到 FCPXML 新问题先翻 `fcp-mcp-server-main/fcpxml/parser.py`（标记/连接片坐标语义是按真实 FCP 文件实现的解读）和 `dtd.py`（定位 App 内 DTD 的方法），再动手。

## 附录：剪映音效库 → FCP 交付默认映射（261007 验证）

用户常备 **剪映/CapCut 音效文件夹**（本机路径各异，示例：`…/剪映素材/音效/`）。FCP 工程只认交付夹里的 **`…/fcp/xml/音效/*.m4a`**（与 `.fcpxml` 同包）。从剪映 **`.mp3` 转 AAC** 再拷进去；**不要用 ffmpeg 自合成短哔声**当叠层主效（常 -30 dB，YouTube 人声下听不见）。

**两套用途：**

| 用途 | 交付文件名 | 响度 | 典型场景 |
|------|------------|------|----------|
| **演示 / 录屏** | 与剪映同名（如 `鼠标单击.m4a`） | 源文件峰值（约 -3～-1 dB） | `SFX_CUES` 里按**素材时间**手写的点击、打字、完成 |
| **透明叠层自动音效** | `叠层-*.m4a` | 与源相同或略 boost 到约 **0 dBFS**（仍用剪映素材，不合成） | `make-fcpxml.py` 按 `ANIM_OVERLAYS` 在 `tl_start + 0.32 s` 自动挂 `lane="-2"` |

**默认映射表（剪映源 → 交付 → `SFX_FILES` 里的 FCP 名）：**

| 剪映源文件 | 交付 `fcp/xml/音效/` | FCP 资源名（`make-fcpxml`） | 用在哪 | 叠层连接片时长（秒） |
|------------|----------------------|-----------------------------|--------|----------------------|
| `啵1.mp3` | `叠层-弹出.m4a` | `音效·叠层弹出` | 胶囊/卡片弹出；自动轮换第 1 拍 | 0.32 |
| `嘟咚，提示音1.mp3` | `叠层-叮.m4a` | `音效·叠层叮` | 轻提示、列表项；轮换第 2 拍 | 0.45 |
| `鼠标单击.mp3` | `叠层-单击.m4a` | `音效·叠层单击` | 强调点击感；轮换第 3 拍 | 0.30 |
| `嗖，咻.mp3` | `叠层-掠过.m4a` | `音效·叠层掠过` | 滑入、流程、步骤条；轮换第 4 拍 | 0.38 |
| `任务完成.mp3` | `叠层-完成.m4a` | `音效·叠层完成` | 交给 AI、拍板、包装完成等 **special** | 0.45–0.65 |
| `键盘打字长音效2.mp3`（只取前 ~0.55 s） | `叠层-打字.m4a` | `音效·叠层打字` | 对话/改稿类叠层 | 0.42 |
| `鼠标单击.mp3` | `鼠标单击.m4a` | `音效·鼠标单击` | 演示段 UI 点击 | 按条（常 0.34） |
| `键盘打字长音效2.m4a` | `键盘打字长音效2.m4a` | `音效·键盘打字` | 演示段打字 | 按条（2–4） |
| `任务完成.mp3` | `任务完成.m4a` | `音效·任务完成` | 演示段「搞定了」 | 按条（如 1.54） |

**透明叠层自动轮换顺序（默认）：** `叠层弹出` → `叠层叮` → `叠层单击` → `叠层掠过`（四条一轮）；下列 MOV 名在 `make-fcpxml.py` 的 `special` 里覆盖：`anim-b-handoff` / `anim-b-loop` / `anim-b-pack` → **完成**；`anim-b-chat` → **打字**；`anim-b-flow` → **掠过**（`anim-e-*` 收尾段同理）。

**同目录可替换候选（未进默认表，按需改映射）：**

| 剪映文件 | 可替代 |
|----------|--------|
| `Swish.mp3` / `风 闪过.mp3` | `叠层掠过`（更长的 whoosh） |
| `滴，提示音.mp3` / `diling提示音.mp3` | `叠层叮`（更柔，源峰值更低需 boost） |
| `叮叮叮.mp3` | 密集列表条目（慎用，易吵） |
| `金币声音.mp3` | 成就/「值钱」类 chip（收尾段） |

**同步命令模板（改 `JY` / `OUT` 路径后执行一次，再重跑 `make-fcpxml.py`）：**

```bash
JY="$HOME/Desktop/素材/Tech指南/剪映素材/音效"
OUT="/path/to/fcp/xml/音效"
mkdir -p "$OUT"
for pair in "啵1.mp3:叠层-弹出.m4a" "嘟咚，提示音1.mp3:叠层-叮.m4a" "鼠标单击.mp3:叠层-单击.m4a" \
            "嗖，咻.mp3:叠层-掠过.m4a" "任务完成.mp3:叠层-完成.m4a"; do
  IFS=: read -r a b <<< "$pair"
  ffmpeg -y -v error -i "$JY/$a" -c:a aac -b:a 192k "$OUT/$b"
done
ffmpeg -y -v error -i "$JY/键盘打字长音效2.mp3" -t 0.55 -c:a aac -b:a 192k "$OUT/叠层-打字.m4a"
ffmpeg -y -v error -i "$JY/鼠标单击.mp3" -c:a aac -b:a 192k "$OUT/鼠标单击.m4a"
ffmpeg -y -v error -i "$JY/任务完成.mp3" -c:a aac -b:a 192k "$OUT/任务完成.m4a"
ffmpeg -y -v error -i "$JY/键盘打字长音效2.mp3" -c:a aac -b:a 192k "$OUT/键盘打字长音效2.m4a"
```

