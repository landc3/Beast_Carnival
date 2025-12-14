<template>
  <div class="werewolf">
    <div class="game-container">
      <!-- 左侧角色面板 -->
      <div class="left-panel">
        <div class="panel-header">
          <span class="game-badge">Beast Carnival</span>
          <h1 class="game-title">狼人杀</h1>
        </div>
        
        <!-- 进度条 -->
        <div class="progress-section">
          <div class="progress-line" :style="{ '--progress': gameProgress + '%' }"></div>
          <span class="progress-text">{{ gameProgress }}%</span>
        </div>
        
        <!-- 创建/加入房间 -->
        <div v-if="!roomId" class="create-room">
          <input v-model="username" placeholder="输入你的名字" class="input" />
          <button @click="createRoom" class="btn-primary">创建房间</button>
          <input v-model="joinRoomId" placeholder="或输入房间号加入" class="input" />
          <button @click="joinRoom" class="btn-secondary">加入房间</button>
        </div>
        
        <!-- 房间信息 -->
        <div v-else class="room-info">
          <div class="room-details">
            <p class="room-id">房间号：{{ roomId }}</p>
            <p class="player-count">玩家数：{{ room?.players?.length || 0 }}/7</p>
          </div>
          <div v-if="room?.phase === 'waiting' && room?.players?.length >= 4">
            <button @click="startGame" class="btn-start">开始游戏</button>
          </div>
        </div>
        
        <!-- 角色头像网格 -->
        <div class="characters-grid">
          <div 
            v-for="(player, index) in displayPlayers" 
            :key="player?.user_id || index"
            class="character-slot"
            :class="{ 
              'has-player': player,
              'alive': player?.alive,
              'dead': player && !player.alive
            }"
          >
            <div class="character-avatar">
              <div v-if="player" class="avatar-content">
                <div class="avatar-icon">{{ getCharacterIcon(player.role) }}</div>
                <div class="avatar-name">{{ player.username }}</div>
              </div>
              <div v-else class="avatar-empty"></div>
            </div>
            <div v-if="player && !player.alive" class="death-indicator">●</div>
          </div>
        </div>
      </div>
      
      <!-- 右侧聊天面板 -->
      <div class="right-panel">
        <div class="chat-header">
          <h2 class="chat-title">AI Host</h2>
          <button @click="closeChat" class="close-btn">×</button>
        </div>
        
        <div class="messages" ref="messagesContainer">
          <div 
            v-for="(msg, index) in publicMessages" 
            :key="index"
            :class="['message-bubble', msg.type]"
          >
            <div class="message-avatar">
              <div class="avatar-icon-small">{{ getMessageAvatar(msg) }}</div>
            </div>
            <div class="message-content-wrapper">
              <div class="message-content">
                {{ msg.content }}
              </div>
              <div class="message-sender">{{ msg.username || 'AI主持人' }}</div>
            </div>
          </div>
        </div>
        
        <div class="input-area">
          <div class="input-icon">1</div>
          <input 
            v-model="inputMessage" 
            @keyup.enter="sendMessage"
            placeholder="输入消息..."
            class="message-input"
          />
          <button @click="sendMessage" class="send-button">发送</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { createWerewolfRoom, joinWerewolfRoom, startWerewolfGame, getWerewolfRoom } from '../api'

export default {
  name: 'Werewolf',
  setup() {
    const router = useRouter()
    const gameStore = useGameStore()
    const roomId = ref('')
    const joinRoomId = ref('')
    const username = ref(gameStore.username)
    const room = ref(null)
    const publicMessages = ref([])
    const privateMessages = ref([])
    const inputMessage = ref('')
    const messagesContainer = ref(null)
    let ws = null
    let pollInterval = null
    
    const createRoom = async () => {
      try {
        const res = await createWerewolfRoom()
        roomId.value = res.data.room_id
        await joinRoom(res.data.room_id)
      } catch (error) {
        console.error('创建房间失败:', error)
        alert('创建房间失败')
      }
    }
    
    const joinRoom = async (targetRoomId = null) => {
      const targetId = targetRoomId || joinRoomId.value
      if (!targetId) {
        alert('请输入房间号')
        return
      }
      
      try {
        await joinWerewolfRoom(targetId, gameStore.userId, username.value)
        roomId.value = targetId
        gameStore.setUsername(username.value)
        connectWebSocket()
        startPolling()
      } catch (error) {
        console.error('加入房间失败:', error)
        alert('加入房间失败')
      }
    }
    
    const startGame = async () => {
      try {
        await startWerewolfGame(roomId.value)
        loadRoom()
      } catch (error) {
        console.error('开始游戏失败:', error)
        alert('开始游戏失败')
      }
    }
    
    const loadRoom = async () => {
      if (!roomId.value) return
      try {
        const res = await getWerewolfRoom(roomId.value)
        room.value = res.data
      } catch (error) {
        console.error('加载房间失败:', error)
      }
    }
    
    const connectWebSocket = () => {
      if (!roomId.value) return
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = `${protocol}//${window.location.host}/ws/werewolf/${roomId.value}/${gameStore.userId}`
      
      ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        console.log('WebSocket连接已建立')
      }
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'room_state') {
          room.value = data.room
        } else if (data.type === 'public_message') {
          const message = typeof data.content === 'string' 
            ? { content: data.content, username: data.username || 'AI主持人', type: data.message_type || 'user' }
            : { ...data.content, type: data.content.type || data.message_type || 'user' }
          publicMessages.value.push(message)
          scrollToBottom()
        } else if (data.type === 'private_message') {
          privateMessages.value.push(data.content)
        } else if (data.type === 'room_update') {
          room.value = data.room
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
      
      // 立即显示用户消息
      publicMessages.value.push({
        content: inputMessage.value,
        username: username.value || '我',
        type: 'user'
      })
      scrollToBottom()
      
      ws.send(JSON.stringify({
        type: 'message',
        content: inputMessage.value
      }))
      
      inputMessage.value = ''
    }
    
    const startPolling = () => {
      pollInterval = setInterval(loadRoom, 2000)
    }
    
    const scrollToBottom = () => {
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    }
    
    const isCurrentUser = (userId) => {
      return userId === gameStore.userId
    }
    
    const getRoleName = (role) => {
      const names = {
        'wolf': '狼人',
        'villager': '平民',
        'seer': '预言家',
        'witch': '女巫',
        'hunter': '猎人'
      }
      return names[role] || '未知'
    }
    
    const getCharacterIcon = (role) => {
      const icons = {
        'wolf': '🐺',
        'villager': '🐑',
        'seer': '🔮',
        'witch': '🧪',
        'hunter': '🏹'
      }
      return icons[role] || '👤'
    }
    
    const getMessageAvatar = (msg) => {
      if (msg.role === 'system' || !msg.username) {
        return '🎭'
      }
      return '👤'
    }
    
    const closeChat = () => {
      router.push('/game-mode')
    }
    
    const gameProgress = ref(0)
    
    const displayPlayers = computed(() => {
      const players = room.value?.players || []
      const maxSlots = 12 // 4行3列
      const slots = Array(maxSlots).fill(null)
      players.forEach((player, index) => {
        if (index < maxSlots) {
          slots[index] = player
        }
      })
      return slots
    })
    
    // 计算游戏进度
    watch(() => room.value?.players?.length, (newLength) => {
      if (newLength) {
        gameProgress.value = Math.round((newLength / 7) * 100)
      }
    }, { immediate: true })
    
    onMounted(() => {
      // 初始化
    })
    
    onUnmounted(() => {
      if (ws) {
        ws.close()
      }
      if (pollInterval) {
        clearInterval(pollInterval)
      }
    })
    
    return {
      roomId,
      joinRoomId,
      username,
      room,
      publicMessages,
      privateMessages,
      inputMessage,
      messagesContainer,
      gameProgress,
      displayPlayers,
      createRoom,
      joinRoom,
      startGame,
      sendMessage,
      isCurrentUser,
      getRoleName,
      getCharacterIcon,
      getMessageAvatar,
      closeChat
    }
  }
}
</script>

<style scoped>
.werewolf {
  min-height: 100vh;
  padding: 0;
  background: #000000;
  display: flex;
  flex-direction: column;
  position: relative;
}

.game-container {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 0;
  height: calc(100vh - 80px);
  max-height: calc(100vh - 80px);
}

/* 左侧面板 - 深色大理石纹理 */
.left-panel {
  background: 
    linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 50%, #1a1a1a 100%),
    repeating-linear-gradient(
      45deg,
      transparent,
      transparent 10px,
      rgba(0, 0, 0, 0.1) 10px,
      rgba(0, 0, 0, 0.1) 20px
    );
  background-blend-mode: overlay;
  padding: 30px 20px;
  overflow-y: auto;
  border-right: 2px solid rgba(100, 150, 200, 0.2);
}

.panel-header {
  margin-bottom: 20px;
}

.game-badge {
  display: inline-block;
  background: rgba(255, 255, 255, 0.9);
  color: #000;
  padding: 4px 16px;
  border-radius: 20px;
  font-size: 0.8em;
  font-weight: 600;
  margin-bottom: 10px;
  letter-spacing: 0.5px;
}

.game-title {
  color: #ffffff;
  font-size: 2.5em;
  font-weight: bold;
  margin: 0;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.progress-section {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 25px;
}

.progress-line {
  flex: 1;
  height: 3px;
  background: linear-gradient(90deg, #ff6b35 0%, #ff6b35 var(--progress, 40%), rgba(255, 255, 255, 0.2) var(--progress, 40%), rgba(255, 255, 255, 0.2) 100%);
  border-radius: 2px;
}

.progress-text {
  color: #ffffff;
  font-size: 0.9em;
  font-weight: 500;
  min-width: 45px;
}

.create-room,
.room-info {
  margin-bottom: 25px;
}

.create-room {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.input {
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  font-size: 0.9em;
  color: #ffffff;
}

.input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.btn-primary,
.btn-secondary,
.btn-start {
  padding: 10px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9em;
  font-weight: bold;
  color: white;
  transition: all 0.3s ease;
}

.btn-primary {
  background: #667eea;
}

.btn-primary:hover {
  background: #5568d3;
}

.btn-secondary {
  background: #48bb78;
}

.btn-secondary:hover {
  background: #38a169;
}

.btn-start {
  background: #ff6b35;
  width: 100%;
  margin-top: 10px;
}

.btn-start:hover {
  background: #e55a2b;
}

.room-details {
  margin-bottom: 15px;
}

.room-id,
.player-count {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9em;
  margin: 5px 0;
}

/* 角色头像网格 */
.characters-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 20px;
}

.character-slot {
  position: relative;
  aspect-ratio: 1;
  background: rgba(0, 0, 0, 0.4);
  border: 2px solid rgba(100, 150, 200, 0.3);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.character-slot.has-player {
  border-color: rgba(100, 150, 200, 0.6);
  background: rgba(30, 40, 60, 0.6);
}

.character-slot.alive {
  border-color: rgba(72, 187, 120, 0.6);
}

.character-slot.dead {
  opacity: 0.5;
  border-color: rgba(229, 62, 62, 0.6);
}

.character-avatar {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.avatar-content {
  text-align: center;
  width: 100%;
  padding: 8px;
}

.avatar-icon {
  font-size: 2.5em;
  margin-bottom: 5px;
}

.avatar-name {
  color: #ffffff;
  font-size: 0.75em;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.avatar-empty {
  width: 60%;
  height: 60%;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 50%;
}

.death-indicator {
  position: absolute;
  top: 5px;
  right: 5px;
  color: #e53e3e;
  font-size: 1.2em;
  font-weight: bold;
}

/* 右侧面板 - 神秘黑色 */
.right-panel {
  background: 
    linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%),
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(100, 150, 200, 0.05) 2px,
      rgba(100, 150, 200, 0.05) 4px
    );
  background-blend-mode: overlay;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-shadow: inset 0 0 50px rgba(0, 0, 0, 0.5);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  border-bottom: 2px solid rgba(100, 150, 200, 0.3);
}

.chat-title {
  color: #ffffff;
  font-size: 1.8em;
  font-weight: bold;
  margin: 0;
  text-shadow: 0 0 10px rgba(100, 150, 200, 0.5), 2px 2px 4px rgba(0, 0, 0, 0.8);
}

.close-btn {
  background: none;
  border: none;
  color: #ffffff;
  font-size: 2em;
  cursor: pointer;
  width: 35px;
  height: 35px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.3s ease;
}

.close-btn:hover {
  background: rgba(100, 150, 200, 0.2);
  color: rgba(255, 255, 255, 0.8);
}

.messages {
  flex: 1;
  padding: 20px 25px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.message-bubble {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.message-avatar {
  flex-shrink: 0;
}

.avatar-icon-small {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(100, 150, 200, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5em;
  border: 2px solid rgba(100, 150, 200, 0.4);
}

.message-content-wrapper {
  flex: 1;
  min-width: 0;
}

.message-content {
  background: rgba(255, 255, 255, 0.1);
  padding: 12px 16px;
  border-radius: 12px;
  color: #e0e0e0;
  font-size: 0.95em;
  line-height: 1.5;
  word-wrap: break-word;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
  margin-bottom: 5px;
  border: 1px solid rgba(100, 150, 200, 0.2);
}

.message-bubble.system .message-content {
  background: rgba(255, 215, 0, 0.15);
  color: #ffd700;
  border-color: rgba(255, 215, 0, 0.3);
}

.message-sender {
  color: rgba(200, 200, 200, 0.7);
  font-size: 0.8em;
  margin-left: 5px;
}

.input-area {
  display: flex;
  align-items: center;
  padding: 15px 25px;
  border-top: 2px solid rgba(100, 150, 200, 0.3);
  gap: 10px;
  background: rgba(10, 10, 10, 0.8);
}

.input-icon {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(100, 150, 200, 0.2);
  border-radius: 50%;
  color: #ffffff;
  font-size: 0.9em;
  font-weight: bold;
  flex-shrink: 0;
  border: 1px solid rgba(100, 150, 200, 0.3);
}

.message-input {
  flex: 1;
  padding: 12px 15px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(100, 150, 200, 0.3);
  border-radius: 20px;
  font-size: 0.95em;
  color: #e0e0e0;
}

.message-input::placeholder {
  color: rgba(200, 200, 200, 0.5);
}

.message-input:focus {
  outline: none;
  border-color: rgba(100, 150, 200, 0.6);
  background: rgba(255, 255, 255, 0.15);
  box-shadow: 0 0 10px rgba(100, 150, 200, 0.3);
}

.send-button {
  padding: 12px 24px;
  background: rgba(100, 150, 200, 0.8);
  color: #ffffff;
  border: 1px solid rgba(100, 150, 200, 0.5);
  border-radius: 20px;
  font-size: 0.95em;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  flex-shrink: 0;
  box-shadow: 0 0 10px rgba(100, 150, 200, 0.3);
}

.send-button:hover {
  background: rgba(100, 150, 200, 1);
  transform: translateY(-1px);
  box-shadow: 0 0 15px rgba(100, 150, 200, 0.5);
}

.send-button:active {
  transform: translateY(0);
}

/* 滚动条样式 */
.messages::-webkit-scrollbar,
.left-panel::-webkit-scrollbar {
  width: 8px;
}

.messages::-webkit-scrollbar-track,
.left-panel::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.1);
}

.messages::-webkit-scrollbar-thumb,
.left-panel::-webkit-scrollbar-thumb {
  background: rgba(139, 115, 85, 0.3);
  border-radius: 4px;
}

.messages::-webkit-scrollbar-thumb:hover,
.left-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(139, 115, 85, 0.5);
}
</style>

