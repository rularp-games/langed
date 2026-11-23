<script setup>
import { computed } from 'vue'
import { gameFacts } from '@/utils/game'
import AppCard from './ui/AppCard.vue'
import PosterImage from './PosterImage.vue'

const props = defineProps({
  /** Игра из gamesApi (см. normalizeGame). */
  game: { type: Object, required: true },
})

const facts = computed(() => gameFacts(props.game))
const creators = computed(() => props.game.creators.map((creator) => creator.displayName).join(', '))
</script>

<template>
  <AppCard as="article" :to="{ name: 'game', params: { id: game.id } }" padding="none" class="game-card">
    <!-- У большинства игр каталога постера нет: пустую рамку не рисуем, карточка остаётся текстовой. -->
    <PosterImage v-if="game.poster" :src="game.poster" alt="" class="game-card__poster" />
    <div class="game-card__body">
      <h2 class="game-card__title">{{ game.name }}</h2>
      <p v-if="creators" class="game-card__creators">{{ creators }}</p>
      <p v-if="game.announcementExcerpt" class="game-card__excerpt">{{ game.announcementExcerpt }}</p>
      <dl v-if="facts.length" class="game-card__facts">
        <div v-for="fact in facts" :key="fact.key">
          <dt>{{ fact.short || fact.label }}</dt>
          <dd>{{ fact.value }}</dd>
        </div>
      </dl>
    </div>
  </AppCard>
</template>

<style scoped>
.game-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.game-card__poster {
  aspect-ratio: 16 / 10;
  border-bottom: 1px solid var(--border);
}
.game-card__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
  padding: var(--space-3) var(--space-4) var(--space-4);
}
.game-card__title {
  font-size: var(--text-md);
}
.game-card__creators {
  margin-top: calc(-1 * var(--space-1));
  color: var(--text-muted);
  font-size: var(--text-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.game-card__excerpt {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
  color: var(--text-muted);
  font-size: var(--text-sm);
}
.game-card__facts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-4);
  margin-top: auto;
  padding-top: var(--space-2);
  font-size: var(--text-sm);
}
.game-card__facts div {
  display: flex;
  gap: var(--space-1);
}
.game-card__facts dt {
  color: var(--text-subtle);
}
.game-card__facts dd {
  font-weight: 550;
  font-variant-numeric: tabular-nums;
}

/* Телефон: компактная строка — миниатюра слева, текст справа. */
@media (max-width: 519px) {
  .game-card {
    flex-direction: row;
  }
  .game-card__poster {
    flex: none;
    width: 96px;
    aspect-ratio: auto;
    border-bottom: 0;
    border-right: 1px solid var(--border);
  }
  .game-card__body {
    padding: var(--space-3);
  }
  .game-card__excerpt {
    -webkit-line-clamp: 2;
    line-clamp: 2;
  }
}
</style>
