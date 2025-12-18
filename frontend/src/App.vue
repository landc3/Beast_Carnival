<template>
  <div id="app" :class="{ 'allow-scroll': isWorldviewRoute }">
    <router-view />
    <nav class="bottom-nav">
      <div class="nav-item" @click="goToRoute('/')" :class="{ active: $route.path === '/' }">
        <div class="nav-icon">🌐</div>
        <span class="nav-label">世界观</span>
      </div>
      <div class="nav-item" @click="goToRoute('/characters')" :class="{ active: $route.path.startsWith('/character') }">
        <div class="nav-icon">👤</div>
        <span class="nav-label">角色</span>
      </div>
      <div class="nav-item" @click="goToRoute('/events')" :class="{ active: $route.path.startsWith('/event') }">
        <div class="nav-icon">📅</div>
        <span class="nav-label">大事件</span>
      </div>
      <div class="nav-item" @click="goToRoute('/game-mode')" :class="{ active: $route.path.startsWith('/game-mode') || $route.path.startsWith('/werewolf') }">
        <div class="nav-icon">🎮</div>
        <span class="nav-label">游戏</span>
      </div>
    </nav>
  </div>
</template>

<script>
import { computed, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { eventBus } from './utils/eventBus'

export default {
  name: 'App',
  setup() {
    const router = useRouter()
    const route = useRoute()
    
    const goToRoute = (path) => {
      // 如果当前在游戏页面，且要跳转到其他页面，触发退出确认
      if (route.path.startsWith('/werewolf') && path !== '/werewolf' && !path.startsWith('/werewolf')) {
        eventBus.emit('show-exit-confirm', path)
      } else {
        router.push(path)
      }
    }
    
    // 监听退出确认事件，确认后执行导航
    const handleExitConfirmed = (targetPath) => {
      router.push(targetPath)
    }
    eventBus.on('exit-confirmed', handleExitConfirmed)
    
    // 判断是否是世界观路由（主页或世界观详情页）
    const isWorldviewRoute = computed(() => {
      return route.path === '/' || route.path === '/worldview'
    })
    
    onUnmounted(() => {
      // 移除事件监听
      eventBus.off('exit-confirmed', handleExitConfirmed)
    })
    
    return {
      goToRoute,
      isWorldviewRoute
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  height: 100%;
  overflow: hidden;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: linear-gradient(135deg, #1a0a2e 0%, #16213e 25%, #0f3460 50%, #533483 75%, #1a0a2e 100%);
  background-attachment: fixed;
  height: 100%;
  overflow: hidden;
  color: #ffffff;
  position: relative;
}

body::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: 0;
}

#app {
  height: 100vh;
  padding-bottom: 80px;
  overflow-y: hidden;
  overflow-x: hidden;
  position: relative;
  z-index: 1;
}

/* 只有世界观界面允许滚动 */
#app.allow-scroll {
  overflow-y: auto;
  /* 隐藏滚动条但保持滚动功能 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

#app.allow-scroll::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(180deg, rgba(26, 10, 46, 0.95) 0%, rgba(19, 33, 62, 0.95) 50%, rgba(83, 52, 131, 0.95) 100%);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.15);
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 10px 0;
  z-index: 1000;
  box-shadow: 0 -2px 20px rgba(83, 52, 131, 0.4);
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 8px 20px;
  transition: all 0.3s ease;
  border-radius: 8px;
  min-width: 70px;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.nav-item.active {
  background: rgba(255, 255, 255, 0.15);
  box-shadow: 0 2px 10px rgba(83, 52, 131, 0.3);
}

.nav-icon {
  font-size: 1.8em;
  margin-bottom: 4px;
  filter: brightness(0.8);
  transition: all 0.3s ease;
}

.nav-item.active .nav-icon {
  filter: brightness(1.2);
  transform: scale(1.1);
}

.nav-label {
  font-size: 0.85em;
  color: rgba(255, 255, 255, 0.7);
  transition: all 0.3s ease;
}

.nav-item.active .nav-label {
  color: rgba(255, 255, 255, 1);
  font-weight: 500;
}
</style>

