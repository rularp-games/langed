import { createRouter, createWebHistory } from 'vue-router'
import HelloWorld from '../components/HelloWorld.vue'
import Cyberwordly from '../components/Cyberwordly.vue'
import Games from '../components/Games.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: HelloWorld,
    props: { msg: 'Welcome to Your Vue.js App' }
  },
  {
    path: '/cyberwordly',
    name: 'Cyberwordly',
    component: Cyberwordly
  },
  {
    path: '/games',
    name: 'Games',
    component: Games
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

