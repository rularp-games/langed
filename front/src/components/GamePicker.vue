<script setup>
import { computed, inject, nextTick, onBeforeUnmount, ref, useId } from 'vue'
import { Search } from '@lucide/vue'
import { isAbortError } from '@/api/client'
import { gamesApi } from '@/api/games'
import { formatRange } from '@/utils/format'
import AppButton from './ui/AppButton.vue'
import AppSpinner from './ui/AppSpinner.vue'

/**
 * Выбор игры поиском по каталогу (игры пагинированы, поэтому списка целиком нет).
 * Работает внутри FormField: id и aria-* приходят от него, как у AppInput.
 *   <FormField label="Игра" required :error="errors.gameId">
 *     <GamePicker v-model="game" label="Игра" required />
 *   </FormField>
 * v-model — объект игры {id, name, playersMin, playersMax, …} либо null.
 * Стрелки — перемещение по списку, Enter — выбор, Esc — закрыть список.
 * Список открывается по клику, вводу и стрелкам, но не по самому фокусу: после ошибки
 * валидации форма ставит фокус в поле программно, и список не должен закрывать сообщение.
 */
const props = defineProps({
  /** Подпись для экранных дикторов (если поле стоит вне FormField). */
  label: { type: String, default: 'Игра' },
  modelValue: { type: Object, default: null },
  required: Boolean,
  disabled: Boolean,
  placeholder: { type: String, default: 'Начните вводить название игры' },
  debounce: { type: Number, default: 250 },
})
const emit = defineEmits(['update:modelValue'])

const field = inject('formField', null)
const listId = `games-${useId()}`
const query = ref('')
const results = ref([])
const open = ref(false)
const loading = ref(false)
const failed = ref(false)
const searched = ref(false)
const active = ref(-1)
const input = ref(null)
const change = ref(null)
let timer = null
let controller = null

const players = (game) => formatRange(game.playersMin, game.playersMax)
const selectedPlayers = computed(() => (props.modelValue ? players(props.modelValue) : null))

async function search() {
  controller?.abort()
  const current = new AbortController()
  controller = current
  loading.value = true
  failed.value = false
  try {
    const page = await gamesApi.list({ search: query.value.trim(), pageSize: 10 }, { signal: current.signal })
    results.value = page.items
    active.value = page.items.length ? 0 : -1
    searched.value = true
  } catch (error) {
    if (isAbortError(error)) return
    results.value = []
    failed.value = true
    searched.value = true
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

function show() {
  open.value = true
  // Пустой запрос — первые игры каталога, чтобы список не был пустым до ввода.
  if (!searched.value && !loading.value) search()
}

function choose(game) {
  emit('update:modelValue', game)
  query.value = ''
  open.value = false
  active.value = -1
  nextTick(() => change.value?.$el?.focus())
}

function reset() {
  emit('update:modelValue', null)
  results.value = []
  searched.value = false
  nextTick(() => {
    input.value?.focus()
    show()
  })
}

function onKeydown(event) {
  const count = results.value.length
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    show()
    if (!count) return
    const step = event.key === 'ArrowDown' ? 1 : -1
    active.value = (active.value + step + count) % count
  } else if (event.key === 'Enter') {
    // Enter в поле поиска никогда не отправляет форму: игра ещё не выбрана.
    event.preventDefault()
    if (open.value && active.value >= 0 && results.value[active.value]) choose(results.value[active.value])
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

defineExpose({ focus: () => (props.modelValue ? change.value?.$el?.focus() : input.value?.focus()) })
</script>

<template>
  <div v-if="modelValue" class="game-picker game-picker--selected">
    <div class="game-picker__chosen">
      <span class="game-picker__chosen-name">{{ modelValue.name }}</span>
      <span v-if="selectedPlayers" class="game-picker__chosen-meta">Игроков: {{ selectedPlayers }}</span>
    </div>
    <AppButton
      :id="field?.id"
      ref="change"
      size="sm"
      :disabled="disabled"
      :aria-label="`Сменить игру: ${modelValue.name}`"
      @click="reset"
    >
      Сменить
    </AppButton>
  </div>

  <div v-else class="game-picker">
    <Search class="game-picker__icon" :size="16" aria-hidden="true" />
    <input
      :id="field?.id"
      ref="input"
      v-model="query"
      type="text"
      class="control game-picker__input"
      role="combobox"
      autocomplete="off"
      aria-autocomplete="list"
      :aria-label="field ? undefined : label"
      :aria-describedby="field?.describedBy.value"
      :aria-invalid="field?.invalid.value ? 'true' : undefined"
      :aria-required="required || field?.required.value || undefined"
      :aria-expanded="open"
      :aria-controls="listId"
      :aria-activedescendant="active >= 0 ? `${listId}-${active}` : undefined"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="onInput"
      @click="show"
      @blur="onBlur"
      @keydown="onKeydown"
    />
    <AppSpinner v-if="loading" class="game-picker__spinner" :size="16" />

    <div v-show="open" class="game-picker__popup">
      <ul :id="listId" class="game-picker__list" role="listbox" :aria-label="label">
        <li
          v-for="(game, index) in results"
          :id="`${listId}-${index}`"
          :key="game.id"
          role="option"
          class="game-picker__option"
          :class="{ 'is-active': index === active }"
          :aria-selected="index === active"
          @mousedown.prevent="choose(game)"
          @mousemove="active = index"
        >
          <span class="game-picker__name">{{ game.name }}</span>
          <span v-if="players(game)" class="game-picker__meta">{{ players(game) }} игр.</span>
        </li>
      </ul>
      <p v-if="!results.length" class="game-picker__status" role="status">
        {{ failed ? 'Не удалось выполнить поиск' : loading || !searched ? 'Ищем…' : 'Игр не нашли' }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.game-picker {
  position: relative;
  width: 100%;
}
.game-picker--selected {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  min-height: var(--control-h-md);
  padding: var(--space-1) var(--space-1) var(--space-1) var(--space-3);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  background: var(--surface-2);
}
.game-picker__chosen {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0 var(--space-3);
  min-width: 0;
}
.game-picker__chosen-name {
  min-width: 0;
  font-weight: 550;
  overflow-wrap: anywhere;
}
.game-picker__chosen-meta {
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.game-picker__icon {
  position: absolute;
  top: 50%;
  left: var(--space-3);
  translate: 0 -50%;
  color: var(--text-subtle);
  pointer-events: none;
}
.game-picker__input {
  padding-inline: calc(var(--space-3) + 16px + var(--space-2)) var(--space-8);
}
.game-picker__spinner {
  position: absolute;
  top: 50%;
  right: var(--space-3);
  translate: 0 -50%;
  color: var(--text-subtle);
}
.game-picker__popup {
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
.game-picker__option {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  min-height: var(--control-h-md);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.game-picker__option.is-active {
  background: var(--surface-hover);
}
.game-picker__name {
  min-width: 0;
  overflow-wrap: anywhere;
}
.game-picker__meta {
  flex: none;
  color: var(--text-subtle);
  font-size: var(--text-sm);
}
.game-picker__status {
  padding: var(--space-2) var(--space-3);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
</style>
