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
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:1998',
        ws: true
      }
    }
  }
})

