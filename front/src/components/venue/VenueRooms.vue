<script setup>
import { ref } from 'vue'
import { Pencil, Plus, Trash2 } from '@lucide/vue'
import { venuesApi } from '@/api/venues'
import { useConfirm } from '@/composables/useConfirm'
import { useToast } from '@/composables/useToast'
import { useAuthStore } from '@/stores/auth'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import RoomDialog from './RoomDialog.vue'

/**
 * Помещения площадки: список и управление (добавить и изменить — любой вошедший,
 * удалить — только staff). Событие update:rooms — новый список после изменения.
 */
const props = defineProps({
  venueId: { type: Number, required: true },
  rooms: { type: Array, required: true },
})
const emit = defineEmits(['update:rooms'])

const auth = useAuthStore()
const toast = useToast()
const confirm = useConfirm()

const dialogOpen = ref(false)
const editing = ref(null)
const removingId = ref(null)

const sorted = (rooms) => [...rooms].sort((a, b) => a.name.localeCompare(b.name, 'ru', { numeric: true }))

function openDialog(room = null) {
  editing.value = room
  dialogOpen.value = true
}

function onSaved(room) {
  const exists = props.rooms.some((item) => item.id === room.id)
  const rooms = exists ? props.rooms.map((item) => (item.id === room.id ? room : item)) : [...props.rooms, room]
  emit('update:rooms', sorted(rooms))
  toast.success(exists ? 'Помещение сохранено' : 'Помещение добавлено')
}

async function remove(room) {
  const ok = await confirm({
    title: 'Удалить помещение?',
    message: `«${room.name}» будет удалено и пропадёт из прогонов, которым оно назначено.`,
    confirmText: 'Удалить',
    danger: true,
  })
  if (!ok) return
  removingId.value = room.id
  try {
    await venuesApi.removeRoom(room.id)
    emit(
      'update:rooms',
      props.rooms.filter((item) => item.id !== room.id),
    )
    toast.success('Помещение удалено')
  } catch (err) {
    toast.apiError(err, 'Не удалось удалить помещение')
  } finally {
    removingId.value = null
  }
}
</script>

<template>
  <section class="rooms" aria-labelledby="venue-rooms-title">
    <div class="rooms__head">
      <h2 id="venue-rooms-title">Помещения</h2>
      <AppButton v-if="auth.isAuthenticated" size="sm" @click="openDialog()">
        <Plus :size="16" aria-hidden="true" />
        Добавить помещение
      </AppButton>
    </div>

    <p v-if="!rooms.length" class="text-muted">Помещения не указаны.</p>
    <ul v-else class="rooms__list">
      <li v-for="room in rooms" :key="room.id" class="rooms__item">
        <span class="rooms__name">{{ room.name }}</span>
        <AppBadge v-if="room.blackbox" tone="info">Blackbox</AppBadge>
        <span v-if="auth.isAuthenticated" class="rooms__actions">
          <AppButton variant="ghost" size="sm" icon-only :aria-label="`Изменить помещение «${room.name}»`" @click="openDialog(room)">
            <Pencil :size="16" aria-hidden="true" />
          </AppButton>
          <AppButton
            v-if="auth.user?.isStaff"
            variant="ghost"
            size="sm"
            icon-only
            :loading="removingId === room.id"
            :aria-label="`Удалить помещение «${room.name}»`"
            @click="remove(room)"
          >
            <Trash2 :size="16" aria-hidden="true" />
          </AppButton>
        </span>
      </li>
    </ul>

    <RoomDialog v-if="auth.isAuthenticated" v-model:open="dialogOpen" :venue-id="venueId" :room="editing" @saved="onSaved" />
  </section>
</template>

<style scoped>
.rooms {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 0;
}
.rooms__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-3);
}
.rooms__head h2 {
  font-size: var(--text-md);
}
.rooms__list {
  border-top: 1px solid var(--border);
}
.rooms__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 2.75rem;
  padding-block: var(--space-1);
  border-bottom: 1px solid var(--border);
}
.rooms__name {
  min-width: 0;
  overflow-wrap: anywhere;
}
.rooms__actions {
  display: inline-flex;
  flex: none;
  gap: var(--space-1);
  margin-left: auto;
}
</style>
