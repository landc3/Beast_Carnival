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
    
    <!-- 事件完成弹窗 -->
    <transition name="modal">
      <div v-if="eventCompletedModal.show" class="modal-overlay" @click.self="closeEventCompletedModal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>🎉 恭喜！</h3>
            <button class="modal-close" @click="closeEventCompletedModal">×</button>
          </div>
          <div class="modal-body">
            <p class="modal-message">{{ eventCompletedModal.message }}</p>
          </div>
          <div class="modal-footer">
            <button @click="closeEventCompletedModal" class="modal-btn">确定</button>
          </div>
        </div>
      </div>
    </transition>
    
    <!-- 角色解锁弹窗 -->
    <transition name="modal">
      <div v-if="characterUnlockModal.show" class="modal-overlay" @click.self="closeCharacterUnlockModal">
        <div class="modal-content">
          <div class="modal-header">
            <h3>🎊 新角色解锁！</h3>
            <button class="modal-close" @click="closeCharacterUnlockModal">×</button>
          </div>
          <div class="modal-body">
            <p class="modal-message">恭喜你解锁了新角色：</p>
            <div class="unlocked-characters">
              <div 
                v-for="char in characterUnlockModal.characters" 
                :key="char.id"
                class="character-item"
              >
                <div class="character-name">{{ char.name }}</div>
                <div class="character-animal">{{ char.animal }}</div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button @click="closeCharacterUnlockModal" class="modal-btn">确定</button>
          </div>
        </div>
      </div>
    </transition>
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
    const eventCompletedModal = ref({
      show: false,
      message: ''
    })
    const characterUnlockModal = ref({
      show: false,
      characters: []
    })
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
          
          // 检查事件是否完成
          if (data.event_completed) {
            // 更新本地事件状态
            if (event.value) {
              event.value.completed = true
            }
            showEventCompletedModal()
          }
          
          // 检查是否有解锁的角色
          if (data.unlocked_characters && data.unlocked_characters.length > 0) {
            // 延迟显示角色解锁弹窗，让事件完成弹窗先显示
            setTimeout(() => {
              showCharacterUnlockModal(data.unlocked_characters)
            }, 1500)
          }
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
    
    const showEventCompletedModal = () => {
      eventCompletedModal.value = {
        show: true,
        message: '你太棒了！完成了第一个大事件！'
      }
    }
    
    const closeEventCompletedModal = () => {
      eventCompletedModal.value.show = false
    }
    
    const showCharacterUnlockModal = (characters) => {
      characterUnlockModal.value = {
        show: true,
        characters: characters
      }
    }
    
    const closeCharacterUnlockModal = () => {
      characterUnlockModal.value.show = false
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
      eventCompletedModal,
      characterUnlockModal,
      sendMessage,
      closeEventCompletedModal,
      closeCharacterUnlockModal
    }
  }
}
</script>

<style scoped>
.event-detail {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: transparent;
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

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  padding: 0;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  animation: modalSlideIn 0.3s ease-out;
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-50px) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-header {
  padding: 25px 30px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  color: #ffffff;
  font-size: 1.8em;
  font-weight: bold;
}

.modal-close {
  background: none;
  border: none;
  color: #ffffff;
  font-size: 2em;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background 0.2s;
}

.modal-close:hover {
  background: rgba(255, 255, 255, 0.2);
}

.modal-body {
  padding: 30px;
  color: #ffffff;
}

.modal-message {
  font-size: 1.2em;
  line-height: 1.6;
  margin-bottom: 20px;
  text-align: center;
}

.unlocked-characters {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-top: 20px;
}

.character-item {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 10px;
  padding: 15px 20px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.character-name {
  font-size: 1.3em;
  font-weight: bold;
  margin-bottom: 5px;
}

.character-animal {
  font-size: 1em;
  opacity: 0.9;
}

.modal-footer {
  padding: 20px 30px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  justify-content: center;
}

.modal-btn {
  padding: 12px 40px;
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
  border: 2px solid rgba(255, 255, 255, 0.5);
  border-radius: 25px;
  cursor: pointer;
  font-size: 1.1em;
  font-weight: bold;
  transition: all 0.3s;
}

.modal-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.7);
  transform: translateY(-2px);
}

/* 弹窗过渡动画 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
</style>

