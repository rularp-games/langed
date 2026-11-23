/** Русское склонение: plural(5, ['игра', 'игры', 'игр']) → 'игр'. */
export function plural(count, [one, few, many]) {
  const n = Math.abs(count) % 100
  const n1 = n % 10
  if (n > 10 && n < 20) return many
  if (n1 > 1 && n1 < 5) return few
  if (n1 === 1) return one
  return many
}

/**
 * Диапазон «5–8», «от 5», «до 8», «6» либо null, если значение не заполнено
 * (оба нуля или пусто) — такие параметры в интерфейсе не выводятся.
 */
export function formatRange(min, max) {
  const lo = Number(min) || 0
  const hi = Number(max) || 0
  if (!lo && !hi) return null
  if (lo && hi) return lo === hi ? String(lo) : `${lo}–${hi}`
  return lo ? `от ${lo}` : `до ${hi}`
}

/** Инициалы для аватара: «Анна Смирнова» → «АС». */
export function initials(name) {
  const parts = String(name || '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
  if (!parts.length) return '?'
  const first = parts[0][0]
  const second = parts.length > 1 ? parts[parts.length - 1][0] : ''
  return (first + second).toUpperCase()
}
