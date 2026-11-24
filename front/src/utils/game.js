/** Возрастные рейтинги игры (как в модели Game.age_rating); '' — не указан. */
export const AGE_RATINGS = ['0+', '6+', '12+', '13+', '14+', '16+', '18+', '21+']

/**
 * Число или диапазон состава игры: «5–8», «от 5», «до 8», «6», «нет» (0 — таких ролей нет)
 * либо null, если не указано (обе границы null).
 */
export function formatCount(min, max) {
  const lo = min === null || min === undefined || min === '' ? null : Number(min)
  const hi = max === null || max === undefined || max === '' ? null : Number(max)
  if (lo === null && hi === null) return null
  if (lo !== null && hi !== null) {
    if (lo === hi) return lo === 0 ? 'нет' : String(lo)
    return lo === 0 ? `до ${hi}` : `${lo}–${hi}`
  }
  if (lo !== null) return lo === 0 ? null : `от ${lo}`
  return hi === 0 ? 'нет' : `до ${hi}`
}

/**
 * Заполненные параметры игры для карточки и страницы: [{ key, label, value }].
 * Не указанные (null) не попадают в список.
 */
export function gameFacts(game) {
  return [
    { key: 'players', label: 'Игроки', value: formatCount(game.playersMin, game.playersMax) },
    { key: 'female', label: 'Женские роли', short: 'Жен. роли', value: formatCount(game.femaleRolesMin, game.femaleRolesMax) },
    { key: 'male', label: 'Мужские роли', short: 'Муж. роли', value: formatCount(game.maleRolesMin, game.maleRolesMax) },
    { key: 'technicians', label: 'Игротехники', value: Number(game.technicians) > 0 ? String(game.technicians) : null },
  ].filter((fact) => fact.value !== null)
}

// Ссылка в тексте: http(s)://… или адрес без схемы на распространённых площадках.
const LINK_RE = /\bhttps?:\/\/[^\s<>"«»()]+|\b(?:www\.|(?:m\.)?vk\.(?:com|ru)\/|t\.me\/)[^\s<>"«»()]+/gi
// Знаки препинания, которыми обычно заканчивается фраза, а не адрес.
const TRAILING_RE = /[.,;:!?]+$/

/**
 * Разбор свободного текста на сегменты для безопасного вывода без v-html:
 * [{ type: 'text', text }, { type: 'link', text, href }]. href — всегда http(s).
 */
export function textSegments(value) {
  const text = String(value ?? '')
  const segments = []
  let last = 0
  for (const match of text.matchAll(LINK_RE)) {
    const raw = match[0].replace(TRAILING_RE, '')
    if (!raw) continue
    if (match.index > last) segments.push({ type: 'text', text: text.slice(last, match.index) })
    const href = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`
    segments.push({ type: 'link', text: raw.replace(/^https?:\/\//i, '').replace(/\/$/, ''), href })
    last = match.index + raw.length
  }
  if (last < text.length) segments.push({ type: 'text', text: text.slice(last) })
  return segments
}

/** Текст без ссылок — для мест, где ссылки неуместны (карточка-ссылка): «Анна (vk.com/a), Иван» → «Анна, Иван». */
export function textWithoutLinks(value) {
  const text = textSegments(value)
    .filter((segment) => segment.type === 'text')
    .map((segment) => segment.text)
    .join('')
  return text
    .split(/[\n,;]/)
    .map((part) =>
      part
        .replace(/\(\s*\)/g, '')
        .replace(/\s+/g, ' ')
        .replace(/(?:\s+\.|[\s:—–-])+$/, '')
        .replace(/^[\s.:—–-]+/, ''),
    )
    .filter(Boolean)
    .join(', ')
}

/** Авторы игры одной строкой: пользователи-авторы, затем авторы текстом (без ссылок). */
export function gameAuthorsLine(game) {
  return [...(game.creators ?? []).map((creator) => creator.displayName), textWithoutLinks(game.authorsText)]
    .filter(Boolean)
    .join(', ')
}

/** Адрес, который можно поставить в href: только http(s). */
export function safeHref(url) {
  return /^https?:\/\/\S+$/i.test(String(url ?? '').trim()) ? String(url).trim() : null
}
