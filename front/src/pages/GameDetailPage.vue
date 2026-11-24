<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ExternalLink, Link, Pencil, Trash2 } from '@lucide/vue'
import { gamesApi } from '@/api/games'
import { useAsyncData } from '@/composables/useAsyncData'
import { useConfirm } from '@/composables/useConfirm'
import { usePageTitle } from '@/composables/usePageTitle'
import { useToast } from '@/composables/useToast'
import { gameFacts, safeHref } from '@/utils/game'
import AuthorsText from '@/components/game/AuthorsText.vue'
import GameRuns from '@/components/game/GameRuns.vue'
import PeopleEditor from '@/components/PeopleEditor.vue'
import PosterImage from '@/components/PosterImage.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppSkeleton from '@/components/ui/AppSkeleton.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import PageHeader from '@/components/ui/PageHeader.vue'

const props = defineProps({
  id: { type: String, required: true },
})

const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const back = { to: { name: 'games' }, label: 'Все игры' }

const { data: game, error, reload } = useAsyncData((signal) => gamesApi.get(props.id, { signal }), {
  watch: () => props.id,
})

usePageTitle(() => game.value?.name)

const facts = computed(() => (game.value ? gameFacts(game.value) : []))
const sourceHref = computed(() => safeHref(game.value?.sourceUrl))
const authorsTitle = computed(() =>
  game.value?.creators.length === 1 && !game.value.authorsText ? 'Автор' : 'Авторы',
)
const deleting = ref(false)

async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    toast.success('Ссылка скопирована')
  } catch {
    toast.error('Не удалось скопировать ссылку. Скопируйте её из адресной строки.')
  }
}

async function addCreator(user) {
  game.value = await gamesApi.addCreator(game.value.id, user.username)
}

async function removeCreator(person) {
  game.value = await gamesApi.removeCreator(game.value.id, person.id)
}

async function removeGame() {
  const ok = await confirm({
    title: 'Удалить игру?',
    message: `«${game.value.name}» будет удалена из каталога без возможности восстановления.`,
    confirmText: 'Удалить',
    danger: true,
  })
  if (!ok) return
  deleting.value = true
  try {
    await gamesApi.remove(game.value.id)
    toast.success('Игра удалена')
    router.push({ name: 'games' })
  } catch (err) {
    toast.apiError(err, 'Не удалось удалить игру')
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <div class="container">
    <template v-if="error">
      <PageHeader :back="back" />
      <ErrorState :error="error" title="Не удалось загрузить игру" not-found-title="Игра не найдена" @retry="reload" />
    </template>

    <template v-else-if="!game">
      <PageHeader :back="back">
        <template #title><AppSkeleton width="min(320px, 70vw)" height="1.2em" /></template>
      </PageHeader>
      <div class="game" aria-busy="true" aria-label="Загрузка игры">
        <div class="game__main">
          <AppSkeleton v-for="n in 5" :key="n" height="1em" :width="n === 5 ? '60%' : '100%'" class="game__line" />
        </div>
        <AppSkeleton class="game__aside" height="280px" radius="lg" />
      </div>
    </template>

    <template v-else>
      <PageHeader :title="game.name" :back="back">
        <template v-if="game.ageRating" #meta>
          <AppBadge title="Возрастной рейтинг" class="game__age">
            <span class="visually-hidden">Возрастной рейтинг:</span>
            {{ game.ageRating }}
          </AppBadge>
        </template>
        <template #actions>
          <AppButton @click="copyLink">
            <Link :size="16" aria-hidden="true" />
            Скопировать ссылку
          </AppButton>
          <template v-if="game.canEdit">
            <AppButton :to="{ name: 'game-edit', params: { id: game.id } }">
              <Pencil :size="16" aria-hidden="true" />
              Изменить
            </AppButton>
            <AppButton variant="ghost" :loading="deleting" @click="removeGame">
              <Trash2 :size="16" aria-hidden="true" />
              Удалить
            </AppButton>
          </template>
        </template>
      </PageHeader>

      <article class="game">
        <div class="game__main">
          <section v-if="game.announcement" aria-labelledby="game-announcement">
            <h2 id="game-announcement">Анонс</h2>
            <p class="prose">{{ game.announcement }}</p>
          </section>
          <p v-else class="text-muted">Анонс пока не добавлен.</p>

          <section v-if="game.redFlags" class="game__flags" aria-labelledby="game-red-flags">
            <h2 id="game-red-flags">Красные флаги</h2>
            <p class="prose">{{ game.redFlags }}</p>
          </section>

          <GameRuns :game-id="game.id" class="game__runs" />
        </div>

        <aside class="game__aside">
          <PosterImage v-if="game.poster" :src="game.poster" :alt="`Постер игры «${game.name}»`" fit="contain" :lazy="false" class="game__poster" />

          <section v-if="facts.length" aria-labelledby="game-facts">
            <h2 id="game-facts" class="game__aside-title">Параметры</h2>
            <dl class="game__facts">
              <div v-for="fact in facts" :key="fact.key">
                <dt>{{ fact.label }}</dt>
                <dd>{{ fact.value }}</dd>
              </div>
            </dl>
          </section>

          <section v-if="game.creators.length || game.authorsText || game.canEdit" aria-labelledby="game-creators">
            <h2 id="game-creators" class="game__aside-title">{{ authorsTitle }}</h2>
            <!-- Сначала пользователи портала (могут редактировать игру), затем авторы текстом. -->
            <PeopleEditor
              v-if="game.creators.length || game.canEdit"
              :people="game.creators"
              :editable="game.canEdit"
              :min="1"
              :add="addCreator"
              :remove="removeCreator"
              add-label="Добавить автора"
              remove-title="Убрать автора?"
              :empty-text="game.authorsText ? 'Пользователи портала не привязаны' : 'Авторы не указаны'"
            />
            <AuthorsText
              v-if="game.authorsText"
              :text="game.authorsText"
              :class="{ 'game__authors-text--after': game.creators.length || game.canEdit }"
            />
          </section>

          <a v-if="sourceHref" :href="sourceHref" target="_blank" rel="noopener noreferrer nofollow" class="game__source">
            <ExternalLink :size="16" aria-hidden="true" />
            Источник
          </a>
        </aside>
      </article>
    </template>
  </div>
</template>

<style scoped>
.game {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: var(--space-8) var(--space-10);
  align-items: start;
}
.game__age {
  font-variant-numeric: tabular-nums;
}
.game__main {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  min-width: 0;
}
.game__main h2 {
  margin-bottom: var(--space-2);
  font-size: var(--text-md);
}
.game__runs {
  padding-top: var(--space-6);
  border-top: 1px solid var(--border);
}
.game__line {
  margin-bottom: var(--space-1);
}
.game__flags {
  padding: var(--space-4);
  border-left: 3px solid var(--warning-text);
  border-radius: var(--radius-md);
  background: var(--warning-soft);
}
.game__aside {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  min-width: 0;
}
.game__poster {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  max-height: 440px;
}
.game__aside-title {
  margin-bottom: var(--space-2);
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 600;
  letter-spacing: 0;
}
.game__facts {
  border-top: 1px solid var(--border);
}
.game__authors-text--after {
  margin-top: var(--space-3);
}
.game__source {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  align-self: flex-start;
  min-height: 1.75rem;
}
.game__facts div {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  padding-block: var(--space-2);
  border-bottom: 1px solid var(--border);
}
.game__facts dt {
  color: var(--text-muted);
}
.game__facts dd {
  font-weight: 550;
  font-variant-numeric: tabular-nums;
}
/* Телефон и планшет: одна колонка, постер и параметры — над текстом. */
@media (max-width: 859px) {
  .game {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-6);
  }
  .game__aside {
    order: -1;
  }
  .game__poster {
    max-height: 320px;
  }
}
</style>
