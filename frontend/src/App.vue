<template>
  <div id="app">
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
import { useRouter } from 'vue-router'

export default {
  name: 'App',
  setup() {
    const router = useRouter()
    
    const goToRoute = (path) => {
      router.push(path)
    }
    
    return {
      goToRoute
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

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #0a0a0a;
  height: 100vh;
  overflow: hidden;
  color: #ffffff;
}

#app {
  min-height: 100vh;
  padding-bottom: 80px;
  overflow-y: auto;
  overflow-x: hidden;
}

.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(20, 20, 20, 0.95);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 10px 0;
  z-index: 1000;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.3);
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
  background: rgba(255, 255, 255, 0.05);
}

.nav-item.active {
  background: rgba(255, 255, 255, 0.1);
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

