import { createRouter, createWebHistory } from 'vue-router'
import Games from '../components/Games.vue'
import Afisha from '../components/Afisha.vue'
import Conventions from '../components/Conventions.vue'
import ConventionSchedule from '../components/ConventionSchedule.vue'
import ScheduleEditor from '../components/ScheduleEditor.vue'

const routes = [
  {
    path: '/',
    name: 'Afisha',
    component: Afisha,
    // Поддержка query параметров: ?run=ID или ?event=ID
    props: route => ({ runId: route.query.run, eventId: route.query.event })
  },
  {
    path: '/games',
    name: 'Games',
    component: Games,
    // Поддержка query параметра: ?id=ID
    props: route => ({ gameId: route.query.id })
  },
  {
    path: '/conventions',
    name: 'Conventions',
    component: Conventions,
    // Поддержка query параметров: ?id=ID или ?event=ID или ?view=schedule
    props: route => ({ 
      conventionId: route.query.id, 
      eventId: route.query.event,
      viewMode: route.query.view
    })
  },
  {
    path: '/schedule/:eventId',
    name: 'ConventionSchedule',
    component: ConventionSchedule,
    props: true
  },
  {
    path: '/schedule/:eventId/edit',
    name: 'ScheduleEditor',
    component: ScheduleEditor,
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // Прокрутка вверх при навигации
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    return { top: 0 }
  }
})

export default router
