import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 世界观
export const getWorldView = () => api.get('/worldview')

// 角色
export const getCharacters = () => api.get('/characters')
export const getUserCharacters = (userId) => api.get(`/user/${userId}/characters`)
export const unlockCharacter = (userId, characterId) => 
  api.post(`/user/${userId}/characters/${characterId}/unlock`)

// 事件
export const getUserEvents = (userId) => api.get(`/user/${userId}/events`)
export const submitAnswer = (eventId, userId, answer1, answer2) => 
  api.post(`/event/${eventId}/submit-answer`, null, { 
    params: { user_id: userId, answer1, answer2 } 
  })

// 狼人杀
export const createWerewolfRoom = () => api.post('/werewolf/room')
export const joinWerewolfRoom = (roomId, userId, username) => 
  api.post(`/werewolf/room/${roomId}/join`, null, { params: { user_id: userId, username } })
export const startWerewolfGame = (roomId) => api.post(`/werewolf/room/${roomId}/start`, null, { timeout: 30000 }) // 30秒超时，因为现在使用后台任务，应该很快返回
export const getWerewolfRoom = (roomId) => api.get(`/werewolf/room/${roomId}`)
export const addAIPlayer = (roomId) => api.post(`/werewolf/room/${roomId}/add-ai`)
export const autoFillAIPlayers = (roomId, targetCount = 7) => 
  api.post(`/werewolf/room/${roomId}/auto-fill-ai`, null, { params: { target_count: targetCount } })

// 真心话大冒险
export const generateTruthOrDare = (gameResult, playerCount = 2) => 
  api.post('/truth-or-dare/generate', null, { params: { game_result: gameResult, player_count: playerCount } })

export default api










