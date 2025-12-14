<template>
  <div class="event-detail">
    <div class="header">
      <button @click="$router.push('/events')" class="btn-back">← 返回</button>
      <h2>{{ event?.title || '大事件' }}</h2>
    </div>
    
    <div class="event-container">
      <div class="background" v-if="background">
        <h3>事件背景</h3>
        <p>{{ background }}</p>
      </div>
      
      <div class="clues" v-if="foundClues.length > 0">
        <h3>已发现的线索</h3>
        <ul>
          <li v-for="clue in foundClues" :key="clue">{{ clue }}</li>
        </ul>
      </div>
      
      <div class="chat-area">
        <div class="messages" ref="messagesContainer">
          <div 
            v-for="(msg, index) in messages" 
            :key="index"
            :class="['message', msg.type]"
          >
            <div class="message-content">{{ msg.content }}</div>
          </div>
        </div>
        
        <div class="input-area">
          <input 
            v-model="inputMessage" 
            @keyup.enter="sendMessage"
            placeholder="输入你的推理或问题..."
            class="message-input"
          />
          <button @click="sendMessage" class="send-btn">发送</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { getUserEvents } from '../api'

export default {
  name: 'EventDetail',
  setup() {
    const route = useRoute()
    const router = useRouter()
    const gameStore = useGameStore()
    const eventId = route.params.id
    const event = ref(null)
    const background = ref('')
    const foundClues = ref([])
    const messages = ref([])
    const inputMessage = ref('')
    const messagesContainer = ref(null)
    let ws = null
    
    const loadEvent = async () => {
      try {
        const res = await getUserEvents(gameStore.userId)
        event.value = res.data.events.find(e => e.id === eventId)
        if (event.value) {
          background.value = event.value.background
          foundClues.value = event.value.found_clues || []
        }
      } catch (error) {
        console.error('加载事件失败:', error)
      }
    }
    
    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws/event/${gameStore.userId}/${eventId}`
      
      ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        console.log('WebSocket连接已建立')
      }
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'background') {
          background.value = data.content
          messages.value.push({
            type: 'system',
            content: data.content
          })
        } else if (data.type === 'message') {
          messages.value.push({
            type: 'assistant',
            content: data.content
          })
          scrollToBottom()
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
      }
      
      ws.onclose = () => {
        console.log('WebSocket连接已关闭')
      }
    }
    
    const sendMessage = () => {
      if (!inputMessage.value.trim() || !ws || ws.readyState !== WebSocket.OPEN) {
        return
      }
      
      messages.value.push({
        type: 'user',
        content: inputMessage.value
      })
      
      ws.send(JSON.stringify({
        message: inputMessage.value
      }))
      
      inputMessage.value = ''
      scrollToBottom()
    }
    
    const scrollToBottom = () => {
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    }
    
    onMounted(async () => {
      await loadEvent()
      connectWebSocket()
    })
    
    onUnmounted(() => {
      if (ws) {
        ws.close()
      }
    })
    
    return {
      event,
      background,
      foundClues,
      messages,
      inputMessage,
      messagesContainer,
      sendMessage
    }
  }
}
</script>

<style scoped>
.event-detail {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0a0a0a;
  background-image: 
    radial-gradient(circle at 1px 1px, rgba(255,255,255,0.15) 1px, transparent 0);
  background-size: 20px 20px;
  padding-bottom: 80px;
}

.header {
  background: rgba(20, 20, 20, 0.95);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.btn-back {
  padding: 8px 16px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1em;
}

.header h2 {
  color: #ffffff;
  font-size: 1.5em;
}

.event-container {
  flex: 1;
  max-width: 1000px;
  width: 100%;
  margin: 20px auto;
  padding: 0 20px;
}

.background {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 15px;
  padding: 30px;
  margin-bottom: 20px;
}

.background h3 {
  color: #667eea;
  margin-bottom: 15px;
}

.background p {
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.6;
}

.clues {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 15px;
  padding: 30px;
  margin-bottom: 20px;
}

.clues h3 {
  color: #667eea;
  margin-bottom: 15px;
}

.clues ul {
  list-style: none;
  padding: 0;
}

.clues li {
  padding: 10px;
  margin: 5px 0;
  background: rgba(102, 126, 234, 0.1);
  border-left: 4px solid #667eea;
  border-radius: 5px;
  color: rgba(255, 255, 255, 0.9);
}

.chat-area {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 15px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 600px;
}

.messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.message {
  margin-bottom: 20px;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant,
.message.system {
  justify-content: flex-start;
}

.message-content {
  max-width: 70%;
  padding: 12px 18px;
  border-radius: 18px;
  word-wrap: break-word;
}

.message.user .message-content {
  background: #667eea;
  color: white;
}

.message.assistant .message-content {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.message.system .message-content {
  background: rgba(255, 215, 0, 0.2);
  color: #ffd700;
  border: 1px solid rgba(255, 215, 0, 0.5);
}

.input-area {
  display: flex;
  padding: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  gap: 10px;
}

.message-input {
  flex: 1;
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  font-size: 1em;
  color: #ffffff;
}

.message-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.message-input:focus {
  outline: none;
  border-color: #667eea;
}

.send-btn {
  padding: 12px 30px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1em;
  font-weight: bold;
}

.send-btn:hover {
  background: #5568d3;
}
</style>

