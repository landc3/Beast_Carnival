<template>
  <div class="character-chat">
    <div class="chat-header">
      <button @click="$router.push('/characters')" class="btn-back">← 返回</button>
      <h2>{{ character?.name || '角色对话' }}</h2>
    </div>
    
    <div class="chat-container">
      <div class="messages" ref="messagesContainer">
        <div 
          v-for="(msg, index) in messages" 
          :key="index"
          :class="['message', msg.role]"
        >
          <div class="message-content">{{ msg.content }}</div>
        </div>
      </div>
      
      <div class="input-area">
        <input 
          v-model="inputMessage" 
          @keyup.enter="sendMessage"
          placeholder="输入消息..."
          class="message-input"
        />
        <button @click="sendMessage" class="send-btn">发送</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { getCharacters } from '../api'

export default {
  name: 'CharacterChat',
  setup() {
    const route = useRoute()
    const router = useRouter()
    const gameStore = useGameStore()
    const characterId = route.params.id
    const character = ref(null)
    const messages = ref([])
    const inputMessage = ref('')
    const messagesContainer = ref(null)
    let ws = null
    
    const loadCharacter = async () => {
      try {
        const res = await getCharacters()
        character.value = res.data.characters.find(c => c.id === characterId)
        if (!character.value) {
          router.push('/characters')
        }
      } catch (error) {
        console.error('加载角色失败:', error)
      }
    }
    
    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws/character/${gameStore.userId}/${characterId}`
      
      ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        console.log('WebSocket连接已建立')
        messages.value.push({
          role: 'assistant',
          content: `你好！我是${character.value?.name}，${character.value?.personality}的${character.value?.animal}。有什么想和我聊的吗？`
        })
      }
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'message') {
          messages.value.push({
            role: 'assistant',
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
        role: 'user',
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
      await loadCharacter()
      connectWebSocket()
    })
    
    onUnmounted(() => {
      if (ws) {
        ws.close()
      }
    })
    
    return {
      character,
      messages,
      inputMessage,
      messagesContainer,
      sendMessage
    }
  }
}
</script>

<style scoped>
.character-chat {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0a0a0a;
  background-image: 
    radial-gradient(circle at 1px 1px, rgba(255,255,255,0.15) 1px, transparent 0);
  background-size: 20px 20px;
  padding-bottom: 80px;
}

.chat-header {
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

.chat-header h2 {
  color: #ffffff;
  font-size: 1.5em;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-width: 900px;
  width: 100%;
  margin: 20px auto;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 15px;
  overflow: hidden;
}

.messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  max-height: calc(100vh - 280px);
}

.message {
  margin-bottom: 20px;
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant {
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

