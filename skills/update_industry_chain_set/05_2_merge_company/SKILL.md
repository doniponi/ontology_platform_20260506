---
name: 05_2_merge_company
description: 产业链图谱更新 - 第五步之二：合并原有图谱和新增企业（脚本实现）
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: script
  input_files:
    - ./图谱/intermediate/02_original_graph.md
    - ./图谱/intermediate/04_v2_optimized.md
    - ./图谱/intermediate/05_new_companies.md
  output_files:
    - ./图谱/intermediate/05_v3_with_companies.md
---
# Role Definition

你是一名数据处理助手，负责通过脚本将新增企业数据合并到图谱中。

## 核心职责

通过执行 Python 脚本，将 05_search_new_company 查询到的新增企业合并到 V2 图谱中，生成 V3 完整图谱。

**此技能通过脚本实现，不进行联网查询。**

## 输入文件

| 文件 | 路径 | 用途 |
|------|------|------|
| 原始图谱 | `./图谱/intermediate/02_original_graph.md` | 提取原有企业数据 |
| V2 优化图谱 | `./图谱/intermediate/04_v2_optimized.md` | 图谱骨架（不含企业） |
| 新增企业清单 | `./图谱/intermediate/05_new_companies.md` | 新增企业数据 |

## 输出文件

| 文件 | 路径 | 内容 |
|------|------|------|
| V3 完整图谱 | `./图谱/intermediate/05_v3_with_companies.md` | 合并后的完整图谱 |

## 执行方式

### 脚本路径
`scripts/merge_companies.py`

### 调用方式
```bash
python scripts/merge_companies.py \
  --original ./图谱/intermediate/02_original_graph.md \
  --skeleton ./图谱/intermediate/04_v2_optimized.md \
  --new-companies ./图谱/intermediate/05_new_companies.md \
  --output ./图谱/intermediate/05_v3_with_companies.md
```

### 超时设置
- **最大执行时长**: 2 分钟

## 合并逻辑

### 核心规则

1. **保留原有节点**
   - V2 图谱中的所有节点必须完整保留
   - 节点名称、层级、父子关系不变

2. **保留原有企业**
   - 原始图谱中已挂载的企业必须保留
   - 格式保持不变

3. **合并新增企业**
   - 将新增企业清单中的企业挂载到对应节点下
   - 与原有企业合并，用 ` & ` 连接

4. **去重处理**
   - 同一节点下的企业去重
   - 同一企业可能出现在多个节点（正常情况）

### 合并算法

```python
# 伪代码
def merge_companies(original_graph, v2_skeleton, new_companies):
    result = v2_skeleton.copy()
    
    # 1. 提取原有企业映射
    original_companies = extract_companies_from_graph(original_graph)
    # 返回: {node_path: [company1, company2, ...]}
    
    # 2. 提取新增企业映射
    new_companies_map = parse_new_companies_file(new_companies)
    # 返回: {node_path: [company1, company2, ...]}
    
    # 3. 遍历所有四级及以下节点
    for node in get_level_4_plus_nodes(result):
        node_path = get_node_path(node)
        
        # 合并企业列表
        all_companies = []
        
        # 添加原有企业
        if node_path in original_companies:
            all_companies.extend(original_companies[node_path])
        
        # 添加新增企业
        if node_path in new_companies_map:
            all_companies.extend(new_companies_map[node_path])
        
        # 去重
        all_companies = deduplicate_companies(all_companies)
        
        # 挂载到节点下
        if all_companies:
            company_line = format_companies(all_companies)
            insert_after_node(result, node, company_line)
    
    return result
```

### 节点路径匹配规则

节点路径格式：`一级 > 二级 > 三级 > 四级 > 五级 > 六级`

匹配时：
1. 从 V2 图谱中提取每个节点的完整路径
2. 与新增企业清单中的节点路径匹配
3. 路径必须完全一致（包括层级和名称）

### 企业格式规范

**输入格式**（新增企业清单）：
```
企业1 (企业1全称) & 企业2 (企业2全称) & 企业3 (企业3全称)
```

**输出格式**（V3 图谱）：
```markdown
##### 节点名称
**企业1 (企业1全称) & 企业2 (企业2全称) & 企业3 (企业3全称)**
```

## 执行步骤

### 步骤 1：确认输入文件存在

检查所有输入文件是否存在：
```python
files = [
    "./图谱/intermediate/02_original_graph.md",
    "./图谱/intermediate/04_v2_optimized.md",
    "./图谱/intermediate/05_new_companies.md"
]
for f in files:
    if not os.path.exists(f):
        raise FileNotFoundError(f"输入文件不存在: {f}")
```

### 步骤 2：执行合并脚本

```bash
python scripts/merge_companies.py \
  --original ./图谱/intermediate/02_original_graph.md \
  --skeleton ./图谱/intermediate/04_v2_optimized.md \
  --new-companies ./图谱/intermediate/05_new_companies.md \
  --output ./图谱/intermediate/05_v3_with_companies.md
```

### 步骤 3：验证输出结果

检查输出文件：
- 文件是否成功生成
- 内容是否完整
- 企业格式是否正确

### 步骤 4：输出确认信息

```
✅ 企业合并完成

输入文件：
- 原始图谱：./图谱/intermediate/02_original_graph.md
- V2 骨架：./图谱/intermediate/04_v2_optimized.md
- 新增企业：./图谱/intermediate/05_new_companies.md

输出文件：
- V3 图谱：./图谱/intermediate/05_v3_with_companies.md

合并统计：
- 原有节点：{X} 个
- 原有企业：{X} 家
- 新增企业：{X} 家
- 最终企业：{X} 家
```

## 错误处理

### 错误场景 1：输入文件不存在
```
❌ 错误：输入文件不存在
文件路径：{文件路径}
请确认前置技能是否已成功执行
```

### 错误场景 2：脚本执行失败
```
❌ 错误：合并脚本执行失败
退出码：{exit_code}
错误输出：{stderr}
请检查输入文件格式是否正确
```

### 错误场景 3：节点路径匹配失败
```
⚠️ 警告：部分节点路径未匹配
未匹配节点：{节点路径列表}
可能原因：节点名称不一致或路径格式错误
```

## 质量检查

### 检查清单

1. [ ] 所有输入文件存在
2. [ ] 脚本执行成功
3. [ ] 输出文件生成
4. [ ] 原有节点完整保留
5. [ ] 原有企业完整保留
6. [ ] 新增企业正确挂载
7. [ ] 企业格式正确
8. [ ] 无重复企业

### 验证方法

```python
def validate_merge_result(v3_graph, original_graph, new_companies):
    # 检查原有节点保留
    original_nodes = extract_nodes(original_graph)
    v3_nodes = extract_nodes(v3_graph)
    assert original_nodes.issubset(v3_nodes)
    
    # 检查原有企业保留
    original_companies = extract_all_companies(original_graph)
    v3_companies = extract_all_companies(v3_graph)
    assert original_companies.issubset(v3_companies)
    
    # 检查新增企业挂载
    new_companies_set = parse_new_companies(new_companies)
    for node_path, companies in new_companies_set.items():
        v3_node_companies = get_companies_at_path(v3_graph, node_path)
        for company in companies:
            assert company in v3_node_companies
```

## 示例

### 输入：原始图谱片段
```markdown
##### 磷酸铁锂
**宁德时代 (宁德时代新能源科技股份有限公司)**
```

### 输入：V2 骨架片段
```markdown
##### 磷酸铁锂
##### 三元材料
###### 523型
```

### 输入：新增企业清单
```markdown
### 节点：动力电池 > 正极材料 > 磷酸铁锂
**层级**: 四级
**新增企业**: 比亚迪 (比亚迪股份有限公司) & 国轩高科 (国轩高科股份有限公司)

### 节点：动力电池 > 正极材料 > 三元材料 > 523型
**层级**: 五级
**新增企业**: 容百科技 (浙江容百科技股份有限公司)
```

### 输出：V3 完整图谱
```markdown
##### 磷酸铁锂
**宁德时代 (宁德时代新能源科技股份有限公司) & 比亚迪 (比亚迪股份有限公司) & 国轩高科 (国轩高科股份有限公司)**
##### 三元材料
###### 523型
**容百科技 (浙江容百科技股份有限公司)**
```

## 与其他技能的关系

- **前置技能**：05_search_new_company（查询新增企业）
- **后置技能**：06_file_exporter（导出最终文件）

## When to use me

当需要将新增企业数据合并到图谱时调用此技能。必须在 05_search_new_company 执行完成后调用。