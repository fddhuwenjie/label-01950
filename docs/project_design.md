## 系统架构

```mermaid
flowchart TD
  subgraph 前端
    FE[SQL 编辑器 Vue3]
  end
  subgraph 后端
    API[FastAPI WebSocket 代理]
    LSP[SQLFluff LSP]
    DB[(MySQL)]
  end
  FE -- WebSocket --> API
  FE -- REST API --> API
  API -- stdin/stdout --> LSP
  API -- CRUD --> DB
```

## ER 图

```mermaid
erDiagram
  WORKSPACES {
    INT id PK
    VARCHAR name
    VARCHAR dialect
    DATETIME created_at
    DATETIME updated_at
  }
  DIALECTS {
    INT id PK
    VARCHAR code
    VARCHAR label
    DATETIME created_at
  }
  COMPLETIONS {
    INT id PK
    VARCHAR category
    VARCHAR value
    VARCHAR dialect
    INT workspace_id
    DATETIME created_at
  }
  WORKSPACES ||--o{ COMPLETIONS : contains
```

## 接口清单

### HealthController
- GET /api/health

### WorkspaceController
- GET /api/workspaces
- POST /api/workspaces
- PUT /api/workspaces/{workspace_id}
- DELETE /api/workspaces/{workspace_id}

### DialectController
- GET /api/dialects

### CompletionController
- GET /api/completions
- POST /api/completions

### LspController
- WS /ws/lsp

## UI/UX 规范

- 主色调: #3B82F6
- 背景色: #F5F7FB
- 字体色: #1F2937
- 卡片圆角: 16px
- 阴影: 0 10px 30px rgba(15, 23, 42, 0.08)
- 全局间距: 8px / 16px / 24px
