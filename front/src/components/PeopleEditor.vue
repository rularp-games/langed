<script setup>
import { ref } from 'vue'
import { X } from '@lucide/vue'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import AppSpinner from './ui/AppSpinner.vue'
import UserChip from './ui/UserChip.vue'
import UserPicker from './UserPicker.vue'

/**
 * Список людей с добавлением и удалением: авторы игры, мастера прогона, организаторы.
 * Сам показывает подтверждение удаления и ошибки API; список хранит родитель и обновляет его
 * из ответа API (add_* / remove_* возвращают обновлённый объект):
 *
 *   <PeopleEditor
 *     :people="game.creators" :editable="game.canEdit" :min="1"
 *     add-label="Добавить автора" remove-title="Убрать автора?" empty-text="Авторы не указаны"
 *     :add="async (user) => { game = await gamesApi.addCreator(game.id, user.username) }"
 *     :remove="async (person) => { game = await gamesApi.removeCreator(game.id, person.id) }"
 *   />
 */
const props = defineProps({
  /** [{id, displayName}] */
  people: { type: Array, required: true },
  /** false — только просмотр (без поля поиска и кнопок удаления). */
  editable: Boolean,
  /** (user: {id, username, displayName}) => Promise — добавить человека. */
  add: { type: Function, default: null },
  /** (person: {id, displayName}) => Promise — убрать человека. */
  remove: { type: Function, default: null },
  /** Сколько человек должно остаться: при min=1 последнего убрать нельзя. */
  min: { type: Number, default: 0 },
  addLabel: { type: String, default: 'Добавить человека' },
  removeTitle: { type: String, default: 'Убрать из списка?' },
  emptyText: { type: String, default: 'Никого нет' },
})

const confirm = useConfirm()
const toast = useToast()
const adding = ref(false)
const removingId = ref(null)

async function onAdd(user) {
  if (!props.add || adding.value) return
  adding.value = true
  try {
    await props.add(user)
  } catch (error) {
    toast.apiError(error, 'Не удалось добавить')
  } finally {
    adding.value = false
  }
}

async function onRemove(person) {
  if (!props.remove || removingId.value !== null) return
  const ok = await confirm({
    title: props.removeTitle,
    message: person.displayName,
    confirmText: 'Убрать',
    danger: true,
  })
  if (!ok) return
  removingId.value = person.id
  try {
    await props.remove(person)
  } catch (error) {
    toast.apiError(error, 'Не удалось убрать')
  } finally {
    removingId.value = null
  }
}
</script>

<template>
  <div class="people">
    <ul v-if="people.length" class="people__list">
      <li v-for="person in people" :key="person.id" class="people__item">
        <UserChip :name="person.displayName" />
        <template v-if="editable && remove && people.length > min">
          <AppSpinner v-if="removingId === person.id" :size="16" label="Убираем" />
          <button
            v-else
            type="button"
            class="people__remove"
            :aria-label="`Убрать: ${person.displayName}`"
            @click="onRemove(person)"
          >
            <X :size="16" aria-hidden="true" />
          </button>
        </template>
      </li>
    </ul>
    <p v-else class="people__empty">{{ emptyText }}</p>

    <UserPicker
      v-if="editable && add"
      :label="addLabel"
      :placeholder="addLabel"
      :exclude="people.map((person) => person.id)"
      :disabled="adding"
      @select="onAdd"
    />
  </div>
</template>

<style scoped>
.people {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.people__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.people__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  min-height: 2rem;
}
.people__remove {
  flex: none;
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
.people__remove:hover {
  background: var(--surface-hover);
  color: var(--danger-text);
}
.people__empty {
  color: var(--text-muted);
}
</style>
