import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { formatTitle } from '@/composables/usePageTitle'

const page = (name) => () => import(`../pages/${name}.vue`)
const ID = ':id(\\d+)'

/**
 * Все маршруты приложения. Страницы подключены лениво; файлы в src/pages/ можно перезаписывать,
 * не трогая этот файл.
 *
 * meta:
 *   title        — заголовок вкладки («Игры — Langed»); динамический — через usePageTitle()
 *   section      — пункт шапки, который подсвечивается (afisha | games | conventions | venues)
 *   requiresAuth — страница только для вошедших: гостю сначала показывается диалог входа
 * Параметр id передаётся в страницу как prop (строка).
 */
const routes = [
  // Афиша и прогоны
  { path: '/', name: 'afisha', component: page('AfishaPage'), meta: { title: 'Афиша', section: 'afisha' } },
  { path: '/runs/new', name: 'run-new', component: page('RunEditPage'), meta: { title: 'Новый прогон', section: 'afisha', requiresAuth: true } },
  { path: `/runs/${ID}`, name: 'run', component: page('RunDetailPage'), props: true, meta: { title: 'Прогон', section: 'afisha' } },
  { path: `/runs/${ID}/edit`, name: 'run-edit', component: page('RunEditPage'), props: true, meta: { title: 'Редактирование прогона', section: 'afisha', requiresAuth: true } },

  // Игры
  { path: '/games', name: 'games', component: page('GamesPage'), meta: { title: 'Игры', section: 'games' } },
  { path: '/games/new', name: 'game-new', component: page('GameEditPage'), meta: { title: 'Новая игра', section: 'games', requiresAuth: true } },
  { path: `/games/${ID}`, name: 'game', component: page('GameDetailPage'), props: true, meta: { title: 'Игра', section: 'games' } },
  { path: `/games/${ID}/edit`, name: 'game-edit', component: page('GameEditPage'), props: true, meta: { title: 'Редактирование игры', section: 'games', requiresAuth: true } },

  // Конвенты и их проведения
  { path: '/conventions', name: 'conventions', component: page('ConventionsPage'), meta: { title: 'Конвенты', section: 'conventions' } },
  { path: '/conventions/new', name: 'convention-new', component: page('ConventionEditPage'), meta: { title: 'Новый конвент', section: 'conventions', requiresAuth: true } },
  { path: `/conventions/${ID}`, name: 'convention', component: page('ConventionDetailPage'), props: true, meta: { title: 'Конвент', section: 'conventions' } },
  { path: `/conventions/${ID}/edit`, name: 'convention-edit', component: page('ConventionEditPage'), props: true, meta: { title: 'Редактирование конвента', section: 'conventions', requiresAuth: true } },
  { path: `/events/${ID}`, name: 'event', component: page('EventPage'), props: true, meta: { title: 'Проведение конвента', section: 'conventions' } },
  { path: `/events/${ID}/edit`, name: 'event-edit', component: page('EventEditPage'), props: true, meta: { title: 'Редактирование расписания', section: 'conventions', requiresAuth: true } },

  // Площадки
  { path: '/venues', name: 'venues', component: page('VenuesPage'), meta: { title: 'Площадки', section: 'venues' } },
  { path: '/venues/new', name: 'venue-new', component: page('VenueEditPage'), meta: { title: 'Новая площадка', section: 'venues', requiresAuth: true } },
  { path: `/venues/${ID}`, name: 'venue', component: page('VenueDetailPage'), props: true, meta: { title: 'Площадка', section: 'venues' } },
  { path: `/venues/${ID}/edit`, name: 'venue-edit', component: page('VenueEditPage'), props: true, meta: { title: 'Редактирование площадки', section: 'venues', requiresAuth: true } },

  // Справочник городов (правка — только staff)
  { path: '/cities', name: 'cities', component: page('CitiesPage'), meta: { title: 'Города', section: 'venues', requiresAuth: true } },

  { path: '/profile', name: 'profile', component: page('ProfilePage'), meta: { title: 'Профиль', requiresAuth: true } },
  { path: '/roadmap', name: 'roadmap', component: page('RoadmapPage'), meta: { title: 'Планы развития' } },

  // Старые адреса расписания
  { path: `/schedule/${ID}`, redirect: (to) => ({ name: 'event', params: { id: to.params.id } }) },
  { path: `/schedule/${ID}/edit`, redirect: (to) => ({ name: 'event-edit', params: { id: to.params.id } }) },

  { path: '/:pathMatch(.*)*', name: 'not-found', component: page('NotFoundPage'), meta: { title: 'Страница не найдена' } },
]

/**
 * Старые ссылки с идентификатором в query (сущности открывались в модальных окнах):
 * имя маршрута → [параметр query, имя нового маршрута].
 */
const LEGACY_QUERY_LINKS = {
  afisha: [
    ['run', 'run'],
    ['event', 'event'],
  ],
  games: [['id', 'game']],
  conventions: [
    ['id', 'convention'],
    ['event', 'event'],
  ],
  venues: [['id', 'venue']],
}

function legacyRedirect(to) {
  for (const [param, name] of LEGACY_QUERY_LINKS[to.name] ?? []) {
    const id = [to.query[param]].flat()[0]
    if (id && /^\d+$/.test(id)) {
      const query = { ...to.query }
      delete query[param]
      delete query.view
      return { name, params: { id }, query, replace: true }
    }
  }
  return null
}

const router = createRouter({
  // Приложение всегда открывается от корня сайта (base сборки влияет только на адреса файлов).
  history: createWebHistory('/'),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash }
    // Ввод в поиске меняет только query — страницу не дёргаем; смена страницы списка — наверх.
    if (to.path === from.path && to.query.page === from.query.page) return false
    return { top: 0 }
  },
})

router.beforeEach(async (to, from) => {
  const redirect = legacyRedirect(to)
  if (redirect) return redirect

  if (to.meta.requiresAuth) {
    const auth = useAuthStore()
    await auth.init()
    if (!auth.isAuthenticated) {
      const ok = await auth.openDialog({ reason: 'Войдите, чтобы открыть эту страницу.' })
      // Отказ от входа: остаёмся где были, а при прямом заходе по ссылке — на афишу.
      if (!ok) return from.matched.length ? false : { name: 'afisha' }
    }
  }
  return true
})

router.afterEach((to) => {
  document.title = formatTitle(to.meta.title)
})

export default router
