import { isDatePast, isPast } from './datetime'
import { plural } from './format'

/**
 * Статусы заявок (на прогон и на проведение конвента): tone для AppBadge, label — нейтральная
 * подпись (для списков заявок), mine — подпись для самого участника.
 */
export const REGISTRATION_STATUSES = {
  pending: { tone: 'warning', label: 'Ожидает подтверждения', mine: 'Заявка на рассмотрении' },
  confirmed: { tone: 'success', label: 'Подтверждена', mine: 'Вы участвуете' },
  waitlist: { tone: 'info', label: 'Лист ожидания', mine: 'Вы в листе ожидания' },
  rejected: { tone: 'danger', label: 'Отклонена', mine: 'Заявка отклонена' },
  cancelled: { tone: 'neutral', label: 'Отменена', mine: 'Заявка отменена' },
}

export function registrationStatusMeta(status) {
  return REGISTRATION_STATUSES[status] ?? { tone: 'neutral', label: status || '', mine: status || '' }
}

/** Варианты предпочтения роли при записи на прогон. */
export const ROLE_PREFERENCES = [
  { value: 'any', label: 'Любая' },
  { value: 'female', label: 'Женская' },
  { value: 'male', label: 'Мужская' },
]

/**
 * Состояние записи на прогон: {key: past|closed|full|open, tone, label, canRegister}.
 * При full записаться можно — заявка попадёт в лист ожидания.
 */
export function runAvailability(run) {
  if (isPast(run.date)) return { key: 'past', tone: 'neutral', label: 'Прошёл', canRegister: false }
  if (!run.registrationOpen) return { key: 'closed', tone: 'neutral', label: 'Запись закрыта', canRegister: false }
  if (run.isFull) return { key: 'full', tone: 'warning', label: 'Мест нет', canRegister: true }
  return { key: 'open', tone: 'success', label: 'Запись открыта', canRegister: true }
}

/** «Занято 3 из 10» либо '' — если лимит неизвестен. */
export function runSeatsLabel(run) {
  if (!run.effectiveMaxPlayers) return ''
  return `Занято ${run.registeredCount} из ${run.effectiveMaxPlayers}`
}

/** Состояние регистрации на проведение конвента: {key: past|closed|full|open, tone, label, canRegister}. */
export function eventAvailability(event) {
  if (isDatePast(event.dateEnd, { timeZone: event.cityTimezone })) {
    return { key: 'past', tone: 'neutral', label: 'Завершён', canRegister: false }
  }
  if (!event.registrationOpen) {
    return { key: 'closed', tone: 'neutral', label: 'Регистрация закрыта', canRegister: false }
  }
  if (event.isFull) return { key: 'full', tone: 'warning', label: 'Мест нет', canRegister: false }
  return { key: 'open', tone: 'success', label: 'Регистрация открыта', canRegister: true }
}

/** «Осталось 12 мест» либо '' — если проведение без ограничения. */
export function eventSeatsLabel(event) {
  if (event.availableSlots === null || event.availableSlots === undefined) return ''
  const n = event.availableSlots
  return `Осталось ${n} ${plural(n, ['место', 'места', 'мест'])}`
}
