import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // 允许外部访问
    port: 4399,
    proxy: {
      '/api': {
        target: 'http://localhost:1998',
        changeOrigin: true,
        secure: false,
        ws: false,
        timeout: 30000, // 增加代理超时时间到30秒
        configure: (proxy, _options) => {
          proxy.on('error', (err, req, res) => {
            console.error('【代理错误】', err);
            console.error('【代理错误】请求URL:', req.url);
            console.error('【代理错误】请求方法:', req.method);
            if (!res.headersSent) {
              res.writeHead(500, {
                'Content-Type': 'text/plain'
              });
              res.end('代理错误: ' + err.message);
            }
          });
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('【代理请求】发送请求到后端:', req.method, req.url);
            console.log('【代理请求】目标地址:', proxyReq.path);
          });
          proxy.on('proxyRes', (proxyRes, req, res) => {
            console.log('【代理响应】收到后端响应:', proxyRes.statusCode, req.url);
          });
          proxy.on('close', (req, socket, head) => {
            console.log('【代理关闭】连接关闭:', req.url);
          });
        }
      },
      '/ws': {
        target: 'ws://localhost:1998',
        ws: true,
        changeOrigin: true,
        secure: false
      }
    }
  }
})

