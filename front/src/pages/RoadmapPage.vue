<script setup>
import AppBadge from '@/components/ui/AppBadge.vue'

/** Статус → подпись и тон бейджа. */
const STATUSES = {
  done: { label: 'Сделано', tone: 'success' },
  progress: { label: 'В работе', tone: 'warning' },
  planned: { label: 'В планах', tone: 'neutral' },
}

const SECTIONS = [
  {
    status: 'done',
    items: [
      { title: 'Базовые возможности', text: 'Каталог игр, конвенты, площадки и афиша прогонов.' },
      { title: 'Новый интерфейс', text: 'Светлая и тёмная темы, спокойное оформление без модальных окон на каждый шаг.' },
      { title: 'Вход без перехода на отдельный сайт', text: 'Вход, регистрация и восстановление пароля — прямо на странице, по почте или через соцсети.' },
      { title: 'Мобильная версия', text: 'Все страницы, включая расписание конвента, работают на телефоне.' },
      { title: 'Отдельные страницы', text: 'У каждой игры, прогона, конвента и площадки — своя страница и постоянная ссылка.' },
      { title: 'Постраничные списки', text: 'Каталоги и афиша загружаются частями, с поиском и фильтрами в адресной строке.' },
    ],
  },
  {
    status: 'progress',
    items: [{ title: 'Расписание мероприятий', text: 'Редактор расписания конвента с перетаскиванием прогонов.' }],
  },
  {
    status: 'planned',
    items: [
      { title: 'Поселение', text: 'Управление размещением участников на конвентах.' },
      {
        title: 'Оповещения',
        text: 'Уведомления о предстоящих играх и изменениях.',
        points: ['Оповещение в канал Telegram', 'Оповещение в личные сообщения Telegram', 'Оповещение в личные сообщения VK'],
      },
      { title: 'Отметка о сдаче взноса на конвент', text: 'Учёт оплаты участия в мероприятиях.' },
    ],
  },
]
</script>

<template>
  <div class="container container--narrow roadmap">
    <header class="roadmap__header">
      <h1>Планы развития</h1>
      <p class="text-muted">Что уже работает в Langed, над чем идёт работа и что появится позже.</p>
    </header>

    <section v-for="section in SECTIONS" :key="section.status" :aria-labelledby="`roadmap-${section.status}`">
      <h2 :id="`roadmap-${section.status}`" class="roadmap__status">
        <AppBadge :tone="STATUSES[section.status].tone">{{ STATUSES[section.status].label }}</AppBadge>
      </h2>
      <ul class="roadmap__list">
        <li v-for="item in section.items" :key="item.title" class="roadmap__item">
          <h3>{{ item.title }}</h3>
          <p>{{ item.text }}</p>
          <ul v-if="item.points" class="roadmap__points">
            <li v-for="point in item.points" :key="point">{{ point }}</li>
          </ul>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.roadmap {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding-bottom: var(--space-10);
}
.roadmap__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding-top: var(--space-5);
}
.roadmap__status {
  display: flex;
  margin-bottom: var(--space-2);
  font-size: var(--text-base);
}
.roadmap__list {
  border-top: 1px solid var(--border);
}
.roadmap__item {
  padding-block: var(--space-3);
  border-bottom: 1px solid var(--border);
}
.roadmap__item h3 {
  font-size: var(--text-base);
}
.roadmap__item p {
  color: var(--text-muted);
}
.roadmap__points {
  margin-top: var(--space-1);
  padding-left: var(--space-5);
  color: var(--text-muted);
  list-style: disc;
}
</style>
