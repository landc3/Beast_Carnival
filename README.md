# Beast Carnival

一款AI驱动的互动游戏Demo，包含角色系统、AI对话、解谜游戏和智能狼人杀。

## 项目特色

- 🎯 **AI原生产品** - 所有交互都基于AI驱动
- 💎 **完整功能** - 角色系统、对话、解谜、狼人杀
- ✅ **模块化设计** - 易于扩展和维护
- 👥 **多人同步** - 支持实时多人游戏

## 技术栈

### 后端
- Python 3.8+
- FastAPI - Web框架
- WebSocket - 实时通信
- Redis - 状态同步
- DashScope (通义千问) - AI服务

### 前端
- Vue 3 - 前端框架
- Vue Router - 路由
- Pinia - 状态管理
- Vite - 构建工具

## 项目结构

```
Beast Carnival/
├── backend/                 # 后端代码
│   ├── main.py             # FastAPI主应用
│   ├── config.py           # 配置文件
│   ├── models/             # 数据模型
│   │   ├── character.py
│   │   ├── game.py
│   │   └── event.py
│   ├── services/           # 业务服务
│   │   ├── ai_service.py
│   │   ├── redis_service.py
│   │   ├── character_service.py
│   │   ├── event_service.py
│   │   └── werewolf_service.py
│   ├── data/               # 数据文件
│   │   ├── characters.json
│   │   └── events.json
│   └── requirements.txt
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   │   ├── WorldView.vue
│   │   │   ├── Characters.vue
│   │   │   ├── CharacterChat.vue
│   │   │   ├── Events.vue
│   │   │   ├── EventDetail.vue
│   │   │   └── Werewolf.vue
│   │   ├── router/         # 路由配置
│   │   ├── stores/         # 状态管理
│   │   ├── api/            # API接口
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 快速开始

### 1. 环境要求

- Python 3.8+
- Node.js 16+
- Redis 6+

### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `backend/.env` 文件：

```env
DASHSCOPE_API_KEY=sk-7e1aeb711dec4355b53ecd8ff0116057
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
HOST=0.0.0.0
PORT=1998
```

### 4. 启动Redis

```bash
# Windows
redis-server

# Linux/Mac
sudo systemctl start redis
```

### 5. 启动后端服务

**推荐方式（自动启动前端）：**
```bash
cd backend
python run.py
```

或者直接运行主应用（需要手动启动前端）：
```bash
cd backend
python main.py
```

后端服务将在 `http://localhost:1998` 启动

### 6. 安装前端依赖

```bash
cd frontend
npm install
```

### 7. 启动前端服务

**注意**：如果使用 `python run.py` 启动后端，前端会自动启动，无需手动执行此步骤。

手动启动前端（仅在直接使用 `python main.py` 时需要）：
```bash
cd frontend
npm run dev
```

前端服务将在 `http://localhost:4399` 启动。
多玩家访问：`http://本机ipv4地址:4399`。

## 功能说明

### 1. 世界观展示
- 游戏背景介绍
- 主持AI介绍
- 快速导航

### 2. 角色系统
- **已解锁角色**：可以查看档案、开始对话
- **未解锁角色**：显示解锁条件，鼠标悬浮查看提示
- **角色档案**：性格、背景、技能等信息

### 3. AI角色对话
- 每个角色有独立人格
- 基于对话历史的记忆系统
- 支持自定义性格特征
- 实时WebSocket通信

### 4. 大事件解谜
- 每个角色对应一个解谜事件
- AI推理引擎提供线索
- 玩家自由提问和推理
- 多分支结局

### 5. AI智能狼人杀
- 多人在线房间
- AI主持人自动推进游戏
- 公共消息+私有消息双通道
- 支持4-12人游戏
- 角色：狼人、平民、预言家、女巫、猎人

### 6. 解锁机制
- 完成新手引导 → 解锁猫（丧彪）
- 赢得3场狼人杀 → 解锁狗（旺财）
- 完成第一个大事件 → 解锁鸭子（嘎嘎）
- 作为平民获胜 → 解锁鳄鱼（鳄霸）
- 作为狼人获胜 → 解锁狼（灰影）

### 7. 真心话/大冒险（待完善）
- 游戏结束后自动生成
- 根据游戏结果选择问题类型
- AI自动生成不同难度的问题

## API文档

启动后端服务后，访问 `http://localhost:1998/docs` 查看Swagger API文档。

### 主要接口

- `GET /api/worldview` - 获取世界观
- `GET /api/characters` - 获取所有角色
- `GET /api/user/{user_id}/characters` - 获取用户角色列表
- `POST /api/user/{user_id}/characters/{character_id}/unlock` - 解锁角色
- `GET /api/user/{user_id}/events` - 获取用户事件列表
- `POST /api/werewolf/room` - 创建狼人杀房间
- `POST /api/werewolf/room/{room_id}/join` - 加入房间
- `POST /api/werewolf/room/{room_id}/start` - 开始游戏

### WebSocket端点

- `ws://localhost:1998/ws/character/{user_id}/{character_id}` - 角色对话
- `ws://localhost:1998/ws/event/{user_id}/{event_id}` - 解谜事件
- `ws://localhost:1998/ws/werewolf/{room_id}/{user_id}` - 狼人杀游戏

## 开发说明

### 添加新角色

1. 在 `backend/data/characters.json` 中添加角色信息
2. 在 `backend/data/events.json` 中添加对应的大事件
3. 前端会自动加载新角色

### 自定义AI Prompt

修改 `backend/services/ai_service.py` 中的prompt构建函数。

### 扩展游戏功能

所有服务都是模块化的，可以轻松扩展：
- 添加新的游戏模式
- 扩展角色技能
- 增加新的解谜类型

## 注意事项

1. **Redis必须运行**：多人游戏和状态同步依赖Redis
2. **API Key配置**：确保DashScope API Key正确配置
3. **WebSocket连接**：前端需要正确配置WebSocket代理
4. **用户ID**：前端使用localStorage存储用户ID，清除缓存会重置进度

## 许可证

MIT License

## 联系方式

如有问题或建议，欢迎提交Issue。





