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
          <button @click="() => joinRoom()" class="btn-secondary">加入房间</button>
        </div>
        
        <!-- 房间信息 -->
        <div v-else class="room-info">
          <div class="room-details">
            <p class="room-id">房间号：{{ roomId }}</p>
            <p class="player-count">玩家数：{{ room?.players?.length || 0 }}/12</p>
          </div>
          <div v-if="room?.phase === 'waiting'" class="room-actions">
            <div class="ai-buttons">
              <button 
                @click="addAIPlayer" 
                class="btn-ai"
                :disabled="!canAddAI"
              >
                🤖 添加人机
              </button>
              <button 
                @click="autoFillAI" 
                class="btn-ai-auto"
                :disabled="!canAutoFill"
              >
                ⚡ 自动填充到12人
              </button>
            </div>
            <div v-if="room?.players?.length >= 4">
              <button @click="startGame" class="btn-start">开始游戏</button>
            </div>
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
              'dead': player && !player.alive,
              'is-current-user': player && isCurrentUser(player.user_id),
              'show-front': player && shouldShowCardFront(player) && !flippedCards[player.user_id],
              'show-back': player && (!shouldShowCardFront(player) || (shouldShowCardFront(player) && flippedCards[player.user_id]))
            }"
            @click="player && shouldShowCardFront(player) && toggleCard(player.user_id)"
          >
            <!-- 数字标识 -->
            <div class="card-number-badge">{{ index + 1 }}</div>
            
            <div class="character-card-inner">
              <!-- 正面：显示角色图标和名字 -->
              <div class="character-card-front">
                <div v-if="player" class="card-front-content">
                  <div class="character-avatar">
                    <div class="avatar-icon">
                      <img v-if="player.role && getCharacterIcon(player.role)" :src="getCharacterIcon(player.role)" :alt="getRoleName(player.role)" />
                      <span v-else>👤</span>
                    </div>
                    <!-- 文字覆盖层 -->
                    <div class="avatar-text-overlay">
                      <div class="avatar-name">{{ player.username }}</div>
                      <div v-if="player.role" class="role-label">
                        {{ getRoleName(player.role) }}
                      </div>
                      <!-- 预言家查验结果标记 -->
                      <div v-if="player && seerCheckedResults[player.user_id]" class="seer-check-badge" :class="{
                        'seer-check-good': seerCheckedResults[player.user_id] === '好人',
                        'seer-check-wolf': seerCheckedResults[player.user_id] === '狼人'
                      }">
                        {{ seerCheckedResults[player.user_id] === '好人' ? '✓ 好人' : '✗ 狼人' }}
                      </div>
                    </div>
                  </div>
                  <!-- 右上角问号按钮 -->
                  <button 
                    v-if="player.role"
                    class="role-info-btn"
                    @click.stop="showRoleInfo(player)"
                    title="查看角色信息"
                  >
                    ?
                  </button>
                </div>
                <div v-else class="avatar-empty"></div>
              </div>
              <!-- 背面：Beast Carnival 样式 -->
              <div class="character-card-back">
                <div class="card-back-content">
                  <div class="rose-decoration"></div>
                  <div class="beast-carnival-text">Beast Carnival</div>
                  <div class="card-back-pattern"></div>
                  <!-- 预言家查验结果标记（在卡片背面也显示） -->
                  <div v-if="player && seerCheckedResults[player.user_id]" class="seer-check-badge-back" :class="{
                    'seer-check-good': seerCheckedResults[player.user_id] === '好人',
                    'seer-check-wolf': seerCheckedResults[player.user_id] === '狼人'
                  }">
                    {{ seerCheckedResults[player.user_id] === '好人' ? '✓ 好人' : '✗ 狼人' }}
                  </div>
                </div>
              </div>
            </div>
            <div v-if="player && !player.alive" class="death-indicator">●</div>
          </div>
        </div>
        
        <!-- 角色信息弹窗 -->
        <transition name="role-info-modal">
          <div v-if="roleInfoModal.show" class="role-info-modal-overlay" @click.self="closeRoleInfo">
            <div class="role-info-modal">
              <div class="role-info-header">
                <h3 class="role-info-title">角色信息</h3>
                <button class="role-info-close" @click="closeRoleInfo">×</button>
              </div>
              <div class="role-info-content" v-if="roleInfoModal.player">
                <div class="role-info-icon">
                  <img v-if="getCharacterIcon(roleInfoModal.player.role)" :src="getCharacterIcon(roleInfoModal.player.role)" :alt="getRoleName(roleInfoModal.player.role)" />
                  <span v-else>👤</span>
                </div>
                <div class="role-info-name">{{ getRoleName(roleInfoModal.player.role) }}</div>
                <div class="role-info-description">{{ getRoleDescription(roleInfoModal.player.role) }}</div>
              </div>
            </div>
          </div>
        </transition>
        
        <!-- 游戏结束结算弹窗 -->
        <transition name="game-over-modal">
          <div v-if="gameOverModal.show" class="game-over-modal-overlay">
            <div class="game-over-modal">
              <div class="game-over-header">
                <h2 class="game-over-title">游戏结束</h2>
              </div>
              <div class="game-over-content">
                <div class="game-over-winner" :class="gameOverModal.winner">
                  <div class="winner-icon">{{ gameOverModal.winner === 'wolves' ? '🐺' : '🛡️' }}</div>
                  <div class="winner-text">{{ gameOverModal.winnerText }}</div>
                </div>
                <div class="game-over-message">
                  所有身份牌已翻开，请查看左侧玩家卡片
                </div>
              </div>
              <div class="game-over-actions">
                <button class="game-over-close-btn" @click="gameOverModal.show = false">关闭</button>
              </div>
            </div>
          </div>
        </transition>
        
        <!-- 退出游戏确认弹窗 -->
        <transition name="exit-confirm-modal">
          <div v-if="exitConfirmModal.show" class="exit-confirm-modal-overlay" @click.self="exitConfirmModal.show = false">
            <div class="exit-confirm-modal">
              <div class="exit-confirm-header">
                <h3 class="exit-confirm-title">退出游戏</h3>
              </div>
              <div class="exit-confirm-content">
                <div class="exit-confirm-message">
                  确定要退出游戏吗？退出后游戏将自动停止。
                </div>
              </div>
              <div class="exit-confirm-actions">
                <button class="exit-confirm-cancel-btn" @click="exitConfirmModal.show = false">取消</button>
                <button class="exit-confirm-confirm-btn" @click="confirmExit">确认退出</button>
              </div>
            </div>
          </div>
        </transition>
        
        <!-- 错误提示弹窗 -->
        <transition name="error-modal">
          <div v-if="errorModal.show" class="error-modal-overlay" @click.self="closeErrorModal">
            <div class="error-modal">
              <div class="error-modal-header">
                <div class="error-icon">⚠️</div>
                <h3 class="error-modal-title">提示</h3>
                <button class="error-modal-close" @click="closeErrorModal">×</button>
              </div>
              <div class="error-modal-content">
                <div class="error-modal-message">
                  {{ errorModal.message }}
                </div>
              </div>
              <div class="error-modal-actions">
                <button class="error-modal-confirm-btn" @click="closeErrorModal">确定</button>
              </div>
            </div>
          </div>
        </transition>
      </div>
      
      <!-- 右侧聊天面板 -->
      <div class="right-panel">
        <div class="chat-header">
          <h2 class="chat-title">AI Host</h2>
          <button @click="closeChat" class="close-btn">×</button>
        </div>
        
        <!-- 阶段弹窗 -->
        <transition name="phase-popup">
          <div v-if="phasePopup.show" class="phase-popup" :class="phasePopup.type">
            <div class="phase-popup-content">
              <div class="phase-popup-text">{{ phasePopup.text }}</div>
            </div>
          </div>
        </transition>
        
        <!-- 夜晚行动弹窗 -->
        <transition name="night-action-modal">
          <div v-if="nightActionModal.show" class="night-action-modal-overlay" @click.self="closeNightActionModal">
            <div class="night-action-modal">
              <div class="night-action-modal-header">
                <h3 class="night-action-title">{{ nightActionModal.title }}</h3>
                <button class="night-action-close" @click="closeNightActionModal">×</button>
              </div>
              <div class="night-action-modal-content">
                <!-- 守卫行动 -->
                <div v-if="nightActionModal.action === 'guard'" class="night-action-guard">
                  <p class="night-action-description">{{ nightActionModal.description }}</p>
                  <div class="night-action-players-grid">
                    <div
                      v-for="player in nightActionModal.players"
                      :key="player.user_id"
                      class="night-action-player-card"
                      :class="{
                        'selected': nightActionModal.selectedTarget === player.user_id,
                        'disabled': player.user_id === nightActionModal.cannotGuard
                      }"
                      @click="selectNightActionTarget(player.user_id)"
                    >
                      <div class="night-action-player-avatar">
                        <div class="night-action-avatar-icon">
                          <img v-if="getCharacterIcon(player.role || 'villager')" :src="getCharacterIcon(player.role || 'villager')" :alt="getRoleName(player.role || 'villager')" />
                          <span v-else>👤</span>
                        </div>
                      </div>
                      <div class="night-action-player-name">{{ player.username }}</div>
                      <div v-if="player.user_id === nightActionModal.cannotGuard" class="night-action-disabled-label">不能守护</div>
                    </div>
                  </div>
                  <div class="night-action-actions">
                    <button
                      @click="submitNightAction"
                      :disabled="!nightActionModal.selectedTarget || nightActionModal.submitting"
                      class="night-action-submit-btn"
                      :class="{ 'disabled': !nightActionModal.selectedTarget || nightActionModal.submitting }"
                    >
                      {{ nightActionModal.submitting ? '提交中...' : '确认守护' }}
                    </button>
                  </div>
                </div>
                
                <!-- 狼人行动 -->
                <div v-if="nightActionModal.action === 'wolf'" class="night-action-wolf">
                  <div class="wolf-action-container">
                    <!-- 左侧聊天区域 -->
                    <div class="wolf-chat-panel">
                      <div class="wolf-chat-header">
                        <h4>狼人讨论</h4>
                        <span class="wolf-chat-subtitle">仅狼人可见</span>
                      </div>
                      <div class="wolf-chat-messages" ref="wolfChatContainer">
                        <div
                          v-for="(msg, index) in wolfChatMessages"
                          :key="index"
                          class="wolf-chat-message"
                          :class="{ 'is-own': msg.username === username }"
                        >
                          <div class="wolf-chat-username">{{ msg.username }}</div>
                          <div class="wolf-chat-content">{{ msg.content }}</div>
                          <div class="wolf-chat-time">{{ formatChatTime(msg.timestamp) }}</div>
                        </div>
                        <div v-if="wolfChatMessages.length === 0" class="wolf-chat-empty">
                          开始讨论击杀目标...
                        </div>
                      </div>
                      <div class="wolf-chat-input-container">
                        <input
                          v-model="wolfChatInput"
                          @keyup.enter="sendWolfChatMessage"
                          type="text"
                          placeholder="输入消息与队友讨论..."
                          class="wolf-chat-input"
                        />
                        <button
                          @click="sendWolfChatMessage"
                          :disabled="!wolfChatInput.trim()"
                          class="wolf-chat-send-btn"
                        >
                          发送
                        </button>
                      </div>
                    </div>
                    <!-- 右侧选择区域 -->
                    <div class="wolf-selection-panel">
                      <p class="night-action-description">{{ nightActionModal.description }}</p>
                      <!-- 狼人投票状态 -->
                      <div v-if="nightActionModal.action === 'wolf'" class="wolf-vote-status">
                        <h4 class="vote-status-title">投票状态</h4>
                        <div class="wolf-vote-list">
                          <div
                            v-for="wolf in allWolves"
                            :key="wolf.user_id"
                            class="wolf-vote-item"
                            :class="{ 'is-current-user': isCurrentUser(wolf.user_id) }"
                          >
                            <div class="wolf-vote-name">
                              <span class="wolf-name">{{ wolf.username }}</span>
                              <span v-if="isCurrentUser(wolf.user_id)" class="current-user-badge">（你）</span>
                              <span v-if="wolf.is_ai" class="ai-badge">AI</span>
                            </div>
                            <div class="wolf-vote-status">
                              <span v-if="getWolfVoteStatus(wolf.user_id)" class="vote-status voted">
                                ✓ 已投票：{{ getVotedTargetName(wolf.user_id) }}
                              </span>
                              <span v-else class="vote-status not-voted">
                                ⏳ 等待投票...
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div v-if="nightActionModal.teammates && nightActionModal.teammates.length > 0" class="night-action-teammates">
                        <p class="teammates-label">你的狼人队友：{{ nightActionModal.teammates.join('、') }}</p>
                      </div>
                      <div class="night-action-players-grid">
                        <div
                          v-for="player in nightActionModal.players"
                          :key="player.user_id"
                          class="night-action-player-card"
                          :class="{ 'selected': nightActionModal.selectedTarget === player.user_id }"
                          @click="selectNightActionTarget(player.user_id)"
                        >
                          <div class="night-action-player-avatar">
                            <div class="night-action-avatar-icon">
                              <img v-if="getCharacterIcon(player.role || 'villager')" :src="getCharacterIcon(player.role || 'villager')" :alt="getRoleName(player.role || 'villager')" />
                              <span v-else>👤</span>
                            </div>
                            <!-- 投票数徽章 -->
                            <div v-if="getPlayerWolfVoteCount(player.user_id) > 0" class="vote-count-badge">
                              {{ getPlayerWolfVoteCount(player.user_id) }}
                            </div>
                          </div>
                          <div class="night-action-player-name">{{ player.username }}</div>
                        </div>
                      </div>
                      <div class="night-action-actions">
                        <button
                          @click="submitNightAction"
                          :disabled="!nightActionModal.selectedTarget || nightActionModal.submitting"
                          class="night-action-submit-btn"
                          :class="{ 'disabled': !nightActionModal.selectedTarget || nightActionModal.submitting }"
                        >
                          {{ nightActionModal.submitting ? '提交中...' : '确认击杀' }}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- 预言家行动 -->
                <div v-if="nightActionModal.action === 'seer'" class="night-action-seer">
                  <p class="night-action-description">{{ nightActionModal.description }}</p>
                  <div class="night-action-players-grid">
                    <div
                      v-for="player in nightActionModal.players"
                      :key="player.user_id"
                      class="night-action-player-card"
                      :class="{ 'selected': nightActionModal.selectedTarget === player.user_id }"
                      @click="selectNightActionTarget(player.user_id)"
                    >
                      <div class="night-action-player-avatar">
                        <div class="night-action-avatar-icon">
                          <img v-if="getCharacterIcon(player.role || 'villager')" :src="getCharacterIcon(player.role || 'villager')" :alt="getRoleName(player.role || 'villager')" />
                          <span v-else>👤</span>
                        </div>
                      </div>
                      <div class="night-action-player-name">{{ player.username }}</div>
                    </div>
                  </div>
                  <div class="night-action-actions">
                    <button
                      @click="submitNightAction"
                      :disabled="!nightActionModal.selectedTarget || nightActionModal.submitting"
                      class="night-action-submit-btn"
                      :class="{ 'disabled': !nightActionModal.selectedTarget || nightActionModal.submitting }"
                    >
                      {{ nightActionModal.submitting ? '提交中...' : '确认查验' }}
                    </button>
                  </div>
                </div>
                
                <!-- 女巫行动 -->
                <div v-if="nightActionModal.action === 'witch'" class="night-action-witch">
                  <p class="night-action-description">{{ nightActionModal.description }}</p>
                  <div class="witch-action-options">
                    <div class="witch-option-section">
                      <h4 class="witch-option-title">解药</h4>
                      <div class="witch-option-buttons">
                        <button
                          @click="selectWitchAction('antidote')"
                          :disabled="nightActionModal.antidoteUsed || nightActionModal.submitting"
                          class="witch-action-btn"
                          :class="{
                            'selected': nightActionModal.witchAction === 'antidote',
                            'disabled': nightActionModal.antidoteUsed || nightActionModal.submitting
                          }"
                        >
                          {{ nightActionModal.antidoteUsed ? '已使用' : '使用解药' }}
                        </button>
                        <span v-if="nightActionModal.wolfTargetName" class="witch-target-info">
                          被击杀者：{{ nightActionModal.wolfTargetName }}
                        </span>
                      </div>
                    </div>
                    <div class="witch-option-section">
                      <h4 class="witch-option-title">毒药</h4>
                      <div v-if="nightActionModal.witchAction === 'poison'" class="witch-poison-targets">
                        <div class="night-action-players-grid">
                          <div
                            v-for="player in nightActionModal.players"
                            :key="player.user_id"
                            class="night-action-player-card"
                            :class="{ 'selected': nightActionModal.selectedTarget === player.user_id }"
                            @click="selectNightActionTarget(player.user_id)"
                          >
                            <div class="night-action-player-avatar">
                              <div class="night-action-avatar-icon">
                                <img v-if="getCharacterIcon(player.role || 'villager')" :src="getCharacterIcon(player.role || 'villager')" :alt="getRoleName(player.role || 'villager')" />
                                <span v-else>👤</span>
                              </div>
                            </div>
                            <div class="night-action-player-name">{{ player.username }}</div>
                          </div>
                        </div>
                      </div>
                      <div class="witch-option-buttons">
                        <button
                          @click="selectWitchAction('poison')"
                          :disabled="nightActionModal.poisonUsed || nightActionModal.submitting"
                          class="witch-action-btn"
                          :class="{
                            'selected': nightActionModal.witchAction === 'poison',
                            'disabled': nightActionModal.poisonUsed || nightActionModal.submitting
                          }"
                        >
                          {{ nightActionModal.poisonUsed ? '已使用' : '使用毒药' }}
                        </button>
                      </div>
                    </div>
                    <div class="witch-option-section">
                      <button
                        @click="selectWitchAction('none')"
                        :disabled="nightActionModal.submitting"
                        class="witch-action-btn"
                        :class="{
                          'selected': nightActionModal.witchAction === 'none',
                          'disabled': nightActionModal.submitting
                        }"
                      >
                        不使用任何药水
                      </button>
                    </div>
                  </div>
                  <div class="night-action-actions">
                    <button
                      @click="submitNightAction"
                      :disabled="nightActionModal.submitting || (nightActionModal.witchAction === 'poison' && !nightActionModal.selectedTarget) || (nightActionModal.witchAction === 'antidote' && !nightActionModal.wolfTarget)"
                      class="night-action-submit-btn"
                      :class="{ 'disabled': nightActionModal.submitting || (nightActionModal.witchAction === 'poison' && !nightActionModal.selectedTarget) || (nightActionModal.witchAction === 'antidote' && !nightActionModal.wolfTarget) }"
                    >
                      {{ nightActionModal.submitting ? '提交中...' : '确认行动' }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>
        
        <!-- 投票界面 -->
        <div v-if="room && room.phase === 'voting'" class="voting-container">
          <div class="voting-header">
            <div class="voting-title">
              <h2>投票阶段</h2>
              <div class="phase-timer">
                <span class="phase-name">投票阶段</span>
                <span v-if="timeRemaining !== null" :class="['timer', { 'timer-warning': timeRemaining <= 10, 'timer-danger': timeRemaining <= 5 }]">
                  {{ formatTime(timeRemaining) }}
                </span>
                <span v-else class="timer">--:--</span>
              </div>
            </div>
            <p class="voting-instruction">请选择你要投票出局的玩家</p>
          </div>
          
          <div class="voting-players-grid">
            <div 
              v-for="player in alivePlayersForVoting" 
              :key="player.user_id"
              class="voting-player-card"
              :class="{ 
                'selected': selectedVoteTarget === player.user_id,
                'voted': player.voted,
                'current-user': isCurrentUser(player.user_id),
                'show-front': shouldShowVotingCardFront(player),
                'show-back': !shouldShowVotingCardFront(player)
              }"
              @click="selectVoteTarget(player.user_id)"
            >
              <div class="voting-card-inner">
                <!-- 正面：显示角色图标 -->
                <div class="voting-card-front">
                  <div class="voting-player-avatar">
                    <div class="voting-avatar-icon">
                      <img v-if="player.role && getCharacterIcon(player.role)" :src="getCharacterIcon(player.role)" :alt="getRoleName(player.role)" />
                      <span v-else>👤</span>
                    </div>
                    <div v-if="player.voted" class="voted-badge">✓</div>
                    <div v-if="getPlayerVoteCount(player.user_id) > 0" class="vote-count-badge">
                      {{ getPlayerVoteCount(player.user_id) }}
                    </div>
                  </div>
                  <div class="voting-player-name">{{ player.username }}</div>
                  <div v-if="isCurrentUser(player.user_id)" class="current-user-label">（你）</div>
                  <div v-if="player.voted" class="voted-label">已投票</div>
                </div>
                <!-- 背面：Beast Carnival 样式 -->
                <div class="voting-card-back">
                  <div class="voting-card-back-content">
                    <div class="rose-decoration-small"></div>
                    <div class="beast-carnival-text-small">Beast Carnival</div>
                    <div class="voting-card-back-pattern"></div>
                  </div>
                  <div class="voting-player-name-back">{{ player.username }}</div>
                  <div v-if="isCurrentUser(player.user_id)" class="current-user-label-back">（你）</div>
                  <div v-if="player.voted" class="voted-badge-back">✓</div>
                  <div v-if="getPlayerVoteCount(player.user_id) > 0" class="vote-count-badge-back">
                    {{ getPlayerVoteCount(player.user_id) }}
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="voting-actions">
            <button 
              @click="submitVote" 
              :disabled="!selectedVoteTarget || hasVoted || isCurrentPlayerDead"
              class="vote-submit-button"
              :class="{ 'button-disabled': !selectedVoteTarget || hasVoted || isCurrentPlayerDead }"
            >
              {{ isCurrentPlayerDead ? '已死亡' : hasVoted ? '已投票' : '确认投票' }}
            </button>
            <div v-if="hasVoted" class="vote-confirmed-message">
              你已投票给：{{ getVotedTargetName() }}
            </div>
            <!-- 只有明确死亡时才显示死亡消息 -->
            <div v-if="isCurrentPlayerDead" class="vote-confirmed-message" style="color: #ff6b6b;">
              你已死亡，无法投票
            </div>
          </div>
          
          <div class="voting-status">
            <div class="voting-status-item">
              <span class="status-label">已投票：</span>
              <span class="status-value">{{ votedCount }}/{{ alivePlayersCount }}</span>
            </div>
          </div>
        </div>
        
        <!-- 聊天界面（非投票阶段） -->
        <template v-else>
          <div class="chat-content">
            <!-- AI引导信息区域 -->
            <div class="ai-guide-section">
              <div class="section-header">
                <span class="section-title">AI引导信息</span>
                <div v-if="room && room.phase !== 'waiting' && room.phase !== 'game_over'" class="phase-timer">
                  <span class="phase-name">{{ getPhaseNameWithTime(room) }}</span>
                  <span v-if="timeRemaining !== null" :class="['timer', { 'timer-warning': timeRemaining <= 30, 'timer-danger': timeRemaining <= 10 }]">
                    {{ formatTime(timeRemaining) }}
                  </span>
                  <span v-else class="timer">--:--</span>
                </div>
              </div>
              <div class="messages ai-messages" ref="aiMessagesContainer">
                <div 
                  v-for="(msg, index) in aiGuideMessages" 
                  :key="'ai-' + index"
                  :class="['message-bubble', msg.type || 'system']"
                >
                  <div class="message-avatar">
                    <div class="avatar-icon-small">{{ getMessageAvatar(msg) }}</div>
                  </div>
                  <div class="message-content-wrapper">
                    <div class="message-content" v-html="formatMessageContent(msg.content)"></div>
                    <div class="message-sender">{{ msg.username || (msg.type === 'identity' || msg.type === 'seer_result' ? '系统' : 'AI主持人') }}</div>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 玩家讨论区域 -->
            <div class="player-discussion-section">
              <div class="section-header">
                <span class="section-title">玩家讨论</span>
              </div>
              <div class="messages player-messages" ref="playerMessagesContainer">
                <div 
                  v-for="(msg, index) in playerDiscussionMessages" 
                  :key="'player-' + index"
                  :class="['message-bubble', msg.type || 'user']"
                >
                  <div class="message-avatar">
                    <div class="avatar-icon-small">{{ getMessageAvatar(msg) }}</div>
                  </div>
                  <div class="message-content-wrapper">
                    <div class="message-content" v-html="formatMessageContent(msg.content)"></div>
                    <div class="message-sender">{{ msg.username || '玩家' }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="input-area">
            <div class="input-icon">🐺</div>
            <input 
              v-model="inputMessage" 
              @keyup.enter="sendMessage"
              :placeholder="canSpeak ? '输入消息...' : (isCurrentPlayerDead ? '你已死亡，无法发言' : '当前阶段不允许发言')"
              :disabled="!canSpeak"
              class="message-input"
              :class="{ 'input-disabled': !canSpeak }"
            />
            <button @click="sendMessage" :disabled="!canSpeak" class="send-button" :class="{ 'button-disabled': !canSpeak }">发送</button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { createWerewolfRoom, joinWerewolfRoom, startWerewolfGame, getWerewolfRoom, addAIPlayer as addAIPlayerAPI, autoFillAIPlayers } from '../api'
import { eventBus } from '../utils/eventBus'

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
    const aiMessagesContainer = ref(null)
    const playerMessagesContainer = ref(null)
    const flippedCards = ref({}) // 跟踪翻转的卡片
    const selectedVoteTarget = ref(null) // 选中的投票目标
    const phasePopup = ref({ show: false, type: '', text: '' }) // 阶段弹窗
    const shownPhasePopups = ref(new Set()) // 已显示的弹窗类型，防止重复显示
    const roleInfoModal = ref({ show: false, player: null }) // 角色信息弹窗
    // 夜晚行动弹窗
    const nightActionModal = ref({
      show: false,
      action: '', // guard/wolf/seer/witch
      title: '',
      description: '',
      players: [],
      selectedTarget: null,
      cannotGuard: null, // 守卫不能守护的目标
      teammates: [], // 狼人队友
      wolfTarget: null, // 女巫：被击杀的目标
      wolfTargetName: null, // 女巫：被击杀的目标名称
      witchAction: null, // 女巫：选择的行动 (antidote/poison/none)
      antidoteUsed: false,
      poisonUsed: false,
      isFirstNight: false,
      submitting: false
    })
    // 遗言弹窗
    const lastWordsModal = ref({
      show: false,
      role: '',
      submitting: false
    })
    const lastWordsInput = ref('') // 遗言输入
    const wolfChatMessages = ref([]) // 狼人聊天消息
    const wolfChatInput = ref('') // 狼人聊天输入
    const wolfChatContainer = ref(null) // 狼人聊天容器引用
    // 预言家查验结果 { [user_id]: '好人' | '狼人' }
    const seerCheckedResults = ref({})
    // 游戏结束结算弹窗
    const gameOverModal = ref({
      show: false,
      winner: null, // 'wolves' 或 'villagers'
      winnerText: ''
    })
    // 退出确认弹窗
    const exitConfirmModal = ref({
      show: false
    })
    // 错误提示弹窗
    const errorModal = ref({
      show: false,
      message: ''
    })
    let ws = null
    let pollInterval = null
    let timerInterval = null // 倒计时定时器
    let phasePopupTimer = null // 阶段弹窗定时器
    
    // AI引导信息（系统消息、身份消息、AI主持人消息、私密消息）
    const aiGuideMessages = computed(() => {
      const messages = []
      // 添加私有消息中的身份信息和预言家查验结果
      privateMessages.value.forEach(msg => {
        if (msg && msg.type === 'identity') {
          const isDuplicate = messages.some(
            m => m.type === 'identity' && m.content === msg.content
          )
          if (!isDuplicate) {
            messages.push({
              ...msg,
              type: 'identity',
              username: '系统'
            })
          }
        } else if (msg && msg.type === 'seer_result') {
          // 添加预言家查验结果到AI引导信息
          const isDuplicate = messages.some(
            m => m.type === 'seer_result' && m.target_user_id === msg.target_user_id
          )
          if (!isDuplicate) {
            messages.push({
              ...msg,
              type: 'seer_result',
              username: '系统'
            })
          }
        }
      })
      // 添加公共消息中的系统消息和AI主持人消息
      publicMessages.value.forEach(msg => {
        // AI引导消息包括：系统消息、身份消息、AI主持人消息
        if (msg.type === 'system' || msg.type === 'identity' || 
            msg.username === 'AI主持人' || msg.type === 'host') {
          messages.push(msg)
        }
      })
      // 按时间排序
      return messages.sort((a, b) => {
        const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0
        const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0
        return timeA - timeB
      })
    })
    
    // 玩家讨论消息（所有玩家发送的消息，包括AI玩家和真实玩家）
    const playerDiscussionMessages = computed(() => {
      return publicMessages.value
        .filter(msg => {
          // 排除系统消息、身份消息和AI主持人消息
          const isSystemMessage = msg.type === 'system' || msg.type === 'identity' || msg.type === 'host'
          const isAIHost = msg.username === 'AI主持人'
          // 玩家讨论包括：用户消息、AI玩家消息（username包含'AI玩家'或不是AI主持人）
          return !isSystemMessage && !isAIHost
        })
        .sort((a, b) => {
          const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0
          const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0
          return timeA - timeB
        })
    })
    
    // 保留 allMessages 用于向后兼容（如果需要）
    const allMessages = computed(() => {
      return [...aiGuideMessages.value, ...playerDiscussionMessages.value]
    })
    
    // 计算剩余时间（秒）
    const timeRemaining = computed(() => {
      if (!room.value || room.value.phase_start_time === null || room.value.phase_start_time === undefined || 
          room.value.phase_duration === null || room.value.phase_duration === undefined) {
        return null
      }
      // phase_start_time是Unix时间戳（秒），Date.now()是毫秒，需要转换
      const currentTime = Date.now() / 1000
      const elapsed = currentTime - room.value.phase_start_time
      const remaining = room.value.phase_duration - elapsed
      return Math.max(0, Math.floor(remaining))
    })
    
    // 计算是否允许发言
    const canSpeak = computed(() => {
      if (!room.value) return false
      if (room.value.phase === 'waiting' || room.value.phase === 'game_over') return false
      if (!room.value.can_speak) return false
      if (timeRemaining.value !== null && timeRemaining.value <= 0) return false
      // 检查玩家是否真正死亡（只有明确为false时才认为是死亡）
      if (isCurrentPlayerDead.value) return false
      return true
    })
    
    // 获取存活的玩家（用于投票，包括自己）
    const alivePlayersForVoting = computed(() => {
      if (!room.value || !room.value.players) return []
      return room.value.players.filter(p => p.alive)
    })
    
    // 获取当前玩家
    const currentPlayer = computed(() => {
      if (!room.value || !room.value.players) return null
      return room.value.players.find(p => p.user_id === gameStore.userId)
    })
    
    // 判断当前玩家是否真正死亡（只有明确为false时才认为是死亡）
    const isCurrentPlayerDead = computed(() => {
      // 如果当前玩家不存在，默认不是死亡
      if (!currentPlayer.value) return false
      // 只有明确为false时才认为是死亡，undefined或null都认为是存活
      return currentPlayer.value.alive === false
    })
    
    // 判断当前玩家是否存活（用于投票等操作）
    const isCurrentPlayerAlive = computed(() => {
      // 如果当前玩家不存在，默认不是存活
      if (!currentPlayer.value) return false
      // 只有明确为true时才认为是存活，undefined或null都认为不是存活（但也不显示死亡）
      return currentPlayer.value.alive === true
    })
    
    // 是否已投票
    const hasVoted = computed(() => {
      return currentPlayer.value?.voted || false
    })
    
    // 已投票人数
    const votedCount = computed(() => {
      if (!room.value || !room.value.players) return 0
      return room.value.players.filter(p => p.alive && p.voted).length
    })
    
    // 存活玩家总数
    const alivePlayersCount = computed(() => {
      if (!room.value || !room.value.players) return 0
      return room.value.players.filter(p => p.alive).length
    })
    
    // 计算每个玩家获得的票数
    const voteCounts = computed(() => {
      if (!room.value || !room.value.players) return {}
      const counts = {}
      room.value.players.forEach(player => {
        if (player.alive && player.vote_target) {
          counts[player.vote_target] = (counts[player.vote_target] || 0) + 1
        }
      })
      return counts
    })
    
    // 获取玩家获得的票数
    const getPlayerVoteCount = (userId) => {
      return voteCounts.value[userId] || 0
    }
    
    // 选择投票目标
    const selectVoteTarget = (userId) => {
      if (hasVoted.value) return // 已投票不能更改
      selectedVoteTarget.value = userId
    }
    
    // 提交投票
    const submitVote = async () => {
      // 检查玩家是否真正死亡（只有明确为false时才认为是死亡）
      if (isCurrentPlayerDead.value) {
        alert('你已死亡，无法投票')
        return
      }
      
      // 检查玩家是否存在且可以投票
      if (!currentPlayer.value || !isCurrentPlayerAlive.value) {
        // 如果玩家状态不明确，也允许投票（可能是数据同步问题）
        console.warn('[投票] 玩家状态不明确，但允许尝试投票')
      }
      
      if (!selectedVoteTarget.value || hasVoted.value || !ws || ws.readyState !== WebSocket.OPEN) {
        return
      }
      
      try {
        ws.send(JSON.stringify({
          type: 'action',
          action: 'vote',
          target: selectedVoteTarget.value
        }))
        
        // 立即更新本地状态
        if (currentPlayer.value) {
          currentPlayer.value.voted = true
          currentPlayer.value.vote_target = selectedVoteTarget.value
        }
      } catch (error) {
        console.error('投票失败:', error)
        alert('投票失败，请重试')
      }
    }
    
    // 获取投票目标名称（用于白天投票）
    const getVotedTargetName = (userId) => {
      // 如果提供了userId，用于获取狼人投票目标
      if (userId !== undefined) {
        const votedTargetId = getWolfVoteStatus(userId)
        if (!votedTargetId || !room.value || !room.value.players) return ''
        const target = room.value.players.find(p => p.user_id === votedTargetId)
        return target?.username || ''
      }
      // 否则用于获取当前玩家的白天投票目标
      if (!currentPlayer.value || !currentPlayer.value.vote_target) return ''
      const target = room.value?.players?.find(p => p.user_id === currentPlayer.value.vote_target)
      return target?.username || ''
    }
    
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
      if (!targetId || !targetId.trim()) {
        showErrorModal('房间号输入错误或没有输入房间号！')
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
        showErrorModal('房间号输入错误或没有输入房间号！')
      }
    }
    
    const startGame = async () => {
      try {
        // 重置弹窗标记，允许新游戏显示弹窗
        shownPhasePopups.value.clear()
        await startWerewolfGame(roomId.value)
        // 等待一下让后端处理完成
        await new Promise(resolve => setTimeout(resolve, 1000))
        loadRoom()
        // 确保WebSocket已连接，如果没有则重新连接
        if (!ws || ws.readyState !== WebSocket.OPEN) {
          connectWebSocket()
        } else {
          // 如果WebSocket已连接，等待一下让消息到达，然后检查阶段弹窗
          setTimeout(() => {
            checkAndShowPhasePopup()
          }, 500)
        }
      } catch (error) {
        console.error('开始游戏失败:', error)
        // 检查是否是网络错误，如果是，可能游戏已经开始了
        if (error.response && error.response.status >= 500) {
          // 服务器错误，但可能游戏已经开始，尝试加载房间
          setTimeout(() => {
            loadRoom()
            checkAndShowPhasePopup()
          }, 500)
        } else {
          alert('开始游戏失败')
        }
      }
    }
    
    const addAIPlayer = async () => {
      if (!roomId.value) return
      try {
        await addAIPlayerAPI(roomId.value)
        loadRoom()
      } catch (error) {
        console.error('添加AI玩家失败:', error)
        alert('添加AI玩家失败')
      }
    }
    
    const autoFillAI = async () => {
      if (!roomId.value) return
      try {
        const res = await autoFillAIPlayers(roomId.value, 12)
        if (res.data.added_count > 0) {
          loadRoom()
        }
      } catch (error) {
        console.error('自动填充AI玩家失败:', error)
        alert('自动填充AI玩家失败')
      }
    }
    
    const canAddAI = computed(() => {
      if (!room.value || room.value.phase !== 'waiting') return false
      return (room.value.players?.length || 0) < 12
    })
    
    const canAutoFill = computed(() => {
      if (!room.value || room.value.phase !== 'waiting') return false
      const currentCount = room.value.players?.length || 0
      return currentCount < 12
    })
    
    const loadRoom = async () => {
      if (!roomId.value) return
      try {
        const res = await getWerewolfRoom(roomId.value)
        room.value = res.data
        // 如果游戏已开始，加载私有消息
        if (room.value && room.value.phase !== 'waiting') {
          loadPrivateMessages()
        }
      } catch (error) {
        console.error('加载房间失败:', error)
      }
    }
    
    const loadPrivateMessages = async () => {
      if (!roomId.value || !ws || ws.readyState !== WebSocket.OPEN) return
      // 私有消息应该已经通过WebSocket接收，这里只是确保显示
      // 如果WebSocket已连接，私有消息会在连接时自动发送
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
          // 加载私有消息
          loadPrivateMessages()
          // 检查并显示阶段弹窗
          setTimeout(() => {
            checkAndShowPhasePopup()
          }, 100)
        } else if (data.type === 'public_message') {
          let message
          if (typeof data.content === 'string') {
            message = { 
              content: data.content, 
              username: data.username || 'AI主持人', 
              type: data.message_type || 'system' 
            }
          } else {
            // data.content 是一个对象
            message = { 
              ...data.content, 
              type: data.content.type || data.message_type || 'system',
              username: data.content.username || data.username || 'AI主持人'
            }
            // 确保phase_popup字段被保留
            if (data.content.phase_popup) {
              message.phase_popup = data.content.phase_popup
            }
          }
          
          // 如果是当前用户发送的消息，移除临时的待确认消息
          if (message.user_id === gameStore.userId && message.content) {
            const pendingIndex = publicMessages.value.findIndex(
              msg => msg.isPending && 
                     msg.user_id === gameStore.userId && 
                     msg.content === message.content
            )
            if (pendingIndex !== -1) {
              publicMessages.value.splice(pendingIndex, 1)
            }
          }
          
          // 避免重复添加相同的消息（使用更可靠的去重逻辑）
          const isDuplicate = publicMessages.value.some(
            msg => {
              // 如果消息有 user_id，使用 user_id + content 来判断
              if (message.user_id && msg.user_id) {
                return msg.user_id === message.user_id && 
                       msg.content === message.content &&
                       msg.type === message.type
              }
              // 否则使用原来的逻辑
              return msg.content === message.content && 
                     msg.type === message.type && 
                     Math.abs((new Date(msg.timestamp || 0) - new Date(message.timestamp || 0))) < 1000
            }
          )
          
          if (!isDuplicate) {
            publicMessages.value.push(message)
            scrollToBottom()
            // 如果消息包含阶段弹窗，立即显示
            if (message.phase_popup) {
              showPhasePopup(message.phase_popup)
            }
          }
        } else if (data.type === 'private_message') {
          privateMessages.value.push(data.content)
          // 如果是身份信息，立即显示
          if (data.content && data.content.type === 'identity') {
            scrollToBottom()
          }
          // 如果是预言家查验结果，存储查验结果
          if (data.content && data.content.type === 'seer_result') {
            console.log('[预言家查验] 收到查验结果:', data.content)
            if (data.content.target_user_id && data.content.result) {
              seerCheckedResults.value[data.content.target_user_id] = data.content.result
              console.log('[预言家查验] 已存储查验结果:', {
                target_user_id: data.content.target_user_id,
                result: data.content.result,
                seerCheckedResults: seerCheckedResults.value
              })
            } else {
              console.warn('[预言家查验] 查验结果缺少必要字段:', data.content)
            }
            scrollToBottom()
          }
          // 如果是夜晚行动消息，显示弹窗（需要检查玩家是否存活）
          if (data.content && data.content.type === 'night_action') {
            // 检查当前玩家是否存活
            if (currentPlayer.value && currentPlayer.value.alive) {
              showNightActionModal(data.content)
            } else {
              console.log('[夜晚行动] 玩家已死亡，不显示夜晚行动弹窗')
            }
          }
          // 如果是遗言消息，显示弹窗
          if (data.content && data.content.type === 'last_words') {
            showLastWordsModal(data.content)
          }
          // 如果是猎人开枪消息，显示弹窗
          if (data.content && data.content.type === 'hunter_shot') {
            showNightActionModal({
              ...data.content,
              action: 'hunter_shot',
              title: '🏹 猎人开枪'
            })
          }
        } else if (data.type === 'wolf_chat') {
          // 接收狼人聊天消息
          if (data.content) {
            wolfChatMessages.value.push({
              content: data.content.content || data.content,
              username: data.content.username || data.username || '未知',
              timestamp: data.content.timestamp || Date.now()
            })
            scrollWolfChat()
          }
        } else if (data.type === 'room_update') {
          const oldPhase = room.value?.phase
          const oldPlayerAlive = currentPlayer.value?.alive
          
          // 关键修复：在投票阶段开始时，保护当前玩家的alive状态
          // 如果从非投票阶段进入投票阶段，且当前玩家之前是存活的，则确保在投票阶段开始时不会错误地显示死亡
          const isEnteringVotingPhase = oldPhase !== 'voting' && data.room?.phase === 'voting'
          const wasAliveBefore = oldPlayerAlive === true
          
          // 更新房间状态
          room.value = data.room
          
          // 如果正在进入投票阶段，且之前是存活的，强制修复错误的死亡状态
          // 重要：只有在投票阶段结束后才会更新死亡状态，所以投票阶段开始时不应该有任何玩家死亡
          if (isEnteringVotingPhase && currentPlayer.value) {
            // 如果玩家之前是存活的，但后端发送的数据中错误地标记为死亡，我们需要在前端修复它
            if (wasAliveBefore && !currentPlayer.value.alive) {
              console.warn('[房间更新] 修复：进入投票阶段时，当前玩家被错误地标记为死亡，强制设置为存活（投票阶段刚开始，不应该有死亡状态）')
              // 强制修复：在投票阶段开始时，如果玩家之前是存活的，就设置为存活
              currentPlayer.value.alive = true
            }
            // 如果玩家之前的状态未知（比如第一次进入），但当前标记为死亡，也修复它
            // 因为投票阶段刚开始时不应该有任何玩家死亡
            else if (oldPlayerAlive === undefined && !currentPlayer.value.alive) {
              console.warn('[房间更新] 修复：进入投票阶段时，当前玩家状态未知但被标记为死亡，强制设置为存活（投票阶段刚开始，不应该有死亡状态）')
              currentPlayer.value.alive = true
            }
          }
          
          // 检查玩家死亡状态变化，如果从存活变为死亡，关闭夜晚行动弹窗
          // 注意：在投票阶段开始时不应该触发这个逻辑，因为我们已经修复了死亡状态
          const newPlayerAlive = currentPlayer.value?.alive
          if (oldPlayerAlive === true && newPlayerAlive === false && nightActionModal.value.show && !isEnteringVotingPhase) {
            console.log('[房间更新] 玩家已死亡，关闭夜晚行动弹窗')
            nightActionModal.value.show = false
          }
          
          // 如果游戏刚刚开始，加载私有消息和公共消息
          if (room.value && oldPhase === 'waiting' && room.value.phase !== 'waiting') {
            // 游戏刚开始，重新加载消息
            setTimeout(() => {
              loadRoom()
              // 重新获取消息
              if (ws && ws.readyState === WebSocket.OPEN) {
                // 消息应该已经通过WebSocket接收，这里确保显示
              }
            }, 300)
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
      
      // 检查是否允许发言
      if (!canSpeak.value) {
        alert('当前阶段不允许发言或发言时间已结束')
        return
      }
      
      const messageContent = inputMessage.value.trim()
      
      // 立即显示用户消息（标记为待确认）
      publicMessages.value.push({
        content: messageContent,
        username: username.value || '我',
        type: 'user',
        user_id: gameStore.userId,
        isPending: true, // 标记为待确认消息
        tempId: Date.now() // 临时ID用于后续匹配
      })
      scrollToBottom()
      
      ws.send(JSON.stringify({
        type: 'message',
        content: messageContent
      }))
      
      inputMessage.value = ''
    }
    
    const startPolling = () => {
      pollInterval = setInterval(loadRoom, 2000)
    }
    
    const scrollToBottom = () => {
      nextTick(() => {
        // 滚动AI引导信息区域
        if (aiMessagesContainer.value) {
          aiMessagesContainer.value.scrollTop = aiMessagesContainer.value.scrollHeight
        }
        // 滚动玩家讨论区域
        if (playerMessagesContainer.value) {
          playerMessagesContainer.value.scrollTop = playerMessagesContainer.value.scrollHeight
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
        'hunter': '猎人',
        'guard': '守卫'
      }
      return names[role] || '未知'
    }
    
    const getRoleDescription = (role) => {
      const descriptions = {
        'wolf': '每晚可以共同决定击杀一名玩家。白天需要伪装成好人，混淆视听。',
        'villager': '无任何技能，全程闭眼。依靠白天发言和逻辑推理找出狼人。',
        'seer': '每晚可以查验一名玩家的身份，得知是"好人"还是"狼人"。',
        'witch': '拥有解药（可救被刀玩家）和毒药（可毒杀任意玩家）。每瓶只能用一次，每晚只能使用一瓶。首夜不能自救。',
        'hunter': '被投票出局或被狼刀（且未被毒）时，可开枪带走一名玩家。若被女巫毒死，则无法开枪。',
        'guard': '每晚可守护一人（包括自己），防止其被刀。不能连续两晚守同一人。若守的人被女巫救，可能出现"同守同救"导致死亡。'
      }
      return descriptions[role] || '未知角色'
    }
    
    const toggleCard = (userId) => {
      const player = room.value?.players?.find(p => p.user_id === userId)
      if (player && shouldShowCardFront(player)) {
        flippedCards.value[userId] = !flippedCards.value[userId]
      }
    }
    
    // 判断是否应该显示卡片正面（自己或狼人队友）
    const shouldShowCardFront = (player) => {
      if (!player) return false
      
      // 如果游戏结束，显示所有玩家的身份
      if (room.value && room.value.phase === 'game_over') {
        return true
      }
      
      // 如果是自己，显示正面（即使还没有角色）
      if (isCurrentUser(player.user_id)) {
        return true
      }
      
      // 如果游戏还没开始或没有角色，显示反面
      if (!player.role || !room.value || room.value.phase === 'waiting') {
        return false
      }
      
      // 如果当前玩家是狼人，检查是否是队友
      const currentPlayer = room.value?.players?.find(p => p.user_id === gameStore.userId)
      if (!currentPlayer || !currentPlayer.role) return false
      
      const currentRole = currentPlayer.role?.toLowerCase?.() || currentPlayer.role
      if (currentRole === 'wolf') {
        // 检查目标玩家是否是狼人
        const playerRole = player.role?.toLowerCase?.() || player.role
        return playerRole === 'wolf'
      }
      
      return false
    }
    
    // 判断投票阶段的卡片是否应该显示正面（只有狼人能看到队友）
    const shouldShowVotingCardFront = (player) => {
      if (!player) return false
      
      // 如果是自己，显示正面
      if (isCurrentUser(player.user_id)) {
        return true
      }
      
      // 如果游戏还没开始或没有角色，显示反面
      if (!player.role || !room.value || room.value.phase !== 'voting') {
        return false
      }
      
      // 在投票阶段，只有狼人才能看到队友的正面
      const currentPlayer = room.value?.players?.find(p => p.user_id === gameStore.userId)
      if (!currentPlayer || !currentPlayer.role) return false
      
      const currentRole = currentPlayer.role?.toLowerCase?.() || currentPlayer.role
      if (currentRole === 'wolf') {
        // 检查目标玩家是否是狼人队友
        const playerRole = player.role?.toLowerCase?.() || player.role
        return playerRole === 'wolf'
      }
      
      // 其他玩家在投票阶段不能看到其他人的角色
      return false
    }
    
    // 显示角色信息弹窗
    const showRoleInfo = (player) => {
      roleInfoModal.value = {
        show: true,
        player: player
      }
    }
    
    // 关闭角色信息弹窗
    const closeRoleInfo = () => {
      roleInfoModal.value = {
        show: false,
        player: null
      }
    }
    
    // 显示错误提示弹窗
    const showErrorModal = (message) => {
      errorModal.value = {
        show: true,
        message: message
      }
    }
    
    // 关闭错误提示弹窗
    const closeErrorModal = () => {
      errorModal.value = {
        show: false,
        message: ''
      }
    }
    
    const getCharacterIcon = (role) => {
      const icons = {
        'wolf': '/role-avatars/狼人.png',
        'villager': '/role-avatars/村民.png',
        'seer': '/role-avatars/预言家.png',
        'witch': '/role-avatars/女巫.png',
        'hunter': '/role-avatars/猎人.png',
        'guard': '/role-avatars/守卫.png'
      }
      return icons[role] || null
    }
    
    const getMessageAvatar = (msg) => {
      if (msg.type === 'system' || msg.type === 'identity' || !msg.username || msg.username === '系统') {
        return '🎭'
      }
      if (msg.username === 'AI主持人') {
        return '🎪'
      }
      return '👤'
    }
    
    const formatMessageContent = (content) => {
      if (typeof content !== 'string') return content
      // 将换行符转换为<br>
      return content.replace(/\n/g, '<br>')
    }
    
    const formatTime = (seconds) => {
      if (seconds === null || seconds < 0) return '--:--'
      const mins = Math.floor(seconds / 60)
      const secs = seconds % 60
      return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    
    const getPhaseName = (phase) => {
      const phaseNames = {
        'waiting': '等待阶段',
        'identity_assign': '身份分配',
        'night': '夜晚阶段',
        'day': '讨论阶段',
        'voting': '投票阶段',
        'elimination': '淘汰阶段',
        'game_over': '游戏结束'
      }
      return phaseNames[phase] || phase
    }
    
    // 获取带时间信息的阶段名称（如"第一夜"、"第二日"等）
    const getPhaseNameWithTime = (room) => {
      if (!room) return ''
      
      const phase = room.phase
      let timePrefix = ''
      
      if (phase === 'night' && room.night_count) {
        timePrefix = `第${room.night_count}夜`
      } else if (phase === 'day' && room.day_count) {
        timePrefix = `第${room.day_count}日`
      } else if (phase === 'voting' && room.day_count) {
        timePrefix = `第${room.day_count}日`
      }
      
      const phaseName = getPhaseName(phase)
      
      if (timePrefix) {
        return `${timePrefix} ${phaseName}`
      }
      return phaseName
    }
    
    // 清理游戏状态
    const cleanupGame = () => {
      stopTimer()
      if (phasePopupTimer) {
        clearTimeout(phasePopupTimer)
        phasePopupTimer = null
      }
      if (ws) {
        ws.close()
        ws = null
      }
      if (pollInterval) {
        clearInterval(pollInterval)
        pollInterval = null
      }
      // 清理游戏数据
      room.value = null
      roomId.value = ''
      publicMessages.value = []
      privateMessages.value = []
      flippedCards.value = {}
      selectedVoteTarget.value = null
    }
    
    // 待跳转的目标路径
    const pendingNavigationPath = ref(null)
    
    // 确认退出游戏
    const confirmExit = () => {
      cleanupGame()
      exitConfirmModal.value.show = false
      const targetPath = pendingNavigationPath.value || '/game-mode'
      pendingNavigationPath.value = null
      // 如果是从导航栏触发的，通知App.vue执行导航
      if (targetPath !== '/game-mode') {
        eventBus.emit('exit-confirmed', targetPath)
      } else {
        router.push(targetPath)
      }
    }
    
    // 显示退出确认弹窗
    const showExitConfirm = (targetPath = null) => {
      pendingNavigationPath.value = targetPath
      exitConfirmModal.value.show = true
    }
    
    const closeChat = () => {
      showExitConfirm()
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
        gameProgress.value = Math.min(100, Math.round((newLength / 12) * 100))
      }
    }, { immediate: true })
    
    // 启动倒计时定时器
    const startTimer = () => {
      if (timerInterval) {
        clearInterval(timerInterval)
      }
      // 每秒更新一次倒计时
      timerInterval = setInterval(() => {
        // 触发响应式更新
        if (room.value) {
          // 通过重新计算timeRemaining来触发更新
          // Vue的computed会自动处理
        }
      }, 1000)
    }
    
    // 停止倒计时定时器
    const stopTimer = () => {
      if (timerInterval) {
        clearInterval(timerInterval)
        timerInterval = null
      }
    }
    
    // 显示阶段弹窗
    const showPhasePopup = (type) => {
      // 对于阶段弹窗，只显示一次
      if (shownPhasePopups.value.has(type)) {
        return
      }
      
      const popupTexts = {
        'night_start': '夜晚到来...',
        'night_end': '夜晚结束...',
        'day_start': '白天到来...',
        'day_end': '白天结束...'
      }
      
      phasePopup.value = {
        show: true,
        type: type,
        text: popupTexts[type] || ''
      }
      
      // 标记为已显示
      shownPhasePopups.value.add(type)
      
      // 1.5秒后自动隐藏（缩短显示时间）
      if (phasePopupTimer) {
        clearTimeout(phasePopupTimer)
      }
      phasePopupTimer = setTimeout(() => {
        phasePopup.value.show = false
      }, 1500)
    }
    
    // 监听公共消息，检查是否有阶段弹窗
    const processedMessageIds = ref(new Set()) // 已处理的消息ID，避免重复处理
    watch(() => publicMessages.value, (newMessages, oldMessages) => {
      if (newMessages && newMessages.length > 0) {
        // 只检查新添加的消息
        const oldLength = oldMessages ? oldMessages.length : 0
        for (let i = oldLength; i < newMessages.length; i++) {
          const msg = newMessages[i]
          if (msg && msg.phase_popup) {
            // 使用消息的 timestamp 作为唯一标识
            const msgId = msg.timestamp || `${msg.content}-${msg.type}`
            if (!processedMessageIds.value.has(msgId)) {
              showPhasePopup(msg.phase_popup)
              processedMessageIds.value.add(msgId)
            }
            break
          }
        }
      }
    }, { deep: true })
    
    // 检查并显示最新的阶段弹窗（用于初始加载）
    const checkAndShowPhasePopup = () => {
      if (publicMessages.value && publicMessages.value.length > 0) {
        for (let i = publicMessages.value.length - 1; i >= 0; i--) {
          const msg = publicMessages.value[i]
          if (msg && msg.phase_popup) {
            showPhasePopup(msg.phase_popup)
            break
          }
        }
      }
    }
    
    // 显示夜晚行动弹窗
    const showNightActionModal = (actionData) => {
      // 检查当前玩家是否存活，如果已死亡则不显示弹窗
      if (!currentPlayer.value || !currentPlayer.value.alive) {
        console.log('[夜晚行动] 玩家已死亡，不显示夜晚行动弹窗')
        return
      }
      
      const action = actionData.action
      const titles = {
        'guard': '🛡️ 守卫行动',
        'wolf': '🐺 狼人行动',
        'seer': '🔮 预言家行动',
        'witch': '🧪 女巫行动'
      }
      
      nightActionModal.value = {
        show: true,
        action: action,
        title: titles[action] || '夜晚行动',
        description: actionData.content || '',
        players: actionData.players || [],
        selectedTarget: null,
        cannotGuard: actionData.cannot_guard || null,
        teammates: actionData.teammates || [],
        wolfTarget: actionData.wolf_target || null,
        wolfTargetName: actionData.wolf_target_name || null,
        witchAction: null,
        antidoteUsed: actionData.antidote_used || false,
        poisonUsed: actionData.poison_used || false,
        isFirstNight: actionData.is_first_night || false,
        submitting: false
      }
      
      // 如果是狼人行动，清空聊天消息（新的一轮）
      if (action === 'wolf') {
        wolfChatMessages.value = []
      }
    }
    
    // 发送狼人聊天消息
    const sendWolfChatMessage = () => {
      if (!wolfChatInput.value.trim() || !ws || ws.readyState !== WebSocket.OPEN) {
        return
      }
      
      // 立即显示用户消息
      wolfChatMessages.value.push({
        content: wolfChatInput.value,
        username: username.value || '我',
        timestamp: Date.now()
      })
      scrollWolfChat()
      
      // 发送到服务器
      ws.send(JSON.stringify({
        type: 'wolf_chat',
        content: wolfChatInput.value
      }))
      
      wolfChatInput.value = ''
    }
    
    // 格式化聊天时间
    const formatChatTime = (timestamp) => {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      const hours = date.getHours().toString().padStart(2, '0')
      const minutes = date.getMinutes().toString().padStart(2, '0')
      return `${hours}:${minutes}`
    }
    
    // 滚动狼人聊天到底部
    const scrollWolfChat = () => {
      nextTick(() => {
        if (wolfChatContainer.value) {
          wolfChatContainer.value.scrollTop = wolfChatContainer.value.scrollHeight
        }
      })
    }
    
    // 获取所有狼人玩家
    const allWolves = computed(() => {
      if (!room.value || !room.value.players || nightActionModal.value.action !== 'wolf') return []
      // 获取当前玩家
      const currentPlayer = room.value.players.find(p => p.user_id === gameStore.userId)
      // 只有当前玩家是狼人时才显示所有狼人
      if (!currentPlayer) return []
      const currentRole = currentPlayer.role?.toLowerCase?.() || currentPlayer.role
      if (currentRole !== 'wolf') return []
      
      // 返回所有存活的狼人玩家
      return room.value.players.filter(p => {
        if (!p.alive) return false
        const role = p.role?.toLowerCase?.() || p.role
        return role === 'wolf'
      })
    })
    
    // 获取狼人投票状态
    const getWolfVoteStatus = (userId) => {
      if (!room.value || !room.value.night_actions || !room.value.night_actions.wolf) {
        return null
      }
      const votes = room.value.night_actions.wolf.votes || {}
      return votes[userId] || null
    }
    
    // 获取玩家获得的投票数（狼人投票）
    const getPlayerWolfVoteCount = (playerId) => {
      if (!room.value || !room.value.night_actions || !room.value.night_actions.wolf) {
        return 0
      }
      const votes = room.value.night_actions.wolf.votes || {}
      // 统计投票给该玩家的数量
      let count = 0
      for (const votedTargetId of Object.values(votes)) {
        if (votedTargetId === playerId) {
          count++
        }
      }
      return count
    }
    
    // 关闭夜晚行动弹窗
    const closeNightActionModal = () => {
      // 只有在未提交的情况下才允许关闭
      if (!nightActionModal.value.submitting) {
        nightActionModal.value.show = false
      }
    }
    
    // 选择夜晚行动目标
    const selectNightActionTarget = (userId) => {
      if (nightActionModal.value.submitting) return
      // 如果是守卫，检查是否是不能守护的目标
      if (nightActionModal.value.action === 'guard' && userId === nightActionModal.value.cannotGuard) {
        return
      }
      nightActionModal.value.selectedTarget = userId
    }
    
    // 女巫选择行动类型
    const selectWitchAction = (action) => {
      if (nightActionModal.value.submitting) return
      if (action === 'antidote' && nightActionModal.value.antidoteUsed) return
      if (action === 'poison' && nightActionModal.value.poisonUsed) return
      
      nightActionModal.value.witchAction = action
      // 如果选择不使用药水，清空目标
      if (action === 'none') {
        nightActionModal.value.selectedTarget = null
      }
      // 如果选择解药，目标是被击杀的玩家
      if (action === 'antidote') {
        nightActionModal.value.selectedTarget = nightActionModal.value.wolfTarget
      }
    }
    
    // 提交夜晚行动
    const submitNightAction = async () => {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        alert('连接已断开，请刷新页面')
        return
      }
      
      if (nightActionModal.value.submitting) return
      
      const action = nightActionModal.value.action
      let actionData = {}
      
      if (action === 'guard') {
        if (!nightActionModal.value.selectedTarget) {
          alert('请选择要守护的玩家')
          return
        }
        actionData = {
          action: 'guard',
          target: nightActionModal.value.selectedTarget
        }
      } else if (action === 'wolf') {
        if (!nightActionModal.value.selectedTarget) {
          alert('请选择要击杀的玩家')
          return
        }
        actionData = {
          action: 'wolf',
          target: nightActionModal.value.selectedTarget
        }
      } else if (action === 'seer') {
        if (!nightActionModal.value.selectedTarget) {
          alert('请选择要查验的玩家')
          return
        }
        actionData = {
          action: 'seer',
          target: nightActionModal.value.selectedTarget
        }
      } else if (action === 'witch') {
        if (!nightActionModal.value.witchAction) {
          alert('请选择你的行动')
          return
        }
        if (nightActionModal.value.witchAction === 'poison' && !nightActionModal.value.selectedTarget) {
          alert('请选择要毒杀的玩家')
          return
        }
        if (nightActionModal.value.witchAction === 'antidote' && !nightActionModal.value.wolfTarget) {
          alert('没有需要救援的玩家')
          return
        }
        // 首夜不能自救
        if (nightActionModal.value.isFirstNight && 
            nightActionModal.value.witchAction === 'antidote' && 
            nightActionModal.value.wolfTarget === gameStore.userId) {
          alert('首夜不能自救！')
          return
        }
        
        actionData = {
          action: 'witch',
          witch_action: nightActionModal.value.witchAction,
          target: nightActionModal.value.selectedTarget
        }
      }
      
      nightActionModal.value.submitting = true
      
      try {
        ws.send(JSON.stringify({
          type: 'action',
          action: actionData.action,
          target: actionData.target,
          witch_action: actionData.witch_action
        }))
        
        // 等待一下，然后关闭弹窗
        setTimeout(() => {
          nightActionModal.value.show = false
          nightActionModal.value.submitting = false
        }, 500)
      } catch (error) {
        console.error('提交夜晚行动失败:', error)
        alert('提交失败，请重试')
        nightActionModal.value.submitting = false
      }
    }
    
    // 监听私有消息，检查是否有夜晚行动消息和预言家查验结果
    watch(() => privateMessages.value, (newMessages) => {
      if (newMessages && newMessages.length > 0) {
        // 处理所有预言家查验结果（包括历史消息）
        newMessages.forEach(msg => {
          if (msg && msg.type === 'seer_result' && msg.target_user_id && msg.result) {
            seerCheckedResults.value[msg.target_user_id] = msg.result
          }
        })
        
        // 查找最新的夜晚行动消息
        for (let i = newMessages.length - 1; i >= 0; i--) {
          const msg = newMessages[i]
          if (msg && msg.type === 'night_action') {
            // 检查当前玩家是否存活
            if (!currentPlayer.value || !currentPlayer.value.alive) {
              console.log('[夜晚行动] 玩家已死亡，不显示夜晚行动弹窗')
              break
            }
            
            // 检查是否已经显示过这个行动（通过检查房间的current_night_phase）
            const currentPhase = room.value?.current_night_phase
            if (currentPhase === msg.action && !nightActionModal.value.show) {
              showNightActionModal(msg)
            }
            break
          }
        }
      }
    }, { deep: true })
    
    // 监听房间状态更新，检查是否有新的夜晚行动阶段
    watch(() => room.value?.current_night_phase, (newPhase) => {
      if (newPhase && room.value?.phase === 'night') {
        // 检查当前玩家是否存活
        if (!currentPlayer.value || !currentPlayer.value.alive) {
          console.log('[夜晚行动] 玩家已死亡，不显示夜晚行动弹窗')
          return
        }
        
        // 检查私有消息中是否有对应的夜晚行动消息
        if (privateMessages.value && privateMessages.value.length > 0) {
          for (let i = privateMessages.value.length - 1; i >= 0; i--) {
            const msg = privateMessages.value[i]
            if (msg && msg.type === 'night_action' && msg.action === newPhase) {
              if (!nightActionModal.value.show || nightActionModal.value.action !== newPhase) {
                showNightActionModal(msg)
              }
              break
            }
          }
        }
      }
    })
    
    // 监听房间变化，启动或停止定时器
    watch(() => room.value?.phase, (newPhase, oldPhase) => {
      // 当游戏从等待状态开始时，重置弹窗标记
      if (oldPhase === 'waiting' && newPhase && newPhase !== 'waiting' && newPhase !== 'game_over') {
        shownPhasePopups.value.clear()
        processedMessageIds.value.clear()
      }
      // 当阶段变化时（如从夜晚到白天），清除对应阶段的弹窗标记，以便显示新阶段的弹窗
      if (oldPhase && newPhase && oldPhase !== newPhase && newPhase !== 'waiting' && newPhase !== 'game_over') {
        // 清除旧阶段的弹窗标记
        if (oldPhase === 'night') {
          shownPhasePopups.value.delete('night_start')
          shownPhasePopups.value.delete('night_end')
        } else if (oldPhase === 'day') {
          shownPhasePopups.value.delete('day_start')
          shownPhasePopups.value.delete('day_end')
        }
      }
      
      // 游戏结束处理
      if (newPhase === 'game_over' && oldPhase !== 'game_over') {
        stopTimer()
        // 翻开所有身份牌：清除所有flippedCards，让所有卡片显示正面
        if (room.value && room.value.players) {
          room.value.players.forEach(player => {
            if (player && player.user_id) {
              // 删除flippedCards中的记录，让!flippedCards[player.user_id]为true，从而显示正面
              delete flippedCards.value[player.user_id]
            }
          })
        }
        // 显示结算弹窗
        const winner = room.value?.winner
        if (winner) {
          gameOverModal.value = {
            show: true,
            winner: winner,
            winnerText: winner === 'wolves' ? '狼人阵营获胜！' : '好人阵营获胜！'
          }
        }
      } else if (newPhase && newPhase !== 'waiting' && newPhase !== 'game_over') {
        startTimer()
      } else {
        stopTimer()
      }
      
      // 当进入投票阶段时，重置投票选择
      if (newPhase === 'voting' && oldPhase !== 'voting') {
        selectedVoteTarget.value = null
        // 如果当前玩家已投票，显示已投票的目标
        if (currentPlayer.value?.voted && currentPlayer.value?.vote_target) {
          selectedVoteTarget.value = currentPlayer.value.vote_target
        }
      }
    }, { immediate: true })
    
    // 监听当前玩家的投票状态
    watch(() => currentPlayer.value?.voted, (voted) => {
      if (voted && currentPlayer.value?.vote_target) {
        selectedVoteTarget.value = currentPlayer.value.vote_target
      }
    })
    
    // 保存事件处理函数引用，以便在onUnmounted中移除
    const handleExitConfirm = (targetPath) => {
      showExitConfirm(targetPath)
    }
    
    onMounted(() => {
      // 如果URL中有房间号，自动加入
      const urlParams = new URLSearchParams(window.location.search)
      const roomIdParam = urlParams.get('roomId')
      if (roomIdParam) {
        roomId.value = roomIdParam
        joinRoom(roomIdParam)
      }
      
      // 监听来自App.vue的退出确认事件
      eventBus.on('show-exit-confirm', handleExitConfirm)
      
      // 监听浏览器窗口关闭事件
      const handleBeforeUnload = (e) => {
        // 如果游戏正在进行中，显示确认提示
        if (room.value && room.value.phase && room.value.phase !== 'waiting' && room.value.phase !== 'game_over') {
          e.preventDefault()
          e.returnValue = '确定要退出游戏吗？退出后游戏将自动停止。'
          return e.returnValue
        }
      }
      window.addEventListener('beforeunload', handleBeforeUnload)
      
      // 保存事件处理函数引用，以便在onUnmounted中移除
      window._werewolfBeforeUnloadHandler = handleBeforeUnload
    })
    
    onUnmounted(() => {
      stopTimer()
      if (phasePopupTimer) {
        clearTimeout(phasePopupTimer)
      }
      if (ws) {
        ws.close()
      }
      if (pollInterval) {
        clearInterval(pollInterval)
      }
      // 移除事件监听
      eventBus.off('show-exit-confirm', handleExitConfirm)
      // 移除浏览器窗口关闭事件监听
      if (window._werewolfBeforeUnloadHandler) {
        window.removeEventListener('beforeunload', window._werewolfBeforeUnloadHandler)
        delete window._werewolfBeforeUnloadHandler
      }
    })
    
    return {
      roomId,
      joinRoomId,
      username,
      room,
      publicMessages,
      privateMessages,
      allMessages,
      aiGuideMessages,
      playerDiscussionMessages,
      inputMessage,
      aiMessagesContainer,
      playerMessagesContainer,
      gameProgress,
      displayPlayers,
      createRoom,
      joinRoom,
      startGame,
      sendMessage,
      isCurrentUser,
      getRoleName,
      getRoleDescription,
      getCharacterIcon,
      getMessageAvatar,
      formatMessageContent,
      formatTime,
      getPhaseName,
      getPhaseNameWithTime,
      timeRemaining,
      canSpeak,
      closeChat,
      confirmExit,
      showExitConfirm,
      exitConfirmModal,
      addAIPlayer,
      autoFillAI,
      canAddAI,
      canAutoFill,
      toggleCard,
      flippedCards,
      shouldShowCardFront,
      showRoleInfo,
      closeRoleInfo,
      roleInfoModal,
      gameOverModal,
      alivePlayersForVoting,
      selectedVoteTarget,
      selectVoteTarget,
      submitVote,
      hasVoted,
      votedCount,
      alivePlayersCount,
      getVotedTargetName,
      getPlayerVoteCount,
      shouldShowVotingCardFront,
      phasePopup,
      nightActionModal,
      showNightActionModal,
      closeNightActionModal,
      selectNightActionTarget,
      selectWitchAction,
      submitNightAction,
      wolfChatMessages,
      wolfChatInput,
      wolfChatContainer,
      sendWolfChatMessage,
      formatChatTime,
      scrollWolfChat,
      allWolves,
      getWolfVoteStatus,
      getPlayerWolfVoteCount,
      seerCheckedResults,
      errorModal,
      showErrorModal,
      closeErrorModal
    }
  }
}
</script>

<style scoped>
.werewolf {
  min-height: 100vh;
  padding: 0;
  background: transparent;
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
  /* 隐藏滚动条但保持滚动功能 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.left-panel::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
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

.room-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ai-buttons {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.btn-ai,
.btn-ai-auto {
  padding: 10px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9em;
  font-weight: bold;
  color: white;
  transition: all 0.3s ease;
  width: 100%;
}

.btn-ai {
  background: #9f7aea;
}

.btn-ai:hover:not(:disabled) {
  background: #805ad5;
}

.btn-ai-auto {
  background: #ed8936;
}

.btn-ai-auto:hover:not(:disabled) {
  background: #dd6b20;
}

.btn-ai:disabled,
.btn-ai-auto:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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
  aspect-ratio: 3/4;
  background: rgba(0, 0, 0, 0.6);
  border: 2px solid rgba(212, 175, 55, 0.4);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  perspective: 1000px;
  cursor: default;
  box-shadow: 
    0 4px 6px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(212, 175, 55, 0.1);
}

.character-slot.is-current-user {
  cursor: pointer;
}

.character-slot.is-current-user:hover {
  border-color: rgba(212, 175, 55, 0.8);
  box-shadow: 
    0 0 20px rgba(212, 175, 55, 0.4),
    0 6px 12px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(212, 175, 55, 0.2);
  transform: translateY(-2px);
}

.character-slot.has-player {
  border-color: rgba(212, 175, 55, 0.5);
  background: rgba(20, 20, 20, 0.8);
  box-shadow: 
    0 4px 8px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(212, 175, 55, 0.1);
}

.character-slot.alive {
  /* 移除绿色边框，保持默认样式 */
}

.character-slot.dead {
  opacity: 0.5;
  border-color: rgba(229, 62, 62, 0.6);
  box-shadow: 
    0 2px 4px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.character-card-inner {
  width: 100%;
  height: 100%;
  position: relative;
  transform-style: preserve-3d;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.character-slot.show-front .character-card-inner {
  transform: rotateY(0deg);
}

.character-slot.show-back .character-card-inner {
  transform: rotateY(180deg);
}

.character-slot.flipped .character-card-inner {
  transform: rotateY(180deg);
}

.character-card-front,
.character-card-back {
  width: 100%;
  height: 100%;
  position: absolute;
  backface-visibility: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  overflow: hidden;
}

.character-card-back {
  transform: rotateY(180deg);
}

.card-front-content {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  background: linear-gradient(135deg, 
    rgba(10, 10, 10, 0.95) 0%, 
    rgba(20, 20, 20, 0.95) 50%,
    rgba(10, 10, 10, 0.95) 100%);
  padding: 4px;
  border-radius: 10px;
  box-shadow: 
    inset 0 2px 4px rgba(0, 0, 0, 0.5),
    inset 0 -2px 4px rgba(212, 175, 55, 0.1);
  border: 1px solid rgba(212, 175, 55, 0.2);
}

.character-avatar {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  position: relative;
  padding: 0;
  overflow: hidden;
}

.avatar-icon {
  font-size: 2.8em;
  transition: transform 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  overflow: hidden;
  z-index: 1;
}

.avatar-icon img {
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
  object-fit: cover;
  filter: blur(1px) brightness(0.85);
  display: block;
  transform: scale(1.1);
}

.character-slot:hover .avatar-icon img {
  filter: blur(0.5px) brightness(0.9);
  transform: scale(1.15);
}

.avatar-text-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  z-index: 2;
  padding: 12px;
  padding-bottom: 16px;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.25) 0%,
    rgba(0, 0, 0, 0.15) 50%,
    rgba(0, 0, 0, 0.4) 100%
  );
}

.avatar-name {
  color: #ffffff;
  font-size: 0.55em;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 3px;
  width: 100%;
  text-align: center;
  text-shadow: 
    0 2px 4px rgba(0, 0, 0, 0.8),
    0 0 8px rgba(0, 0, 0, 0.6);
  flex-shrink: 0;
}

.role-label {
  color: rgba(255, 255, 255, 0.95);
  font-size: 0.55em;
  font-weight: 700;
  background: linear-gradient(135deg, 
    rgba(212, 175, 55, 0.9) 0%, 
    rgba(212, 175, 55, 0.8) 100%);
  padding: 2px 6px;
  border-radius: 3px;
  margin-top: 1px;
  display: inline-block;
  border: 1.5px solid rgba(212, 175, 55, 1);
  box-shadow: 
    0 2px 4px rgba(0, 0, 0, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.3),
    0 0 8px rgba(212, 175, 55, 0.5);
  text-shadow: 
    0 2px 4px rgba(0, 0, 0, 0.9),
    0 0 8px rgba(0, 0, 0, 0.6);
  flex-shrink: 0;
  letter-spacing: 0.15px;
}

/* 预言家查验结果标记 */
.seer-check-badge {
  margin-top: 8px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.75em;
  font-weight: 700;
  display: inline-block;
  text-shadow: 
    0 2px 4px rgba(0, 0, 0, 0.9),
    0 0 8px rgba(0, 0, 0, 0.6);
  box-shadow: 
    0 4px 8px rgba(0, 0, 0, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  animation: seerCheckPulse 0.5s ease-out;
  flex-shrink: 0;
}

.seer-check-good {
  color: #ffffff;
  background: linear-gradient(135deg, 
    rgba(72, 187, 120, 0.95) 0%, 
    rgba(56, 161, 105, 0.9) 100%);
  border: 2px solid rgba(72, 187, 120, 1);
  box-shadow: 
    0 3px 6px rgba(0, 0, 0, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.3),
    0 0 15px rgba(72, 187, 120, 0.5);
}

.seer-check-wolf {
  color: #ffffff;
  background: linear-gradient(135deg, 
    rgba(245, 101, 101, 0.95) 0%, 
    rgba(229, 62, 62, 0.9) 100%);
  border: 2px solid rgba(245, 101, 101, 1);
  box-shadow: 
    0 3px 6px rgba(0, 0, 0, 0.6),
    inset 0 1px 0 rgba(255, 255, 255, 0.3),
    0 0 15px rgba(245, 101, 101, 0.5);
}

/* 卡片背面的查验标记 */
.seer-check-badge-back {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 0.85em;
  font-weight: 800;
  display: inline-block;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 1);
  box-shadow: 
    0 4px 8px rgba(0, 0, 0, 0.7),
    inset 0 2px 0 rgba(255, 255, 255, 0.4),
    0 0 20px rgba(255, 255, 255, 0.3);
  animation: seerCheckPulse 0.5s ease-out;
  z-index: 100;
  letter-spacing: 1px;
  backdrop-filter: blur(4px);
}

.seer-check-badge-back.seer-check-good {
  color: #ffffff;
  background: linear-gradient(135deg, 
    rgba(72, 187, 120, 1) 0%, 
    rgba(56, 161, 105, 0.95) 100%);
  border: 3px solid rgba(72, 187, 120, 1);
  box-shadow: 
    0 4px 8px rgba(0, 0, 0, 0.7),
    inset 0 2px 0 rgba(255, 255, 255, 0.4),
    0 0 25px rgba(72, 187, 120, 0.6);
}

.seer-check-badge-back.seer-check-wolf {
  color: #ffffff;
  background: linear-gradient(135deg, 
    rgba(245, 101, 101, 1) 0%, 
    rgba(229, 62, 62, 0.95) 100%);
  border: 3px solid rgba(245, 101, 101, 1);
  box-shadow: 
    0 4px 8px rgba(0, 0, 0, 0.7),
    inset 0 2px 0 rgba(255, 255, 255, 0.4),
    0 0 25px rgba(245, 101, 101, 0.6);
}

@keyframes seerCheckPulse {
  0% {
    transform: scale(0.8);
    opacity: 0;
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

.role-info-btn {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, 
    rgba(212, 175, 55, 0.6) 0%, 
    rgba(212, 175, 55, 0.4) 100%);
  border: 2px solid rgba(212, 175, 55, 0.7);
  color: rgba(212, 175, 55, 1);
  font-size: 1.1em;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  z-index: 10;
  padding: 0;
  line-height: 1;
  box-shadow: 
    0 2px 6px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(212, 175, 55, 0.3);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
}

.role-info-btn:hover {
  background: linear-gradient(135deg, 
    rgba(212, 175, 55, 0.8) 0%, 
    rgba(212, 175, 55, 0.6) 100%);
  transform: scale(1.15) rotate(90deg);
  box-shadow: 
    0 0 15px rgba(212, 175, 55, 0.6),
    0 4px 8px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(212, 175, 55, 0.4);
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
  border-radius: 10px;
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

/* 数字标识样式 */
.card-number-badge {
  position: absolute;
  top: 4px;
  left: 4px;
  width: 24px;
  height: 24px;
  background: transparent;
  border: none;
  border-radius: 0;
  color: rgba(212, 175, 55, 0.6);
  font-size: 0.9em;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  box-shadow: none;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.8);
  transition: all 0.3s ease;
}

.character-slot:hover .card-number-badge {
  transform: scale(1.1);
  color: rgba(212, 175, 55, 0.8);
}

.character-slot.alive .card-number-badge {
  /* 移除绿色背景，保持默认蓝色样式 */
}

.character-slot.dead .card-number-badge {
  background: transparent;
  border: none;
  color: rgba(212, 175, 55, 0.4);
  opacity: 0.7;
}

.avatar-empty {
  width: 60%;
  height: 60%;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 50%;
}

/* 确保空卡槽显示背面 */
.character-slot:not(.has-player) .character-card-back {
  display: flex;
}

.character-slot:not(.has-player) .character-card-front {
  display: none;
}

.death-indicator {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, 
    rgba(229, 62, 62, 0.9) 0%, 
    rgba(197, 48, 48, 0.9) 100%);
  border: 2px solid rgba(229, 62, 62, 1);
  border-radius: 50%;
  color: #ffffff;
  font-size: 1.1em;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
  box-shadow: 
    0 2px 8px rgba(229, 62, 62, 0.6),
    0 0 15px rgba(229, 62, 62, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
  animation: pulse-death 2s ease-in-out infinite;
}

@keyframes pulse-death {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.05);
  }
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
  overflow: hidden;
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

.chat-content {
  flex: 1;
  display: flex;
  flex-direction: row;
  overflow: hidden;
  min-height: 0;
}

.ai-guide-section,
.player-discussion-section {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}

.ai-guide-section {
  flex: 0 0 40%;
  max-width: 40%;
  border-right: 1px solid rgba(100, 150, 200, 0.2);
}

.player-discussion-section {
  flex: 1;
  min-width: 0;
}

.section-header {
  padding: 12px 20px;
  background: rgba(10, 10, 10, 0.6);
  border-bottom: 1px solid rgba(100, 150, 200, 0.2);
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  color: rgba(100, 150, 200, 0.9);
  font-size: 0.9em;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.phase-timer {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.85em;
}

.phase-name {
  color: rgba(100, 150, 200, 0.7);
  font-weight: 500;
}

.timer {
  color: rgba(100, 150, 200, 0.9);
  font-weight: bold;
  font-family: 'Courier New', monospace;
  padding: 4px 8px;
  background: rgba(100, 150, 200, 0.1);
  border-radius: 4px;
  min-width: 50px;
  text-align: center;
}

.timer-warning {
  color: #ffa500;
  background: rgba(255, 165, 0, 0.15);
  animation: pulse 1s infinite;
}

.timer-danger {
  color: #ff4444;
  background: rgba(255, 68, 68, 0.15);
  animation: pulse 0.5s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.messages {
  flex: 1;
  padding: 15px 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  min-width: 0;
  /* 隐藏滚动条但保持滚动功能 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.messages::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
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

.message-bubble.identity .message-content {
  background: rgba(100, 150, 200, 0.2);
  color: #90cdf4;
  border-color: rgba(100, 150, 200, 0.4);
  font-weight: 500;
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
  background: rgba(10, 10, 10, 0.9);
  flex-shrink: 0;
  z-index: 10;
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

.message-input.input-disabled {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(100, 150, 200, 0.1);
  color: rgba(200, 200, 200, 0.4);
  cursor: not-allowed;
}

.message-input.input-disabled::placeholder {
  color: rgba(150, 150, 150, 0.3);
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

.send-button.button-disabled,
.send-button:disabled {
  background: rgba(100, 150, 200, 0.3);
  border-color: rgba(100, 150, 200, 0.2);
  color: rgba(255, 255, 255, 0.4);
  cursor: not-allowed;
  opacity: 0.6;
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

/* AI消息区域特殊样式 */
.ai-messages .message-bubble {
  opacity: 0.95;
}

/* 玩家讨论区域特殊样式 */
.player-messages .message-bubble.user .message-content {
  background: rgba(102, 126, 234, 0.2);
  border-color: rgba(102, 126, 234, 0.4);
}

/* 投票界面样式 */
.voting-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  overflow-y: auto;
  /* 隐藏滚动条但保持滚动功能 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.voting-container::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.voting-header {
  margin-bottom: 30px;
  text-align: center;
}

.voting-title {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.voting-title h2 {
  color: #ffffff;
  font-size: 2em;
  font-weight: bold;
  margin: 0;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.voting-instruction {
  color: rgba(255, 255, 255, 0.8);
  font-size: 1.1em;
  margin: 0;
}

.voting-players-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 15px;
  margin-bottom: 30px;
  flex: 1;
}

.voting-player-card {
  background: rgba(255, 255, 255, 0.1);
  border: 2px solid rgba(100, 150, 200, 0.3);
  border-radius: 12px;
  padding: 0;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  perspective: 1000px;
  min-height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.voting-player-card:hover:not(.voted):not(.current-user) {
  border-color: rgba(100, 150, 200, 0.8);
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(100, 150, 200, 0.3);
}

.voting-player-card.selected {
  border-color: #ff6b35;
  background: rgba(255, 107, 53, 0.2);
  box-shadow: 0 0 20px rgba(255, 107, 53, 0.5);
}

.voting-player-card.voted {
  opacity: 0.7;
  cursor: not-allowed;
  border-color: rgba(72, 187, 120, 0.6);
  background: rgba(72, 187, 120, 0.1);
}

.voting-player-card.current-user {
  border-color: rgba(100, 150, 200, 0.6);
  background: rgba(100, 150, 200, 0.15);
  cursor: default;
}

.voting-card-inner {
  width: 100%;
  height: 100%;
  position: relative;
  transform-style: preserve-3d;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.voting-player-card.show-front .voting-card-inner {
  transform: rotateY(0deg);
}

.voting-player-card.show-back .voting-card-inner {
  transform: rotateY(180deg);
}

.voting-card-front,
.voting-card-back {
  width: 100%;
  height: 100%;
  position: absolute;
  backface-visibility: hidden;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 15px;
  gap: 8px;
  border-radius: 12px;
}

.voting-card-back {
  transform: rotateY(180deg);
}

.voting-player-avatar {
  position: relative;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.voting-avatar-icon {
  font-size: 2.5em;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: auto;
}

.voting-avatar-icon img {
  width: 100%;
  max-width: 60px;
  height: auto;
  object-fit: contain;
}

.vote-count-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  background: #ff6b35;
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  border: 2px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  z-index: 10;
}

.voted-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 24px;
  height: 24px;
  background: #48bb78;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 0.9em;
  border: 2px solid rgba(255, 255, 255, 0.9);
}

.voting-player-name {
  color: #ffffff;
  font-size: 0.9em;
  font-weight: 500;
  word-break: break-word;
}

.current-user-label {
  color: rgba(100, 150, 200, 0.8);
  font-size: 0.75em;
}

.voted-label {
  color: #48bb78;
  font-size: 0.75em;
  font-weight: 600;
}

/* 投票卡片背面样式 */
.voting-card-back-content {
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
  border: 2px solid #d4af37;
  border-radius: 10px;
  box-shadow: 
    inset 0 0 20px rgba(212, 175, 55, 0.3),
    inset 0 2px 4px rgba(212, 175, 55, 0.15),
    0 0 15px rgba(212, 175, 55, 0.2),
    0 2px 4px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.rose-decoration-small {
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

.rose-decoration-small::before {
  content: '🌹';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) rotate(-15deg) scale(1.8);
  font-size: 2em;
  filter: drop-shadow(0 0 6px rgba(220, 20, 60, 0.8)) 
          drop-shadow(0 0 12px rgba(220, 20, 60, 0.6))
          drop-shadow(0 0 20px rgba(220, 20, 60, 0.4));
  animation: roseGlowSmall 3s ease-in-out infinite;
}

@keyframes roseGlowSmall {
  0%, 100% {
    opacity: 0.7;
    transform: translate(-50%, -50%) rotate(-15deg) scale(1.8);
  }
  50% {
    opacity: 0.9;
    transform: translate(-50%, -50%) rotate(-12deg) scale(1.9);
  }
}

.beast-carnival-text-small {
  font-family: 'Georgia', 'Times New Roman', serif;
  font-size: 0.7em;
  font-weight: bold;
  color: #d4af37;
  text-align: center;
  letter-spacing: 2px;
  text-shadow: 
    0 0 10px rgba(212, 175, 55, 0.8),
    0 0 20px rgba(212, 175, 55, 0.5),
    1px 1px 3px rgba(0, 0, 0, 0.8);
  z-index: 4;
  position: relative;
  padding: 0 6px;
  line-height: 1.2;
  background: linear-gradient(180deg, 
    rgba(212, 175, 55, 1) 0%, 
    rgba(184, 134, 11, 1) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.8));
}

.voting-card-back-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    radial-gradient(circle at 20% 30%, rgba(212, 175, 55, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 80% 70%, rgba(212, 175, 55, 0.1) 0%, transparent 50%),
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(212, 175, 55, 0.05) 2px,
      rgba(212, 175, 55, 0.05) 4px
    );
  opacity: 0.6;
  z-index: 1;
}

.voting-player-name-back {
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.9em;
  font-weight: 500;
  word-break: break-word;
  margin-top: 8px;
  z-index: 2;
  position: relative;
}

.current-user-label-back {
  color: rgba(100, 150, 200, 0.8);
  font-size: 0.75em;
  z-index: 2;
  position: relative;
}

.voted-badge-back {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 20px;
  height: 20px;
  background: #48bb78;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 0.8em;
  border: 2px solid rgba(255, 255, 255, 0.9);
  z-index: 3;
}

.vote-count-badge-back {
  position: absolute;
  top: 6px;
  left: 6px;
  background: #ff6b35;
  color: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: bold;
  border: 2px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  z-index: 3;
}

.voting-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  margin-bottom: 20px;
  padding: 20px;
  background: rgba(10, 10, 10, 0.6);
  border-radius: 12px;
  border: 1px solid rgba(100, 150, 200, 0.2);
}

.vote-submit-button {
  padding: 15px 40px;
  background: #ff6b35;
  color: #ffffff;
  border: none;
  border-radius: 25px;
  font-size: 1.1em;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(255, 107, 53, 0.4);
  min-width: 150px;
}

.vote-submit-button:hover:not(.button-disabled) {
  background: #e55a2b;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 53, 0.6);
}

.vote-submit-button.button-disabled,
.vote-submit-button:disabled {
  background: rgba(100, 100, 100, 0.5);
  color: rgba(255, 255, 255, 0.5);
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.vote-confirmed-message {
  color: #48bb78;
  font-size: 0.95em;
  font-weight: 500;
  text-align: center;
}

.voting-status {
  display: flex;
  justify-content: center;
  padding: 15px;
  background: rgba(10, 10, 10, 0.4);
  border-radius: 8px;
  border: 1px solid rgba(100, 150, 200, 0.2);
}

.voting-status-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-label {
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.9em;
}

.status-value {
  color: #ffffff;
  font-size: 1em;
  font-weight: bold;
}

/* 阶段弹窗样式 */
.phase-popup {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  pointer-events: none;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(5px);
}

.phase-popup-content {
  padding: 60px 100px;
  border-radius: 30px;
  border: 4px solid;
  box-shadow: 0 0 80px rgba(255, 255, 255, 0.4), inset 0 0 60px rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  position: relative;
  overflow: hidden;
}

.phase-popup-content::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  animation: rotateGradient 8s linear infinite;
}

@keyframes rotateGradient {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* 夜晚开始 - 深蓝紫色渐变 */
.phase-popup.night_start .phase-popup-content {
  border-color: #4a5568;
  background: linear-gradient(135deg, 
    rgba(26, 32, 44, 0.98) 0%, 
    rgba(45, 55, 72, 0.98) 25%,
    rgba(30, 41, 59, 0.98) 50%,
    rgba(51, 65, 85, 0.98) 75%,
    rgba(26, 32, 44, 0.98) 100%);
  box-shadow: 0 0 80px rgba(74, 85, 104, 0.6), 
              0 0 120px rgba(59, 130, 246, 0.3),
              inset 0 0 60px rgba(59, 130, 246, 0.1);
}

/* 夜晚结束 - 深蓝灰色渐变 */
.phase-popup.night_end .phase-popup-content {
  border-color: #2d3748;
  background: linear-gradient(135deg, 
    rgba(26, 32, 44, 0.98) 0%, 
    rgba(45, 55, 72, 0.98) 25%,
    rgba(30, 41, 59, 0.98) 50%,
    rgba(51, 65, 85, 0.98) 75%,
    rgba(26, 32, 44, 0.98) 100%);
  box-shadow: 0 0 80px rgba(45, 55, 72, 0.6), 
              0 0 120px rgba(100, 116, 139, 0.3),
              inset 0 0 60px rgba(100, 116, 139, 0.1);
}

/* 白天开始 - 金黄色渐变 */
.phase-popup.day_start .phase-popup-content {
  border-color: #f6ad55;
  background: linear-gradient(135deg, 
    rgba(237, 137, 54, 0.98) 0%, 
    rgba(251, 191, 36, 0.98) 25%,
    rgba(245, 158, 11, 0.98) 50%,
    rgba(251, 211, 141, 0.98) 75%,
    rgba(237, 137, 54, 0.98) 100%);
  box-shadow: 0 0 80px rgba(246, 173, 85, 0.6), 
              0 0 120px rgba(251, 191, 36, 0.4),
              inset 0 0 60px rgba(255, 255, 255, 0.2);
}

/* 白天结束 - 橙黄色渐变 */
.phase-popup.day_end .phase-popup-content {
  border-color: #ed8936;
  background: linear-gradient(135deg, 
    rgba(237, 137, 54, 0.98) 0%, 
    rgba(251, 191, 36, 0.98) 25%,
    rgba(245, 158, 11, 0.98) 50%,
    rgba(251, 211, 141, 0.98) 75%,
    rgba(237, 137, 54, 0.98) 100%);
  box-shadow: 0 0 80px rgba(237, 137, 54, 0.6), 
              0 0 120px rgba(251, 191, 36, 0.4),
              inset 0 0 60px rgba(255, 255, 255, 0.2);
}

.phase-popup-text {
  font-size: 3.5em;
  font-weight: bold;
  text-align: center;
  letter-spacing: 0.15em;
  position: relative;
  z-index: 1;
  animation: phasePopupPulse 2s ease-in-out infinite, textGlow 3s ease-in-out infinite;
  background: linear-gradient(90deg, transparent, currentColor, transparent);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  animation: phasePopupPulse 2s ease-in-out infinite, textShimmer 3s linear infinite;
}

.phase-popup.night_start .phase-popup-text,
.phase-popup.night_end .phase-popup-text {
  color: #cbd5e0;
  text-shadow: 0 0 30px rgba(203, 213, 224, 0.6),
               0 0 60px rgba(59, 130, 246, 0.4),
               0 0 90px rgba(59, 130, 246, 0.2);
}

.phase-popup.day_start .phase-popup-text,
.phase-popup.day_end .phase-popup-text {
  color: #fff;
  text-shadow: 0 0 30px rgba(255, 255, 255, 0.8),
               0 0 60px rgba(251, 191, 36, 0.6),
               0 0 90px rgba(245, 158, 11, 0.4);
}

@keyframes phasePopupPulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.9;
    transform: scale(1.05);
  }
}

@keyframes textShimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* 弹窗进入和退出动画 */
.phase-popup-enter-active {
  transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.phase-popup-leave-active {
  transition: all 0.5s ease-in;
}

.phase-popup-enter-from {
  opacity: 0;
  transform: scale(0.5) rotate(-10deg);
}

.phase-popup-leave-to {
  opacity: 0;
  transform: scale(1.3) rotate(5deg);
}

/* 夜晚行动弹窗样式 */
.night-action-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  backdrop-filter: blur(5px);
}

.night-action-modal {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border: 2px solid rgba(100, 150, 200, 0.5);
  border-radius: 20px;
  box-shadow: 0 0 50px rgba(100, 150, 200, 0.5), inset 0 0 30px rgba(0, 0, 0, 0.5);
  max-width: 1200px;
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.night-action-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  border-bottom: 2px solid rgba(100, 150, 200, 0.3);
  background: rgba(0, 0, 0, 0.3);
}

.night-action-title {
  color: #ffffff;
  font-size: 1.8em;
  font-weight: bold;
  margin: 0;
  text-shadow: 0 0 10px rgba(100, 150, 200, 0.8);
}

.night-action-close {
  background: none;
  border: none;
  color: #ffffff;
  font-size: 2.5em;
  cursor: pointer;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.3s ease;
  line-height: 1;
}

.night-action-close:hover {
  background: rgba(229, 62, 62, 0.3);
  transform: rotate(90deg);
}

.night-action-modal-content {
  padding: 30px;
  overflow-y: auto;
  flex: 1;
  /* 隐藏滚动条但保持滚动功能 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.night-action-modal-content::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.night-action-description {
  color: rgba(255, 255, 255, 0.9);
  font-size: 1.1em;
  line-height: 1.6;
  margin-bottom: 25px;
  white-space: pre-line;
}

.night-action-players-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 15px;
  margin-bottom: 25px;
}

.night-action-player-card {
  background: rgba(30, 40, 60, 0.6);
  border: 2px solid rgba(100, 150, 200, 0.3);
  border-radius: 12px;
  padding: 15px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.night-action-player-card:hover:not(.disabled) {
  border-color: rgba(100, 150, 200, 0.8);
  background: rgba(30, 40, 60, 0.8);
  transform: translateY(-3px);
  box-shadow: 0 5px 15px rgba(100, 150, 200, 0.4);
}

.night-action-player-card.selected {
  border-color: rgba(72, 187, 120, 0.8);
  background: rgba(72, 187, 120, 0.2);
  box-shadow: 0 0 20px rgba(72, 187, 120, 0.5);
}

.night-action-player-card.disabled {
  opacity: 0.4;
  cursor: not-allowed;
  border-color: rgba(229, 62, 62, 0.3);
}

.night-action-player-avatar {
  margin-bottom: 10px;
  position: relative;
  display: inline-block;
}

.night-action-avatar-icon {
  font-size: 2.5em;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: auto;
}

.night-action-avatar-icon img {
  width: 100%;
  max-width: 60px;
  height: auto;
  object-fit: contain;
}

/* 投票数徽章 */
.vote-count-badge {
  position: absolute;
  top: -8px;
  right: -8px;
  min-width: 24px;
  height: 24px;
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-weight: bold;
  font-size: 0.85em;
  padding: 0 8px;
  border: 2px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 8px rgba(255, 107, 107, 0.5);
  z-index: 10;
}

.night-action-player-name {
  color: #ffffff;
  font-size: 0.9em;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.night-action-disabled-label {
  color: rgba(229, 62, 62, 0.8);
  font-size: 0.75em;
  margin-top: 5px;
}

.night-action-actions {
  display: flex;
  justify-content: center;
  margin-top: 25px;
}

.night-action-submit-btn {
  padding: 15px 40px;
  background: rgba(72, 187, 120, 0.8);
  color: #ffffff;
  border: 2px solid rgba(72, 187, 120, 0.5);
  border-radius: 25px;
  font-size: 1.1em;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 0 15px rgba(72, 187, 120, 0.4);
}

.night-action-submit-btn:hover:not(.disabled) {
  background: rgba(72, 187, 120, 1);
  transform: translateY(-2px);
  box-shadow: 0 0 25px rgba(72, 187, 120, 0.6);
}

.night-action-submit-btn.disabled,
.night-action-submit-btn:disabled {
  background: rgba(100, 100, 100, 0.3);
  border-color: rgba(100, 100, 100, 0.2);
  color: rgba(255, 255, 255, 0.4);
  cursor: not-allowed;
  opacity: 0.6;
}

/* 狼人队友信息 */
.night-action-teammates {
  background: rgba(139, 69, 19, 0.3);
  border: 1px solid rgba(139, 69, 19, 0.5);
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
}

.teammates-label {
  color: rgba(255, 255, 255, 0.9);
  font-size: 1em;
  margin: 0;
}

/* 女巫行动样式 */
.witch-action-options {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

.witch-option-section {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(100, 150, 200, 0.3);
  border-radius: 12px;
  padding: 20px;
}

.witch-option-title {
  color: #ffffff;
  font-size: 1.2em;
  font-weight: bold;
  margin: 0 0 15px 0;
  text-shadow: 0 0 10px rgba(100, 150, 200, 0.5);
}

.witch-option-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.witch-action-btn {
  padding: 12px 24px;
  background: rgba(100, 150, 200, 0.3);
  color: #ffffff;
  border: 2px solid rgba(100, 150, 200, 0.5);
  border-radius: 8px;
  font-size: 1em;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.witch-action-btn:hover:not(.disabled) {
  background: rgba(100, 150, 200, 0.5);
  border-color: rgba(100, 150, 200, 0.8);
  transform: translateY(-2px);
}

.witch-action-btn.selected {
  background: rgba(72, 187, 120, 0.5);
  border-color: rgba(72, 187, 120, 0.8);
  box-shadow: 0 0 15px rgba(72, 187, 120, 0.4);
}

.witch-action-btn.disabled,
.witch-action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: rgba(100, 100, 100, 0.2);
  border-color: rgba(100, 100, 100, 0.2);
}

.witch-target-info {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9em;
  margin-top: 10px;
  padding: 8px;
  background: rgba(229, 62, 62, 0.2);
  border-radius: 6px;
}

.witch-poison-targets {
  margin-top: 15px;
}

/* 弹窗动画 */
.night-action-modal-enter-active {
  transition: all 0.3s ease;
}

.night-action-modal-leave-active {
  transition: all 0.3s ease;
}

.night-action-modal-enter-from {
  opacity: 0;
}

.night-action-modal-enter-from .night-action-modal {
  transform: scale(0.9) translateY(-20px);
}

.night-action-modal-leave-to {
  opacity: 0;
}

.night-action-modal-leave-to .night-action-modal {
  transform: scale(0.9) translateY(20px);
}

/* 狼人行动特殊样式 */
.wolf-action-container {
  display: flex;
  gap: 20px;
  height: 100%;
  min-height: 500px;
}

.wolf-chat-panel {
  flex: 0 0 350px;
  display: flex;
  flex-direction: column;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  border: 1px solid rgba(200, 100, 100, 0.3);
  overflow: hidden;
}

.wolf-chat-header {
  padding: 15px 20px;
  background: rgba(200, 100, 100, 0.2);
  border-bottom: 1px solid rgba(200, 100, 100, 0.3);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.wolf-chat-header h4 {
  color: #ff6b6b;
  margin: 0;
  font-size: 1.2em;
  text-shadow: 0 0 10px rgba(255, 107, 107, 0.5);
}

.wolf-chat-subtitle {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.85em;
}

.wolf-chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  /* 隐藏滚动条但保持滚动功能 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.wolf-chat-messages::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.wolf-chat-message {
  background: rgba(30, 30, 40, 0.6);
  border-radius: 8px;
  padding: 10px 12px;
  border-left: 3px solid rgba(200, 100, 100, 0.5);
}

.wolf-chat-message.is-own {
  background: rgba(200, 100, 100, 0.2);
  border-left-color: rgba(255, 107, 107, 0.8);
}

.wolf-chat-username {
  color: #ff6b6b;
  font-size: 0.9em;
  font-weight: 600;
  margin-bottom: 4px;
}

.wolf-chat-content {
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.95em;
  line-height: 1.4;
  word-wrap: break-word;
}

.wolf-chat-time {
  color: rgba(255, 255, 255, 0.4);
  font-size: 0.75em;
  margin-top: 4px;
}

.wolf-chat-empty {
  color: rgba(255, 255, 255, 0.5);
  text-align: center;
  padding: 40px 20px;
  font-style: italic;
}

.wolf-chat-input-container {
  display: flex;
  gap: 10px;
  padding: 15px;
  border-top: 1px solid rgba(200, 100, 100, 0.3);
  background: rgba(0, 0, 0, 0.2);
}

.wolf-chat-input {
  flex: 1;
  background: rgba(30, 30, 40, 0.8);
  border: 1px solid rgba(200, 100, 100, 0.3);
  border-radius: 6px;
  padding: 10px 12px;
  color: #ffffff;
  font-size: 0.95em;
}

.wolf-chat-input:focus {
  outline: none;
  border-color: rgba(255, 107, 107, 0.6);
  box-shadow: 0 0 8px rgba(255, 107, 107, 0.3);
}

.wolf-chat-send-btn {
  background: rgba(255, 107, 107, 0.6);
  border: 1px solid rgba(255, 107, 107, 0.8);
  border-radius: 6px;
  padding: 10px 20px;
  color: #ffffff;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.wolf-chat-send-btn:hover:not(:disabled) {
  background: rgba(255, 107, 107, 0.8);
  box-shadow: 0 0 12px rgba(255, 107, 107, 0.4);
}

.wolf-chat-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.wolf-selection-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 狼人投票状态样式 */
.wolf-vote-status {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
  border: 1px solid rgba(200, 100, 100, 0.3);
}

.vote-status-title {
  color: #ff6b6b;
  font-size: 1.1em;
  margin: 0 0 12px 0;
  text-shadow: 0 0 8px rgba(255, 107, 107, 0.5);
}

.wolf-vote-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.wolf-vote-item {
  background: rgba(30, 30, 40, 0.6);
  border-radius: 6px;
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-left: 3px solid rgba(200, 100, 100, 0.5);
  transition: all 0.3s ease;
}

.wolf-vote-item.is-current-user {
  background: rgba(200, 100, 100, 0.15);
  border-left-color: rgba(255, 107, 107, 0.8);
}

.wolf-vote-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.wolf-name {
  color: rgba(255, 255, 255, 0.9);
  font-weight: 500;
}

.current-user-badge {
  color: #ff6b6b;
  font-size: 0.85em;
  font-weight: 600;
}

.ai-badge {
  background: rgba(100, 150, 200, 0.3);
  color: rgba(255, 255, 255, 0.8);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.75em;
  font-weight: 600;
}

.wolf-vote-status {
  display: flex;
  align-items: center;
}

.vote-status {
  font-size: 0.9em;
  padding: 4px 8px;
  border-radius: 4px;
}

.vote-status.voted {
  color: #48bb78;
  background: rgba(72, 187, 120, 0.2);
  border: 1px solid rgba(72, 187, 120, 0.4);
}

.vote-status.not-voted {
  color: rgba(255, 255, 255, 0.5);
  background: rgba(100, 100, 100, 0.2);
  border: 1px solid rgba(100, 100, 100, 0.3);
}

/* 角色信息弹窗样式 */
.role-info-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10001;
  backdrop-filter: blur(5px);
}

.role-info-modal {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border: 2px solid rgba(100, 150, 200, 0.5);
  border-radius: 20px;
  box-shadow: 0 0 50px rgba(100, 150, 200, 0.5), inset 0 0 30px rgba(0, 0, 0, 0.5);
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.role-info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  border-bottom: 2px solid rgba(100, 150, 200, 0.3);
  background: rgba(0, 0, 0, 0.3);
}

.role-info-title {
  color: #ffffff;
  font-size: 1.5em;
  font-weight: bold;
  margin: 0;
  text-shadow: 0 0 10px rgba(100, 150, 200, 0.8);
}

.role-info-close {
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
  line-height: 1;
}

.role-info-close:hover {
  background: rgba(229, 62, 62, 0.3);
  transform: rotate(90deg);
}

.role-info-content {
  padding: 30px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.role-info-icon {
  font-size: 4em;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: auto;
}

.role-info-icon img {
  width: 100%;
  max-width: 120px;
  height: auto;
  object-fit: contain;
}

.role-info-name {
  color: #ffffff;
  font-size: 1.8em;
  font-weight: bold;
  margin-bottom: 10px;
  text-shadow: 0 0 10px rgba(100, 150, 200, 0.5);
}

.role-info-description {
  color: rgba(255, 255, 255, 0.9);
  font-size: 1em;
  line-height: 1.6;
  padding: 0 10px;
}

/* 角色信息弹窗动画 */
.role-info-modal-enter-active {
  transition: all 0.3s ease;
}

.role-info-modal-leave-active {
  transition: all 0.3s ease;
}

.role-info-modal-enter-from {
  opacity: 0;
}

.role-info-modal-enter-from .role-info-modal {
  transform: scale(0.9) translateY(-20px);
}

.role-info-modal-leave-to {
  opacity: 0;
}

.role-info-modal-leave-to .role-info-modal {
  transform: scale(0.9) translateY(20px);
}

/* 游戏结束结算弹窗样式 */
.game-over-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10002;
  backdrop-filter: blur(10px);
}

.game-over-modal {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border: 3px solid rgba(100, 150, 200, 0.6);
  border-radius: 25px;
  box-shadow: 0 0 80px rgba(100, 150, 200, 0.6), inset 0 0 40px rgba(0, 0, 0, 0.6);
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.game-over-header {
  padding: 30px;
  border-bottom: 2px solid rgba(100, 150, 200, 0.3);
  background: rgba(0, 0, 0, 0.3);
  text-align: center;
}

.game-over-title {
  color: #ffffff;
  font-size: 2em;
  font-weight: bold;
  margin: 0;
  text-shadow: 0 0 15px rgba(100, 150, 200, 0.8);
}

.game-over-content {
  padding: 40px 30px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 30px;
}

.game-over-winner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 30px;
  border-radius: 15px;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid;
  min-width: 300px;
}

.game-over-winner.wolves {
  border-color: rgba(255, 107, 53, 0.6);
  box-shadow: 0 0 30px rgba(255, 107, 53, 0.4);
}

.game-over-winner.villagers {
  border-color: rgba(72, 187, 120, 0.6);
  box-shadow: 0 0 30px rgba(72, 187, 120, 0.4);
}

.winner-icon {
  font-size: 5em;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.winner-text {
  color: #ffffff;
  font-size: 2.2em;
  font-weight: bold;
  text-shadow: 0 0 15px rgba(100, 150, 200, 0.8);
}

.game-over-winner.wolves .winner-text {
  color: #ff6b35;
  text-shadow: 0 0 15px rgba(255, 107, 53, 0.8);
}

.game-over-winner.villagers .winner-text {
  color: #48bb78;
  text-shadow: 0 0 15px rgba(72, 187, 120, 0.8);
}

.game-over-message {
  color: rgba(255, 255, 255, 0.9);
  font-size: 1.1em;
  line-height: 1.6;
  padding: 20px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
  border: 1px solid rgba(100, 150, 200, 0.2);
}

.game-over-actions {
  padding: 20px 30px;
  border-top: 2px solid rgba(100, 150, 200, 0.3);
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  justify-content: center;
}

.game-over-close-btn {
  padding: 12px 40px;
  background: #ff6b35;
  color: #ffffff;
  border: none;
  border-radius: 25px;
  font-size: 1.1em;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(255, 107, 53, 0.4);
}

.game-over-close-btn:hover {
  background: #e55a2b;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 53, 0.6);
}

/* 游戏结束弹窗动画 */
.game-over-modal-enter-active {
  transition: all 0.4s ease;
}

.game-over-modal-leave-active {
  transition: all 0.4s ease;
}

.game-over-modal-enter-from {
  opacity: 0;
}

.game-over-modal-enter-from .game-over-modal {
  transform: scale(0.8) translateY(-30px);
}

.game-over-modal-leave-to {
  opacity: 0;
}

.game-over-modal-leave-to .game-over-modal {
  transform: scale(0.8) translateY(30px);
}

/* 退出确认弹窗样式 */
.exit-confirm-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10003;
  backdrop-filter: blur(10px);
}

.exit-confirm-modal {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border: 3px solid rgba(255, 107, 53, 0.6);
  border-radius: 25px;
  box-shadow: 0 0 80px rgba(255, 107, 53, 0.6), inset 0 0 40px rgba(0, 0, 0, 0.6);
  max-width: 500px;
  width: 90%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.exit-confirm-header {
  padding: 30px;
  border-bottom: 2px solid rgba(255, 107, 53, 0.3);
  background: rgba(0, 0, 0, 0.3);
  text-align: center;
}

.exit-confirm-title {
  color: #ffffff;
  font-size: 1.8em;
  font-weight: bold;
  margin: 0;
  text-shadow: 0 0 15px rgba(255, 107, 53, 0.8);
}

.exit-confirm-content {
  padding: 40px 30px;
  text-align: center;
}

.exit-confirm-message {
  color: rgba(255, 255, 255, 0.9);
  font-size: 1.2em;
  line-height: 1.6;
  padding: 20px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
  border: 1px solid rgba(255, 107, 53, 0.2);
}

.exit-confirm-actions {
  padding: 20px 30px;
  border-top: 2px solid rgba(255, 107, 53, 0.3);
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  justify-content: center;
  gap: 20px;
}

.exit-confirm-cancel-btn {
  padding: 12px 40px;
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 25px;
  font-size: 1em;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.exit-confirm-cancel-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(255, 255, 255, 0.2);
}

.exit-confirm-confirm-btn {
  padding: 12px 40px;
  background: #ff6b35;
  color: #ffffff;
  border: none;
  border-radius: 25px;
  font-size: 1em;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(255, 107, 53, 0.4);
}

.exit-confirm-confirm-btn:hover {
  background: #ff8555;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 53, 0.6);
}

.exit-confirm-confirm-btn:active {
  transform: translateY(0);
}

/* 退出确认弹窗动画 */
.exit-confirm-modal-enter-active {
  transition: all 0.4s ease;
}

.exit-confirm-modal-leave-active {
  transition: all 0.4s ease;
}

.exit-confirm-modal-enter-from {
  opacity: 0;
}

.exit-confirm-modal-enter-from .exit-confirm-modal {
  transform: scale(0.8) translateY(-30px);
}

.exit-confirm-modal-leave-to {
  opacity: 0;
}

.exit-confirm-modal-leave-to .exit-confirm-modal {
  transform: scale(0.8) translateY(30px);
}

/* 错误提示弹窗样式 */
.error-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10004;
  backdrop-filter: blur(10px);
}

.error-modal {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border: 3px solid rgba(255, 107, 53, 0.7);
  border-radius: 25px;
  box-shadow: 0 0 80px rgba(255, 107, 53, 0.5), inset 0 0 40px rgba(0, 0, 0, 0.6);
  max-width: 500px;
  width: 90%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: errorModalShake 0.5s ease;
}

@keyframes errorModalShake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
  20%, 40%, 60%, 80% { transform: translateX(5px); }
}

.error-modal-header {
  padding: 25px 30px;
  border-bottom: 2px solid rgba(255, 107, 53, 0.3);
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  position: relative;
  text-align: center;
}

.error-icon {
  font-size: 2em;
  animation: errorIconPulse 2s ease-in-out infinite;
}

@keyframes errorIconPulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.error-modal-title {
  color: #ffffff;
  font-size: 1.8em;
  font-weight: bold;
  margin: 0;
  text-shadow: 0 0 15px rgba(255, 107, 53, 0.8);
}

.error-modal-close {
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
  line-height: 1;
  position: absolute;
  top: 20px;
  right: 20px;
}

.error-modal-close:hover {
  background: rgba(255, 107, 53, 0.3);
  transform: rotate(90deg);
}

.error-modal-content {
  padding: 40px 30px;
  text-align: center;
}

.error-modal-message {
  color: rgba(255, 255, 255, 0.95);
  font-size: 1.2em;
  line-height: 1.6;
  padding: 20px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
  border: 1px solid rgba(255, 107, 53, 0.2);
  word-wrap: break-word;
}

.error-modal-actions {
  padding: 20px 30px;
  border-top: 2px solid rgba(255, 107, 53, 0.3);
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  justify-content: center;
}

.error-modal-confirm-btn {
  padding: 12px 50px;
  background: #ff6b35;
  color: #ffffff;
  border: none;
  border-radius: 25px;
  font-size: 1.1em;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(255, 107, 53, 0.4);
  min-width: 120px;
}

.error-modal-confirm-btn:hover {
  background: #ff8555;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 53, 0.6);
}

.error-modal-confirm-btn:active {
  transform: translateY(0);
}

/* 错误弹窗动画 */
.error-modal-enter-active {
  transition: all 0.3s ease;
}

.error-modal-leave-active {
  transition: all 0.3s ease;
}

.error-modal-enter-from {
  opacity: 0;
}

.error-modal-enter-from .error-modal {
  transform: scale(0.8) translateY(-30px);
}

.error-modal-leave-to {
  opacity: 0;
}

.error-modal-leave-to .error-modal {
  transform: scale(0.8) translateY(30px);
}
</style>

