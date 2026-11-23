<script setup>
defineProps({
  /** neutral | accent | success | warning | danger | info */
  tone: { type: String, default: 'neutral' },
})
</script>

<template>
  <span class="badge" :class="`badge--${tone}`"><slot /></span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: 0.125rem var(--space-2);
  border-radius: var(--radius-full);
  background: var(--surface-2);
  color: var(--text-muted);
  font-size: var(--text-xs);
  font-weight: 550;
  line-height: 1.4;
  white-space: nowrap;
}
.badge--accent {
  background: var(--accent-soft);
  color: var(--accent-text);
}
.badge--success {
  background: var(--success-soft);
  color: var(--success-text);
}
.badge--warning {
  background: var(--warning-soft);
  color: var(--warning-text);
}
.badge--danger {
  background: var(--danger-soft);
  color: var(--danger-text);
}
.badge--info {
  background: var(--info-soft);
  color: var(--info-text);
}
</style>
