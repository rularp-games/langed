<script setup>
import { computed, onBeforeUnmount, ref, useId } from 'vue'
import { Search } from '@lucide/vue'
import { isAbortError } from '@/api/client'
import { usersApi } from '@/api/users'
import AppSpinner from './ui/AppSpinner.vue'

/**
 * Поиск и выбор пользователя (GET /api/users/search/, только для вошедших).
 * Стрелки — перемещение по списку, Enter — выбор, Esc — закрыть. После выбора поле очищается.
 *   <UserPicker label="Добавить автора" :exclude="game.creators.map((c) => c.id)" @select="add" />
 * Событие select: {id, username, displayName, email|null} — username нужен для add_* в API.
 */
const props = defineProps({
  /** Подпись поля для экранных дикторов. */
  label: { type: String, required: true },
  placeholder: { type: String, default: 'Имя, фамилия или логин' },
  /** id пользователей, которых не предлагать (уже добавленные). */
  exclude: { type: Array, default: () => [] },
  disabled: Boolean,
  debounce: { type: Number, default: 250 },
})
const emit = defineEmits(['select'])

const listId = `users-${useId()}`
const query = ref('')
const results = ref([])
const open = ref(false)
const loading = ref(false)
const failed = ref(false)
const active = ref(-1)
const input = ref(null)
let timer = null
let controller = null

const options = computed(() => results.value.filter((user) => !props.exclude.includes(user.id)))
const tooShort = computed(() => query.value.trim().length < 2)

async function search() {
  controller?.abort()
  const text = query.value.trim()
  if (text.length < 2) {
    results.value = []
    loading.value = false
    return
  }
  const current = new AbortController()
  controller = current
  loading.value = true
  failed.value = false
  try {
    results.value = await usersApi.search(text, { signal: current.signal })
    active.value = options.value.length ? 0 : -1
  } catch (error) {
    if (isAbortError(error)) return
    results.value = []
    failed.value = true
  } finally {
    if (controller === current) loading.value = false
  }
}

function onInput() {
  open.value = true
  active.value = -1
  clearTimeout(timer)
  timer = setTimeout(search, props.debounce)
}

function choose(user) {
  emit('select', user)
  query.value = ''
  results.value = []
  open.value = false
  active.value = -1
  input.value?.focus()
}

function onKeydown(event) {
  const count = options.value.length
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    open.value = true
    if (!count) return
    const step = event.key === 'ArrowDown' ? 1 : -1
    active.value = (active.value + step + count) % count
  } else if (event.key === 'Enter') {
    if (open.value && active.value >= 0 && options.value[active.value]) {
      event.preventDefault()
      choose(options.value[active.value])
    }
  } else if (event.key === 'Escape' && open.value) {
    // Не даём Esc закрыть диалог, в котором стоит поле.
    event.preventDefault()
    event.stopPropagation()
    open.value = false
  }
}

function onBlur() {
  // Клик по варианту обрабатывается на mousedown, поэтому закрывать можно сразу.
  open.value = false
}

onBeforeUnmount(() => {
  clearTimeout(timer)
  controller?.abort()
})

defineExpose({ focus: () => input.value?.focus() })
</script>

<template>
  <div class="picker">
    <Search class="picker__icon" :size="16" aria-hidden="true" />
    <input
      ref="input"
      v-model="query"
      type="text"
      class="control picker__input"
      role="combobox"
      autocomplete="off"
      aria-autocomplete="list"
      :aria-label="label"
      :aria-expanded="open && !tooShort"
      :aria-controls="listId"
      :aria-activedescendant="active >= 0 ? `${listId}-${active}` : undefined"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="onInput"
      @focus="open = true"
      @blur="onBlur"
      @keydown="onKeydown"
    />
    <AppSpinner v-if="loading" class="picker__spinner" :size="16" />

    <div v-show="open && !tooShort" class="picker__popup">
      <ul :id="listId" class="picker__list" role="listbox" :aria-label="label">
        <li
          v-for="(user, index) in options"
          :id="`${listId}-${index}`"
          :key="user.id"
          role="option"
          class="picker__option"
          :class="{ 'is-active': index === active }"
          :aria-selected="index === active"
          @mousedown.prevent="choose(user)"
          @mousemove="active = index"
        >
          <span class="picker__name">{{ user.displayName }}</span>
          <span v-if="user.username && user.username !== user.displayName" class="picker__username">{{ user.username }}</span>
        </li>
      </ul>
      <p v-if="!options.length" class="picker__status" role="status">
        {{ failed ? 'Не удалось выполнить поиск' : loading ? 'Ищем…' : 'Никого не нашли' }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.picker {
  position: relative;
  width: 100%;
}
.picker__icon {
  position: absolute;
  top: 50%;
  left: var(--space-3);
  translate: 0 -50%;
  color: var(--text-subtle);
  pointer-events: none;
}
.picker__input {
  padding-inline: calc(var(--space-3) + 16px + var(--space-2)) var(--space-8);
}
.picker__spinner {
  position: absolute;
  top: 50%;
  right: var(--space-3);
  translate: 0 -50%;
  color: var(--text-subtle);
}
.picker__popup {
  position: absolute;
  top: calc(100% + var(--space-1));
  left: 0;
  right: 0;
  z-index: 30;
  max-height: 260px;
  padding: var(--space-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--shadow-md);
  overflow-y: auto;
}
.picker__option {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  min-height: var(--control-h-md);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.picker__option.is-active {
  background: var(--surface-hover);
}
.picker__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.picker__username {
  flex: none;
  color: var(--text-subtle);
  font-size: var(--text-sm);
}
.picker__status {
  padding: var(--space-2) var(--space-3);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
</style>
