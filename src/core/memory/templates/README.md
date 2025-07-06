# 内存模板子模块

本目录包含企业级Agent系统的内存模板实现，支持多种记忆结构：

- `template_base.py`：内存模板基类，定义统一接口
- `semantic_template.py`：语义内存模板，适用于文本、知识等结构化语义信息
- `vector_template.py`：向量内存模板，适用于嵌入向量等结构化数据

## 用法示例

```python
from .semantic_template import SemanticMemoryTemplate
from .vector_template import VectorMemoryTemplate

semantic = SemanticMemoryTemplate()
encoded = semantic.encode("知识点A")
decoded = semantic.decode(encoded)

vector = VectorMemoryTemplate()
vec_encoded = vector.encode([0.1, 0.2, 0.3])
vec_decoded = vector.decode(vec_encoded)
``` 