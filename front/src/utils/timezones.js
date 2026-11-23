/**
 * Часовые пояса городов. Список совпадает с City.TIMEZONE_CHOICES на backend:
 * другие значения он не примет.
 */
export const TIMEZONES = [
  { value: 'Europe/Kaliningrad', label: 'UTC+2 (МСК−1) — Калининград' },
  { value: 'Europe/Moscow', label: 'UTC+3 (МСК) — Москва, Санкт-Петербург, Минск' },
  { value: 'Europe/Samara', label: 'UTC+4 (МСК+1) — Самара, Ижевск, Тбилиси, Ереван, Баку' },
  { value: 'Asia/Yekaterinburg', label: 'UTC+5 (МСК+2) — Екатеринбург, Уфа, Алматы, Ташкент' },
  { value: 'Asia/Omsk', label: 'UTC+6 (МСК+3) — Омск, Бишкек' },
  { value: 'Asia/Krasnoyarsk', label: 'UTC+7 (МСК+4) — Красноярск, Новосибирск, Томск' },
  { value: 'Asia/Irkutsk', label: 'UTC+8 (МСК+5) — Иркутск, Улан-Удэ' },
  { value: 'Asia/Yakutsk', label: 'UTC+9 (МСК+6) — Якутск, Чита' },
  { value: 'Asia/Vladivostok', label: 'UTC+10 (МСК+7) — Владивосток, Хабаровск' },
  { value: 'Asia/Magadan', label: 'UTC+11 (МСК+8) — Магадан, Южно-Сахалинск' },
  { value: 'Asia/Kamchatka', label: 'UTC+12 (МСК+9) — Петропавловск-Камчатский' },
]
export const DEFAULT_TIMEZONE = 'Europe/Moscow'

/** Короткая подпись пояса: 'Asia/Omsk' → 'UTC+6 (МСК+3)'. */
export function timezoneLabel(value) {
  const label = TIMEZONES.find((item) => item.value === value)?.label
  return label ? label.split(' — ')[0] : value || ''
}
