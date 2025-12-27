import { createRouter, createWebHistory } from 'vue-router'
import Games from '../components/Games.vue'
import Afisha from '../components/Afisha.vue'
import Conventions from '../components/Conventions.vue'

const routes = [
  {
    path: '/',
    name: 'Afisha',
    component: Afisha
  },
  {
    path: '/games',
    name: 'Games',
    component: Games
  },
  {
    path: '/conventions',
    name: 'Conventions',
    component: Conventions
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
