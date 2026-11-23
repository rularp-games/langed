import { computed, inject, useAttrs } from 'vue'

/**
 * Атрибуты элемента ввода с учётом окружающего FormField (id, aria-*), поверх которых
 * накладываются атрибуты, переданные компоненту напрямую.
 */
export function useFormField() {
  const field = inject('formField', null)
  const attrs = useAttrs()
  return computed(() => ({
    id: field?.id,
    'aria-describedby': field?.describedBy.value,
    'aria-invalid': field?.invalid.value ? 'true' : undefined,
    required: field?.required.value || undefined,
    ...attrs,
  }))
}
