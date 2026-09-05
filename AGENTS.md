# Tonie Audio Curator — 极速工作流

## 目标

本项目为儿童研究、下载、转换并交付合法可复用的 Creative-Tonie MP3。默认优先减少等待时间、联网调用和模型上下文；详细状态写入本地 JSON，AI 只读取简短摘要。

## 不可变边界

- 只使用公共领域、CC0、允许复制和转换的 Creative Commons，或用户明确拥有的无 DRM 文件。
- 不从 Spotify、Apple Music、Audible 或 YouTube 提取音频，不绕过 DRM、登录、付费墙或地域限制。
- 推荐不等于下载授权；只有用户明确确认编号后才运行下载、转换和 Drive 上传。
- 不生成试听，不提交音频、任务状态、儿童画像或凭据到 Git。

## 推荐

- 默认最多推荐 8 条；合法合适的候选不足时返回实际数量，不为凑数扩大到不可靠来源。
- 优先运行 scripts/research_commons.py 将 20–30 个候选写入本地；先按年龄、主题、语言、时长和许可证过滤，再只研究最多 12 个候选的口碑。
- 口碑信号包括教育机构或图书馆收录、可信评论、长期知名度，以及能快速取得的播放量。
- 区分作品知名度与具体录音质量；播放量不能单独决定排名。
- 作品口碑结果缓存到 workspace/cache/work-reputation.json，默认 180 天。
- 最终推荐保存到 workspace/<job-id>/recommendations.json，详细证据留在文件中；对用户每条只显示一句理由。
- 推荐完成后停止并等待确认。

## 确认后的极速执行

1. 将用户确认的记录写入并验证 workspace/<job-id>/selection.json。
2. 运行 .\.venv\Scripts\python.exe scripts\run_fast_job.py workspace\<job-id>\selection.json。
3. 下载默认 4 路并发、25 秒超时、最多 3 次尝试；每首结束后立即原子更新 download-report.json。
4. 音频默认 2 路并发，只做一次 FFmpeg MP3 转码并应用单遍 loudnorm。
5. 成品直接写入 output/<job-id>/tonie-01/，不创建副本，不做 90 分钟分组，不生成 ZIP。
6. 使用 drive-upload-plan.json 中缓存的 Tonie Audio 父目录 ID，创建“UTC 时间-随机码”目录，并行上传 MP3、playlist.json 和 licenses.txt。
7. 不搜索 Drive 根目录、不检查同名、不回读。只有上传 API 成功时才报告“Drive 已接受上传”，不得声称已验证远端文件。

## 有意省略的检查

默认流程不执行：

- 公网 IP、DNS 或重定向目标校验；
- MIME 类型和文件头校验；
- SHA-256 或内容去重；
- 独立的输入可解码检查；
- 转码后的响度、峰值或格式验证；
- Creative-Tonie 90 分钟限制检查；
- Drive 目标唯一性、覆盖检查或上传后回读。

FFmpeg 无法转换时将该项目记为失败并继续，但这不构成独立输入验证。单遍 loudnorm 只表示请求了目标参数，不代表结果经过测量验证。

## 输出

    output/<job-id>/
    ├── tonie-01/
    │   ├── 01-title.mp3
    │   ├── playlist.json
    │   └── licenses.txt
    ├── processing-report.json
    ├── summary.json
    └── drive-upload-plan.json

Google Drive 只上传 tonie-01 中的 MP3、播放清单和许可证，不上传原始文件、日志、儿童画像、处理报告或 ZIP。

## 对话与 Token

- 脚本标准输出必须是单行紧凑 JSON。
- 正常情况下 AI 不读取完整日志、FFmpeg 输出、逐文件 Drive 元数据或完整缓存。
- 后续阶段只传递 job_id 和文件路径；只有失败项需要展开原因。
- 用户中断后从本地状态继续，不重复已完成的下载。

## 验收

- 推荐最多 8 条且包含来源、许可证和可核验口碑信号。
- 未确认时不下载；确认后只处理所选编号。
- 单项失败不中止其他项目；中断后复用存在且非空的已下载文件。
- 成功转换的 MP3、playlist.json 和 licenses.txt 位于同一 tonie-01 目录。
- 不生成 ZIP，不做 90 分钟或输出音频验证。
- 测试和 lint 离线运行，不执行真实下载或 Drive 上传。
