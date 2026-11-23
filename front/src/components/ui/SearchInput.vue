<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { Search, X } from '@lucide/vue'

/**
 * Поле поиска: v-model обновляется с задержкой (debounce), сразу — по Enter и при очистке.
 *   <SearchInput v-model="search" label="Поиск по играм" placeholder="Название игры" />
 */
const props = defineProps({
  /** Подпись для экранных дикторов (видимой подписи у поля нет). */
  label: { type: String, required: true },
  placeholder: { type: String, default: 'Поиск' },
  debounce: { type: Number, default: 300 },
})
const model = defineModel({ type: String, default: '' })

const text = ref(model.value)
const input = ref(null)
let timer = null

// Внешнее изменение (кнопка «назад», сброс фильтров) — подхватываем.
watch(model, (value) => {
  if (value !== text.value.trim()) text.value = value
})

function commit() {
  clearTimeout(timer)
  const value = text.value.trim()
  if (value !== model.value) model.value = value
}

function onInput() {
  clearTimeout(timer)
  timer = setTimeout(commit, props.debounce)
}

function clear() {
  text.value = ''
  commit()
  input.value?.focus()
}

onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <form class="search" role="search" @submit.prevent="commit">
    <Search class="search__icon" :size="16" aria-hidden="true" />
    <input
      ref="input"
      v-model="text"
      type="search"
      class="control search__input"
      :placeholder="placeholder"
      :aria-label="label"
      autocomplete="off"
      enterkeyhint="search"
      @input="onInput"
    />
    <button v-if="text" type="button" class="search__clear" aria-label="Очистить поиск" @click="clear">
      <X :size="16" aria-hidden="true" />
    </button>
  </form>
</template>

<style scoped>
.search {
  position: relative;
  flex: 1 1 280px;
  max-width: 420px;
  min-width: 0;
}
.search__icon {
  position: absolute;
  top: 50%;
  left: var(--space-3);
  translate: 0 -50%;
  color: var(--text-subtle);
  pointer-events: none;
}
.search__input {
  padding-inline: calc(var(--space-3) + 16px + var(--space-2)) var(--control-h-md);
}
.search__input::-webkit-search-cancel-button {
  display: none;
}
.search__clear {
  position: absolute;
  top: 50%;
  right: var(--space-1);
  translate: 0 -50%;
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-subtle);
}
.search__clear:hover {
  color: var(--text);
  background: var(--surface-hover);
}
</style>
