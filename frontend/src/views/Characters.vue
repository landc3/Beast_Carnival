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
            :class="{ 'flipped': flippedCards[char.id] }"
            @click="toggleCard(char.id)"
          >
            <div class="character-card-inner">
              <!-- 正面：显示角色信息 -->
              <div class="character-card-front">
                <div class="card-front-content">
                  <div class="card-front-pattern"></div>
                  <div class="card-front-content-inner">
                    <div class="character-avatar">
                      <span class="emoji">{{ getEmoji(char.animal) }}</span>
                    </div>
                    <h3>{{ char.name }}</h3>
                    <p class="animal">{{ char.animal }}</p>
                    <p class="personality">{{ char.personality }}</p>
                    <button class="btn-chat" @click.stop="openChat(char.id)">开始对话</button>
                    <button class="btn-profile" @click.stop="showProfile(char)">查看档案</button>
                  </div>
                </div>
              </div>
              <!-- 背面：Beast Carnival 样式 -->
              <div class="character-card-back">
                <div class="card-back-content">
                  <div class="rose-decoration"></div>
                  <div class="beast-carnival-text">Beast Carnival</div>
                  <div class="card-back-pattern"></div>
                </div>
              </div>
            </div>
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
            <div class="locked-card-content">
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
    const flippedCards = ref({})
    
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
    
    const toggleCard = (characterId) => {
      flippedCards.value[characterId] = !flippedCards.value[characterId]
    }
    
    onMounted(loadCharacters)
    
    return {
      unlocked,
      locked,
      selectedCharacter,
      showUnlockHint,
      flippedCards,
      getEmoji,
      openChat,
      showProfile,
      toggleCard
    }
  }
}
</script>

<style scoped>
.characters {
  min-height: calc(100vh - 80px);
  padding: 20px 15px 100px;
  background: transparent;
  overflow-y: auto;
  overflow-x: hidden;
  /* 隐藏滚动条但保持滚动功能 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.characters::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
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
  
  .character-card {
    min-height: 220px;
    max-height: 260px;
  }
  
  .character-card-inner {
    min-height: 220px;
    max-height: 260px;
  }
  
  .character-avatar {
    width: 60px;
    height: 60px;
    font-size: 1.8em;
  }
  
  .card-front-content-inner {
    padding: 10px 8px;
    gap: 4px;
  }
  
  .locked-card-content {
    padding: 10px 8px;
    gap: 4px;
  }
  
  .character-card h3 {
    font-size: 0.9em;
  }
  
  .character-card.locked h3 {
    font-size: 0.85em;
  }
  
  .animal {
    font-size: 0.7em;
  }
  
  .character-card.locked .animal {
    font-size: 0.65em;
  }
  
  .personality {
    font-size: 0.65em;
    padding: 2px 6px;
  }
  
  .btn-chat,
  .btn-profile {
    padding: 5px 6px;
    font-size: 0.7em;
  }
  
  .unlock-hint {
    font-size: 0.65em;
    padding: 5px 6px;
  }
}

@media (min-width: 1400px) {
  .character-grid {
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 20px;
  }
  
  .character-card {
    min-height: 260px;
    max-height: 300px;
  }
  
  .character-card-inner {
    min-height: 260px;
    max-height: 300px;
  }
}

.character-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 0;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  min-height: 240px;
  max-height: 280px;
  position: relative;
  perspective: 1000px;
  overflow: hidden;
}

.character-card.unlocked:hover {
  border-color: rgba(102, 126, 234, 0.5);
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.2);
}

.character-card.unlocked:hover .character-card-inner {
  transform: translateY(-8px);
}

.character-card.unlocked.flipped:hover .character-card-inner {
  transform: translateY(-8px) rotateY(180deg);
}

.character-card-inner {
  width: 100%;
  height: 100%;
  position: relative;
  transform-style: preserve-3d;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 240px;
  max-height: 280px;
  box-sizing: border-box;
}

.character-card.flipped .character-card-inner {
  transform: rotateY(180deg);
}

.character-card-front,
.character-card-back {
  width: 100%;
  height: 100%;
  position: absolute;
  backface-visibility: hidden;
  border-radius: 12px;
  overflow: hidden;
}

.character-card-back {
  transform: rotateY(180deg);
}

.card-front-content {
  width: 100%;
  height: 100%;
  padding: 0;
  position: relative;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  box-sizing: border-box;
  overflow: hidden;
  border: 1px solid rgba(212, 175, 55, 0.2);
}

.character-card.unlocked:hover .card-front-content {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(212, 175, 55, 0.4);
}

.card-front-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at 20% 20%, rgba(212, 175, 55, 0.08) 0%, transparent 40%),
    radial-gradient(circle at 80% 80%, rgba(212, 175, 55, 0.08) 0%, transparent 40%),
    repeating-linear-gradient(
      45deg,
      transparent,
      transparent 8px,
      rgba(212, 175, 55, 0.03) 8px,
      rgba(212, 175, 55, 0.03) 16px
    ),
    repeating-linear-gradient(
      -45deg,
      transparent,
      transparent 8px,
      rgba(212, 175, 55, 0.02) 8px,
      rgba(212, 175, 55, 0.02) 16px
    );
  opacity: 0.6;
  z-index: 1;
  pointer-events: none;
}

.card-front-content-inner {
  width: 100%;
  height: 100%;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 6px;
  position: relative;
  z-index: 2;
}

.character-card.locked {
  opacity: 0.5;
  cursor: default;
  position: relative;
  min-height: 240px;
  max-height: 280px;
  overflow: hidden;
}

.character-card.locked:hover {
  opacity: 0.7;
  transform: translateY(-3px);
  border-color: rgba(255, 255, 255, 0.15);
}

.locked-card-content {
  width: 100%;
  height: 100%;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 6px;
  box-sizing: border-box;
  overflow: hidden;
}

.character-avatar {
  width: 70px;
  height: 70px;
  margin: 0 auto 0;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.2em;
  position: relative;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  flex-shrink: 0;
}

.character-avatar.locked {
  filter: grayscale(80%);
  opacity: 0.6;
  width: 70px;
  height: 70px;
  margin: 0 auto 0;
  font-size: 2.2em;
  flex-shrink: 0;
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
  font-size: 1em;
  color: #ffffff;
  margin: 0;
  font-weight: 600;
  line-height: 1.2;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  padding: 0 4px;
  flex-shrink: 0;
}

.character-card.locked h3 {
  font-size: 0.95em;
}

.animal {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.75em;
  margin: 0;
  line-height: 1.2;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  padding: 0 4px;
  flex-shrink: 0;
}

.character-card.locked .animal {
  font-size: 0.7em;
}

.personality {
  color: #667eea;
  font-weight: 500;
  font-size: 0.7em;
  margin: 0;
  padding: 2px 8px;
  background: rgba(102, 126, 234, 0.15);
  border-radius: 8px;
  display: inline-block;
  line-height: 1.3;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: calc(100% - 16px);
}

.btn-chat {
  width: calc(100% - 8px);
  padding: 6px 8px;
  background: linear-gradient(135deg, #667eea 0%, #5568d3 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.75em;
  margin-top: auto;
  transition: all 0.3s;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  width: calc(100% - 8px);
  padding: 6px 8px;
  background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.75em;
  margin-top: 4px;
  transition: all 0.3s;
  font-weight: 500;
  box-shadow: 0 2px 8px rgba(72, 187, 120, 0.3);
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  margin-top: auto;
  padding: 6px 8px;
  background: rgba(255, 215, 0, 0.15);
  border: 1px solid rgba(255, 215, 0, 0.4);
  border-radius: 6px;
  color: #ffd700;
  font-size: 0.7em;
  line-height: 1.3;
  animation: fadeIn 0.3s ease;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  white-space: normal;
  max-width: calc(100% - 16px);
  flex-shrink: 0;
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

/* 卡片背面样式 - Beast Carnival */
.card-back-content {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: 
    linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%),
    repeating-linear-gradient(
      45deg,
      transparent,
      transparent 10px,
      rgba(0, 0, 0, 0.15) 10px,
      rgba(0, 0, 0, 0.15) 20px
    );
  background-blend-mode: overlay;
  border: 3px solid #d4af37;
  border-radius: 12px;
  box-shadow: 
    inset 0 0 30px rgba(212, 175, 55, 0.4),
    inset 0 2px 4px rgba(212, 175, 55, 0.2),
    0 0 25px rgba(212, 175, 55, 0.3),
    0 4px 8px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.rose-decoration {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80%;
  height: 60%;
  z-index: 3;
  pointer-events: none;
  opacity: 0.7;
}

.rose-decoration::before {
  content: '🌹';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) rotate(-15deg) scale(2.5);
  font-size: 3em;
  filter: drop-shadow(0 0 8px rgba(220, 20, 60, 0.8)) 
          drop-shadow(0 0 15px rgba(220, 20, 60, 0.6))
          drop-shadow(0 0 25px rgba(220, 20, 60, 0.4));
  animation: roseGlow 3s ease-in-out infinite;
}

@keyframes roseGlow {
  0%, 100% {
    opacity: 0.7;
    transform: translate(-50%, -50%) rotate(-15deg) scale(2.5);
  }
  50% {
    opacity: 0.9;
    transform: translate(-50%, -50%) rotate(-12deg) scale(2.6);
  }
}

.beast-carnival-text {
  font-family: 'Georgia', 'Times New Roman', serif;
  font-size: 0.85em;
  font-weight: bold;
  color: #d4af37;
  text-align: center;
  letter-spacing: 3px;
  text-shadow: 
    0 0 15px rgba(212, 175, 55, 1),
    0 0 30px rgba(212, 175, 55, 0.6),
    0 0 45px rgba(212, 175, 55, 0.3),
    2px 2px 6px rgba(0, 0, 0, 0.9);
  z-index: 4;
  position: relative;
  padding: 0 8px;
  line-height: 1.3;
  transform: perspective(500px) rotateX(5deg);
  background: linear-gradient(180deg, 
    rgba(212, 175, 55, 1) 0%, 
    rgba(184, 134, 11, 1) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.8));
}

.card-back-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at 20% 30%, rgba(212, 175, 55, 0.15) 0%, transparent 50%),
    radial-gradient(circle at 80% 70%, rgba(212, 175, 55, 0.15) 0%, transparent 50%),
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(212, 175, 55, 0.08) 2px,
      rgba(212, 175, 55, 0.08) 4px
    ),
    repeating-linear-gradient(
      90deg,
      transparent,
      transparent 2px,
      rgba(212, 175, 55, 0.05) 2px,
      rgba(212, 175, 55, 0.05) 4px
    );
  opacity: 0.7;
  z-index: 1;
}
</style>

