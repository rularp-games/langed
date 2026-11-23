import { api } from './client'
import { normalizeList, normalizePerson } from './normalize'

export const usersApi = {
  /**
   * Поиск пользователей по имени, фамилии или username (от 2 символов; только для вошедших).
   * @returns {Promise<Array<{id, username, displayName, email|null}>>} не более 10; email — только для staff
   */
  async search(query, options) {
    const q = String(query ?? '').trim()
    if (q.length < 2) return []
    return normalizeList(await api.get('/api/users/search/', { ...options, params: { q } }), normalizePerson)
  },
}
