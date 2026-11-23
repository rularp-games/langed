import { toValue, watchEffect } from 'vue'

const SITE = 'Langed'

export function formatTitle(title) {
  return title ? `${title} — ${SITE}` : `${SITE} — кабинетные ролевые игры`
}

/**
 * Заголовок вкладки для страниц с динамическим названием (статичные задаются в meta.title
 * маршрута). Пока значение пустое, остаётся заголовок из маршрута.
 *   usePageTitle(() => game.value?.name)
 */
export function usePageTitle(source) {
  watchEffect(() => {
    const title = toValue(source)
    if (title) document.title = formatTitle(title)
  })
}
