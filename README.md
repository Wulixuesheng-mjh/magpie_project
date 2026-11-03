# Magpie 意图识别研究

研究目标：梳理 Magpie 原生意图识别与路由机制，横向比较冻结 BERT＋分类头、简单聊天模型、向量相似度、Jev，再纵向比较 BERT 编码器微调及复杂请求表现。

## 当前状态（2026-11-03）

- 已固定上游提交，下载六个源码/设计文件并记录文件哈希；没有修改上游实现。完整仓库克隆未完成，已停止；以 `research/source-lock.json` 中的文件快照为证据。
- 已完成原生流程初步梳理、分类规范、数据格式、分组划分和指标计算工具。
- 已实现原生数字解析、截断、前轮回退的 Python 行为摘录，尚未与 Go 运行时做差分验证。
- 模型适配器、模型训练、真实预测、参数搜索、置信区间、挑战集评测与路由回放均未完成。
- 正式数据量为 0。测试代码中的手工样例仅验证工程行为，不是模型评测结果。
- 按用户选择已采集 60 条公开问题单代理候选；标题预筛排除 8 条，52 条待正文、许可和标注审查。详见 `docs/public-pilot-status.md`，不得将 60 当作已合格样本数。
- 可公开的来源索引保存在 `data/public/`；原始问题单正文与响应快照保留在被 Git 忽略的 `data/private/`。源码快照许可证和派生代码归属见 `THIRD_PARTY_NOTICES.md`。

环境实测：Windows、Python 3.11.9、16 个逻辑 CPU，RTX 4060 Laptop GPU（8188 MiB，驱动 596.36）。当前 Python 没有 torch / transformers / sentence-transformers / numpy。显存容量不等于模型已验证可训练。

## 先阅读

1. `docs/magpie-intent-flow.md`：带固定源码行号的原生逻辑报告。
2. `docs/annotation-guide.md`：分类边界、采集和标注规则。
3. `docs/data-contract.md`：输入、输出与数据操作。
4. `docs/work-log.md`：计划进度、待确认项和下一步。
5. `docs/public-pilot-status.md`：候选数据及质量问题。

## 无需安装依赖的检查

在项目根目录运行 PowerShell：

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests -v
python -m intent_study.cli --help
```

模型依赖单独列在 `pyproject.toml` 的 `models` 可选组。本轮没有安装或下载模型。账号和密钥不要写入配置文件；后续 API 适配器只从环境变量读取。

## 数据工具

将人工收集并完成标注的数据保存到 `data/private/annotated.jsonl`，格式见数据契约。该目录被 `.gitignore` 排除。

```powershell
$env:PYTHONPATH = 'src'
python -m intent_study.cli validate data/private/annotated.jsonl --formal
python -m intent_study.cli split data/private/annotated.jsonl data/private/split-v1.jsonl --formal
python -m intent_study.cli score data/private/split-v1.jsonl outputs/validation-predictions.jsonl --split validation
```

划分只接受未划分数据，输出不覆盖已有文件。划分后检查各类数量和来源比例；分组较大时无法保证精确的 60/20/20。人工近重复审查仍然必要。正式模型评测前须固定模型 revision、数据哈希和实验配置。

## 仓库与提交

- GitHub：<https://github.com/Wulixuesheng-mjh/magpie_project>
- Gitee：<https://gitee.com/Wulixuesheng-mjh/magpie_project>

主分支为 `main`，使用 Conventional Commits 风格提交信息（如 `feat:`、`fix:`、`docs:`）。本地 remote `origin` 指向 GitHub，`gitee` 指向 Gitee；两个 remote 使用同一个提交历史，分别推送，不使用强制推送。
