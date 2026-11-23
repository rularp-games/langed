/**
 * Расчёты расписания проведения: дни, помещения-столбцы, раскладка блоков по времени,
 * конфликты по помещениям. Всё время — локальное время города (dateLocal), в минутах от полуночи
 * дня, в который событие начинается; Date в поясе браузера не создаётся.
 */
import { dateKey, isPast, parseLocal, shiftDateKey } from '@/utils/datetime'

/** id столбца для прогонов без помещения. */
export const NO_ROOM = 0
/** Высота одной минуты в сетке, px. */
export const PX_PER_MINUTE = 1.2
/** Длительность по умолчанию, если у записи она не задана (как в backend). */
export const DEFAULT_RUN_DURATION = 180
export const DEFAULT_COMMON_DURATION = 60
/** Блок короче этого рисуется этой высоты, чтобы поместилась строка текста. */
const MIN_BLOCK_MINUTES = 30
/** Рабочие часы пустого дня в редакторе. */
const EDITOR_DAY_START = 9 * 60
const EDITOR_DAY_END = 23 * 60

const pad = (value) => String(value).padStart(2, '0')

/** Минуты от полуночи: '2026-12-13T12:30:00' → 750. */
export function minutesOf(local) {
  const parts = parseLocal(local)
  return parts ? parts.hour * 60 + parts.minute : 0
}

/** Минуты → «12:30»; значения после полуночи (1500) показываются как время следующего дня («01:00»). */
export function formatMinutes(minutes) {
  const value = ((minutes % 1440) + 1440) % 1440
  return `${pad(Math.floor(value / 60))}:${pad(value % 60)}`
}

/** День и минуты → значение для записи в API: ('2026-12-13', 750) → '2026-12-13T12:30:00'. */
export function toLocalDateTime(day, minutes) {
  const date = shiftDateKey(day, Math.floor(minutes / 1440))
  return `${date}T${formatMinutes(minutes)}:00`
}

/** Текущий момент в поясе города: {day: 'YYYY-MM-DD', minutes}. Без пояса — по браузеру. */
export function nowInZone(timeZone) {
  const now = new Date()
  if (timeZone) {
    try {
      const parts = new Intl.DateTimeFormat('en-CA', {
        timeZone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hourCycle: 'h23',
      }).formatToParts(now)
      const get = (type) => parts.find((part) => part.type === type)?.value
      return {
        day: `${get('year')}-${get('month')}-${get('day')}`,
        minutes: Number(get('hour')) * 60 + Number(get('minute')),
      }
    } catch {
      // неизвестный пояс — считаем по браузеру
    }
  }
  return {
    day: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
    minutes: now.getHours() * 60 + now.getMinutes(),
  }
}

/** Дни проведения 'YYYY-MM-DD' по порядку (плюс дни записей, оказавшихся вне дат проведения). */
export function eventDays(event) {
  const days = new Set()
  const start = dateKey(event.dateStart)
  const end = dateKey(event.dateEnd) || start
  // Ограничение на случай испорченных дат: не больше 60 дней.
  for (let day = start, guard = 0; day && day <= end && guard < 60; day = shiftDateKey(day, 1), guard += 1) {
    days.add(day)
  }
  for (const item of [...event.runs, ...event.commonEvents]) {
    const day = dateKey(item.dateLocal)
    if (day) days.add(day)
  }
  return [...days].sort()
}

const byName = (a, b) => a.name.localeCompare(b.name, 'ru', { numeric: true })

/**
 * Столбцы сетки: помещения площадки проведения, затем прочие помещения, занятые прогонами,
 * и «Без помещения» — если такие прогоны есть (или помещений нет вовсе).
 * @returns {{id:number, name:string, blackbox:boolean}[]}
 */
export function scheduleRooms(event) {
  const rooms = new Map()
  for (const room of [...event.venueRooms].sort(byName)) rooms.set(room.id, room)
  const extra = new Map()
  let hasNoRoom = false
  for (const run of event.runs) {
    if (!run.rooms.length) hasNoRoom = true
    for (const room of run.rooms) if (!rooms.has(room.id)) extra.set(room.id, room)
  }
  const list = [...rooms.values(), ...[...extra.values()].sort(byName)]
  if (hasNoRoom || !list.length) list.push({ id: NO_ROOM, name: 'Без помещения', blackbox: false })
  return list
}

const runDuration = (run) => run.duration || DEFAULT_RUN_DURATION
const commonDuration = (item) => item.duration || DEFAULT_COMMON_DURATION

/** Интервал записи в минутах от полуночи дня начала: {start, end}. */
export function runInterval(run) {
  const start = minutesOf(run.dateLocal)
  return { start, end: start + runDuration(run) }
}

/**
 * Конфликты по помещениям: прогоны одного дня, пересекающиеся по времени в общем помещении.
 * @returns {Map<number, {run: object, room: object}[]>} id прогона → с кем и где он пересекается
 */
export function findConflicts(runs) {
  const conflicts = new Map()
  const add = (run, other, room) => {
    if (!conflicts.has(run.id)) conflicts.set(run.id, [])
    conflicts.get(run.id).push({ run: other, room })
  }
  // Абсолютное время в минутах, чтобы учесть прогоны, переходящие через полночь.
  const span = (run) => {
    const parts = parseLocal(run.dateLocal)
    if (!parts) return null
    const start = Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute) / 60000
    return { start, end: start + runDuration(run) }
  }
  const items = runs.map((run) => ({ run, span: span(run) })).filter((item) => item.span && item.run.rooms.length)
  for (let i = 0; i < items.length; i += 1) {
    for (let j = i + 1; j < items.length; j += 1) {
      const a = items[i]
      const b = items[j]
      if (a.span.start >= b.span.end || b.span.start >= a.span.end) continue
      const room = a.run.rooms.find((candidate) => b.run.rooms.some((other) => other.id === candidate.id))
      if (!room) continue
      add(a.run, b.run, room)
      add(b.run, a.run, room)
    }
  }
  return conflicts
}

/**
 * Раскладка пересекающихся блоков одного столбца по «дорожкам», чтобы они не накладывались.
 * @param {{start:number, end:number}[]} items
 * @returns тот же массив, отсортированный по началу, с полями lane (с нуля) и lanes (всего в группе)
 */
export function assignLanes(items) {
  const sorted = [...items].sort((a, b) => a.start - b.start || a.end - b.end)
  let cluster = []
  let clusterEnd = -Infinity
  let laneEnds = []
  const flush = () => {
    for (const item of cluster) item.lanes = laneEnds.length
    cluster = []
    laneEnds = []
  }
  for (const item of sorted) {
    const visualEnd = Math.max(item.end, item.start + MIN_BLOCK_MINUTES)
    if (item.start >= clusterEnd) flush()
    let lane = laneEnds.findIndex((end) => end <= item.start)
    if (lane === -1) lane = laneEnds.length
    laneEnds[lane] = visualEnd
    item.lane = lane
    cluster.push(item)
    clusterEnd = Math.max(clusterEnd, visualEnd)
  }
  flush()
  return sorted
}

/**
 * Данные одного дня для сетки и списка.
 * @param {object} event   проведение с расписанием (eventsApi.schedule)
 * @param {string} day     'YYYY-MM-DD'
 * @param {object} options
 * @param {object[]} options.rooms    столбцы (scheduleRooms, возможно отфильтрованные)
 * @param {boolean} options.editable  в редакторе день не короче рабочих часов
 * @returns {{day, runs, commons, items, isEmpty, start, end, hours, columns, bands}}
 */
export function buildDay(event, day, { rooms, editable = false }) {
  const roomIds = new Set(rooms.map((room) => room.id))
  const inRooms = (run) =>
    run.rooms.length ? run.rooms.some((room) => roomIds.has(room.id)) : roomIds.has(NO_ROOM)
  const byStart = (a, b) => a.dateLocal.localeCompare(b.dateLocal) || a.id - b.id

  const runs = event.runs.filter((run) => dateKey(run.dateLocal) === day && inRooms(run)).sort(byStart)
  const commons = event.commonEvents.filter((item) => dateKey(item.dateLocal) === day).sort(byStart)

  const bands = commons.map((item) => {
    const start = minutesOf(item.dateLocal)
    return { item, start, end: start + commonDuration(item) }
  })
  const blocks = runs.map((run) => ({ run, ...runInterval(run) }))

  // Границы оси времени — по целым часам.
  const all = [...blocks, ...bands]
  let start = all.length ? Math.min(...all.map((item) => item.start)) : EDITOR_DAY_START
  let end = all.length
    ? Math.max(...all.map((item) => Math.max(item.end, item.start + MIN_BLOCK_MINUTES)))
    : EDITOR_DAY_END
  if (editable) {
    start = Math.min(start, EDITOR_DAY_START)
    end = Math.max(end, EDITOR_DAY_END)
  }
  start = Math.floor(start / 60) * 60
  end = Math.ceil(end / 60) * 60

  const hours = []
  for (let minute = start; minute < end; minute += 60) hours.push(minute)

  const columns = rooms.map((room) => ({
    room,
    blocks: assignLanes(
      blocks
        .filter(({ run }) =>
          room.id === NO_ROOM ? !run.rooms.length : run.rooms.some((candidate) => candidate.id === room.id),
        )
        .map((block) => ({ ...block })),
    ),
  }))

  // Список: всё вперемешку по времени начала, общие события — перед прогонами того же времени.
  const items = [
    ...bands.map((band) => ({ type: 'common', key: `c${band.item.id}`, ...band })),
    ...blocks.map((block) => ({ type: 'run', key: `r${block.run.id}`, item: block.run, start: block.start, end: block.end })),
  ].sort((a, b) => a.start - b.start || (a.type === b.type ? 0 : a.type === 'common' ? -1 : 1))

  return { day, runs, commons, items, isEmpty: !all.length, start, end, hours, columns, bands }
}

/** Положение блока в сетке: {top, height} в px относительно начала дня. */
export function blockBox(day, start, end) {
  const height = Math.max(end - start, MIN_BLOCK_MINUTES) * PX_PER_MINUTE
  return { top: (start - day.start) * PX_PER_MINUTE, height }
}

/**
 * Отметки прогона для текущего пользователя и состояние мест: [{key, tone, label}].
 * @param {object} run
 * @param {object} context
 * @param {Map<number, string>} [context.myRuns]  id прогона → статус моей заявки
 * @param {number|null} [context.userId]
 */
export function runBadges(run, { myRuns, userId } = {}) {
  const badges = []
  if (userId && run.masters.some((master) => master.id === userId)) {
    badges.push({ key: 'master', tone: 'accent', label: 'Вы мастер' })
  }
  const status = myRuns?.get(run.id)
  if (status === 'confirmed') badges.push({ key: 'mine', tone: 'success', label: 'Вы записаны' })
  else if (status === 'pending') badges.push({ key: 'mine', tone: 'warning', label: 'Заявка подана' })
  else if (status === 'waitlist') badges.push({ key: 'mine', tone: 'info', label: 'Вы в листе ожидания' })

  if (!isPast(run.date)) {
    if (!run.registrationOpen) badges.push({ key: 'closed', tone: 'neutral', label: 'Запись закрыта' })
    else if (run.isFull) badges.push({ key: 'full', tone: 'warning', label: 'Мест нет' })
  }
  return badges
}

/** «3/10» либо '' — если лимит неизвестен. */
export function runSeatsShort(run) {
  return run.effectiveMaxPlayers ? `${run.registeredCount}/${run.effectiveMaxPlayers}` : ''
}

export function runMastersLabel(run) {
  return run.masters.map((master) => master.displayName).join(', ')
}

export function runRoomsLabel(run) {
  return run.rooms.map((room) => room.name).join(', ')
}
