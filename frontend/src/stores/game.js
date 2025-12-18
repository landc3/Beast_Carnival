import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useGameStore = defineStore('game', () => {
  const userId = ref(localStorage.getItem('userId') || `user_${Date.now()}`)
  const username = ref(localStorage.getItem('username') || '玩家')
  const unlockedCharacters = ref(JSON.parse(localStorage.getItem('unlockedCharacters') || '["cat"]'))
  
  function setUserId(id) {
    userId.value = id
    localStorage.setItem('userId', id)
  }
  
  function setUsername(name) {
    username.value = name
    localStorage.setItem('username', name)
  }
  
  function addUnlockedCharacter(characterId) {
    if (!unlockedCharacters.value.includes(characterId)) {
      unlockedCharacters.value.push(characterId)
      localStorage.setItem('unlockedCharacters', JSON.stringify(unlockedCharacters.value))
    }
  }
  
  return {
    userId,
    username,
    unlockedCharacters,
    setUserId,
    setUsername,
    addUnlockedCharacter
  }
})





















