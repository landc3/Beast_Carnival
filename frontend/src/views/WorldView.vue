<template>
  <div class="home">
    <div class="header">
      <h1 class="main-title">Beast Carnival</h1>
      <p class="subtitle">萌原镇的秘密</p>
    </div>
    
    <div class="cards-container">
      <div class="card-row">
        <div class="category-card" @click="goToWorldView">
          <div class="card-title">世界观</div>
          <div class="card-subtitle">已更新 {{ stats.worldview }}项</div>
          <div class="card-icon">▼</div>
        </div>
        
        <div class="category-card" @click="goToCharacters">
          <div class="card-title">角色</div>
          <div class="card-subtitle">已更新 {{ stats.characters }}项</div>
          <div class="card-icon">▼</div>
        </div>
        
        <div class="category-card" @click="goToEvents">
          <div class="card-title">大事件</div>
          <div class="card-subtitle">已更新 {{ stats.events }}项</div>
          <div class="card-icon">▼</div>
        </div>
      </div>
      
      <div class="card-row">
        <div class="category-card" @click="goToGameMode">
          <div class="card-title">游戏模式</div>
          <div class="card-subtitle">已更新 {{ stats.gameMode }}项</div>
          <div class="card-icon">▼</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getWorldView, getCharacters, getUserEvents } from '../api'
import { useGameStore } from '../stores/game'

export default {
  name: 'WorldView',
  setup() {
    const router = useRouter()
    const gameStore = useGameStore()
    const stats = ref({
      worldview: 26,
      characters: 30,
      events: 11,
      gameMode: 1
    })
    
    const loadStats = async () => {
      try {
        // 加载统计数据
        const [charsRes, eventsRes] = await Promise.all([
          getCharacters().catch(() => ({ data: { characters: [] } })),
          getUserEvents(gameStore.userId).catch(() => ({ data: { events: [] } }))
        ])
        
        stats.value.characters = charsRes.data.characters?.length || 30
        stats.value.events = eventsRes.data.events?.length || 11
      } catch (error) {
        console.error('加载统计数据失败:', error)
      }
    }
    
    onMounted(loadStats)
    
    const goToWorldView = () => {
      // 可以导航到一个详细的世界观页面，或者保持当前页面
      // 暂时不做操作，或者可以显示世界观详情
    }
    
    const goToCharacters = () => router.push('/characters')
    const goToEvents = () => router.push('/events')
    const goToGameMode = () => router.push('/game-mode')
    
    return {
      stats,
      goToWorldView,
      goToCharacters,
      goToEvents,
      goToGameMode
    }
  }
}
</script>

<style scoped>
.home {
  height: 100vh;
  padding: 40px 20px 100px;
  background: #0a0a0a;
  background-image: 
    radial-gradient(circle at 1px 1px, rgba(255,255,255,0.15) 1px, transparent 0);
  background-size: 20px 20px;
  overflow: hidden;
  box-sizing: border-box;
}

.header {
  text-align: center;
  margin-bottom: 60px;
}

.main-title {
  font-size: 3.5em;
  color: #ffffff;
  margin-bottom: 10px;
  font-weight: bold;
  letter-spacing: 2px;
}

.subtitle {
  font-size: 1.2em;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 300;
}

.cards-container {
  max-width: 1200px;
  margin: 0 auto;
}

.card-row {
  display: flex;
  gap: 30px;
  margin-bottom: 30px;
  justify-content: center;
  flex-wrap: wrap;
}

.category-card {
  flex: 1;
  min-width: 250px;
  max-width: 280px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 30px 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  min-height: 200px;
}

.category-card:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.card-title {
  font-size: 2.5em;
  color: #ffffff;
  writing-mode: vertical-rl;
  text-orientation: upright;
  letter-spacing: 8px;
  margin: 20px 0;
  font-weight: bold;
}

.card-subtitle {
  font-size: 0.9em;
  color: rgba(255, 255, 255, 0.6);
  margin-top: auto;
  margin-bottom: 10px;
}

.card-icon {
  position: absolute;
  right: 15px;
  bottom: 15px;
  color: #ffd700;
  font-size: 1.2em;
}

@media (max-width: 768px) {
  .main-title {
    font-size: 2.5em;
  }
  
  .card-row {
    flex-direction: column;
    align-items: center;
  }
  
  .category-card {
    max-width: 100%;
    width: 100%;
  }
}
</style>

