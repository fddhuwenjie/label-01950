## How to Run

1. 启动数据库并初始化表结构

```bash
docker-compose up --build -d
```

2. 本地开发模式
- 数据库建表: 执行 schema.sql
- 后端启动: 进入 backend 目录，使用 conda 环境 SQLAIEditor，安装 requirements.txt 后运行 uvicorn app.main:app --host 0.0.0.0 --port 8000
- 前端启动: 进入 frontend-user 目录，npm install 后运行 npm run dev

## Services

- 后端 API: http://localhost:8000
- WebSocket LSP: ws://localhost:8000/ws/lsp
- 前端: http://localhost:8081
- MySQL: localhost:3306

## 测试账号

- 默认无需账号登录

## 题目内容

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

开发任务包括：
1. 编写完整的后端Python代码，实现LSP服务集成与WebSocket代理功能
2. 编写完整的前端应用代码，实现SQL编辑器及相关交互功能
3. 编写全面的单元测试和集成测试代码，验证各功能模块的正确性
4. 生成后端Python项目的requirements.txt依赖文件，明确指定所有必要的Python包及其版本号

注意事项：
- 不允许执行任何代码，仅需编写源代码和测试代码
- 后端Python环境使用conda虚拟环境SQLAIEditor(无需在代码中体现环境配置)
- 确保代码符合行业最佳实践，包含适当的注释、错误处理和日志记录

## 项目介绍

SQL AI Editor 是一个前后端分离的 SQL 编辑器系统，后端通过 SQLFluff LSP 提供语法校验与诊断推送，并提供工作区、方言、补全词条等配套接口，前端基于 Monaco Editor 实现实时高亮、自动补全、错误定位与断线重连能力。

## 测试

- 后端: pytest
- 前端: npm run test
