# 数据与结果契约 v1

主数据是一行一个 JSON 对象，UTF-8。下例仅说明字段，不能直接复制成为真实数据：

```json
{
  "id": "唯一编号",
  "text": "实际采集的请求原文（必要脱敏后）",
  "conversation_id": "会话唯一编号",
  "source_group": "原始开发任务编号",
  "source_ref": "可追溯原始材料的链接或本地编号，不含秘密",
  "provenance": "real_assistant",
  "language": "zh",
  "label": "test",
  "context": [{"role": "user", "content": "前轮用户文字"}, {"role": "assistant", "content": "前轮助手文字"}],
  "duplicate_group": "人工审查发现的近重复组编号（无则省略）",
  "consent_or_license_checked": true,
  "annotation_status": "adjudicated",
  "annotator": "标注者编号",
  "reviewer": null,
  "rationale": "标签判断理由"
}
```

正式输入不得有 synthetic_debug、未检查的数据使用许可或未完成标注。划分命令写入 split，值为 train/validation/test；challenge 单独维护。分组是 conversation、source 和 duplicate 三种关系的传递闭包，避免间接泄漏。划分算法近似平衡各类别，但数据分组优先，须人工检查各类别在三集合中都有覆盖。划分之后固定文件哈希；不重新打乱已划分数据。

预测结果至少包含：

```json
{"id":"对应样本编号","label":"test","abstained":false,"error":null,"elapsed_ms":12.5,"raw_output":"原始回答","score":null,"score_type":null}
```

超时：label=null、error="timeout"。拒识：label=null、abstained=true。语义上的 other：label="other"，不是拒识。失败与拒识计入总体准确率的分母；另报覆盖率及接受样本准确率。预测缺失也计为错误，重复/外来预测 ID 直接拒绝计分。不得给 error/abstained 同时附上一个已接受标签。

score 命令只接收所选 split 的预测，禁止把全数据预测混入验证结果。模型返回概率、向量分数等在 score_type 中标清含义，当前计分器不会把它们混成统一置信度。当前 Macro-F1 固定平均标签配置中的所有类别，缺失类别按 0 处理；因此正式评测前必须检查类别覆盖。

后续模型运行还需记录：方法名、模型及 revision、数据和配置哈希、精度、设备、seed、可见上下文、截断、模板版本、耗时、用量和缓存状态。当前尚未实现运行器，不能把设计配置当作已跑实验。
