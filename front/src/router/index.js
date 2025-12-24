import { createRouter, createWebHistory } from 'vue-router'
import HelloWorld from '../components/HelloWorld.vue'
import Games from '../components/Games.vue'
import Afisha from '../components/Afisha.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: HelloWorld,
    props: { msg: 'Welcome to Your Vue.js App' }
  },
  {
    path: '/games',
    name: 'Games',
    component: Games
  },
  {
    path: '/afisha',
    name: 'Afisha',
    component: Afisha
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

