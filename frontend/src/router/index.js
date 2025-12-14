import { createRouter, createWebHistory } from 'vue-router'
import WorldView from '../views/WorldView.vue'
import Characters from '../views/Characters.vue'
import CharacterChat from '../views/CharacterChat.vue'
import Events from '../views/Events.vue'
import EventDetail from '../views/EventDetail.vue'
import GameMode from '../views/GameMode.vue'
import Werewolf from '../views/Werewolf.vue'

const routes = [
  {
    path: '/',
    name: 'WorldView',
    component: WorldView
  },
  {
    path: '/characters',
    name: 'Characters',
    component: Characters
  },
  {
    path: '/character/:id/chat',
    name: 'CharacterChat',
    component: CharacterChat
  },
  {
    path: '/events',
    name: 'Events',
    component: Events
  },
  {
    path: '/event/:id',
    name: 'EventDetail',
    component: EventDetail
  },
  {
    path: '/game-mode',
    name: 'GameMode',
    component: GameMode
  },
  {
    path: '/werewolf',
    name: 'Werewolf',
    component: Werewolf
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

