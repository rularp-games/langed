import { defineStore } from 'pinia'
import { computed, shallowRef } from 'vue'
import { citiesApi } from '@/api/cities'

/**
 * Справочник городов: загружается один раз за сеанс.
 *   const cities = useCitiesStore(); cities.load()   // Promise<City[]>, повторные вызовы — из кэша
 *   cities.items, cities.byId(3)
 */
export const useCitiesStore = defineStore('cities', () => {
  const items = shallowRef([])
  const loaded = shallowRef(false)
  const error = shallowRef(null)
  let pending = null

  function load({ force = false } = {}) {
    if (force) pending = null
    pending ??= citiesApi
      .list()
      .then((list) => {
        items.value = list
        loaded.value = true
        error.value = null
        return list
      })
      .catch((err) => {
        pending = null
        error.value = err
        throw err
      })
    return pending
  }

  const index = computed(() => new Map(items.value.map((city) => [city.id, city])))
  const byId = (id) => index.value.get(Number(id)) ?? null

  /** Добавляет только что созданный город в кэш. */
  function add(city) {
    items.value = [...items.value, city].sort((a, b) => a.name.localeCompare(b.name, 'ru'))
  }

  /** Заменяет изменённый город в кэше. */
  function replace(city) {
    items.value = items.value
      .map((item) => (item.id === city.id ? city : item))
      .sort((a, b) => a.name.localeCompare(b.name, 'ru'))
  }

  return { items, loaded, error, load, byId, add, replace }
})
