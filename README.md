# Tonie Audio Curator

一个面向 Creative-Tonie 的极速儿童音频工作流：AI 研究少量真实候选并保留教育机构、评论、播放量和知名度信号；用户确认后，本地工具并发下载、单遍转换，并把最终 MP3 直接交付到 Google Drive。

## 主要特性

- 默认最多推荐 8 条，只对最多 12 个候选做口碑研究。
- 只有明确确认的编号才会下载。
- 4 路并发下载，25 秒超时，最多 3 次尝试。
- 每首下载完成即保存状态，支持中断后继续。
- 2 路并行、单遍 FFmpeg 转为 MP3。
- 转码逐首保存状态；同一来源文件和参数再次执行时复用非空 MP3，摘要中的 reused 表示复用数。旧报告缺少复用信息时会重新转换一次。
- FFmpeg 超时记为单项失败，其他项目继续；续跑只重做失败或已变化的项目。
- 直接生成 tonie-01；不复制音频、不分包、不生成 ZIP。
- Drive 使用缓存的 Tonie Audio ID，上传 MP3、播放清单和许可证，不回读。
- 命令只向 AI 返回紧凑摘要，详细状态留在本地。

## 安装

需要 Windows 10/11、Python 3.11+、FFmpeg 和 Git。

    .\setup.ps1
    .\.venv\Scripts\python.exe scripts\verify_environment.py

## 使用

1. 向 Codex 提供年龄、语言、兴趣、类型、禁止内容和单曲时长。
2. Codex 可先用以下命令把 Commons 候选写入本地，只读取返回的数量摘要；随后仅对最多 12 个候选研究口碑：

       .\.venv\Scripts\python.exe scripts\research_commons.py "关键词" --output workspace\<job-id>\candidates.json

3. Codex 最多显示 8 条真实推荐并等待确认。
4. 确认后执行：

    .\.venv\Scripts\python.exe scripts\run_fast_job.py workspace\<job-id>\selection.json

命令生成：

    output/<job-id>/
    ├── tonie-01/
    │   ├── *.mp3
    │   ├── playlist.json
    │   └── licenses.txt
    ├── processing-report.json
    ├── summary.json
    └── drive-upload-plan.json

Codex 根据上传计划创建一个随机任务目录，并行上传计划中列出的交付文件。

上传计划每次按当前 playlist.json 更新文件清单，保留已有目标目录信息；目录中的历史 MP3 不会自动加入计划。该计划仍由 Codex 执行上传，不代表文件已上传。

## 默认音频参数

- MP3
- 44.1 kHz
- 160 kbps
- 立体声
- 单遍 loudnorm 请求目标：-18 LUFS、-1.5 dBTP、LRA 7

极速模式不执行输入探测、噪声分析或输出测量，因此这些参数是转换请求值，不是验证结果。

## 明确省略的校验

不执行公网 URL、MIME/文件头、SHA-256、重复内容、独立解码、输出响度/峰值、90 分钟限制和 Drive 回读校验。只保留许可证准入、文件大小限制、网络超时，以及 FFmpeg/上传接口的自然成功或失败结果。

## 测试

    .\.venv\Scripts\python.exe -m pytest -q --basetemp workspace\pytest-temp
    .\.venv\Scripts\python.exe -m ruff check .

测试不会执行真实联网下载或 Drive 上传。
