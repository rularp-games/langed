/**
 * Даты и время. Главное правило: время события показывается в поясе города проведения.
 * Backend отдаёт его готовым в поле date_local (dateLocal) — строка 'YYYY-MM-DDTHH:mm:ss' без пояса.
 * Эти функции разбирают такую строку по частям и НЕ создают из неё Date в поясе браузера,
 * поэтому сдвига не бывает. Поле date (UTC, с Z) нужно только чтобы понять, прошло ли событие.
 *
 * Аргументом «локальная строка» везде может быть 'YYYY-MM-DDTHH:mm[:ss]' либо дата 'YYYY-MM-DD'.
 */

const MONTHS_GENITIVE = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
]
const WEEKDAYS_SHORT = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб']
const WEEKDAYS_LONG = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота']

const pad = (value) => String(value).padStart(2, '0')

/** Разбор локальной строки: {year, month (1–12), day, hour, minute, hasTime} либо null. */
export function parseLocal(value) {
  const match = String(value ?? '').match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/)
  if (!match) return null
  return {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
    hour: Number(match[4] ?? 0),
    minute: Number(match[5] ?? 0),
    hasTime: match[4] !== undefined,
  }
}

// Date в UTC используется только как календарь (день недели, прибавление минут).
const toUtc = (parts) => new Date(Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute))
const fromUtc = (date) =>
  `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}` +
  `T${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:00`

/** Ключ дня 'YYYY-MM-DD' — для группировки по дням и сравнения дат. */
export function dateKey(value) {
  const parts = parseLocal(value)
  return parts ? `${parts.year}-${pad(parts.month)}-${pad(parts.day)}` : ''
}

/** Сегодняшняя дата 'YYYY-MM-DD' в поясе города (IANA, например 'Asia/Omsk') или в поясе браузера. */
export function todayKey(timeZone) {
  const now = new Date()
  if (timeZone) {
    try {
      // en-CA даёт формат YYYY-MM-DD
      return new Intl.DateTimeFormat('en-CA', { timeZone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(now)
    } catch {
      // неизвестный пояс — считаем по браузеру
    }
  }
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}

/** Сдвиг даты-ключа на число дней: shiftDateKey('2026-12-31', 1) → '2027-01-01'. */
export function shiftDateKey(key, days) {
  const parts = parseLocal(key)
  if (!parts) return ''
  return dateKey(fromUtc(new Date(Date.UTC(parts.year, parts.month - 1, parts.day + days))))
}

/** «сегодня» | «завтра» | «вчера» | null. timeZone — пояс города события (run.cityTimezone). */
export function relativeDay(value, { timeZone } = {}) {
  const key = dateKey(value)
  if (!key) return null
  const today = todayKey(timeZone)
  if (key === today) return 'сегодня'
  if (key === shiftDateKey(today, 1)) return 'завтра'
  if (key === shiftDateKey(today, -1)) return 'вчера'
  return null
}

/** День недели: «сб» (или «суббота» при long). */
export function formatWeekday(value, { long = false } = {}) {
  const parts = parseLocal(value)
  if (!parts) return ''
  return (long ? WEEKDAYS_LONG : WEEKDAYS_SHORT)[toUtc(parts).getUTCDay()]
}

/**
 * Дата: «14 декабря». year: 'auto' (по умолчанию) — год добавляется, если он не текущий;
 * true — всегда («14 декабря 2026»); false — никогда. weekday: true — «сб, 14 декабря».
 */
export function formatDate(value, { year = 'auto', weekday = false } = {}) {
  const parts = parseLocal(value)
  if (!parts) return ''
  const withYear = year === true || (year === 'auto' && parts.year !== new Date().getFullYear())
  const text = `${parts.day} ${MONTHS_GENITIVE[parts.month - 1]}${withYear ? ` ${parts.year}` : ''}`
  return weekday ? `${formatWeekday(value)}, ${text}` : text
}

/** Время: «19:00». */
export function formatTime(value) {
  const parts = parseLocal(value)
  return parts?.hasTime ? `${pad(parts.hour)}:${pad(parts.minute)}` : ''
}

/**
 * Дата и время: «сб, 14 декабря, 19:00».
 * relative: true — для ближайших дней «сегодня, 19:00» / «завтра, 19:00» (нужен timeZone города).
 */
export function formatDateTime(value, { relative = false, timeZone, year = 'auto' } = {}) {
  const parts = parseLocal(value)
  if (!parts) return ''
  const day = (relative && relativeDay(value, { timeZone })) || formatDate(value, { year, weekday: true })
  return parts.hasTime ? `${day}, ${formatTime(value)}` : day
}

/** Локальная строка, сдвинутая на число минут: addMinutes('2026-12-14T23:00:00', 90) → '2026-12-15T00:30:00'. */
export function addMinutes(value, minutes) {
  const parts = parseLocal(value)
  if (!parts) return ''
  return fromUtc(new Date(toUtc(parts).getTime() + minutes * 60000))
}

/** Интервал времени по началу и длительности в минутах: «19:00–22:30». */
export function formatTimeRange(value, durationMinutes) {
  const start = formatTime(value)
  if (!start || !durationMinutes) return start
  return `${start}–${formatTime(addMinutes(value, durationMinutes))}`
}

/**
 * Диапазон дат проведения: «21–23 февраля 2026», «28 февраля – 2 марта 2026»,
 * «30 декабря 2026 – 2 января 2027», один день — «21 февраля 2026». Год выводится всегда.
 */
export function formatDateRange(start, end) {
  const from = parseLocal(start)
  const to = parseLocal(end) ?? from
  if (!from) return ''
  const month = (parts) => MONTHS_GENITIVE[parts.month - 1]
  if (dateKey(start) === dateKey(end ?? start)) return `${from.day} ${month(from)} ${from.year}`
  if (from.year !== to.year) return `${from.day} ${month(from)} ${from.year} – ${to.day} ${month(to)} ${to.year}`
  if (from.month !== to.month) return `${from.day} ${month(from)} – ${to.day} ${month(to)} ${to.year}`
  return `${from.day}–${to.day} ${month(from)} ${from.year}`
}

/** Длительность в минутах: 210 → «3 ч 30 мин», 180 → «3 ч», 45 → «45 мин». */
export function formatDuration(minutes) {
  const total = Number(minutes)
  if (!Number.isFinite(total) || total <= 0) return ''
  const hours = Math.floor(total / 60)
  const rest = total % 60
  return [hours && `${hours} ч`, rest && `${rest} мин`].filter(Boolean).join(' ')
}

/** Прошёл ли момент. Аргумент — поле date (UTC с Z), не dateLocal. */
export function isPast(utcIso) {
  const time = Date.parse(utcIso)
  return Number.isFinite(time) && time < Date.now()
}

/** Завершилось ли проведение: сравнение dateEnd ('YYYY-MM-DD') с сегодняшним днём города. */
export function isDatePast(key, { timeZone } = {}) {
  const value = dateKey(key)
  return Boolean(value) && value < todayKey(timeZone)
}

/**
 * Служебная отметка времени (createdAt, updatedAt — UTC с Z) в поясе браузера:
 * «14 декабря 2026, 19:05». Для времени событий не использовать.
 */
export function formatTimestamp(utcIso) {
  const date = new Date(utcIso)
  if (Number.isNaN(date.getTime())) return ''
  const local = `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
  return `${formatDate(local, { year: true })}, ${formatTime(local)}`
}

// --- Формы ---

/** dateLocal → значение для <input type="datetime-local">: 'YYYY-MM-DDTHH:mm'. */
export function toDateTimeInput(value) {
  const parts = parseLocal(value)
  if (!parts) return ''
  return `${dateKey(value)}T${pad(parts.hour)}:${pad(parts.minute)}`
}

/**
 * Значение <input type="datetime-local"> → формат записи API: 'YYYY-MM-DDTHH:mm:00' без пояса
 * (backend трактует его как локальное время города). Пустое значение → null.
 */
export function fromDateTimeInput(value) {
  const parts = parseLocal(value)
  if (!parts || !parts.hasTime) return null
  return `${dateKey(value)}T${pad(parts.hour)}:${pad(parts.minute)}:00`
}

/** Дата и время из отдельных полей <input type="date"> и <input type="time"> → формат записи API. */
export function combineDateTime(date, time) {
  return fromDateTimeInput(`${date}T${time || '00:00'}`)
}
