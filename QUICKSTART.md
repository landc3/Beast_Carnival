# 快速开始指南

## 前置要求

1. **Python 3.8+**
   ```bash
   python --version
   ```

2. **Node.js 16+**
   ```bash
   node --version
   ```

3. **Redis**
   - Windows: 下载并安装 [Redis for Windows](https://github.com/microsoftarchive/redis/releases)
   - Linux: `sudo apt-get install redis-server`
   - Mac: `brew install redis`

## 安装步骤

### 1. 克隆项目（如果从Git仓库）

```bash
git clone <repository-url>
cd "Beast Carnival"
```

### 2. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `backend/.env` 文件（复制 `.env.example`）：

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

编辑 `.env` 文件，确保API Key正确：

```env
DASHSCOPE_API_KEY=sk-7e1aeb711dec4355b53ecd8ff0116057
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
HOST=0.0.0.0
PORT=8000
```

### 4. 启动Redis

**Windows:**
```bash
redis-server
```

**Linux/Mac:**
```bash
# 启动Redis服务
sudo systemctl start redis
# 或
redis-server
```

验证Redis是否运行：
```bash
redis-cli ping
# 应该返回: PONG
```

### 5. 启动后端服务

```bash
cd backend
python main.py
```

或者使用uvicorn直接运行：
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将在 `http://localhost:8000` 启动

### 6. 安装前端依赖

打开新的终端窗口：

```bash
cd frontend
npm install
```

### 7. 启动前端服务

```bash
npm run dev
```

前端服务将在 `http://localhost:3000` 启动

## 使用一键启动脚本

### Windows

```bash
start.bat
```

### Linux/Mac

```bash
chmod +x start.sh
./start.sh
```

## 验证安装

1. 打开浏览器访问 `http://localhost:3000`
2. 应该看到"猛兽派对"首页
3. 点击"查看角色"应该能看到角色列表
4. 点击"开始狼人杀"可以创建房间

## 常见问题

### 1. Redis连接失败

**错误**: `Connection refused` 或 `无法连接到Redis`

**解决**:
- 确保Redis服务正在运行
- 检查 `REDIS_HOST` 和 `REDIS_PORT` 配置
- Windows用户可能需要手动启动Redis服务器

### 2. API Key错误

**错误**: `AI服务错误` 或 `401 Unauthorized`

**解决**:
- 检查 `backend/.env` 文件中的 `DASHSCOPE_API_KEY` 是否正确
- 确保API Key有效且有足够的额度

### 3. 端口被占用

**错误**: `Address already in use`

**解决**:
- 修改 `backend/.env` 中的 `PORT` 配置
- 或修改 `frontend/vite.config.js` 中的端口配置

### 4. 前端无法连接后端

**错误**: `Network Error` 或 `CORS Error`

**解决**:
- 确保后端服务正在运行
- 检查 `frontend/vite.config.js` 中的代理配置
- 确保后端CORS配置允许前端域名

### 5. WebSocket连接失败

**错误**: `WebSocket connection failed`

**解决**:
- 确保后端服务正在运行
- 检查防火墙设置
- 如果使用HTTPS，确保WebSocket使用WSS协议

## 开发模式

### 后端热重载

使用 `uvicorn` 的 `--reload` 参数：

```bash
cd backend
uvicorn main:app --reload
```

### 前端热重载

Vite默认支持热重载，修改代码后自动刷新。

## 生产部署

### 后端

使用Gunicorn + Uvicorn：

```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 前端

构建生产版本：

```bash
cd frontend
npm run build
```

构建产物在 `frontend/dist` 目录，可以部署到任何静态文件服务器。

## 多人游戏 - 让其他设备访问

### 问题修复

已修复以下问题：
1. ✅ 修复了"加入房间"按钮点击时传递事件对象的问题
2. ✅ 配置前端服务器绑定到 `0.0.0.0`，允许外部设备访问

### 如何让其他设备加入游戏

#### 1. 获取服务器IP地址

**Windows:**
```bash
ipconfig
```
查找 "IPv4 地址"，例如：`192.168.1.100`

**Linux/Mac:**
```bash
ifconfig
# 或
ip addr show
```
查找局域网IP地址，例如：`192.168.1.100`

#### 2. 确保服务已正确启动

- **后端服务**：已配置为绑定到 `0.0.0.0:1998`（在 `backend/config.py` 中）
- **前端服务**：已配置为绑定到 `0.0.0.0:4399`（在 `frontend/vite.config.js` 中）

#### 3. 配置防火墙

**Windows:**
1. 打开"Windows Defender 防火墙"
2. 点击"高级设置"
3. 添加入站规则，允许端口 `4399` 和 `1998` 的TCP连接

**Linux:**
```bash
sudo ufw allow 4399/tcp
sudo ufw allow 1998/tcp
```

#### 4. 其他设备访问

在同一局域网内的其他设备（手机、平板、其他电脑）上：

1. 打开浏览器
2. 访问：`http://<服务器IP>:4399`
   - 例如：`http://192.168.1.100:4399`
3. 创建房间或输入房间号加入游戏

#### 5. 注意事项

- ✅ 所有设备必须在**同一局域网**内
- ✅ 确保防火墙允许端口 `4399` 和 `1998` 的访问
- ✅ 如果使用移动数据，无法通过局域网IP访问，需要使用内网穿透工具（如 ngrok、frp 等）
- ✅ 房间号在服务器上共享，所有连接到同一服务器的玩家可以看到相同的房间

### 跨网络访问（可选）

如果需要跨网络访问（例如朋友不在同一局域网），可以使用内网穿透工具：

**使用 ngrok（示例）:**
```bash
# 安装 ngrok
# 然后运行
ngrok http 4399
```

这会生成一个公网URL，例如：`https://xxxx.ngrok.io`，其他人可以通过这个URL访问。

## 下一步

- 查看 [README.md](README.md) 了解项目详情
- 查看 API 文档: `http://localhost:8000/docs`
- 开始探索游戏功能！



