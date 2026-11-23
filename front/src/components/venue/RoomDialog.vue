<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { venuesApi } from '@/api/venues'
import AppAlert from '@/components/ui/AppAlert.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppCheckbox from '@/components/ui/AppCheckbox.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import AppInput from '@/components/ui/AppInput.vue'
import FormField from '@/components/ui/FormField.vue'

/** Добавление и изменение помещения площадки. Событие saved — с сохранённым помещением. */
const props = defineProps({
  venueId: { type: Number, required: true },
  /** Помещение для изменения; null — добавление нового. */
  room: { type: Object, default: null },
})
const emit = defineEmits(['saved'])
const open = defineModel('open', { type: Boolean, default: false })

const form = reactive({ name: '', blackbox: false })
const nameError = ref('')
const formError = ref('')
const saving = ref(false)
const isEdit = computed(() => Boolean(props.room))

watch(open, (value) => {
  if (!value) return
  form.name = props.room?.name ?? ''
  form.blackbox = props.room?.blackbox ?? false
  nameError.value = ''
  formError.value = ''
  saving.value = false
})

async function submit() {
  if (saving.value) return
  nameError.value = ''
  formError.value = ''
  const name = form.name.trim()
  if (!name) {
    nameError.value = 'Укажите название помещения'
    return
  }
  saving.value = true
  try {
    const data = { name, blackbox: form.blackbox }
    const saved = isEdit.value
      ? await venuesApi.updateRoom(props.room.id, data)
      : await venuesApi.createRoom({ ...data, venueId: props.venueId })
    emit('saved', saved)
    open.value = false
  } catch (err) {
    nameError.value = err?.field?.('name') ?? ''
    if (!nameError.value) formError.value = err?.detail || 'Не удалось сохранить помещение. Попробуйте ещё раз.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <AppDialog v-model:open="open" :title="isEdit ? 'Помещение' : 'Новое помещение'" :dismissible="!saving">
    <form id="room-form" class="room-form" novalidate @submit.prevent="submit">
      <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>
      <FormField label="Название" :error="nameError" required>
        <AppInput v-model="form.name" maxlength="255" autocomplete="off" autofocus placeholder="Например, «Малый зал»" />
      </FormField>
      <div>
        <AppCheckbox v-model="form.blackbox">Blackbox</AppCheckbox>
        <p class="room-form__hint">Затемнённое помещение с управляемым светом и звуком.</p>
      </div>
    </form>
    <template #footer>
      <AppButton :disabled="saving" @click="open = false">Отмена</AppButton>
      <AppButton type="submit" form="room-form" variant="primary" :loading="saving">
        {{ isEdit ? 'Сохранить' : 'Добавить' }}
      </AppButton>
    </template>
  </AppDialog>
</template>

<style scoped>
.room-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.room-form__hint {
  margin-top: var(--space-1);
  color: var(--text-muted);
  font-size: var(--text-sm);
}
</style>
