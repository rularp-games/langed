import { computed } from 'vue'
import { eventsApi } from '@/api/events'
import { runsApi } from '@/api/runs'
import { useAsyncData } from '@/composables/useAsyncData'
import { useAuthStore } from '@/stores/auth'

/**
 * Проведение с расписанием и отметками текущего пользователя.
 *   const { event, error, reload, myRuns, userId } = useEventSchedule(() => props.id)
 * myRuns: Map id прогона → статус моей заявки (pending | confirmed | waitlist).
 */
export function useEventSchedule(id) {
  const auth = useAuthStore()

  const { data: event, error, loading, reload } = useAsyncData((signal) => eventsApi.schedule(id(), { signal }), {
    watch: id,
  })

  // В расписании нет моих заявок на прогоны — берём их отдельным запросом (только вошедшим).
  const { data: mine, reload: reloadMine } = useAsyncData(
    (signal) =>
      auth.isAuthenticated
        ? runsApi.list({ event: id(), mine: true, time: 'all', pageSize: 100 }, { signal })
        : Promise.resolve(null),
    { watch: id },
  )

  const myRuns = computed(() => {
    const map = new Map()
    for (const run of mine.value?.items ?? []) {
      const status = run.myRegistration?.status
      if (status && status !== 'cancelled') map.set(run.id, status)
    }
    return map
  })
  const userId = computed(() => auth.user?.id ?? null)

  return {
    event,
    error,
    loading,
    myRuns,
    userId,
    reload: () => Promise.all([reload(), reloadMine()]),
  }
}
