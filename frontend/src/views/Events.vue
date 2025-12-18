<template>
  <div class="events">
    <div class="header">
      <h1>大事件</h1>
    </div>
    
    <div class="events-container">
      <div 
        v-for="event in events" 
        :key="event.id"
        class="event-card"
        :class="{ completed: event.completed }"
        @click="goToEvent(event.id)"
      >
        <h3>{{ event.title }}</h3>
        <p class="character">角色：{{ getCharacterName(event.character_id) }}</p>
        <p class="status" v-if="event.completed">✅ 已完成</p>
        <p class="status" v-else>🔍 进行中</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { getUserEvents, getCharacters } from '../api'

export default {
  name: 'Events',
  setup() {
    const router = useRouter()
    const gameStore = useGameStore()
    const events = ref([])
    const characters = ref([])
    
    const loadEvents = async () => {
      try {
        const [eventsRes, charsRes] = await Promise.all([
          getUserEvents(gameStore.userId),
          getCharacters()
        ])
        events.value = eventsRes.data.events
        characters.value = charsRes.data.characters
      } catch (error) {
        console.error('加载事件失败:', error)
      }
    }
    
    const getCharacterName = (characterId) => {
      const char = characters.value.find(c => c.id === characterId)
      return char ? char.name : '未知'
    }
    
    const goToEvent = (eventId) => {
      router.push(`/event/${eventId}`)
    }
    
    onMounted(loadEvents)
    
    return {
      events,
      getCharacterName,
      goToEvent
    }
  }
}
</script>

<style scoped>
.events {
  min-height: 100vh;
  padding: 40px 20px 100px;
  background: transparent;
  box-sizing: border-box;
}

.header {
  max-width: 1200px;
  margin: 0 auto 40px;
  text-align: center;
}

.header h1 {
  color: #ffffff;
  font-size: 2.5em;
  font-weight: bold;
}

.events-container {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 30px;
}

.event-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 15px;
  padding: 30px;
  cursor: pointer;
  transition: all 0.3s;
}

.event-card:hover {
  transform: translateY(-5px);
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.event-card.completed {
  opacity: 0.8;
  background: rgba(102, 126, 234, 0.1);
  border-color: rgba(102, 126, 234, 0.3);
}

.event-card h3 {
  font-size: 1.5em;
  color: #ffffff;
  margin-bottom: 15px;
}

.character {
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 10px;
}

.status {
  color: #667eea;
  font-weight: bold;
  margin-top: 10px;
}
</style>

