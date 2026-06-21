# Embed — Text-to-Vector

独立的 infra feature，将文本转换为稠密向量（embedding）。

## 定位

`embed` 不与任何存储层耦合。任何需要文本转向量的组件（OSS 的投影管道、VDB 的查询向量化等）都可以独立依赖此 feature。

## Contract

| 成员 | 类型 | 说明 |
|------|------|------|
| `model` | `str` (property) | 模型名，如 `text-embedding-3-small` |
| `dim` | `int` (property) | 输出向量维度 |
| `embed(texts)` | `(list[str]) -> list[list[float]]` | 批量嵌入 |
| `__call__(texts)` | 同上 | 语法糖，实例可直接调用 |

## 与 kb_info 的关系

调用方应校验 `EmbedFunction.model` / `EmbedFunction.dim` 与 `kb_info.embed_model` / `kb_info.embed_dim` 一致。

## Feature 间关系

```
embed  ← oss    (OSS projection: .any → .md → .vector)
embed  ← vdb    (query embedding before VectorStore.search)
embed  ← kb     (orchestration: chunk embedding pipeline)
```

`embed` 不依赖任何其他 feature。
