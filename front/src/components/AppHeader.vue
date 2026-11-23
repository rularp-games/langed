<script setup>
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAuthDialog } from '@/composables/useAuthDialog'
import AppButton from './ui/AppButton.vue'
import ThemeSwitcher from './ThemeSwitcher.vue'
import UserMenu from './UserMenu.vue'

const auth = useAuthStore()
const route = useRoute()
const { open: openAuth } = useAuthDialog()

// section совпадает с meta.section маршрута — так подсвечиваются и вложенные страницы.
const links = [
  { to: '/', label: 'Афиша', section: 'afisha' },
  { to: '/games', label: 'Игры', section: 'games' },
  { to: '/conventions', label: 'Конвенты', section: 'conventions' },
  { to: '/venues', label: 'Площадки', section: 'venues' },
]
</script>

<template>
  <header class="header">
    <div class="container header__inner">
      <RouterLink to="/" class="header__logo" aria-label="Langed — на главную">
        <svg viewBox="0 0 32 32" width="26" height="26" aria-hidden="true">
          <rect width="32" height="32" rx="7" fill="var(--accent)" />
          <path d="M11 8v16h11" fill="none" stroke="var(--on-accent)" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <span>Langed</span>
      </RouterLink>

      <nav class="header__nav" aria-label="Основная навигация">
        <RouterLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="header__link"
          :class="{ 'is-active': route.meta.section === link.section }"
          :aria-current="route.meta.section === link.section ? 'page' : undefined"
        >
          {{ link.label }}
        </RouterLink>
      </nav>

      <div class="header__actions">
        <ThemeSwitcher />
        <template v-if="auth.ready">
          <UserMenu v-if="auth.isAuthenticated" />
          <AppButton v-else variant="primary" size="sm" @click="openAuth()">Войти</AppButton>
        </template>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header {
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.header__inner {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  min-height: var(--header-height);
}
.header__logo {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--text);
  font-size: var(--text-md);
  font-weight: 700;
  letter-spacing: -0.02em;
  text-decoration: none;
}
.header__nav {
  display: flex;
  align-self: stretch;
  gap: var(--space-1);
  flex: 1;
  min-width: 0;
}
.header__link {
  position: relative;
  display: inline-flex;
  align-items: center;
  padding: 0 var(--space-3);
  color: var(--text-muted);
  font-weight: 550;
  text-decoration: none;
  white-space: nowrap;
}
.header__link:hover {
  color: var(--text);
}
.header__link.is-active {
  color: var(--text);
}
.header__link.is-active::after {
  content: '';
  position: absolute;
  inset: auto var(--space-3) -1px;
  height: 2px;
  background: var(--accent);
}
.header__link:focus-visible {
  outline-offset: -4px;
}
.header__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-left: auto;
  /* Резерв под кнопку входа, пока неизвестно состояние пользователя. */
  min-width: 7rem;
  justify-content: flex-end;
}

/* Телефон: логотип и действия — первой строкой, навигация — второй, во всю ширину. */
@media (max-width: 639px) {
  .header {
    position: static;
  }
  .header__inner {
    flex-wrap: wrap;
    gap: 0 var(--space-3);
  }
  .header__logo {
    min-height: 48px;
  }
  .header__nav {
    order: 3;
    flex: 0 0 100%;
    justify-content: space-between;
    gap: 0;
    margin-inline: calc(-1 * var(--space-2));
    width: auto;
    flex-basis: calc(100% + 2 * var(--space-2));
  }
  .header__link {
    min-height: 40px;
    padding: 0 var(--space-2);
    font-size: var(--text-sm);
  }
  .header__link.is-active::after {
    inset-inline: var(--space-2);
  }
}
</style>
