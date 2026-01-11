<template>
  <div class="schedule-page">
    <!-- Загрузка -->
    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>Загрузка расписания...</p>
    </div>

    <!-- Ошибка -->
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="fetchSchedule" class="retry-btn">Повторить</button>
    </div>

    <!-- Расписание -->
    <template v-else-if="schedule">
      <!-- Шапка конвента -->
      <div class="schedule-header">
        <div class="convention-info">
          <h1 class="convention-title">{{ schedule.convention_name }}</h1>
          <div class="convention-meta">
            <span class="convention-dates">
              📅 {{ formatDates(schedule.date_start, schedule.date_end) }}
            </span>
            <span class="convention-city">
              📍 {{ schedule.city_name }}
            </span>
            <span v-if="schedule.venue_name" class="convention-venue">
              🏢 {{ schedule.venue_name }}
            </span>
          </div>
          <p v-if="schedule.convention_description" class="convention-description">
            {{ schedule.convention_description }}
          </p>
        </div>
        
        <div class="header-actions">
          <router-link 
            v-if="schedule.can_edit"
            :to="`/schedule/${eventId}/edit`"
            class="edit-schedule-btn"
          >
            ✏️ Редактировать расписание
          </router-link>
          <router-link to="/conventions" class="back-link">
            ← К конвентам
          </router-link>
          <button @click="copyLink" class="copy-link-btn" :title="linkCopied ? 'Скопировано!' : 'Скопировать ссылку'">
            {{ linkCopied ? '✓' : '🔗' }}
          </button>
        </div>
      </div>

      <!-- Ссылки конвента -->
      <div v-if="schedule.links && schedule.links.length > 0" class="convention-links">
        <a 
          v-for="link in schedule.links" 
          :key="link.id"
          :href="link.url"
          target="_blank"
          rel="noopener noreferrer"
          class="link-item"
          :class="'link-type-' + link.link_type"
        >
          <span class="link-icon">{{ getLinkIcon(link.link_type) }}</span>
          <span class="link-title">{{ link.display_title }}</span>
        </a>
      </div>

      <!-- Статус регистрации на конвент (если есть) -->
      <div v-if="schedule.current_user_registration" class="user-registration-bar">
        <span v-if="schedule.current_user_registration.status === 'pending'" class="reg-status reg-pending">
          ⏳ Ваша заявка на участие ожидает подтверждения
        </span>
        <span v-else-if="schedule.current_user_registration.status === 'confirmed'" class="reg-status reg-confirmed">
          ✅ Вы — участник конвента
        </span>
        <span v-else-if="schedule.current_user_registration.status === 'rejected'" class="reg-status reg-rejected">
          ❌ Ваша заявка отклонена
        </span>
      </div>

      <!-- Фильтры -->
      <div class="schedule-controls">
        <div class="view-switcher">
          <button 
            :class="{ active: viewMode === 'timeline' }"
            @click="viewMode = 'timeline'"
          >
            Таймлайн
          </button>
          <button 
            :class="{ active: viewMode === 'list' }"
            @click="viewMode = 'list'"
          >
            Список
          </button>
        </div>
        
        <div class="filter-controls">
          <select v-model="selectedDay" class="control-select">
            <option value="">Все дни</option>
            <option v-for="day in days" :key="day" :value="day">
              {{ formatDayOption(day) }}
            </option>
          </select>
          
          <select v-model="selectedRoom" class="control-select">
            <option value="">Все помещения</option>
            <option v-for="room in allRooms" :key="room.id" :value="room.id">
              {{ room.name }}
            </option>
          </select>
        </div>
      </div>

      <!-- Пустое расписание -->
      <div v-if="filteredRuns.length === 0 && filteredCommonEvents.length === 0" class="empty-schedule">
        <p v-if="schedule.runs.length === 0 && (!schedule.common_events || schedule.common_events.length === 0)">Расписание пока пусто</p>
        <p v-else>Нет событий по выбранным фильтрам</p>
      </div>

      <!-- Таймлайн -->
      <div v-else-if="viewMode === 'timeline'" class="timeline-view">
        <div v-for="day in filteredDays" :key="day" class="timeline-day">
          <div class="timeline-day-header">
            <span class="day-name">{{ formatDayName(day) }}</span>
            <span class="day-date">{{ formatDayDate(day) }}</span>
          </div>
          
          <div class="timeline-content">
            <!-- Шкала времени -->
            <div class="timeline-scale" :class="{ 'with-headers': allRooms.length > 0 }" :style="{ height: getTimelineHeightForDay(day) + 'px' }">
              <div 
                v-for="hour in getTimelineHoursForDay(day)" 
                :key="hour"
                class="timeline-hour"
                :style="{ top: getHourPosition(hour, day) + 'px' }"
              >
                {{ formatHour(hour) }}
              </div>
            </div>
            
            <!-- Прогоны по помещениям -->
            <div class="timeline-rooms">
              <!-- Заголовки помещений (выровнены по высоте) -->
              <div class="timeline-rooms-headers" v-if="allRooms.length > 0">
                <div 
                  v-for="room in getRoomsForDay(day)" 
                  :key="'header-' + (room.id || 'no-room')"
                  class="room-header"
                >
                  {{ room.name || 'Без помещения' }}
                </div>
              </div>
              <!-- Контейнер для колонок с прогонами и общих событий -->
              <div class="timeline-rooms-content" :class="{ 'no-rooms': allRooms.length === 0 }" :style="{ height: getTimelineHeightForDay(day) + 'px' }">
                <!-- Общие события (на всю ширину) -->
                <div 
                  v-for="commonEvent in getCommonEventsForDay(day)" 
                  :key="'common-' + commonEvent.id"
                  class="timeline-common-event"
                  :style="getCommonEventStyle(commonEvent, day)"
                  @click="openCommonEventModal(commonEvent)"
                >
                  <div class="common-event-time">{{ formatTime(commonEvent.date_local || commonEvent.date) }}</div>
                  <div class="common-event-name">{{ commonEvent.name }}</div>
                </div>
                <!-- Колонки с прогонами -->
                <div class="timeline-rooms-columns">
                  <div 
                    v-for="room in getRoomsForDay(day)" 
                    :key="room.id || 'no-room'"
                    class="timeline-room"
                  >
                    <div class="room-runs" :style="{ height: getTimelineHeightForDay(day) + 'px' }">
                      <div 
                        v-for="run in getRunsForDayRoom(day, room.id)" 
                        :key="run.id"
                        class="timeline-run"
                        :style="getRunStyle(run, day)"
                        :class="{ 'run-full': run.is_full }"
                        @click="openRunModal(run)"
                      >
                        <div class="run-time">{{ formatTime(run.date_local || run.date) }}</div>
                        <div class="run-name">{{ run.game_name }}</div>
                        <div class="run-info">
                          <span class="run-slots">
                            {{ run.registered_count }}/{{ run.effective_max_players }}
                          </span>
                          <span v-if="run.is_full" class="run-full-badge">МЕСТ НЕТ</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Список -->
      <div v-else-if="viewMode === 'list'" class="list-view">
        <div v-for="day in filteredDays" :key="day" class="list-day">
          <div class="list-day-header">
            <span class="day-name">{{ formatDayName(day) }}</span>
            <span class="day-date">{{ formatDayDate(day) }}</span>
          </div>
          
          <div class="list-runs">
            <!-- Общие события и прогоны, отсортированные по времени -->
            <template v-for="item in getItemsForDaySorted(day)" :key="item.type + '-' + item.id">
              <!-- Общее событие -->
              <div 
                v-if="item.type === 'common'"
                class="list-common-event"
                @click="openCommonEventModal(item)"
              >
                <div class="run-time-col">
                  <span class="run-time common-time">{{ formatTime(item.date_local || item.date) }}</span>
                  <span class="run-duration">{{ formatDuration(item.duration) }}</span>
                </div>
                <div class="run-main-col">
                  <div class="run-name">{{ item.name }}</div>
                  <div class="common-event-label">📢 Общее событие</div>
                </div>
              </div>
              <!-- Прогон -->
              <div 
                v-else
                class="list-run"
                :class="{ 'run-full': item.is_full }"
                @click="openRunModal(item)"
              >
                <div class="run-time-col">
                  <span class="run-time">{{ formatTime(item.date_local || item.date) }}</span>
                  <span class="run-duration">{{ formatDuration(item.duration) }}</span>
                </div>
                <div class="run-main-col">
                  <div class="run-name">{{ item.game_name }}</div>
                  <div class="run-rooms" v-if="item.rooms && item.rooms.length">📍 {{ item.rooms.map(r => r.name).join(', ') }}</div>
                  <div class="run-masters" v-if="item.masters && item.masters.length">
                    👤 {{ item.masters.map(m => m.display_name).join(', ') }}
                  </div>
                </div>
                <div class="run-slots-col">
                  <span class="run-slots" :class="{ 'slots-full': item.is_full }">
                    {{ item.registered_count }}/{{ item.effective_max_players }}
                  </span>
                  <span v-if="item.is_full" class="run-full-badge">МЕСТ НЕТ</span>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </template>

    <!-- Модальное окно прогона -->
    <div v-if="selectedRun" class="modal-overlay" @click.self="closeRunModal">
      <div class="modal-content run-modal">
        <button class="modal-close" @click="closeRunModal">×</button>
        
        <div class="modal-run-date">
          {{ formatFullDate(selectedRun.date_local || selectedRun.date) }}
          <span class="modal-run-time">{{ formatTime(selectedRun.date_local || selectedRun.date) }}</span>
        </div>
        
        <h2>{{ selectedRun.game_name }}</h2>
        
        <div class="modal-rooms" v-if="selectedRun.rooms && selectedRun.rooms.length">
          📍 {{ selectedRun.rooms.map(r => r.name).join(', ') }}
        </div>
        
        <div class="modal-section" v-if="selectedRun.masters && selectedRun.masters.length > 0">
          <h3>{{ selectedRun.masters.length > 1 ? 'Мастера' : 'Мастер' }}</h3>
          <div class="masters-list">
            <span v-for="master in selectedRun.masters" :key="master.id" class="master-item">
              👤 {{ master.display_name }}
            </span>
          </div>
        </div>
        
        <div class="modal-stats">
          <div class="modal-stat">
            <span class="modal-stat-label">Записано</span>
            <span class="modal-stat-value" :class="{ 'full': selectedRun.is_full }">
              {{ selectedRun.registered_count }} / {{ selectedRun.effective_max_players }}
            </span>
          </div>
          <div class="modal-stat">
            <span class="modal-stat-label">Длительность</span>
            <span class="modal-stat-value">{{ formatDuration(selectedRun.duration) }}</span>
          </div>
          <div class="modal-stat" v-if="selectedRun.game">
            <span class="modal-stat-label">Игроки</span>
            <span class="modal-stat-value">{{ selectedRun.game.players_min }} – {{ selectedRun.game.players_max }}</span>
          </div>
        </div>
        
        <div class="modal-actions">
          <a :href="`/?run=${selectedRun.id}`" class="btn btn-primary">
            Подробнее / Записаться
          </a>
        </div>
      </div>
    </div>

    <!-- Модальное окно общего события -->
    <div v-if="selectedCommonEvent" class="modal-overlay" @click.self="closeCommonEventModal">
      <div class="modal-content common-event-modal">
        <button class="modal-close" @click="closeCommonEventModal">×</button>
        
        <div class="modal-run-date">
          {{ formatFullDate(selectedCommonEvent.date_local || selectedCommonEvent.date) }}
          <span class="modal-run-time">{{ formatTime(selectedCommonEvent.date_local || selectedCommonEvent.date) }}</span>
        </div>
        
        <h2>{{ selectedCommonEvent.name }}</h2>
        
        <div class="common-event-badge">Общее событие</div>
        
        <div class="modal-stats">
          <div class="modal-stat">
            <span class="modal-stat-label">Длительность</span>
            <span class="modal-stat-value">{{ formatDuration(selectedCommonEvent.duration) }}</span>
          </div>
        </div>
        
        <div v-if="selectedCommonEvent.description" class="common-event-description">
          {{ selectedCommonEvent.description }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConventionSchedule',
  props: {
    eventId: {
      type: [String, Number],
      required: true
    }
  },
  emits: ['edit', 'close'],
  data() {
    return {
      schedule: null,
      loading: true,
      error: null,
      viewMode: 'timeline',
      selectedDay: '',
      selectedRoom: '',
      selectedRun: null,
      selectedCommonEvent: null,
      linkCopied: false,
      timelineStartHour: 9,
      timelineEndHour: 24,
      hourHeight: 60
    }
  },
  computed: {
    days() {
      if (!this.schedule) return []
      const daysSet = new Set()
      
      // Дни из прогонов
      if (this.schedule.runs) {
        this.schedule.runs.forEach(run => {
          const dateStr = run.date_local || run.date
          const day = dateStr.split('T')[0]
          daysSet.add(day)
        })
      }
      
      // Дни из общих событий
      if (this.schedule.common_events) {
        this.schedule.common_events.forEach(event => {
          const dateStr = event.date_local || event.date
          const day = dateStr.split('T')[0]
          daysSet.add(day)
        })
      }
      
      return Array.from(daysSet).sort()
    },
    filteredDays() {
      if (this.selectedDay) {
        return [this.selectedDay]
      }
      return this.days
    },
    filteredRuns() {
      if (!this.schedule || !this.schedule.runs) return []
      let runs = this.schedule.runs
      
      if (this.selectedDay) {
        runs = runs.filter(run => {
          const dateStr = run.date_local || run.date
          return dateStr.startsWith(this.selectedDay)
        })
      }
      
      if (this.selectedRoom) {
        runs = runs.filter(run => {
          return run.rooms && run.rooms.some(r => r.id === this.selectedRoom)
        })
      }
      
      // Сортируем по локальной дате
      return runs.sort((a, b) => {
        const dateA = a.date_local || a.date
        const dateB = b.date_local || b.date
        return dateA.localeCompare(dateB)
      })
    },
    filteredCommonEvents() {
      if (!this.schedule || !this.schedule.common_events) return []
      let events = this.schedule.common_events
      
      if (this.selectedDay) {
        events = events.filter(event => {
          const dateStr = event.date_local || event.date
          return dateStr.startsWith(this.selectedDay)
        })
      }
      
      // Сортируем по локальной дате
      return events.sort((a, b) => {
        const dateA = a.date_local || a.date
        const dateB = b.date_local || b.date
        return dateA.localeCompare(dateB)
      })
    },
    // timelineHours теперь вычисляется динамически в getTimelineHoursForDay
    allRooms() {
      if (!this.schedule) return []
      
      // Если у конвента указана площадка с комнатами, используем их
      if (this.schedule.venue_rooms && this.schedule.venue_rooms.length > 0) {
        return [...this.schedule.venue_rooms].sort((a, b) => 
          (a.name || '').localeCompare(b.name || '', 'ru')
        )
      }
      
      // Иначе собираем уникальные помещения из прогонов
      if (!this.schedule.runs) return []
      const roomsMap = new Map()
      let hasNoRoom = false
      
      this.schedule.runs.forEach(run => {
        if (run.rooms && run.rooms.length > 0) {
          run.rooms.forEach(room => {
            if (!roomsMap.has(room.id)) {
              roomsMap.set(room.id, room)
            }
          })
        } else {
          hasNoRoom = true
        }
      })
      
      // Сортируем по имени
      const rooms = Array.from(roomsMap.values()).sort((a, b) => 
        (a.name || '').localeCompare(b.name || '', 'ru')
      )
      
      // "Без помещения" добавляем в конец
      if (hasNoRoom) {
        rooms.push({ id: null, name: 'Без помещения' })
      }
      
      return rooms
    }
  },
  mounted() {
    this.fetchSchedule()
  },
  watch: {
    eventId() {
      this.fetchSchedule()
    }
  },
  methods: {
    async fetchSchedule() {
      this.loading = true
      this.error = null
      
      try {
        const response = await fetch(`/api/convention-events/${this.eventId}/schedule/`)
        if (!response.ok) {
          throw new Error('Ошибка загрузки расписания')
        }
        this.schedule = await response.json()
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    },
    
    formatDateDDMMYYYY(date) {
      const d = new Date(date)
      const day = String(d.getDate()).padStart(2, '0')
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const year = d.getFullYear()
      return `${day}/${month}/${year}`
    },
    
    formatDates(start, end) {
      return `${this.formatDateDDMMYYYY(start)} — ${this.formatDateDDMMYYYY(end)}`
    },
    
    formatDayOption(day) {
      const date = new Date(day)
      const weekday = date.toLocaleDateString('ru-RU', { weekday: 'short' })
      return `${weekday}, ${this.formatDateDDMMYYYY(day)}`
    },
    
    formatDayName(day) {
      const date = new Date(day)
      return date.toLocaleDateString('ru-RU', { weekday: 'long' })
    },
    
    formatDayDate(day) {
      return this.formatDateDDMMYYYY(day)
    },
    
    formatTime(dateStr) {
      // dateStr может быть date_local (без таймзоны) или date (ISO с Z)
      if (dateStr && !dateStr.endsWith('Z') && !dateStr.includes('+')) {
        // Локальная дата без таймзоны - парсим напрямую
        const parts = dateStr.split('T')
        if (parts.length === 2) {
          return parts[1].slice(0, 5)
        }
      }
      const date = new Date(dateStr)
      return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    },
    
    formatFullDate(dateStr) {
      // Для локальной даты используем простой парсинг
      let date
      if (dateStr && !dateStr.endsWith('Z') && !dateStr.includes('+')) {
        const parts = dateStr.split('T')
        if (parts.length >= 1) {
          date = new Date(parts[0] + 'T12:00:00')
        }
      } else {
        date = new Date(dateStr)
      }
      const weekday = date.toLocaleDateString('ru-RU', { weekday: 'long' })
      return `${weekday}, ${this.formatDateDDMMYYYY(date)}`
    },
    
    // Получить локальную дату прогона
    getRunLocalDate(run) {
      return run.date_local || run.date
    },
    
    formatDuration(minutes) {
      if (!minutes) return ''
      const hours = Math.floor(minutes / 60)
      const mins = minutes % 60
      if (hours === 0) return `${mins} мин`
      if (mins === 0) return `${hours} ч`
      return `${hours} ч ${mins} мин`
    },
    
    formatHour(hour) {
      // Если час >= 24, показываем как время следующего дня (24:00 -> 00:00, 25:00 -> 01:00 и т.д.)
      const displayHour = hour >= 24 ? hour - 24 : hour
      const suffix = hour >= 24 ? ' +1' : ''
      return `${displayHour.toString().padStart(2, '0')}:00${suffix}`
    },
    
    getLinkIcon(linkType) {
      const icons = {
        'vk': '📱',
        'telegram': '💬',
        'website': '🌐',
        'discord': '🎮',
        'youtube': '▶️',
        'other': '🔗'
      }
      return icons[linkType] || '🔗'
    },
    
    getHourPosition(hour, day) {
      const timeRange = this.getTimeRangeForDay(day)
      return (hour - timeRange.startHour) * this.hourHeight
    },
    
    getTimeRangeForDay(day) {
      const runs = this.getRunsForDay(day)
      const commonEvents = this.getCommonEventsForDay(day)
      
      if (runs.length === 0 && commonEvents.length === 0) {
        return { startHour: 9, endHour: 24 }
      }
      
      let minHour = 24
      let maxHour = 0
      
      // Обрабатываем прогоны
      runs.forEach(run => {
        const dateStr = this.getRunLocalDate(run)
        if (dateStr) {
          const parts = dateStr.split('T')
          if (parts.length === 2) {
            const timeParts = parts[1].split(':')
            const startHour = parseInt(timeParts[0], 10)
            // Вычисляем час окончания, позволяя переход за полночь (> 24)
            const endHour = startHour + Math.ceil((run.duration || 60) / 60)
            
            minHour = Math.min(minHour, startHour)
            maxHour = Math.max(maxHour, endHour)
          }
        }
      })
      
      // Обрабатываем общие события
      commonEvents.forEach(event => {
        const dateStr = event.date_local || event.date
        if (dateStr) {
          const parts = dateStr.split('T')
          if (parts.length === 2) {
            const timeParts = parts[1].split(':')
            const startHour = parseInt(timeParts[0], 10)
            const endHour = startHour + Math.ceil((event.duration || 60) / 60)
            
            minHour = Math.min(minHour, startHour)
            maxHour = Math.max(maxHour, endHour)
          }
        }
      })
      
      // Не ограничиваем endHour до 24, чтобы игры, переходящие на следующий день, отображались корректно
      return { 
        startHour: Math.max(0, minHour), 
        endHour: maxHour 
      }
    },
    
    getTimelineHoursForDay(day) {
      const timeRange = this.getTimeRangeForDay(day)
      const hours = []
      for (let h = timeRange.startHour; h <= timeRange.endHour; h++) {
        hours.push(h)
      }
      return hours
    },
    
    getTimelineHeightForDay(day) {
      const timeRange = this.getTimeRangeForDay(day)
      return (timeRange.endHour - timeRange.startHour) * this.hourHeight
    },
    
    // eslint-disable-next-line no-unused-vars
    getRoomsForDay(day) {
      // Возвращаем все помещения из всех дней (чтобы столбцы были одинаковыми)
      // Помещения уже отсортированы по алфавиту в allRooms
      return this.allRooms
    },
    
    getRunsForDay(day) {
      return this.filteredRuns.filter(run => {
        const dateStr = this.getRunLocalDate(run)
        return dateStr && dateStr.startsWith(day)
      })
    },
    
    getItemsForDaySorted(day) {
      // Объединяем прогоны и общие события, сортируем по времени
      const runs = this.getRunsForDay(day).map(run => ({
        ...run,
        type: 'run'
      }))
      
      const commonEvents = this.getCommonEventsForDay(day).map(event => ({
        ...event,
        type: 'common'
      }))
      
      const items = [...runs, ...commonEvents]
      
      // Сортируем по локальной дате
      items.sort((a, b) => {
        const dateA = a.date_local || a.date
        const dateB = b.date_local || b.date
        return dateA.localeCompare(dateB)
      })
      
      return items
    },
    
    getRunsForDayRoom(day, roomId) {
      return this.getRunsForDay(day).filter(run => {
        if (roomId === null) {
          return !run.rooms || run.rooms.length === 0
        }
        return run.rooms && run.rooms.some(r => r.id === roomId)
      })
    },
    
    getRunStyle(run, day) {
      // Используем локальную дату для правильного позиционирования
      const dateStr = this.getRunLocalDate(run)
      let hours = 12 // default
      
      if (dateStr) {
        const parts = dateStr.split('T')
        if (parts.length === 2) {
          const timeParts = parts[1].split(':')
          hours = parseInt(timeParts[0], 10) + parseInt(timeParts[1] || 0, 10) / 60
        }
      }
      
      const timeRange = this.getTimeRangeForDay(day)
      const top = (hours - timeRange.startHour) * this.hourHeight
      const height = (run.duration / 60) * this.hourHeight
      
      return {
        top: `${top}px`,
        height: `${Math.max(height, 40)}px`
      }
    },
    
    getCommonEventsForDay(day) {
      if (!this.schedule || !this.schedule.common_events) return []
      return this.schedule.common_events.filter(event => {
        const dateStr = event.date_local || event.date
        return dateStr && dateStr.startsWith(day)
      })
    },
    
    getCommonEventStyle(event, day) {
      // Используем локальную дату для правильного позиционирования
      const dateStr = event.date_local || event.date
      let hours = 12 // default
      
      if (dateStr) {
        const parts = dateStr.split('T')
        if (parts.length === 2) {
          const timeParts = parts[1].split(':')
          hours = parseInt(timeParts[0], 10) + parseInt(timeParts[1] || 0, 10) / 60
        }
      }
      
      const timeRange = this.getTimeRangeForDay(day)
      const top = (hours - timeRange.startHour) * this.hourHeight
      const height = (event.duration / 60) * this.hourHeight
      
      return {
        top: `${top}px`,
        height: `${Math.max(height, 30)}px`
      }
    },
    
    openRunModal(run) {
      this.selectedRun = run
    },
    
    closeRunModal() {
      this.selectedRun = null
    },
    
    openCommonEventModal(event) {
      this.selectedCommonEvent = event
    },
    
    closeCommonEventModal() {
      this.selectedCommonEvent = null
    },
    
    copyLink() {
      const url = `${window.location.origin}/conventions?event=${this.eventId}&view=schedule`
      navigator.clipboard.writeText(url).then(() => {
        this.linkCopied = true
        setTimeout(() => {
          this.linkCopied = false
        }, 2000)
      })
    }
  }
}
</script>

<style scoped>
/* ========== Базовые стили ========== */
.schedule-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%);
  padding: 40px 20px;
  color: #e0e0e0;
}

/* ========== Загрузка / Ошибка ========== */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: #ff6b35;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 3px solid #1a1a2e;
  border-top-color: #ff6b35;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error {
  text-align: center;
  padding: 40px;
  color: #ff4444;
}

.retry-btn {
  margin-top: 20px;
  padding: 10px 30px;
  background: transparent;
  border: 2px solid #ff6b35;
  color: #ff6b35;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s;
  border-radius: 8px;
}

.retry-btn:hover {
  background: #ff6b35;
  color: #0a0a0a;
}

/* ========== Шапка ========== */
.schedule-header {
  max-width: 1400px;
  margin: 0 auto 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  flex-wrap: wrap;
}

.convention-info {
  flex: 1;
}

.convention-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 2.5rem;
  color: #ff6b35;
  text-shadow: 0 0 20px rgba(255, 107, 53, 0.5);
  letter-spacing: 0.1em;
  margin-bottom: 12px;
}

.convention-meta {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.convention-dates,
.convention-city,
.convention-venue {
  color: #00ccff;
  font-size: 1.1rem;
}

.convention-description {
  color: #aaa;
  line-height: 1.6;
  max-width: 800px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.edit-schedule-btn {
  padding: 12px 24px;
  background: linear-gradient(145deg, #ff6b35, #e55a2b);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  text-decoration: none;
}

.edit-schedule-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(255, 107, 53, 0.4);
}

.back-link {
  padding: 12px 24px;
  background: transparent;
  border: 2px solid #ff6b3566;
  border-radius: 8px;
  color: #ff6b35;
  font-size: 1rem;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.3s ease;
}

.back-link:hover {
  border-color: #ff6b35;
  background: rgba(255, 107, 53, 0.1);
}

.copy-link-btn {
  background: rgba(0, 204, 255, 0.1);
  border: 1px solid #00ccff55;
  color: #00ccff;
  width: 44px;
  height: 44px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  transition: all 0.2s ease;
}

.copy-link-btn:hover {
  background: rgba(0, 204, 255, 0.2);
  border-color: #00ccff;
}

/* ========== Ссылки ========== */
.convention-links {
  max-width: 1400px;
  margin: 0 auto 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.link-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #ff6b3533;
  border-radius: 8px;
  color: #ccc;
  text-decoration: none;
  transition: all 0.2s ease;
}

.link-item:hover {
  background: rgba(255, 107, 53, 0.15);
  border-color: #ff6b35;
  color: #fff;
}

/* ========== Контролы ========== */
.schedule-controls {
  max-width: 1400px;
  margin: 0 auto 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  padding: 16px 24px;
  background: rgba(26, 26, 46, 0.6);
  border-radius: 12px;
  border: 1px solid #ff6b3533;
}

.view-switcher {
  display: flex;
  gap: 4px;
  padding: 4px;
  background: rgba(10, 10, 10, 0.5);
  border-radius: 10px;
}

.view-switcher button {
  padding: 10px 20px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #888;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.view-switcher button:hover {
  color: #ccc;
}

.view-switcher button.active {
  background: linear-gradient(145deg, #ff6b35, #e55a2b);
  color: #fff;
}

.filter-controls {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.control-select {
  padding: 10px 16px;
  background: #0a0a0a;
  border: 2px solid #ff6b3555;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 0.95rem;
  cursor: pointer;
  min-width: 160px;
}

.control-select:focus {
  outline: none;
  border-color: #ff6b35;
}

/* ========== Пустое расписание ========== */
.empty-schedule {
  max-width: 1400px;
  margin: 0 auto;
  text-align: center;
  padding: 80px 40px;
  color: #666;
  font-size: 1.2rem;
}

/* ========== Таймлайн ========== */
.timeline-view {
  max-width: 1400px;
  margin: 0 auto;
}

.timeline-day {
  margin-bottom: 40px;
}

.timeline-day-header,
.list-day-header,
.grid-day-header {
  display: flex;
  gap: 16px;
  align-items: baseline;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid #ff6b3555;
}

.day-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.5rem;
  color: #ff6b35;
  text-transform: capitalize;
}

.day-date {
  color: #888;
  font-size: 1rem;
}

.timeline-content {
  display: flex;
  position: relative;
}

.timeline-scale {
  width: 60px;
  flex-shrink: 0;
  position: relative;
}

.timeline-scale.with-headers {
  margin-top: 52px; /* Отступ для заголовков помещений (44px min-height + 8px gap) */
}

.timeline-hour {
  position: absolute;
  color: #666;
  font-size: 0.85rem;
  font-family: 'JetBrains Mono', monospace;
  transform: translateY(-50%);
}

.timeline-rooms {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  overflow-x: auto;
  padding-bottom: 20px;
}

.timeline-rooms-headers {
  display: flex;
  gap: 16px;
  position: sticky;
  top: 0;
  z-index: 2;
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%);
  padding-bottom: 8px;
  width: fit-content;
}

.room-header {
  flex: 1;
  min-width: 200px;
  max-width: 300px;
  background: rgba(26, 26, 46, 0.95);
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid #ff6b3555;
  color: #00ccff;
  font-weight: 600;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
}

.timeline-rooms-columns {
  display: flex;
  gap: 16px;
  width: fit-content;
}

.timeline-room {
  flex: 1;
  min-width: 200px;
  max-width: 300px;
}

.timeline-rooms-content {
  position: relative;
  width: fit-content;
}

.timeline-rooms-content.no-rooms {
  min-width: 300px;
}

.timeline-common-event {
  position: absolute;
  left: 0;
  right: 0;
  padding: 6px 12px;
  background: linear-gradient(145deg, rgba(0, 204, 255, 0.2), rgba(0, 180, 220, 0.15));
  border: 1px solid #00ccff88;
  border-left: 3px solid #00ccff;
  border-radius: 6px;
  cursor: pointer;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s ease;
  backdrop-filter: blur(4px);
}

.timeline-common-event:hover {
  background: linear-gradient(145deg, rgba(0, 204, 255, 0.3), rgba(0, 180, 220, 0.25));
  border-color: #00ccff;
  box-shadow: 0 4px 20px rgba(0, 204, 255, 0.3);
}

.common-event-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  color: #00ccff;
  font-weight: bold;
  white-space: nowrap;
}

.common-event-name {
  font-weight: 600;
  color: #e0e0e0;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.room-runs {
  position: relative;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #ff6b3533;
  border-radius: 8px;
}

.timeline-run {
  position: absolute;
  left: 8px;
  right: 8px;
  padding: 8px 12px;
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border: 1px solid #ff6b3555;
  border-left: 3px solid #ff6b35;
  border-radius: 6px;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.2s ease;
}

.timeline-run:hover {
  border-color: #ff6b35;
  box-shadow: 0 4px 20px rgba(255, 107, 53, 0.3);
  z-index: 10;
}

.timeline-run.run-full {
  border-left-color: #666;
  opacity: 0.7;
}

.run-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  color: #ff6b35;
  margin-bottom: 4px;
}

.run-name {
  font-weight: 600;
  color: #e0e0e0;
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.run-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}

.run-slots {
  font-size: 0.8rem;
  color: #00ccff;
}

.run-full-badge {
  font-size: 0.7rem;
  padding: 2px 6px;
  background: #ff4444;
  color: #fff;
  border-radius: 4px;
  text-transform: uppercase;
}

/* ========== Список ========== */
.list-view {
  max-width: 1400px;
  margin: 0 auto;
}

.list-day {
  margin-bottom: 40px;
}

.list-runs {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.list-run {
  display: flex;
  gap: 20px;
  padding: 16px 20px;
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border: 1px solid #ff6b3533;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.list-run:hover {
  border-color: #ff6b35;
  transform: translateX(4px);
  box-shadow: 0 4px 20px rgba(255, 107, 53, 0.2);
}

.list-run.run-full {
  opacity: 0.6;
}

.list-common-event {
  display: flex;
  gap: 20px;
  padding: 16px 20px;
  background: linear-gradient(145deg, rgba(0, 204, 255, 0.1), rgba(0, 180, 220, 0.05));
  border: 1px solid #00ccff55;
  border-left: 3px solid #00ccff;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.list-common-event:hover {
  border-color: #00ccff;
  background: linear-gradient(145deg, rgba(0, 204, 255, 0.15), rgba(0, 180, 220, 0.1));
  box-shadow: 0 4px 20px rgba(0, 204, 255, 0.2);
}

.common-time {
  color: #00ccff !important;
}

.common-event-label {
  font-size: 0.85rem;
  color: #00ccff;
  margin-top: 4px;
}

.run-time-col {
  flex-shrink: 0;
  width: 80px;
  text-align: center;
}

.run-time-col .run-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.1rem;
  color: #ff6b35;
  font-weight: bold;
}

.run-duration {
  display: block;
  font-size: 0.8rem;
  color: #666;
  margin-top: 4px;
}

.run-main-col {
  flex: 1;
}

.run-main-col .run-name {
  font-size: 1.1rem;
  margin-bottom: 6px;
}

.run-rooms,
.run-masters {
  font-size: 0.9rem;
  color: #888;
  margin-top: 4px;
}

.run-slots-col {
  flex-shrink: 0;
  text-align: right;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.run-slots-col .run-slots {
  font-size: 1.1rem;
  font-weight: 600;
}

.run-slots-col .slots-full {
  color: #ff4444;
}

/* ========== Модальное окно ========== */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border: 2px solid #ff6b35;
  border-radius: 16px;
  padding: 32px;
  max-width: 500px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 0 60px rgba(255, 107, 53, 0.3);
}

.modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  color: #ff6b35;
  font-size: 2rem;
  cursor: pointer;
  line-height: 1;
  transition: transform 0.2s;
}

.modal-close:hover {
  transform: scale(1.2);
}

.modal-run-date {
  color: #ff6b35;
  font-size: 1rem;
  margin-bottom: 8px;
  text-transform: capitalize;
}

.modal-run-time {
  font-family: 'JetBrains Mono', monospace;
  font-weight: bold;
  margin-left: 8px;
}

.modal-content h2 {
  font-family: 'JetBrains Mono', monospace;
  color: #e0e0e0;
  font-size: 1.5rem;
  margin-bottom: 16px;
  padding-right: 40px;
}

.modal-rooms {
  color: #00ccff;
  margin-bottom: 16px;
}

.modal-section {
  margin-bottom: 20px;
}

.modal-section h3 {
  color: #ff6b35;
  font-size: 0.9rem;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.masters-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.master-item {
  padding: 6px 12px;
  background: rgba(0, 204, 255, 0.1);
  border-radius: 6px;
  color: #00ccff;
  font-size: 0.9rem;
}

.modal-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin: 20px 0;
}

.modal-stat {
  flex: 1;
  min-width: 100px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  text-align: center;
}

.modal-stat-label {
  display: block;
  color: #888;
  font-size: 0.8rem;
  margin-bottom: 4px;
}

.modal-stat-value {
  display: block;
  color: #e0e0e0;
  font-size: 1.1rem;
  font-weight: 600;
}

.modal-stat-value.full {
  color: #ff4444;
}

.modal-actions {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}

.btn {
  padding: 12px 28px;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background: linear-gradient(145deg, #ff6b35, #e55a2b);
  border: none;
  color: #fff;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 53, 0.35);
}

/* ========== Модальное окно общего события ========== */
.common-event-modal {
  border-color: #00ccff;
  box-shadow: 0 0 60px rgba(0, 204, 255, 0.3);
}

.common-event-badge {
  display: inline-block;
  padding: 4px 12px;
  background: rgba(0, 204, 255, 0.2);
  border: 1px solid #00ccff;
  border-radius: 16px;
  color: #00ccff;
  font-size: 0.85rem;
  font-weight: 600;
  margin-bottom: 16px;
}

.common-event-description {
  padding: 16px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  color: #aaa;
  line-height: 1.6;
  margin-top: 16px;
}

/* ========== Адаптив ========== */
@media (max-width: 768px) {
  .convention-title {
    font-size: 1.8rem;
  }
  
  .schedule-header {
    flex-direction: column;
  }
  
  .schedule-controls {
    flex-direction: column;
    gap: 16px;
  }
  
  .view-switcher {
    width: 100%;
    justify-content: center;
  }
  
  .filter-controls {
    width: 100%;
  }
  
  .control-select {
    flex: 1;
  }
  
  .list-run {
    flex-wrap: wrap;
  }
  
  .run-time-col {
    width: auto;
    text-align: left;
  }
  
  .run-slots-col {
    width: 100%;
    flex-direction: row;
    justify-content: flex-start;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #ff6b3522;
  }
}

/* ========== Статус регистрации на конвент ========== */
.user-registration-bar {
  max-width: 1400px;
  margin: 0 auto 24px;
  padding: 14px 24px;
  background: linear-gradient(145deg, rgba(0, 204, 255, 0.1), rgba(0, 150, 200, 0.05));
  border: 1px solid #00ccff55;
  border-radius: 10px;
  text-align: center;
}

.reg-status {
  font-size: 1rem;
  font-weight: 500;
}

.reg-pending {
  color: #ffaa00;
}

.reg-confirmed {
  color: #4caf50;
}

.reg-rejected {
  color: #ff4444;
}
</style>

