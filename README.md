# AgentShopping

AI 驱动的智能电商平台 —— 将传统电商交易引擎与 RAG 对话式购物助手深度融合。

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    用户入口                               │
│          shopping-platform 前端 (Vue 3 / Vite)           │
│                    http://localhost:5173                  │
└─────────────┬───────────────────────────┬───────────────┘
              │                           │
              ▼                           ▼
┌─────────────────────────┐  ┌─────────────────────────────┐
│   shopping-platform     │  │    commerce-rag-agent        │
│   Java / Spring Boot    │◄─┤    Python / FastAPI          │
│   交易引擎 (port 8080)   │  │    AI 对话层 (port 8000)     │
│                         │  │                              │
│  · 用户认证 (JWT)        │  │  · LangGraph 意图路由         │
│  · 商品管理              │  │  · ChromaDB 向量检索          │
│  · 搜索 (Elasticsearch)  │  │  · BGE-M3 嵌入               │
│  · 购物车 / 订单 / 库存   │  │  · Chinese-CLIP 多模态搜索    │
│  · 支付                  │  │  · 流式对话 (SSE)             │
│  · 营销 / 秒杀           │  │  · 价格提醒 / 行为追踪        │
└───────────┬─────────────┘  └──────────────┬──────────────┘
            │                               │
            ▼                               ▼
     ┌──────────────┐              ┌──────────────┐
     │ MySQL / Redis │              │ SQLite / Redis │
     │ Elasticsearch │              │  ChromaDB     │
     │    MinIO      │              │               │
     └──────────────┘              └──────────────┘
```

## 子项目说明

### shopping-platform

完整的 Java 电商微服务后端 + Vue 3 前端，承担所有交易操作。

| 技术栈 | 版本 |
|---|---|
| Java | 17 |
| Spring Boot | 3.4.11 |
| MyBatis-Plus | 3.5.10.1 |
| MySQL | 8.x |
| Redis | 6.x+ |
| Elasticsearch | 8.x |
| MinIO | 最新版 |
| Vue 3 + Vite + Pinia | 见 `package.json` |

**Maven 模块：**

| 模块 | 职责 |
|---|---|
| `platform-app` | 应用入口 |
| `platform-common` | 公共工具类 |
| `platform-security` | JWT 认证与安全配置 |
| `platform-infrastructure` | 基础设施（Redis / ES / MinIO） |
| `platform-user` | 用户管理 |
| `platform-product` | 商品管理 |
| `platform-search` | ES 搜索 |
| `platform-cart` | 购物车 |
| `platform-order` | 订单管理 |
| `platform-inventory` | 库存管理 |
| `platform-marketing` | 营销活动 / 优惠券 |
| `platform-seckill` | 秒杀 |
| `platform-payment` | 支付 |
| `platform-job` | 定时任务 |

---

### commerce-rag-agent

基于 LangGraph 的 RAG 购物助手，支持文本与图片多模态交互。

| 技术栈 | 版本 |
|---|---|
| Python | 3.11+ |
| FastAPI | 0.115+ |
| LangGraph | 0.2+ |
| ChromaDB | 0.5+ |
| FlagEmbedding (BGE-M3) | 1.3+ |
| Chinese-CLIP (可选) | PyTorch 2.2+ |
| Vue 3 + Tailwind CSS | 调试 UI |

**LangGraph 意图路由：**

```
用户输入
   │
   ▼
intent_router（意图分类）
   │
   ├──► shopping_guide    ── 商品搜索与推荐
   ├──► product_knowledge ── 商品详情问答
   ├──► compare           ── 多商品对比
   ├──► decision_guide    ── 决策支持
   ├──► order             ── 订单查询
   ├──► purchase_help     ── 下单协助
   ├──► faq               ── 常见问题（RAG 检索）
   ├──► clarification     ── 澄清追问
   └──► chitchat          ── 闲聊兜底
           │
           ▼
         END（响应返回）
```

**API 概览（16 个路由）：**

| 路由前缀 | 功能 |
|---|---|
| `/api/chat` | 流式对话，运行 LangGraph Agent |
| `/api/commerce` | 购物车、结算预览、支付回调 |
| `/api/cart` | 购物车兼容层（对接 Java 平台） |
| `/api/products` | 商品详情、分类、评价、问答 |
| `/api/image-search` | 图片搜索 |
| `/api/voice` | TTS 语音合成、语音识别 |
| `/api/sessions` | 会话管理 |
| `/api/profile` | 用户画像 |
| `/api/alerts` | 价格提醒 |
| `/api/behavior` | 行为追踪、收藏夹、心愿单 |
| `/api/feedback` | 消息反馈 |
| `/api/ops` | 运维仪表盘 |
| `/api/catalog` | 商品数据导入 |
| `/api/docs` | 知识库文档导入 |
| `/api/upload` | 图片上传 |
| `/api/auth` | JWT 认证（与 Java 平台共享密钥） |

## 快速开始

### 环境要求

- **Java 17** + Maven 3.8+
- **Python 3.11+**
- **Node.js 18+** + npm / pnpm
- **MySQL 8.x**、**Redis 6.x+**、**Elasticsearch 8.x**（Java 平台依赖）
- **Docker**（可选，用于运行 RAG Agent）

### 1. 启动 Java 电商平台

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE shopping DEFAULT CHARACTER SET utf8mb4;"

# 启动 Redis / Elasticsearch（确保已安装）

# 构建并运行
cd shopping-platform/backend
mvn clean package -DskipTests
java -jar platform-app/target/platform-app-1.0.0-SNAPSHOT.jar

# 启动前端（另开终端）
cd shopping-platform/frontend
npm install
npm run dev
# 访问 http://localhost:5173
```

### 2. 启动 RAG Agent（Docker）

```bash
cd commerce-rag-agent

# 创建 .env 文件并配置（参考 docker-compose.yml 中的环境变量）
cp backend/.env.example backend/.env   # 如有

# Docker 启动
docker compose up -d --build

# Agent API: http://localhost:8000
# 调试 UI:  http://localhost:8080
```

### 3. 本地开发运行 RAG Agent

```bash
cd commerce-rag-agent/backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 安装依赖
pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env        # 编辑 .env 填写配置

# 启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 启动调试 UI

```bash
cd commerce-rag-agent/web-debug
npm install
npm run dev
# 访问 http://localhost:5173
```

## 项目结构

```
AgentShopping/
├── shopping-platform/              # Java 电商平台
│   ├── backend/                    # Spring Boot 后端（14 个 Maven 模块）
│   │   ├── platform-app/           #   应用入口
│   │   ├── platform-common/        #   公共模块
│   │   ├── platform-security/      #   安全认证
│   │   ├── platform-product/       #   商品服务
│   │   ├── platform-cart/          #   购物车服务
│   │   ├── platform-order/         #   订单服务
│   │   ├── platform-payment/       #   支付服务
│   │   └── ...                     #   其余模块
│   └── frontend/                   # Vue 3 前端
│
└── commerce-rag-agent/             # Python RAG Agent
    ├── backend/
    │   └── app/
    │       ├── agents/             # LangGraph Agent 节点
    │       ├── api/                # FastAPI 路由（16 个）
    │       ├── clients/            # Java 平台 HTTP 客户端
    │       ├── data/               # 商品数据、向量库
    │       └── main.py             # FastAPI 入口
    ├── web-debug/                  # Vue 3 调试 UI
    └── docker-compose.yml
```

## 两个子项目如何协作

```
用户发起对话  ──►  RAG Agent (Python:8000)
                      │
                      ├─ 意图识别 & RAG 检索
                      ├─ 生成回复（文本 / 商品卡片）
                      │
                      │  需要执行交易操作时
                      ▼
                Java Platform (Java:8080)
                      │
                      ├─ 添加购物车 / 下单 / 支付
                      ├─ 查询订单状态 / 库存
                      └─ 返回结果给 Agent → 用户
```

- **认证互通**：两端共享 JWT Secret，用户登录一次即可在两个系统间无缝切换
- **数据一致性**：所有交易数据由 Java 平台管理，Python Agent 仅负责 AI 推理

## 许可证

[MIT](LICENSE)
