import { formatRange } from './format'

/**
 * Заполненные параметры игры для карточки и страницы: [{ key, label, value }].
 * Незаполненные (0–0, пусто) не попадают в список.
 */
export function gameFacts(game) {
  return [
    { key: 'players', label: 'Игроки', value: formatRange(game.playersMin, game.playersMax) },
    { key: 'female', label: 'Женские роли', short: 'Жен. роли', value: formatRange(game.femaleRolesMin, game.femaleRolesMax) },
    { key: 'male', label: 'Мужские роли', short: 'Муж. роли', value: formatRange(game.maleRolesMin, game.maleRolesMax) },
    { key: 'technicians', label: 'Игротехники', value: Number(game.technicians) > 0 ? String(game.technicians) : null },
  ].filter((fact) => fact.value !== null)
}
