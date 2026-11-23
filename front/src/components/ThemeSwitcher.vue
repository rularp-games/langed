<script setup>
import { computed } from 'vue'
import { Monitor, Moon, Sun } from '@lucide/vue'
import { useUiStore } from '@/stores/ui'
import AppButton from './ui/AppButton.vue'
import AppMenu from './ui/AppMenu.vue'
import AppMenuItem from './ui/AppMenuItem.vue'

const ui = useUiStore()
const options = [
  { value: 'system', label: 'Как в системе', icon: Monitor },
  { value: 'light', label: 'Светлая', icon: Sun },
  { value: 'dark', label: 'Тёмная', icon: Moon },
]
const current = computed(() => options.find((option) => option.value === ui.theme) || options[0])
</script>

<template>
  <AppMenu label="Тема оформления">
    <template #trigger="{ attrs, toggle }">
      <AppButton
        v-bind="attrs"
        variant="ghost"
        icon-only
        :aria-label="`Тема оформления: ${current.label.toLowerCase()}`"
        @click="toggle"
      >
        <component :is="current.icon" :size="18" aria-hidden="true" />
      </AppButton>
    </template>
    <AppMenuItem
      v-for="option in options"
      :key="option.value"
      :checked="option.value === ui.theme"
      @select="ui.setTheme(option.value)"
    >
      <component :is="option.icon" :size="16" aria-hidden="true" />
      {{ option.label }}
    </AppMenuItem>
  </AppMenu>
</template>
