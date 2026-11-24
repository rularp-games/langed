/**
 * Общие нормализаторы ответов backend → объекты интерфейса (camelCase).
 * Каждый принимает «сырой» объект и терпимо относится к отсутствующим полям:
 * один и тот же ресурс backend отдаёт в полном, списочном и кратком виде.
 */

/**
 * Адрес файла из /media/. Backend отдаёт абсолютный URL, собранный по заголовкам запроса;
 * за прокси в нём может оказаться не тот хост или схема, поэтому оставляем только путь.
 */
export function mediaPath(url) {
  if (!url) return null
  const match = String(url).match(/^https?:\/\/[^/]+(\/media\/.*)$/)
  return match ? match[1] : url
}

/** Ответ списка: {count, next, previous, results} либо простой массив → {count, hasNext, hasPrevious, items}. */
export function normalizePage(data, normalizeItem) {
  const results = Array.isArray(data) ? data : (data?.results ?? [])
  return {
    count: Array.isArray(data) ? data.length : (data?.count ?? results.length),
    hasNext: Boolean(data?.next),
    hasPrevious: Boolean(data?.previous),
    items: results.map(normalizeItem),
  }
}

export function normalizeList(data, normalizeItem) {
  return normalizePage(data, normalizeItem).items
}

/** Человек: {id, displayName, username|null, email|null}. username есть только в заявках и поиске. */
export function normalizePerson(raw) {
  if (!raw) return null
  return {
    id: raw.id,
    displayName: raw.display_name || raw.username || 'Без имени',
    username: raw.username ?? null,
    email: raw.email ?? null,
  }
}

export function normalizePeople(list) {
  return (list ?? []).map(normalizePerson)
}

/** Город: {id, name, timezone, region: {id, name}|null}. */
export function normalizeCity(raw) {
  if (!raw) return null
  return {
    id: raw.id,
    name: raw.name ?? '',
    timezone: raw.timezone ?? null,
    region: raw.region ? { id: raw.region.id, name: raw.region.name } : null,
  }
}

/** Помещение: {id, name, blackbox, venueId, venueName|null}. */
export function normalizeRoom(raw) {
  return {
    id: raw.id,
    name: raw.name ?? '',
    blackbox: Boolean(raw.blackbox),
    venueId: raw.venue_id ?? null,
    venueName: raw.venue_name ?? null,
  }
}

/** Площадка кратко: {id, name, address}. */
export function normalizeVenueBrief(raw) {
  if (!raw) return null
  return { id: raw.id, name: raw.name ?? '', address: raw.address ?? '' }
}

/**
 * Игра: полный, списочный и краткие виды.
 * {id, name, kind, poster, playersMin, playersMax, femaleRolesMin, femaleRolesMax, maleRolesMin,
 *  maleRolesMax, technicians, creators[], authorsText, sourceUrl, ageRating, announcementExcerpt,
 *  announcement, redFlags, canEdit, createdAt, updatedAt}
 * Числа состава: null — не указано. authorsText — авторы, не зарегистрированные на портале
 * (свободный текст, может содержать ссылки). kind — larp (КРИ), ttrpg (НРИ), other (другое).
 * ageRating — 0+, 6+, 12+, 16+, 18+; '' — не указан.
 */
export function normalizeGame(raw) {
  if (!raw) return null
  return {
    id: raw.id,
    name: raw.name ?? '',
    kind: raw.kind ?? 'larp',
    poster: mediaPath(raw.poster ?? raw.poster_url ?? null),
    playersMin: raw.players_min ?? null,
    playersMax: raw.players_max ?? null,
    femaleRolesMin: raw.female_roles_min ?? null,
    femaleRolesMax: raw.female_roles_max ?? null,
    maleRolesMin: raw.male_roles_min ?? null,
    maleRolesMax: raw.male_roles_max ?? null,
    technicians: raw.technicians ?? null,
    creators: normalizePeople(raw.creators),
    authorsText: raw.authors_text ?? '',
    sourceUrl: raw.source_url ?? '',
    ageRating: raw.age_rating ?? '',
    announcementExcerpt: raw.announcement_excerpt ?? '',
    announcement: raw.announcement ?? '',
    redFlags: raw.red_flags ?? '',
    canEdit: Boolean(raw.can_edit),
    createdAt: raw.created_at ?? null,
    updatedAt: raw.updated_at ?? null,
  }
}

/**
 * Заявка на прогон.
 * {id, user, rolePreference: any|female|male, rolePreferenceLabel, isTechnician,
 *  status: pending|confirmed|rejected|cancelled|waitlist, statusLabel, comment, createdAt, updatedAt}
 */
export function normalizeRunRegistration(raw) {
  if (!raw) return null
  return {
    id: raw.id,
    user: normalizePerson(raw.user),
    rolePreference: raw.role_preference ?? 'any',
    rolePreferenceLabel: raw.role_preference_display ?? '',
    isTechnician: Boolean(raw.is_technician),
    status: raw.status,
    statusLabel: raw.status_display ?? '',
    comment: raw.comment ?? '',
    createdAt: raw.created_at ?? null,
    updatedAt: raw.updated_at ?? null,
  }
}

/**
 * Заявка на проведение конвента.
 * {id, user, status: pending|confirmed|rejected|cancelled, statusLabel, comment, adminComment,
 *  createdAt, updatedAt}
 */
export function normalizeEventRegistration(raw) {
  if (!raw) return null
  return {
    id: raw.id,
    user: normalizePerson(raw.user),
    status: raw.status,
    statusLabel: raw.status_display ?? '',
    comment: raw.comment ?? '',
    adminComment: raw.admin_comment ?? '',
    createdAt: raw.created_at ?? null,
    updatedAt: raw.updated_at ?? null,
  }
}

/**
 * Прогон: списочный, полный и вид из расписания конвента.
 * {id, game, masters[], date (UTC, ISO с Z), dateLocal (время города, без пояса), duration (мин),
 *  cityId, cityName, cityTimezone, rooms[], venueName, eventId, conventionName,
 *  maxPlayers (собственный лимит прогона или null), effectiveMaxPlayers, registrationOpen,
 *  registeredCount, availableSlots, isFull, myRegistration, registrations (массив только для
 *  управляющих заявками, иначе null), canEdit, canManageRegistrations, createdAt, updatedAt}
 * В расписании нет cityId/cityName/venueName/eventId/conventionName/myRegistration (null).
 */
export function normalizeRun(raw) {
  if (!raw) return null
  return {
    id: raw.id,
    game: normalizeGame(raw.game),
    masters: normalizePeople(raw.masters),
    date: raw.date ?? null,
    dateLocal: raw.date_local ?? null,
    duration: raw.duration ?? null,
    cityId: raw.city_id ?? null,
    cityName: typeof raw.city === 'string' ? raw.city : null,
    cityTimezone: raw.city_timezone ?? null,
    rooms: (raw.rooms ?? []).map(normalizeRoom),
    venueName: raw.venue_name ?? null,
    eventId: raw.convention_event ?? null,
    conventionName: raw.convention_name ?? null,
    maxPlayers: raw.max_players ?? null,
    effectiveMaxPlayers: raw.effective_max_players ?? null,
    registrationOpen: Boolean(raw.registration_open),
    registeredCount: raw.registered_count ?? 0,
    availableSlots: raw.available_slots ?? null,
    isFull: Boolean(raw.is_full),
    myRegistration: normalizeRunRegistration(raw.current_user_registration),
    registrations: Array.isArray(raw.registrations) ? raw.registrations.map(normalizeRunRegistration) : null,
    canEdit: Boolean(raw.can_edit),
    canManageRegistrations: Boolean(raw.can_manage_registrations),
    createdAt: raw.created_at ?? null,
    updatedAt: raw.updated_at ?? null,
  }
}

/** Ссылка конвента: {id, conventionId, url, type: vk|telegram|website|discord|youtube|other, typeLabel, title, displayTitle}. */
export function normalizeLink(raw) {
  return {
    id: raw.id,
    conventionId: raw.convention_id ?? null,
    url: raw.url ?? '',
    type: raw.link_type ?? 'other',
    typeLabel: raw.link_type_display ?? '',
    title: raw.title ?? '',
    displayTitle: raw.display_title || raw.title || raw.link_type_display || raw.url || '',
  }
}

/** Убирает из объекта ключи со значением undefined (для PATCH: шлём только заданное). */
export function compact(object) {
  return Object.fromEntries(Object.entries(object).filter(([, value]) => value !== undefined))
}

/** FormData с одним файлом для import_csv. */
export function fileForm(file, field = 'file') {
  const form = new FormData()
  form.append(field, file)
  return form
}
