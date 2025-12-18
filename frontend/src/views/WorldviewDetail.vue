<template>
  <div class="worldview-detail">
    <div class="header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>{{ worldview.title || '世界观' }}</h1>
      <p class="subtitle">{{ worldview.subtitle || '萌原镇的秘密' }}</p>
    </div>
    
    <div class="content-container">
      <!-- 世界观介绍 -->
      <section class="section">
        <h2>世界观介绍</h2>
        <div class="intro-card">
          <p class="intro-text">{{ formattedIntroduction }}</p>
          <div class="host-info" v-if="worldview.host_ai">
            <p><strong>主持AI：</strong>{{ worldview.host_ai }}</p>
          </div>
        </div>
        
        <!-- 世界观设定 -->
        <div v-if="worldview.settings && worldview.settings.length > 0" class="settings-grid">
          <div 
            v-for="setting in worldview.settings" 
            :key="setting.id"
            class="setting-card"
          >
            <h3>{{ setting.title }}</h3>
            <p>{{ setting.description }}</p>
          </div>
        </div>
      </section>
      
      <!-- 角色概览 -->
      <section class="section" v-if="worldview.characters_overview && worldview.characters_overview.length > 0">
        <h2>角色概览</h2>
        <div class="characters-grid">
          <div 
            v-for="char in worldview.characters_overview" 
            :key="char.id"
            class="character-overview-card"
          >
            <h3>{{ char.name }}</h3>
            <p class="animal">{{ char.animal }}</p>
            <p class="description">{{ char.description }}</p>
          </div>
        </div>
      </section>
      
      <!-- 游戏玩法介绍 -->
      <section class="section">
        <h2>游戏玩法介绍</h2>
        
        <!-- 核心功能 -->
        <div v-if="worldview.gameplay_features && worldview.gameplay_features.length > 0" class="features-list">
          <div 
            v-for="feature in worldview.gameplay_features" 
            :key="feature.id"
            class="feature-card"
          >
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.description }}</p>
          </div>
        </div>
        
        <!-- 游戏规则 -->
        <div v-if="worldview.gameplay_rules && worldview.gameplay_rules.length > 0" class="rules-list">
          <h3 class="rules-title">游戏规则</h3>
          <div 
            v-for="rule in worldview.gameplay_rules" 
            :key="rule.id"
            class="rule-card"
          >
            <h4>{{ rule.title }}</h4>
            <pre class="rule-content">{{ rule.description }}</pre>
          </div>
        </div>
      </section>
      
      <!-- 联系我们 -->
      <section class="section contact-section">
        <h2>联系我们</h2>
        <div class="contact-card">
          <div class="contact-icon">📮</div>
          <h3>投稿</h3>
          <p class="contact-description">{{ worldview.contact?.description || '如果你有好的创意、角色设定、故事剧情或其他想法，欢迎联系我们！我们期待你的投稿。' }}</p>
          <div class="contact-email">
            <strong>联系邮箱：</strong>
            <a :href="`mailto:${worldview.contact?.email || '3231360739@qq.com'}`" class="email-link">
              {{ worldview.contact?.email || '3231360739@qq.com' }}
            </a>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getWorldView } from '../api'

export default {
  name: 'WorldviewDetail',
  setup() {
    const router = useRouter()
    const worldview = ref({})
    
    const formattedIntroduction = computed(() => {
      const intro = worldview.value.introduction || ''
      return intro.split('\n').filter(line => line.trim()).join('\n\n')
    })
    
    const loadWorldview = async () => {
      try {
        const res = await getWorldView()
        worldview.value = res.data
      } catch (error) {
        console.error('加载世界观数据失败:', error)
      }
    }
    
    const goBack = () => {
      router.push('/')
    }
    
    onMounted(loadWorldview)
    
    return {
      worldview,
      formattedIntroduction,
      goBack
    }
  }
}
</script>

<style scoped>
.worldview-detail {
  min-height: 100vh;
  padding: 40px 20px 100px;
  background: transparent;
  box-sizing: border-box;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  text-align: center;
  margin-bottom: 40px;
  position: relative;
}

.back-btn {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #ffffff;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1em;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
}

.header h1 {
  font-size: 3em;
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

.content-container {
  display: flex;
  flex-direction: column;
  gap: 40px;
}

.section {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 30px;
}

.section h2 {
  font-size: 2em;
  color: #ffffff;
  margin-bottom: 20px;
  border-bottom: 2px solid rgba(255, 255, 255, 0.2);
  padding-bottom: 10px;
}

.intro-card {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.intro-text {
  font-size: 1.1em;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.9);
  white-space: pre-line;
  margin-bottom: 15px;
}

.host-info {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.host-info p {
  color: rgba(255, 255, 255, 0.8);
  font-size: 1em;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.setting-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 20px;
  transition: all 0.3s ease;
}

.setting-card:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-3px);
}

.setting-card h3 {
  color: #ffd700;
  font-size: 1.3em;
  margin-bottom: 10px;
}

.setting-card p {
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
}

.characters-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.character-overview-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  transition: all 0.3s ease;
}

.character-overview-card:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-3px);
}

.character-overview-card h3 {
  color: #ffffff;
  font-size: 1.5em;
  margin-bottom: 8px;
}

.character-overview-card .animal {
  color: #ffd700;
  font-size: 1.1em;
  margin-bottom: 10px;
}

.character-overview-card .description {
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.9em;
  line-height: 1.6;
}

.features-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-top: 20px;
}

.feature-card {
  background: rgba(255, 255, 255, 0.05);
  border-left: 4px solid #ffd700;
  border-radius: 8px;
  padding: 20px;
  transition: all 0.3s ease;
}

.feature-card:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateX(5px);
}

.feature-card h3 {
  color: #ffd700;
  font-size: 1.3em;
  margin-bottom: 10px;
}

.feature-card p {
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.8;
}

.rules-list {
  margin-top: 30px;
}

.rules-title {
  color: #ffffff;
  font-size: 1.5em;
  margin-bottom: 20px;
}

.rule-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 15px;
}

.rule-card h4 {
  color: #ffd700;
  font-size: 1.2em;
  margin-bottom: 10px;
}

.rule-content {
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.8;
  white-space: pre-wrap;
  font-family: inherit;
  margin: 0;
}

.contact-section {
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.1), rgba(255, 215, 0, 0.05));
  border: 2px solid rgba(255, 215, 0, 0.3);
}

.contact-card {
  text-align: center;
  padding: 30px;
}

.contact-icon {
  font-size: 4em;
  margin-bottom: 20px;
}

.contact-card h3 {
  color: #ffd700;
  font-size: 2em;
  margin-bottom: 15px;
}

.contact-description {
  color: rgba(255, 255, 255, 0.9);
  font-size: 1.1em;
  line-height: 1.8;
  margin-bottom: 25px;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.contact-email {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 20px;
  display: inline-block;
  margin-top: 20px;
}

.contact-email strong {
  color: rgba(255, 255, 255, 0.9);
  font-size: 1.1em;
  margin-right: 10px;
}

.email-link {
  color: #ffd700;
  font-size: 1.2em;
  text-decoration: none;
  transition: all 0.3s ease;
}

.email-link:hover {
  color: #ffed4e;
  text-decoration: underline;
}

@media (max-width: 768px) {
  .header h1 {
    font-size: 2em;
  }
  
  .back-btn {
    position: relative;
    margin-bottom: 20px;
    transform: none;
  }
  
  .section {
    padding: 20px;
  }
  
  .settings-grid,
  .characters-grid {
    grid-template-columns: 1fr;
  }
}
</style>





