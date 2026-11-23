<script setup>
import { Compass } from '@lucide/vue'
import AppButton from '@/components/ui/AppButton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
</script>

<template>
  <div class="container">
    <EmptyState
      :icon="Compass"
      title="Страница не найдена"
      description="Такой страницы нет. Возможно, ссылка устарела или в адресе опечатка."
    >
      <AppButton variant="primary" to="/">На афишу</AppButton>
      <AppButton :to="{ name: 'games' }">К играм</AppButton>
    </EmptyState>
  </div>
</template>
