# Ontology Platform

本仓库包含一个面向产业链/本体建模场景的全栈项目：

- `frontend/`：React + TypeScript + Vite
- `bff/`：Node.js + Express + TypeScript
- `backend/`：Spring Boot 3 + MyBatis-Plus
- `sql/`：数据库初始化、种子数据和全量快照

## 仓库地址

- GitHub: [https://github.com/lmh450201598/ontology_platform](https://github.com/lmh450201598/ontology_platform)
- 当前工作分支：`codex/next-feature-dev`

## 本次交付重点

本次改动除了前后端代码外，还依赖数据库中的本体规则、价格监控数据、事件跟踪演示数据等配置。

为了避免开发环境出现“代码已更新，但数据库状态不一致”的问题，建议直接使用当前库导出的完整 SQL 快照：

- 完整快照：[`sql/2026-04-16_ontology_full_snapshot.sql`](/Users/loopyotter/Documents/backup/claude_projects/ontology_platform/sql/2026-04-16_ontology_full_snapshot.sql)

这份 SQL 以当前本地 `ontology` 数据库为准，已经包含：

- 当前表结构
- 当前本体规则 / 动作类型 / 函数配置
- 碳酸锂价格监控数据
- 事件跟踪与公司关系演示数据
- 本地已修正过的数据状态

## 部署建议

### 1. 拉取代码

```bash
git clone https://github.com/lmh450201598/ontology_platform.git
cd ontology_platform
git checkout codex/next-feature-dev
```

如果后续将当前分支合并到其他分支，请以实际部署分支为准。

### 2. 初始化数据库

先确保 MySQL 可用，然后创建空库：

```sql
CREATE DATABASE ontology_20260506 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

再执行完整快照 SQL（文件位于项目根目录）：

```bash
mysql -h127.0.0.1 -P3306 -uroot -p<your_password> ontology_20260506 < ontology20260506.sql
```

> 注：本项目使用独立数据库 `ontology_20260506`，与旧版本的 `ontology` 库互不干扰，可同机并存。

### 3. 安装依赖

```bash
cd frontend && npm install
cd ../bff && npm install
cd ../backend && mvn -q -DskipTests compile
```

### 4. 启动服务

后端：

```bash
cd backend
mvn spring-boot:run
```

BFF：

```bash
cd bff
npm run dev
```

前端：

```bash
cd frontend
npm run dev
```

默认端口：

- 前端：`3010`（访问 http://localhost:3010）
- BFF：`3001`
- 后端：`8081`

> 端口与旧版本项目（前端 3000 / 后端 8080）错开，可在同一台机器上同时运行。

## 环境要求

- Java 17+
- Maven 3.8+
- Node.js 18+
- MySQL 8.x

## 关键配置

后端数据库配置在：

- [`backend/src/main/resources/application.yml`](/Users/loopyotter/Documents/backup/claude_projects/ontology_platform/backend/src/main/resources/application.yml)

默认值：

- DB: `ontology_20260506`
- User: `root`
- Password: 按本地 MySQL 实际密码填写

BFF 常用环境变量（复制 `.env.example` 为 `.env` 后修改）：

```env
PORT=3001
JAVA_BACKEND_URL=http://localhost:8081
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

## 本次功能点

- 事件跟踪中的公司关系创建 / 删除链路
- 公司关系写回动作与事件跟踪联动
- 碳酸锂价格监控与概念层价格传导分析
- 手动录入碳酸锂最新价格并生成分析报告
- 分析报告删除能力
- 价格传导图源头价格口径修正

## 验证建议

部署后建议至少验证以下场景：

1. “碳酸锂标的跟踪”可以正常加载分析报告
2. 手动输入最新价格后，会生成新的分析报告
3. 价格传导图中的源头价格与输入价格一致
4. 分析报告删除按钮可用
5. 事件跟踪页面的“创建链接 / 删除链接”只弹一条成功提示

## 说明

`sql/` 目录中保留了历史增量脚本，但如果是新环境部署，优先建议直接使用：

- `sql/2026-04-16_ontology_full_snapshot.sql`

这样最不容易遗漏本地临时修正和种子数据差异。
