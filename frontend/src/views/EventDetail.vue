<template>
  <div class="event-detail" :class="{ 'duck-mystery': isDuckMystery }">
    <div class="header">
      <button @click="$router.push('/events')" class="btn-back">← 返回</button>
      <h2>{{ event?.title || '大事件' }}</h2>
    </div>
    
    <!-- 嘎嘎事件专用界面 -->
    <div v-if="isDuckMystery" class="duck-mystery-container">
      <!-- 首页：标题 + 开始游戏按钮 -->
      <div v-if="currentStep === 'home'" class="step-home">
        <div class="title-box">
          <h1 class="main-title">失踪的钻石项链</h1>
          <p class="subtitle">一个豪华游轮上的神秘案件</p>
        </div>
        <button @click="startGame" class="start-btn">开始游戏</button>
      </div>
      
      <!-- 故事页：背景故事 + 查看线索按钮 -->
      <div v-if="currentStep === 'story'" class="step-story">
        <div class="story-box">
          <h2 class="section-title">事件背景</h2>
          <p class="story-text">{{ background }}</p>
        </div>
        <button @click="showClues" class="clues-btn">查看线索</button>
      </div>
      
      <!-- 线索展示 -->
      <div v-if="currentStep === 'clues'" class="step-clues">
        <div class="story-box">
          <h2 class="section-title">事件背景</h2>
          <p class="story-text">{{ background }}</p>
        </div>
        <div class="clues-box">
          <h2 class="section-title">关键线索</h2>
          <ul class="clues-list">
            <li v-for="(clue, index) in clues" :key="index" class="clue-item">
              {{ clue }}
            </li>
          </ul>
        </div>
        <button @click="goToAnswer" class="answer-btn">开始答题</button>
      </div>
      
      <!-- 答题页：两个输入框 + 提交按钮 -->
      <div v-if="currentStep === 'answer'" class="step-answer">
        <button @click="goBackToClues" class="btn-back-to-clues">← 返回查看线索</button>
        <div class="questions-box">
          <h2 class="section-title">请回答以下问题</h2>
          <div class="question-item">
            <label class="question-label">谁偷了项链？</label>
            <input 
              v-model="answer1" 
              placeholder="请输入你的答案..."
              class="answer-input"
            />
          </div>
          <div class="question-item">
            <label class="question-label">他是怎么做到的？</label>
            <textarea 
              v-model="answer2" 
              placeholder="请详细描述作案手法..."
              class="answer-textarea"
              rows="4"
            ></textarea>
          </div>
          <button @click="submitAnswers" class="submit-btn" :disabled="!answer1.trim() || !answer2.trim()">
            提交答案
          </button>
        </div>
      </div>
      
      <!-- 结果页：显示判断结果 -->
      <div v-if="currentStep === 'result'" class="step-result">
        <div class="result-box" :class="{ 'correct': result.correct, 'wrong': !result.correct }">
          <div v-if="result.correct" class="result-content">
            <div class="result-icon">✅</div>
            <h2 class="result-title">正确！</h2>
            <div class="result-solution">
              <h3>真相是：</h3>
              <p>{{ result.solution }}</p>
            </div>
          </div>
          <div v-else class="result-content">
            <div class="result-icon">❌</div>
            <h2 class="result-title">再想想…</h2>
            <p class="result-hint">{{ result.hint }}</p>
            <button @click="showSolution" class="solution-btn">查看真相</button>
          </div>
        </div>
      </div>
      
      <!-- 真相展示 -->
      <div v-if="currentStep === 'solution'" class="step-solution">
        <div class="solution-box">
          <h2 class="section-title">完整答案解析</h2>
          <div class="solution-content">
            <p>{{ solution }}</p>
          </div>
          <button @click="restartGame" class="restart-btn">重新开始</button>
        </div>
      </div>
    </div>
    
    <!-- 其他事件的原有界面 -->
    <div v-else class="event-container">
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
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { getUserEvents, submitAnswer } from '../api'

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
    
    // 嘎嘎事件专用状态
    const isDuckMystery = computed(() => eventId === 'event_duck_mystery')
    const currentStep = ref('home') // home, story, clues, answer, result, solution
    const clues = ref([])
    const answer1 = ref('')
    const answer2 = ref('')
    const result = ref({
      correct: false,
      solution: '',
      hint: ''
    })
    const solution = ref('')
    
    const loadEvent = async () => {
      try {
        const res = await getUserEvents(gameStore.userId)
        event.value = res.data.events.find(e => e.id === eventId)
        if (event.value) {
          background.value = event.value.background
          foundClues.value = event.value.found_clues || []
          
          // 如果是嘎嘎事件，加载线索和答案
          if (isDuckMystery.value && event.value.clues) {
            clues.value = event.value.clues.map(c => {
              if (typeof c === 'string') return c
              return c.content || c
            })
            solution.value = event.value.solution || '真正偷走钻石项链的是私人助理。他并没有直接知道密码，而是在一次送物品时，将微型录音设备藏在房间（很可能就在那只小海龟装饰品里），录下了女演员输入密码的声音，从而破解了保险箱。小海龟的位置靠近保险箱且面向海景，实则是为了隐蔽录音设备并获得最佳收音效果。'
          }
          
          // 如果事件已完成，直接显示真相页（但用户仍可重新开始）
          if (event.value.completed && isDuckMystery.value) {
            // 可以选择直接显示真相，或者让用户重新开始
            // 这里选择显示真相，但提供重新开始按钮
            currentStep.value = 'solution'
          }
        }
      } catch (error) {
        console.error('加载事件失败:', error)
      }
    }
    
    // 嘎嘎事件专用方法
    const startGame = () => {
      currentStep.value = 'story'
    }
    
    const showClues = () => {
      currentStep.value = 'clues'
    }
    
    const goToAnswer = () => {
      currentStep.value = 'answer'
    }
    
    const goBackToClues = () => {
      currentStep.value = 'clues'
    }
    
    const submitAnswers = async () => {
      if (!answer1.value.trim() || !answer2.value.trim()) {
        return
      }
      
      try {
        const res = await submitAnswer(eventId, gameStore.userId, answer1.value, answer2.value)
        result.value = {
          correct: res.data.correct,
          solution: res.data.solution || solution.value,
          hint: res.data.hint || '再想想…提示：注意那只小海龟的作用。'
        }
        currentStep.value = 'result'
        
        // 如果答案正确，显示完成弹窗
        if (res.data.correct) {
          setTimeout(() => {
            showEventCompletedModal()
          }, 500)
          
          // 检查是否有解锁的角色
          if (res.data.unlocked_characters && res.data.unlocked_characters.length > 0) {
            setTimeout(() => {
              showCharacterUnlockModal(res.data.unlocked_characters)
            }, 2000)
          }
        }
      } catch (error) {
        console.error('提交答案失败:', error)
        result.value = {
          correct: false,
          solution: solution.value,
          hint: '提交失败，请重试'
        }
        currentStep.value = 'result'
      }
    }
    
    const showSolution = () => {
      currentStep.value = 'solution'
    }
    
    const restartGame = () => {
      currentStep.value = 'home'
      answer1.value = ''
      answer2.value = ''
      result.value = {
        correct: false,
        solution: '',
        hint: ''
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
            console.log('事件已完成，显示弹窗')
            // 更新本地事件状态
            if (event.value) {
              event.value.completed = true
            }
            // 延迟一点显示弹窗，确保消息已经渲染
            setTimeout(() => {
              showEventCompletedModal()
            }, 500)
          }
          
          // 检查是否有解锁的角色
          if (data.unlocked_characters && data.unlocked_characters.length > 0) {
            console.log('有角色解锁:', data.unlocked_characters)
            // 延迟显示角色解锁弹窗，让事件完成弹窗先显示
            setTimeout(() => {
              showCharacterUnlockModal(data.unlocked_characters)
            }, 2000)
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
      console.log('显示事件完成弹窗')
      eventCompletedModal.value = {
        show: true,
        message: '你太棒了！完成了一个大事件！'
      }
    }
    
    const closeEventCompletedModal = () => {
      eventCompletedModal.value.show = false
    }
    
    const showCharacterUnlockModal = (characters) => {
      console.log('显示角色解锁弹窗:', characters)
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
      // 只有非嘎嘎事件才连接WebSocket
      if (!isDuckMystery.value) {
        connectWebSocket()
      }
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
      closeCharacterUnlockModal,
      // 嘎嘎事件专用
      isDuckMystery,
      currentStep,
      clues,
      answer1,
      answer2,
      result,
      solution,
      startGame,
      showClues,
      goToAnswer,
      goBackToClues,
      submitAnswers,
      showSolution,
      restartGame
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

/* 嘎嘎事件专用样式 - 深蓝色背景 + 金色/白色文字 */
.event-detail.duck-mystery {
  background: linear-gradient(135deg, #0a1929 0%, #1a2332 50%, #0f1419 100%);
  background-attachment: fixed;
}

.duck-mystery-container {
  flex: 1;
  max-width: 900px;
  width: 100%;
  margin: 40px auto;
  padding: 0 20px;
  min-height: calc(100vh - 200px);
  overflow-y: auto;
  max-height: calc(100vh - 200px);
  box-sizing: border-box;
  /* 隐藏滚动条但保留滚动功能 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.duck-mystery-container::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
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
  /* 隐藏滚动条但保留滚动功能 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.messages::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
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

/* ========== 嘎嘎事件专用样式 ========== */

/* 首页样式 */
.step-home {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
}

.title-box {
  margin-bottom: 60px;
  animation: fadeInUp 0.8s ease-out;
}

.main-title {
  font-size: 3.5em;
  font-weight: bold;
  color: #ffd700;
  text-shadow: 0 0 20px rgba(255, 215, 0, 0.5), 0 4px 8px rgba(0, 0, 0, 0.3);
  margin-bottom: 20px;
  letter-spacing: 2px;
}

.subtitle {
  font-size: 1.3em;
  color: rgba(255, 255, 255, 0.9);
  font-style: italic;
}

.start-btn {
  padding: 18px 50px;
  font-size: 1.3em;
  font-weight: bold;
  color: #0a1929;
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  border: none;
  border-radius: 50px;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(255, 215, 0, 0.4);
  transition: all 0.3s;
  animation: fadeInUp 0.8s ease-out 0.3s both;
}

.start-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 30px rgba(255, 215, 0, 0.6);
}

.start-btn:active {
  transform: translateY(-1px);
}

/* 故事页样式 */
.step-story {
  animation: fadeIn 0.5s ease-out;
}

.story-box {
  background: rgba(255, 255, 255, 0.08);
  border: 2px solid rgba(255, 215, 0, 0.3);
  border-radius: 20px;
  padding: 40px;
  margin-bottom: 30px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.section-title {
  font-size: 2em;
  color: #ffd700;
  margin-bottom: 25px;
  text-align: center;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.story-text {
  font-size: 1.15em;
  line-height: 2;
  color: rgba(255, 255, 255, 0.95);
  text-align: justify;
}

.clues-btn,
.answer-btn {
  display: block;
  width: 100%;
  max-width: 300px;
  margin: 0 auto;
  padding: 15px 40px;
  font-size: 1.2em;
  font-weight: bold;
  color: #0a1929;
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  border: none;
  border-radius: 50px;
  cursor: pointer;
  box-shadow: 0 6px 20px rgba(255, 215, 0, 0.4);
  transition: all 0.3s;
}

.clues-btn:hover,
.answer-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(255, 215, 0, 0.6);
}

/* 线索页样式 */
.step-clues {
  animation: fadeIn 0.5s ease-out;
  overflow-y: auto;
  max-height: calc(100vh - 200px);
  padding-bottom: 20px;
  box-sizing: border-box;
  /* 隐藏滚动条但保留滚动功能 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.step-clues::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.clues-box {
  background: rgba(255, 255, 255, 0.08);
  border: 2px solid rgba(255, 215, 0, 0.3);
  border-radius: 20px;
  padding: 40px;
  margin-bottom: 30px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.clues-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.clue-item {
  padding: 18px 25px;
  margin: 15px 0;
  background: rgba(255, 215, 0, 0.1);
  border-left: 4px solid #ffd700;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.95);
  font-size: 1.1em;
  line-height: 1.8;
  transition: all 0.3s;
}

.clue-item:hover {
  background: rgba(255, 215, 0, 0.15);
  transform: translateX(5px);
}

/* 答题页样式 */
.step-answer {
  animation: fadeIn 0.5s ease-out;
  overflow-y: auto;
  max-height: calc(100vh - 200px);
  padding-bottom: 20px;
  box-sizing: border-box;
  /* 隐藏滚动条但保留滚动功能 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.step-answer::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.btn-back-to-clues {
  margin-bottom: 20px;
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
  border: 2px solid rgba(255, 215, 0, 0.3);
  border-radius: 8px;
  cursor: pointer;
  font-size: 1em;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-back-to-clues:hover {
  background: rgba(255, 215, 0, 0.2);
  border-color: #ffd700;
  color: #ffd700;
  transform: translateX(-3px);
}

.questions-box {
  background: rgba(255, 255, 255, 0.08);
  border: 2px solid rgba(255, 215, 0, 0.3);
  border-radius: 20px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.question-item {
  margin-bottom: 30px;
}

.question-label {
  display: block;
  font-size: 1.3em;
  color: #ffd700;
  margin-bottom: 12px;
  font-weight: bold;
}

.answer-input,
.answer-textarea {
  width: 100%;
  padding: 15px 20px;
  font-size: 1.1em;
  color: rgba(255, 255, 255, 0.95);
  background: rgba(255, 255, 255, 0.1);
  border: 2px solid rgba(255, 215, 0, 0.3);
  border-radius: 10px;
  font-family: inherit;
  transition: all 0.3s;
  box-sizing: border-box;
}

.answer-input::placeholder,
.answer-textarea::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.answer-input:focus,
.answer-textarea:focus {
  outline: none;
  border-color: #ffd700;
  background: rgba(255, 255, 255, 0.15);
  box-shadow: 0 0 15px rgba(255, 215, 0, 0.3);
}

.answer-textarea {
  resize: vertical;
  min-height: 120px;
}

.submit-btn {
  display: block;
  width: 100%;
  max-width: 300px;
  margin: 30px auto 0;
  padding: 18px 50px;
  font-size: 1.3em;
  font-weight: bold;
  color: #0a1929;
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  border: none;
  border-radius: 50px;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(255, 215, 0, 0.4);
  transition: all 0.3s;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 12px 30px rgba(255, 215, 0, 0.6);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 结果页样式 */
.step-result {
  animation: fadeIn 0.5s ease-out;
}

.result-box {
  background: rgba(255, 255, 255, 0.08);
  border: 2px solid;
  border-radius: 20px;
  padding: 50px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  text-align: center;
}

.result-box.correct {
  border-color: rgba(76, 175, 80, 0.5);
  background: rgba(76, 175, 80, 0.1);
}

.result-box.wrong {
  border-color: rgba(244, 67, 54, 0.5);
  background: rgba(244, 67, 54, 0.1);
}

.result-content {
  animation: fadeInUp 0.6s ease-out;
}

.result-icon {
  font-size: 4em;
  margin-bottom: 20px;
  animation: scaleIn 0.5s ease-out;
}

.result-title {
  font-size: 2.5em;
  color: #ffd700;
  margin-bottom: 30px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.result-solution {
  text-align: left;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 15px;
  padding: 30px;
  margin-top: 30px;
}

.result-solution h3 {
  color: #ffd700;
  font-size: 1.5em;
  margin-bottom: 15px;
}

.result-solution p {
  color: rgba(255, 255, 255, 0.95);
  font-size: 1.15em;
  line-height: 2;
}

.result-hint {
  font-size: 1.3em;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 30px;
}

.solution-btn {
  padding: 15px 40px;
  font-size: 1.2em;
  font-weight: bold;
  color: #0a1929;
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  border: none;
  border-radius: 50px;
  cursor: pointer;
  box-shadow: 0 6px 20px rgba(255, 215, 0, 0.4);
  transition: all 0.3s;
}

.solution-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(255, 215, 0, 0.6);
}

/* 真相页样式 */
.step-solution {
  animation: fadeIn 0.5s ease-out;
}

.solution-box {
  background: rgba(255, 255, 255, 0.08);
  border: 2px solid rgba(255, 215, 0, 0.3);
  border-radius: 20px;
  padding: 50px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.solution-content {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 15px;
  padding: 40px;
  margin: 30px 0;
}

.solution-content p {
  color: rgba(255, 255, 255, 0.95);
  font-size: 1.2em;
  line-height: 2;
  text-align: justify;
}

.restart-btn {
  display: block;
  width: 100%;
  max-width: 300px;
  margin: 30px auto 0;
  padding: 15px 40px;
  font-size: 1.2em;
  font-weight: bold;
  color: #0a1929;
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  border: none;
  border-radius: 50px;
  cursor: pointer;
  box-shadow: 0 6px 20px rgba(255, 215, 0, 0.4);
  transition: all 0.3s;
}

.restart-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(255, 215, 0, 0.6);
}

/* 动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes scaleIn {
  from {
    transform: scale(0);
  }
  to {
    transform: scale(1);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .main-title {
    font-size: 2.5em;
  }
  
  .section-title {
    font-size: 1.5em;
  }
  
  .story-box,
  .clues-box,
  .questions-box,
  .result-box,
  .solution-box {
    padding: 25px;
  }
}
</style>

