<template>
  <div class="characters">
    <div class="header">
      <h1>角色图鉴</h1>
    </div>
    
    <div class="characters-container">
      <div class="section unlocked">
        <h2>已解锁角色</h2>
        <div v-if="unlocked.length === 0" class="empty-state">
          <div class="empty-icon">🔓</div>
          <p>还没有解锁任何角色</p>
          <p class="empty-hint">完成游戏任务来解锁更多角色吧！</p>
        </div>
        <div v-else class="character-grid">
          <div 
            v-for="char in unlocked" 
            :key="char.id"
            class="character-card unlocked"
            @click="openChat(char.id)"
          >
            <div class="character-avatar">
              <span class="emoji">{{ getEmoji(char.animal) }}</span>
            </div>
            <h3>{{ char.name }}</h3>
            <p class="animal">{{ char.animal }}</p>
            <p class="personality">{{ char.personality }}</p>
            <button class="btn-chat">开始对话</button>
            <button class="btn-profile" @click.stop="showProfile(char)">查看档案</button>
          </div>
        </div>
      </div>
      
      <div class="section locked">
        <h2>未解锁角色</h2>
        <div v-if="locked.length === 0" class="empty-state">
          <div class="empty-icon">🎉</div>
          <p>太棒了！所有角色都已解锁</p>
        </div>
        <div v-else class="character-grid">
          <div 
            v-for="char in locked" 
            :key="char.id"
            class="character-card locked"
            @mouseenter="showUnlockHint = char.id"
            @mouseleave="showUnlockHint = null"
          >
            <div class="character-avatar locked">
              <span class="emoji">{{ getEmoji(char.animal) }}</span>
              <div class="lock-overlay">🔒</div>
            </div>
            <h3>{{ char.name }}</h3>
            <p class="animal">{{ char.animal }}</p>
            <div v-if="showUnlockHint === char.id" class="unlock-hint">
              {{ char.unlock_condition }}
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 角色档案弹窗 -->
    <div v-if="selectedCharacter" class="modal" @click.self="selectedCharacter = null">
      <div class="modal-content">
        <button class="close-btn" @click="selectedCharacter = null">×</button>
        <h2>{{ selectedCharacter.name }}</h2>
        <div class="profile-info">
          <p><strong>动物：</strong>{{ selectedCharacter.animal }}</p>
          <p><strong>性格：</strong>{{ selectedCharacter.personality }}</p>
          <p><strong>背景：</strong>{{ selectedCharacter.background }}</p>
          <p><strong>技能：</strong>{{ selectedCharacter.skills.join('、') }}</p>
        </div>
        <button @click="openChat(selectedCharacter.id)" class="btn-chat">开始对话</button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { getUserCharacters } from '../api'

export default {
  name: 'Characters',
  setup() {
    const router = useRouter()
    const gameStore = useGameStore()
    const unlocked = ref([])
    const locked = ref([])
    const selectedCharacter = ref(null)
    const showUnlockHint = ref(null)
    
    const emojiMap = {
      '猫': '🐱',
      '狗': '🐶',
      '鸭子': '🦆',
      '鳄鱼': '🐊',
      '狼': '🐺'
    }
    
    const getEmoji = (animal) => emojiMap[animal] || '🐾'
    
    const loadCharacters = async () => {
      try {
        const res = await getUserCharacters(gameStore.userId)
        unlocked.value = res.data.unlocked
        locked.value = res.data.locked
      } catch (error) {
        console.error('加载角色失败:', error)
      }
    }
    
    const openChat = (characterId) => {
      router.push(`/character/${characterId}/chat`)
    }
    
    const showProfile = (character) => {
      selectedCharacter.value = character
    }
    
    onMounted(loadCharacters)
    
    return {
      unlocked,
      locked,
      selectedCharacter,
      showUnlockHint,
      getEmoji,
      openChat,
      showProfile
    }
  }
}
</script>

<style scoped>
.characters {
  min-height: calc(100vh - 80px);
  padding: 20px 15px 100px;
  background: #0a0a0a;
  background-image: 
    radial-gradient(circle at 1px 1px, rgba(255,255,255,0.15) 1px, transparent 0);
  background-size: 20px 20px;
  overflow-y: auto;
  overflow-x: hidden;
}

.header {
  max-width: 1200px;
  margin: 0 auto 20px;
  text-align: center;
}

.header h1 {
  color: #ffffff;
  font-size: 1.8em;
  font-weight: bold;
  text-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
}

.characters-container {
  max-width: 1200px;
  margin: 0 auto;
}

.section {
  margin-bottom: 35px;
}

.section:last-child {
  margin-bottom: 0;
}

.section h2 {
  color: #ffffff;
  font-size: 1.4em;
  margin-bottom: 18px;
  padding-bottom: 8px;
  border-bottom: 2px solid rgba(102, 126, 234, 0.3);
  display: flex;
  align-items: center;
  gap: 8px;
}

.section.unlocked h2::before {
  content: "✨";
  font-size: 0.9em;
}

.section.locked h2::before {
  content: "🔒";
  font-size: 0.9em;
}

.character-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 18px;
  padding-bottom: 10px;
}

@media (max-width: 768px) {
  .character-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 15px;
  }
}

@media (min-width: 1400px) {
  .character-grid {
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 20px;
  }
}

.character-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 16px 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 240px;
  position: relative;
}

.character-card.unlocked:hover {
  transform: translateY(-8px);
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(102, 126, 234, 0.5);
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.2);
}

.character-card.locked {
  opacity: 0.5;
  cursor: default;
  position: relative;
}

.character-card.locked:hover {
  opacity: 0.7;
  transform: translateY(-3px);
  border-color: rgba(255, 255, 255, 0.15);
}

.character-avatar {
  width: 80px;
  height: 80px;
  margin: 0 auto 12px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5em;
  position: relative;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  flex-shrink: 0;
}

.character-avatar.locked {
  filter: grayscale(80%);
  opacity: 0.6;
}

.lock-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4em;
  backdrop-filter: blur(2px);
}

.character-card h3 {
  font-size: 1.1em;
  color: #ffffff;
  margin-bottom: 6px;
  font-weight: 600;
  line-height: 1.3;
}

.animal {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.85em;
  margin-bottom: 5px;
}

.personality {
  color: #667eea;
  font-weight: 500;
  font-size: 0.8em;
  margin-bottom: 12px;
  padding: 3px 10px;
  background: rgba(102, 126, 234, 0.15);
  border-radius: 10px;
  display: inline-block;
}

.btn-chat {
  width: 100%;
  padding: 8px;
  background: linear-gradient(135deg, #667eea 0%, #5568d3 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85em;
  margin-top: auto;
  transition: all 0.3s;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.btn-chat:hover {
  background: linear-gradient(135deg, #5568d3 0%, #4858c2 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-chat:active {
  transform: translateY(0);
}

.btn-profile {
  width: 100%;
  padding: 8px;
  background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85em;
  margin-top: 6px;
  transition: all 0.3s;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(72, 187, 120, 0.3);
}

.btn-profile:hover {
  background: linear-gradient(135deg, #38a169 0%, #2f855a 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(72, 187, 120, 0.4);
}

.btn-profile:active {
  transform: translateY(0);
}

.unlock-hint {
  margin-top: 10px;
  padding: 8px 10px;
  background: rgba(255, 215, 0, 0.15);
  border: 1px solid rgba(255, 215, 0, 0.4);
  border-radius: 6px;
  color: #ffd700;
  font-size: 0.75em;
  line-height: 1.4;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  animation: fadeIn 0.3s ease;
  padding: 20px;
}

.modal-content {
  background: rgba(20, 20, 20, 0.98);
  border: 1px solid rgba(102, 126, 234, 0.3);
  border-radius: 20px;
  padding: 40px;
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-content h2 {
  color: #ffffff;
  font-size: 2em;
  margin-bottom: 25px;
  text-align: center;
}

.close-btn {
  position: absolute;
  top: 15px;
  right: 15px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  font-size: 2em;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.7);
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
  line-height: 1;
}

.close-btn:hover {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.2);
  transform: rotate(90deg);
}

.profile-info {
  margin: 25px 0;
  line-height: 1.8;
}

.profile-info p {
  margin: 15px 0;
  color: rgba(255, 255, 255, 0.9);
  font-size: 1.05em;
}

.profile-info strong {
  color: #667eea;
  margin-right: 8px;
}

.modal-content .btn-chat {
  margin-top: 20px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: rgba(255, 255, 255, 0.5);
}

.empty-icon {
  font-size: 3em;
  margin-bottom: 15px;
  opacity: 0.6;
}

.empty-state p {
  font-size: 1em;
  margin: 8px 0;
  color: rgba(255, 255, 255, 0.6);
}

.empty-hint {
  font-size: 0.85em !important;
  color: rgba(255, 255, 255, 0.4) !important;
  margin-top: 8px;
}
</style>

