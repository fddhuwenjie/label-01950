# SQLFluff LSP SQL Editor

一个基于 SQLFluff LSP 的实时 SQL 语法检查编辑器，支持 SparkSQL、HiveSQL 等多种 SQL 方言。

## How to Run

### 使用 Docker Compose（推荐）

```bash
# 构建并启动所有服务
docker-compose up --build -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 本地开发

**后端启动：**
```bash
cd backend

# 创建虚拟环境（可选，项目使用 SQLAIEditor conda 环境）
# conda activate SQLAIEditor

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**前端启动：**
```bash
cd frontend-user

# 安装依赖
npm install

# 开发模式启动
npm run dev

# 构建生产版本
npm run build
```

## Services

| 服务 | 端口 | 说明 |
|------|------|------|
| Frontend | 8081 | Vue3 + Monaco Editor SQL 编辑器 |
| Backend | 8000 | FastAPI + SQLFluff LSP WebSocket 服务 |

### 访问地址

- **前端编辑器**: http://localhost:8081
- **后端 API**: http://localhost:8000
- **健康检查**: http://localhost:8000/health
- **支持的方言**: http://localhost:8000/dialects

## 测试账号

本项目无需登录认证，直接访问前端地址即可使用。

## 题目内容

### 用户需求

部署服务端环境以支持SQLFluff的语言服务器协议(LSP)服务及WebSocket代理功能，确保LSP服务能够实时接收和处理SQL代码分析请求。服务端实现需使用Python语言，采用适当的Web框架(如FastAPI或Flask)构建WebSocket代理服务，集成SQLFluff LSP服务，并配置高并发处理能力。

同时，开发一个功能完善的前端SQL编辑器应用，该编辑器需基于成熟的代码编辑组件(如Monaco Editor或Ace Editor)构建，具备以下核心功能：

1. 实时语法高亮显示，支持主流SQL方言(SparkSQL、HiveSQL等)的语法规则
2. 智能代码自动补全建议功能，提供关键字、函数名、表名等上下文相关补全
3. 通过WebSocket与后端LSP服务建立持久连接，实现SQL代码输入过程中的实时语法错误检测与即时反馈

系统架构设计应确保前后端通信的低延迟和高可靠性，具体要求包括：

- 语法错误检测响应时间需严格控制在200ms以内
- 支持主流SQL方言(SparkSQL、HiveSQL)的完整语法规则校验
- 提供清晰的错误提示信息与精确的代码行定位功能
- 实现断线重连机制，保障连接稳定性

---

## 项目架构

```
label-01950/
├── backend/                    # Python 后端服务
│   ├── app/
│   │   ├── main.py            # FastAPI 应用入口
│   │   ├── config.py          # 配置管理
│   │   ├── core/              # 核心模块（日志、异常）
│   │   ├── models/            # Pydantic 数据模型
│   │   ├── services/          # 业务服务层
│   │   │   ├── linter_service.py    # SQLFluff Linter
│   │   │   ├── completion_service.py # 代码补全
│   │   │   └── lsp_service.py       # LSP 协议处理
│   │   └── websocket/         # WebSocket 处理
│   │       ├── manager.py     # 连接管理
│   │       ├── handler.py     # 消息处理
│   │       └── protocol.py    # LSP 协议
│   ├── tests/                 # 单元测试
│   ├── requirements.txt       # Python 依赖
│   └── Dockerfile
│
├── frontend-user/             # Vue3 前端应用
│   ├── src/
│   │   ├── api/              # WebSocket 客户端
│   │   ├── stores/           # Pinia 状态管理
│   │   ├── views/            # 页面视图
│   │   ├── components/       # UI 组件
│   │   │   ├── SqlEditor.vue       # Monaco 编辑器
│   │   │   ├── StatusBar.vue       # 状态栏
│   │   │   ├── DiagnosticsPanel.vue # 问题面板
│   │   │   └── DialectSelector.vue  # 方言选择
│   │   ├── utils/            # 工具函数
│   │   └── styles/           # SCSS 样式
│   ├── package.json
│   └── Dockerfile
│
├── docs/                      # 设计文档
│   └── project_design.md
│
├── docker-compose.yml         # Docker 编排
├── .gitignore
└── README.md
```

## 核心功能

### 后端功能

- **SQLFluff 集成**: 使用 SQLFluff 3.0 进行 SQL 语法检查
- **多方言支持**: ANSI SQL、SparkSQL、HiveSQL
- **WebSocket 服务**: 实时双向通信
- **LSP 协议**: 标准语言服务器协议实现
- **高并发处理**: 异步处理 + 线程池
- **全局异常处理**: 统一错误响应
- **日志记录**: 使用 Loguru 记录关键操作

### 前端功能

- **Monaco Editor**: VS Code 同款编辑器
- **实时语法高亮**: SQL 关键字、函数、字符串等
- **智能补全**: 关键字、函数、数据类型补全
- **实时诊断**: 错误/警告/提示实时显示
- **断线重连**: 指数退避重连机制
- **状态栏**: 连接状态、诊断统计、光标位置

## 技术栈

### 后端
- Python 3.11
- FastAPI 0.109
- SQLFluff 3.0
- WebSockets
- Pydantic 2.x
- Loguru

### 前端
- Vue 3.4
- Vite 5.0
- Monaco Editor 0.45
- Ant Design Vue 4.x
- Pinia
- TypeScript
- SCSS

## API 文档

### WebSocket 端点

**连接**: `ws://localhost:8000/ws?client_id=<uuid>`

### 消息格式 (JSON-RPC 2.0)

**打开文档**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "textDocument/didOpen",
  "params": {
    "textDocument": {
      "uri": "file:///editor.sql",
      "languageId": "sql",
      "text": "SELECT * FROM users"
    }
  }
}
```

**文档变更**:
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "textDocument/didChange",
  "params": {
    "textDocument": { "uri": "file:///editor.sql" },
    "contentChanges": [{ "text": "SELECT * FROM users WHERE id = 1" }]
  }
}
```

**请求补全**:
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "textDocument/completion",
  "params": {
    "textDocument": { "uri": "file:///editor.sql" },
    "position": { "line": 0, "character": 7 }
  }
}
```

**设置方言**:
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "setDialect",
  "params": {
    "uri": "file:///editor.sql",
    "dialect": "sparksql"
  }
}
```

### HTTP 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | / | 服务器信息 |
| GET | /health | 健康检查 |
| GET | /dialects | 支持的 SQL 方言列表 |

## 测试

### 后端测试
```bash
cd backend
pytest tests/ -v --cov=app
```

### 前端测试
```bash
cd frontend-user
npm run test
```

## 性能指标

- 语法检查响应时间: < 200ms
- WebSocket 重连: 指数退避 (1s -> 2s -> 4s...)
- 最大重连次数: 10 次
- 输入防抖: 300ms

## License

MIT License
