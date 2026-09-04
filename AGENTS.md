# Tonie Audio Curator — 项目方案与 AI 操作说明

## 1. 文档定位

`AGENTS.md` 是本项目的统一方案和 AI 操作说明。Codex、VS Code 中的 AI 助手或其他 AI 环境开始工作前，都必须先完整阅读本文件。如果其他文档与本文件冲突，以用户最新明确指令和本文件为准。

当前阶段：实施阶段。

## 2. 项目目标

本项目用于为儿童寻找、下载并整理适合 Creative-Tonie/Toniebox 使用的 MP3 音频，采用“AI 对话交互 + 本地确定性工具”的轻量模式：

1. 用户用自然语言提供儿童年龄、语言、兴趣、内容偏好和限制。
2. AI 联网查询真实、适龄且合法可下载的音频。
3. AI 固定输出 20 条推荐，然后停止并等待用户明确确认，不提供试听。
4. 用户确认后，AI 调用本地工具下载所选音频；找不到合法来源或下载失败时跳过，不影响其他音频。
5. 本地工具进行音频检测、必要的保守降噪、响度统一和 MP3 输出。
6. 根据 Creative-Tonie 的 90 分钟限制分组和打包。
7. 将最终音频和报告上传到 Google Drive 的“Chatgpt工作区”文件夹。
8. 将源码、Skill、配置、文档和测试同步到私有 GitHub 仓库，便于更换电脑部署。

## 3. 实现模式

第一版不开发 Web 前端、移动应用、独立后端服务、数据库、用户账号系统、后台任务队列、OpenAI API 集成、在线试听、Tonies 账号自动登录或 Creative-Tonie 自动上传。

AI 交互由 Codex 或类似 AI 环境完成，可使用用户的 ChatGPT 账号，不要求 OpenAI API Key。本地 Python 和 FFmpeg 工具负责安全下载、文件校验、音频分析、条件降噪、响度归一化、MP3 编码、时长分组、ZIP 打包和 Google Drive 上传结果校验。任务状态保存在本地 JSON 文件中，不使用数据库。

## 4. 核心产品约束

- 每次推荐必须恰好包含 20 条；推荐完成后必须等待用户确认，不能自动下载。
- 不生成试听文件；最终交付格式为 MP3；文件名不得超过 128 个字符。
- Creative-Tonie 按最多 90 分钟内容规划。20 条推荐可以超过 90 分钟，但最终文件必须分包；如果用户只需要一个包，超出项目进入备用清单。
- 任何授权不明、来源不可靠或无法下载的音频必须跳过。
- 不能绕过 DRM、登录、付费墙或地域限制。

## 5. 用户交互流程

### 5.1 需求解析

从自然语言中提取年龄或年龄段、首选及可接受语言、兴趣主题、内容类型偏好、禁止主题、单条期望时长、总时长、Creative-Tonie 数量、指定来源和特殊条件。只有缺失信息会显著改变结果时才提问；其他字段使用默认值并明确说明假设。

### 5.2 查询和推荐

1. 根据儿童画像生成搜索关键词和检索意图。
2. 联网查询真实候选音频及其来源。
3. 获取标题、作者、语言、时长、来源页面和许可证信息。
4. 过滤年龄、语言、内容安全、授权和时长。
5. 对真实候选项排序，固定输出 20 条并保存 `recommendations.json`。
6. 停止并等待用户确认。

不得虚构音频标题、作者、来源页面、下载地址、许可证或时长。无法验证的信息必须标记为 `unknown`。

每条推荐至少包含：`id`、`title`、`type`、`language`、`duration_seconds`、`age_range`、`recommendation_reason`、`source_name`、`source_page_url`、`license`、`download_status` 和 `safety_tags`。

排序参考权重：年龄适配 30%、兴趣匹配 25%、内容安全 15%、语言匹配 10%、时长组合 10%、授权可信度 5%、原始音质 5%。向用户显示编号、标题、类型、语言、时长、来源、授权状态和推荐理由，不提供试听。

### 5.3 用户确认

只有用户明确确认编号后，AI 才能创建 `selection.json`、下载完整音频、处理音频、创建 ZIP 和上传 Google Drive。修改推荐、询问来源或要求重新排序都不等于下载授权。

## 6. 下载政策

下载工具必须：

- 只下载用户确认且授权明确、可直接访问的音频。
- 校验 URL 和重定向目标，防止访问本机或内网地址。
- 校验 MIME 类型和真实文件头，限制文件大小、超时和重试次数。
- 检查有效音频、计算 SHA-256，并按哈希避免重复下载。
- 保存来源和许可证证据；单项失败时继续；找不到合法文件时跳过。
- 不使用来源可疑的替代下载站。

允许来源包括 CC0、可靠标记的公共领域、明确允许下载复制和必要处理的 Creative Commons、用户自有音频、用户合法拥有且无 DRM 的可下载文件，以及官方明确许可的免费内容。

禁止从 Spotify、Apple Music、Audible 提取音频，禁止 YouTube 转 MP3，禁止绕过 DRM、账号登录、付费墙或地域限制，禁止来源不明的下载站，禁止将在线播放权解释为下载和复制权。

下载状态为：`downloaded`、`skipped_not_found`、`skipped_license_unclear`、`failed_invalid_audio`、`failed_network`、`failed_size_limit`。

每项至少保存原始推荐编号、标题、来源页面、最终下载 URL、作者或上传者、许可证及 URL、检索和下载时间、SHA-256、下载状态及原因。

## 7. 音频处理规范

1. 使用 ffprobe 检查完整性并获取编码、采样率、声道、时长、响度和峰值。
2. 检查削波、异常静音、直流偏移和明显噪声。
3. 只有噪声超过阈值时才启用保守降噪；干净音乐或故事不得默认降噪。
4. 使用 FFmpeg 两遍 `loudnorm` 做响度归一化，最多进行一次有损编码。
5. 处理后再次检测并生成 `processing-report.json`。

默认输出：MP3、44.1 kHz、160 kbps CBR；默认立体声，纯语音可保留单声道；集成响度 -18 LUFS；最大真峰值 -1.5 dBTP；响度范围约 7 LU 或更低；ID3v2.3；清理非法文件名并限制为 128 字符。

不能承诺完全无损。工程目标是只编码一次、保守使用滤镜、避免无必要降噪、防止削波并尽量降低可感知音质损失。

## 8. 时长分组和打包

- 总时长不超过 90 分钟时生成一个包。
- 超过 90 分钟时按用户确认顺序拆分多个包。
- 用户要求仅一个包时，将超出音频写入 `overflow-items.json`。
- 不生成试听文件。

输出结构：

```text
output/<job-id>/
├── tonie-01/
│   ├── 01-title.mp3
│   ├── 02-title.mp3
│   ├── playlist.json
│   └── licenses.txt
├── tonie-02/
├── skipped-items.json
├── overflow-items.json
├── processing-report.json
└── tonie-audio-package.zip
```

## 9. Google Drive 固定交付要求

所有成功下载并处理的最终 MP3 及交付文件上传到 Google Drive 的“Chatgpt工作区”文件夹，推荐结构为 `Chatgpt工作区/Tonie Audio/<YYYY-MM-DD_job-id>/`，包含 `individual-mp3/`、各 Tonie 目录、ZIP、播放清单、许可证和处理报告。

- 使用已连接的 Google Drive 插件，第一次上传前搜索“Chatgpt工作区”并保存唯一 Drive ID。
- 不能只按名称猜测；如果存在多个同名文件夹，停止并请用户选择。
- 不上传原始文件、失败文件、缓存或儿童画像；不修改共享权限、不公开文件、不静默覆盖同名任务。
- 每个任务使用独立子目录；上传后回读目标目录并校验文件名、大小和父目录。
- 上传失败时保留全部本地成品；无法写入时不得声称上传成功。

## 10. GitHub 固定要求

实施开始后创建私有 GitHub 仓库，默认名称 `tonie-audio-curator`。仓库保存 Python 源码、项目 Skill、本文件、README、JSON Schema、默认非敏感配置、单元测试、环境检查脚本、`setup.ps1`、依赖清单和 GitHub Actions 配置。

不得保存 MP3/WAV/ZIP、下载缓存、任务目录、儿童画像、Google Drive 凭据、GitHub Token、Codex 登录信息、`.env` 或其他认证文件。

`.gitignore` 至少包括：`.env`、`workspace/`、`output/`、`downloads/`、`*.mp3`、`*.wav`、`*.zip`、`credentials*`、`rclone.conf`、`__pycache__/`、`.pytest_cache/`。

实施时检查 GitHub 登录账号、创建私有仓库、设置 origin；每阶段测试并创建有意义的提交，推送后验证工作树干净，并在另一个临时目录测试克隆和安装。CI 只运行代码测试和格式检查，不执行联网音频下载。

## 11. 项目结构

```text
tonie_downloader/
├── AGENTS.md
├── README.md
├── .agents/skills/tonie-audio-curator/
│   ├── SKILL.md
│   └── references/
├── scripts/
│   ├── download_audio.py
│   ├── process_audio.py
│   ├── package_audio.py
│   ├── upload_google_drive.py
│   └── verify_environment.py
├── schemas/
│   ├── recommendations.schema.json
│   └── selection.schema.json
├── config/audio-profile.json
├── tests/
├── workspace/
├── output/
├── setup.ps1
├── requirements.txt
├── .env.example
└── .gitignore
```

## 12. Skill 设计

第一版仅创建项目级 Skill `tonie-audio-curator`。它负责理解儿童音频需求、生成搜索意图、查询真实候选、过滤不适龄或授权不明内容、固定输出 20 条推荐并等待确认、将确认项目写入 `selection.json`、调用本地下载/处理/打包工具、上传 Google Drive并汇总结果。Skill 不重复实现确定性算法；模块间使用稳定 JSON Schema。

## 13. Token 和上下文优化

- 年龄、许可证、格式和时长过滤尽量使用代码规则；AI 主要负责兴趣理解、搜索意图、适龄判断和排序。
- 脚本仅向 AI 返回简洁 JSON 摘要，详细日志写文件；后续传递 `job_id` 和路径，不重复历史。
- 使用 URL 和 SHA-256 缓存下载及许可证结果；只为最终 20 条生成用户理由。
- Skill 保持简短，详细 Schema 和参数放在代码、配置或按需读取的 reference 中。

## 14. 跨电脑部署

另一台 Windows PC 应能执行 `git clone <repository-url>`、进入目录并运行 `.\setup.ps1`。脚本检查 Python、FFmpeg、ffprobe、Python 依赖、本地 workspace/output、非敏感配置、GitHub 登录提示和 Google Drive 插件连接提示。每台电脑需分别登录 AI 环境、GitHub 和 Google Drive；认证信息不得通过 GitHub 同步。

## 15. 验收标准

- 推荐：有效需求始终输出 20 条；真实来源；每条含来源和授权；推荐后不下载、不试听。
- 下载：只下载明确确认编号；授权不明或找不到时跳过；单文件失败不中止；记录来源、授权和哈希。
- 音频：输出符合配置；响度和真峰值在容差内；不产生新削波；仅明显噪声时降噪；正确执行 90 分钟分组。
- Google Drive：最终文件进入目标任务目录并回读验证；不改变权限；失败不删除本地结果。
- GitHub：私有仓库含全部可部署源码和文档，无音频、任务数据或密钥；新电脑可按 README 和 setup 完成部署。

## 16. 实施顺序

1. 保存并检查本文件。
2. 创建 README、基础目录、JSON Schema、默认配置和 `.gitignore`。
3. 实现环境检查工具。
4. 实现安全下载工具。
5. 实现音频分析、条件降噪和响度归一化。
6. 实现 90 分钟分组和 ZIP 打包。
7. 实现 Google Drive 上传与回读验证。
8. 创建 `tonie-audio-curator` Skill。
9. 添加单元测试。
10. 使用明确无版权的短测试音频执行端到端测试。
11. 创建私有 GitHub 仓库并推送。
12. 在另一个目录验证 clone 和 `setup.ps1`。
13. 使用测试儿童画像验证“推荐—确认—下载—处理—上传”流程。

## 17. 实施默认值与待核实项

- GitHub 仓库名称默认为 `tonie-audio-curator`，创建前检查当前登录账号或组织。
- Google Drive 首次上传时解析“Chatgpt工作区”的唯一文件夹 ID。
- 原始下载本地保留期默认 7 天。
- 默认允许自动拆分多个 90 分钟包。
- 环境检查负责确认 Python、FFmpeg 和 ffprobe。

## 18. 参考资料

- [Tonies 支持的音频格式](https://support.tonies.com/hc/en-au/articles/29036563051154-Supported-audio-formats-for-Creative-Tonies)
- [Creative-Tonie 90 分钟说明](https://support.tonies.com/hc/en-us/articles/29036590864658-Why-can-a-Creative-Tonie-only-hold-90-minutes-of-audio-content)
- [Tonies 上传说明](https://support.tonies.com/hc/en-us/articles/16618096791954-How-do-I-upload-content-onto-my-Creative-Tonie)
- [FFmpeg 滤镜文档](https://ffmpeg.org/ffmpeg-filters.html)
- [Creative Commons 公共领域说明](https://creativecommons.org/public-domain/)
