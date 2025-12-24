import { createRouter, createWebHistory } from 'vue-router'
import HelloWorld from '../components/HelloWorld.vue'
import Cyberwordly from '../components/Cyberwordly.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

