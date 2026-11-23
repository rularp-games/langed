<script setup>
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from '@lucide/vue'

/**
 * Серверная пагинация. Скрывается, если страница одна.
 *   <AppPagination v-model:page="page" :count="data.count" :page-size="24" />
 */
const props = defineProps({
  /** Всего записей. */
  count: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  disabled: Boolean,
})
const page = defineModel('page', { type: Number, default: 1 })

const total = computed(() => Math.max(1, Math.ceil(props.count / props.pageSize)))

/** Номера страниц с пропусками: 1 … 4 5 6 … 12 */
const items = computed(() => {
  const last = total.value
  const current = Math.min(page.value, last)
  const wanted = new Set([1, last, current - 1, current, current + 1])
  if (current <= 3) [2, 3, 4].forEach((n) => wanted.add(n))
  if (current >= last - 2) [last - 1, last - 2, last - 3].forEach((n) => wanted.add(n))
  const pages = [...wanted].filter((n) => n >= 1 && n <= last).sort((a, b) => a - b)
  const result = []
  pages.forEach((n, index) => {
    if (index && n - pages[index - 1] > 1) result.push({ gap: true, key: `gap-${n}` })
    result.push({ page: n, key: n })
  })
  return result
})

function go(target) {
  if (props.disabled) return
  const next = Math.min(Math.max(1, target), total.value)
  if (next !== page.value) page.value = next
}
</script>

<template>
  <nav v-if="total > 1" class="pagination" aria-label="Страницы">
    <button type="button" class="pagination__btn" :disabled="page <= 1 || disabled" aria-label="Предыдущая страница" @click="go(page - 1)">
      <ChevronLeft :size="18" aria-hidden="true" />
    </button>
    <ul class="pagination__pages">
      <li v-for="item in items" :key="item.key">
        <span v-if="item.gap" class="pagination__gap" aria-hidden="true">…</span>
        <button
          v-else
          type="button"
          class="pagination__btn"
          :class="{ 'is-current': item.page === page }"
          :aria-current="item.page === page ? 'page' : undefined"
          :aria-label="`Страница ${item.page}`"
          @click="go(item.page)"
        >
          {{ item.page }}
        </button>
      </li>
    </ul>
    <span class="pagination__compact" aria-hidden="true">{{ page }} из {{ total }}</span>
    <button type="button" class="pagination__btn" :disabled="page >= total || disabled" aria-label="Следующая страница" @click="go(page + 1)">
      <ChevronRight :size="18" aria-hidden="true" />
    </button>
  </nav>
</template>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
}
.pagination__pages {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}
.pagination__compact {
  display: none;
  padding: 0 var(--space-3);
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-variant-numeric: tabular-nums;
}
.pagination__btn {
  display: grid;
  place-items: center;
  min-width: var(--control-h-md);
  height: var(--control-h-md);
  padding: 0 var(--space-2);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 550;
  font-variant-numeric: tabular-nums;
}
.pagination__btn:hover:not(:disabled) {
  background: var(--surface-hover);
  color: var(--text);
}
.pagination__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.pagination__btn.is-current {
  border-color: var(--border-strong);
  background: var(--surface);
  color: var(--text);
}
.pagination__gap {
  display: grid;
  place-items: center;
  min-width: 1.5rem;
  color: var(--text-subtle);
}

/* На телефоне — только «назад / 3 из 8 / вперёд». */
@media (max-width: 519px) {
  .pagination__pages {
    display: none;
  }
  .pagination__compact {
    display: block;
  }
}
</style>
