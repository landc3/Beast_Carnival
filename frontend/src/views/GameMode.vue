<template>
  <div class="game-mode">
    <div class="header">
      <h1>游戏模式</h1>
    </div>
    
    <div class="game-list">
      <div class="game-card" @click="goToWerewolf">
        <div class="game-icon">🐺</div>
        <h2>AI智能狼人杀</h2>
        <p>与AI角色一起体验经典的狼人杀游戏</p>
      </div>
    </div>
  </div>
</template>

<script>
import { useRouter } from 'vue-router'

export default {
  name: 'GameMode',
  setup() {
    const router = useRouter()
    
    const goToWerewolf = () => {
      router.push('/werewolf')
    }
    
    return {
      goToWerewolf
    }
  }
}
</script>

<style scoped>
.game-mode {
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
  margin-bottom: 40px;
}

.header h1 {
  font-size: 2.5em;
  color: #ffffff;
  font-weight: bold;
}

.game-list {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  gap: 30px;
  justify-content: center;
  flex-wrap: wrap;
}

.game-card {
  min-width: 300px;
  max-width: 350px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 40px 30px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.game-card:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.game-icon {
  font-size: 4em;
  margin-bottom: 20px;
}

.game-card h2 {
  font-size: 1.8em;
  color: #ffffff;
  margin-bottom: 15px;
}

.game-card p {
  font-size: 1em;
  color: rgba(255, 255, 255, 0.7);
  line-height: 1.6;
}
</style>

