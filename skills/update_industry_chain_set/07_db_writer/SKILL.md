---
name: 07_db_writer
description: 产业链图谱更新 - 第七步：数据库写入（将最终图谱写入 MySQL 数据库）
license: MIT
compatibility: opencode
metadata:
  audience: maintainers
  workflow: sequential
  input_file: ./图谱/{行业}_产业链图谱.md
---
# Role Definition

你是一名数据库操作助手，负责将更新后的产业链图谱写入 MySQL 数据库。

## 核心职责

调用 Python 脚本将最终图谱文件写入 `aicp.industry_graph` 表，完成整个更新流程。

## 输入文件

- **最终图谱文件**: `./图谱/{行业}_产业链图谱.md`
- 从任务参数中获取行业名称

## 数据库配置

```python
DB_CONFIG = {
    'host': '168.64.21.39',
    'port': 8880,
    'user': 'hiagent',
    'password': 'ePPYbo458We3_',
    'database': 'aicp'
}
```

## 目标表结构

```sql
CREATE TABLE `industry_graph` (
  `graph_content` longtext CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci COMMENT 'markdown 原始内容',
  `graph_name` varchar(255) DEFAULT NULL,
  `version` varchar(255) DEFAULT NULL,
  `create_datetime` varchar(255) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL COMMENT 'yyyymmdd hh24:mi:ss',
  `graph_json` longtext COMMENT 'json 版本的最终图谱内容',
  `graph_node_code` longtext,
  `graph_md` longtext,
  `update_datetime` varchar(255) DEFAULT NULL COMMENT 'yyyymmdd hh24:mi:ss'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3
```

## 执行脚本

### 脚本路径
`scripts/import_industry_graph_full.py`

### 调用方式
```bash
python scripts/import_industry_graph_full.py {行业名称} {图谱文件路径}
```

### 示例
```bash
python scripts/import_industry_graph_full.py 新能源汽车 ./图谱/新能源汽车_产业链图谱.md
```

### 超时设置
- **最大执行时长**: 6 分钟
- **超时处理**: 若超时，返回错误信息并建议重试

## 执行步骤

### 步骤 1：确认输入文件存在

检查最终图谱文件是否存在：
```python
import os

graph_path = f"./图谱/{行业}_产业链图谱.md"
if not os.path.exists(graph_path):
    # 检查是否有时间戳版本
    import glob
    files = glob.glob(f"./图谱/{行业}_产业链图谱_*.md")
    if files:
        graph_path = sorted(files)[-1]  # 取最新版本
    else:
        raise FileNotFoundError(f"未找到图谱文件：{graph_path}")
```

### 步骤 2：确认脚本存在

检查导入脚本是否存在：
```python
script_path = "scripts/import_industry_graph_full.py"
if not os.path.exists(script_path):
    raise FileNotFoundError(f"未找到导入脚本：{script_path}")
```

### 步骤 3：执行导入脚本

使用 `exec` 工具执行脚本：
```bash
python scripts/import_industry_graph_full.py {行业名称} {图谱文件路径}
```

**超时设置**: 6 分钟（360 秒）

### 步骤 4：验证写入结果

执行查询验证数据是否成功写入：
```sql
SELECT graph_name, version, create_datetime, LENGTH(graph_content) as content_length
FROM industry_graph
WHERE graph_name = '{行业名称}'
ORDER BY create_datetime DESC
LIMIT 1;
```

**验证要点**：
- 新记录已创建
- `graph_name` 匹配
- `graph_content` 长度合理
- `create_datetime` 为当前时间

### 步骤 5：输出确认信息

向用户展示写入结果：
```
✅ 数据库写入完成

写入信息：
- 行业：{行业名称}
- 图谱文件：{图谱文件路径}
- 写入时间：{YYYY-MM-DD HH:MM:SS}
- 内容长度：{X}字符

数据库记录：
- 图谱名称：{graph_name}
- 版本：{version}
- 创建时间：{create_datetime}
- 内容长度：{content_length}字符

后续操作：
- 可在数据库中查询最新图谱
- 可调用 02_db_fetcher 技能验证数据
```

## 错误处理

### 错误场景 1：脚本不存在
```
❌ 错误：导入脚本不存在
文件路径：scripts/import_industry_graph_full.py
请确认脚本已部署到正确位置
```

### 错误场景 2：图谱文件不存在
```
❌ 错误：图谱文件不存在
请确认技能 06 是否已成功执行
预期路径：./图谱/{行业}_产业链图谱.md
```

### 错误场景 3：脚本执行失败
```
❌ 错误：脚本执行失败
退出码：{exit_code}
错误输出：{stderr}
请检查脚本日志或联系管理员
```

### 错误场景 4：数据库连接失败
```
❌ 错误：数据库连接失败
请检查数据库配置或联系管理员
配置：168.64.21.39:8880/aicp
```

### 错误场景 5：脚本执行超时
```
⚠️ 警告：脚本执行超时（超过 6 分钟）
可能原因：数据量大，处理时间长
建议：
1. 等待几分钟后查询数据库验证
2. 若确认失败，可重试执行
```

## 版本管理

### 版本命名规则

脚本会自动生成版本号：
- 格式：`v{YYYYMMDD}_{HHMMSS}`
- 示例：`v20260414_183000`

### 历史版本保留

- 每次写入都会创建新记录
- 原有记录不会被删除或修改
- 可通过 `create_datetime` 区分版本

## 示例

### 输入
- 行业：新能源汽车
- 图谱文件：`./图谱/新能源汽车_产业链图谱.md`

### 执行命令
```bash
python scripts/import_industry_graph_full.py 新能源汽车 ./图谱/新能源汽车_产业链图谱.md
```

### 输出
```
✅ 数据库写入完成

正在执行导入脚本...
脚本执行时间：45 秒

验证查询结果：
- 图谱名称：新能源汽车
- 版本：v20260414_183000
- 创建时间：20260414 18:30:00
- 内容长度：125847 字符

✅ 数据已成功写入 aicp.industry_graph 表
```

## 注意事项

1. **只读操作原则**
   - 此技能只执行 INSERT 操作
   - 不 UPDATE 或 DELETE 原有记录
   - 确保历史版本可追溯

2. **幂等性**
   - 多次执行会创建多个版本
   - 不会覆盖原有数据

3. **超时处理**
   - 脚本可能因数据量大而执行时间长
   - 设置 6 分钟超时是合理的
   - 超时后应验证是否实际成功

## When to use me

当需要将最终图谱写入数据库时调用此技能。必须在技能 06 执行完成后调用。这是整个更新流程的最后一步。
