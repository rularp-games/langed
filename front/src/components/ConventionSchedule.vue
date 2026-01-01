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
          </div>
          <p v-if="schedule.convention_description" class="convention-description">
            {{ schedule.convention_description }}
          </p>
        </div>
        
        <div class="header-actions">
          <button 
            v-if="schedule.can_edit"
            @click="$emit('edit')"
            class="edit-schedule-btn"
          >
            ✏️ Редактировать расписание
          </button>
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
          <button 
            :class="{ active: viewMode === 'grid' }"
            @click="viewMode = 'grid'"
          >
            Сетка
          </button>
        </div>
        
        <div class="filter-controls">
          <select v-model="selectedDay" class="control-select">
            <option value="">Все дни</option>
            <option v-for="day in days" :key="day" :value="day">
              {{ formatDayOption(day) }}
            </option>
          </select>
          
          <select v-model="selectedVenue" class="control-select">
            <option value="">Все площадки</option>
            <option v-for="venue in schedule.venues" :key="venue.id" :value="venue.id">
              {{ venue.name }}
            </option>
          </select>
        </div>
      </div>

      <!-- Пустое расписание -->
      <div v-if="filteredRuns.length === 0" class="empty-schedule">
        <p v-if="schedule.runs.length === 0">Расписание пока пусто</p>
        <p v-else>Нет прогонов по выбранным фильтрам</p>
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
            <div class="timeline-scale">
              <div 
                v-for="hour in timelineHours" 
                :key="hour"
                class="timeline-hour"
                :style="{ top: getHourPosition(hour) + 'px' }"
              >
                {{ formatHour(hour) }}
              </div>
            </div>
            
            <!-- Прогоны по площадкам -->
            <div class="timeline-venues">
              <div 
                v-for="venue in getVenuesForDay(day)" 
                :key="venue.id || 'no-venue'"
                class="timeline-venue"
              >
                <div class="venue-header">{{ venue.name || 'Без площадки' }}</div>
                <div class="venue-runs">
                  <div 
                    v-for="run in getRunsForDayVenue(day, venue.id)" 
                    :key="run.id"
                    class="timeline-run"
                    :style="getRunStyle(run)"
                    :class="{ 'run-full': run.is_full }"
                    @click="openRunModal(run)"
                  >
                    <div class="run-time">{{ formatTime(run.date) }}</div>
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

      <!-- Список -->
      <div v-else-if="viewMode === 'list'" class="list-view">
        <div v-for="day in filteredDays" :key="day" class="list-day">
          <div class="list-day-header">
            <span class="day-name">{{ formatDayName(day) }}</span>
            <span class="day-date">{{ formatDayDate(day) }}</span>
          </div>
          
          <div class="list-runs">
            <div 
              v-for="run in getRunsForDay(day)" 
              :key="run.id"
              class="list-run"
              :class="{ 'run-full': run.is_full }"
              @click="openRunModal(run)"
            >
              <div class="run-time-col">
                <span class="run-time">{{ formatTime(run.date) }}</span>
                <span class="run-duration">{{ formatDuration(run.duration) }}</span>
              </div>
              <div class="run-main-col">
                <div class="run-name">{{ run.game_name }}</div>
                <div class="run-venue" v-if="run.venue_name">📍 {{ run.venue_name }}</div>
                <div class="run-masters" v-if="run.masters && run.masters.length">
                  👤 {{ run.masters.map(m => m.display_name).join(', ') }}
                </div>
              </div>
              <div class="run-slots-col">
                <span class="run-slots" :class="{ 'slots-full': run.is_full }">
                  {{ run.registered_count }}/{{ run.effective_max_players }}
                </span>
                <span v-if="run.is_full" class="run-full-badge">МЕСТ НЕТ</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Сетка (по площадкам) -->
      <div v-else-if="viewMode === 'grid'" class="grid-view">
        <div class="grid-header">
          <div class="grid-time-col"></div>
          <div 
            v-for="venue in gridVenues" 
            :key="venue.id || 'no-venue'"
            class="grid-venue-col"
          >
            {{ venue.name || 'Без площадки' }}
          </div>
        </div>
        
        <div v-for="day in filteredDays" :key="day" class="grid-day">
          <div class="grid-day-header" :style="{ gridColumn: `span ${gridVenues.length + 1}` }">
            <span class="day-name">{{ formatDayName(day) }}</span>
            <span class="day-date">{{ formatDayDate(day) }}</span>
          </div>
          
          <template v-for="slot in getTimeSlotsForDay(day)" :key="slot.time">
            <div class="grid-time-cell">{{ formatTime(slot.time) }}</div>
            <div 
              v-for="venue in gridVenues" 
              :key="(venue.id || 'no-venue') + '-' + slot.time"
              class="grid-cell"
            >
              <div 
                v-for="run in getRunsForSlotVenue(slot, venue.id)"
                :key="run.id"
                class="grid-run"
                :class="{ 'run-full': run.is_full }"
                @click="openRunModal(run)"
              >
                <div class="run-name">{{ run.game_name }}</div>
                <div class="run-slots">{{ run.registered_count }}/{{ run.effective_max_players }}</div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </template>

    <!-- Модальное окно прогона -->
    <div v-if="selectedRun" class="modal-overlay" @click.self="closeRunModal">
      <div class="modal-content run-modal">
        <button class="modal-close" @click="closeRunModal">×</button>
        
        <div class="modal-run-date">
          {{ formatFullDate(selectedRun.date) }}
          <span class="modal-run-time">{{ formatTime(selectedRun.date) }}</span>
        </div>
        
        <h2>{{ selectedRun.game_name }}</h2>
        
        <div class="modal-venue" v-if="selectedRun.venue_name">
          📍 {{ selectedRun.venue_name }}
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
      selectedVenue: '',
      selectedRun: null,
      linkCopied: false,
      timelineStartHour: 9,
      timelineEndHour: 24,
      hourHeight: 60
    }
  },
  computed: {
    days() {
      if (!this.schedule || !this.schedule.runs) return []
      const daysSet = new Set()
      this.schedule.runs.forEach(run => {
        const day = run.date.split('T')[0]
        daysSet.add(day)
      })
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
        runs = runs.filter(run => run.date.startsWith(this.selectedDay))
      }
      
      if (this.selectedVenue) {
        runs = runs.filter(run => {
          return run.venue && run.venue.id === this.selectedVenue
        })
      }
      
      return runs.sort((a, b) => new Date(a.date) - new Date(b.date))
    },
    timelineHours() {
      const hours = []
      for (let h = this.timelineStartHour; h <= this.timelineEndHour; h++) {
        hours.push(h)
      }
      return hours
    },
    gridVenues() {
      if (!this.schedule) return []
      const venues = [...(this.schedule.venues || [])]
      // Добавляем "Без площадки" если есть прогоны без venue
      const hasNoVenue = this.schedule.runs.some(r => !r.venue)
      if (hasNoVenue) {
        venues.push({ id: null, name: 'Без площадки' })
      }
      return venues
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
    
    formatDates(start, end) {
      const startDate = new Date(start)
      const endDate = new Date(end)
      const startDay = startDate.getDate()
      const endDay = endDate.getDate()
      const month = startDate.toLocaleDateString('ru-RU', { month: 'long' })
      const year = startDate.getFullYear()
      
      if (startDate.getMonth() === endDate.getMonth() && startDate.getFullYear() === endDate.getFullYear()) {
        return `${startDay}–${endDay} ${month} ${year}`
      }
      const startFormatted = startDate.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' })
      const endFormatted = endDate.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' })
      return `${startFormatted} — ${endFormatted}`
    },
    
    formatDayOption(day) {
      const date = new Date(day)
      return date.toLocaleDateString('ru-RU', { weekday: 'short', day: 'numeric', month: 'short' })
    },
    
    formatDayName(day) {
      const date = new Date(day)
      return date.toLocaleDateString('ru-RU', { weekday: 'long' })
    },
    
    formatDayDate(day) {
      const date = new Date(day)
      return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
    },
    
    formatTime(dateStr) {
      const date = new Date(dateStr)
      return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    },
    
    formatFullDate(dateStr) {
      const date = new Date(dateStr)
      return date.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })
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
      return `${hour.toString().padStart(2, '0')}:00`
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
    
    getHourPosition(hour) {
      return (hour - this.timelineStartHour) * this.hourHeight
    },
    
    getVenuesForDay(day) {
      const runs = this.getRunsForDay(day)
      const venueIds = new Set()
      const venues = []
      
      runs.forEach(run => {
        const venueId = run.venue ? run.venue.id : null
        if (!venueIds.has(venueId)) {
          venueIds.add(venueId)
          venues.push(run.venue || { id: null, name: 'Без площадки' })
        }
      })
      
      return venues
    },
    
    getRunsForDay(day) {
      return this.filteredRuns.filter(run => run.date.startsWith(day))
    },
    
    getRunsForDayVenue(day, venueId) {
      return this.getRunsForDay(day).filter(run => {
        const runVenueId = run.venue ? run.venue.id : null
        return runVenueId === venueId
      })
    },
    
    getRunStyle(run) {
      const date = new Date(run.date)
      const hours = date.getHours() + date.getMinutes() / 60
      const top = (hours - this.timelineStartHour) * this.hourHeight
      const height = (run.duration / 60) * this.hourHeight
      
      return {
        top: `${top}px`,
        height: `${Math.max(height, 40)}px`
      }
    },
    
    getTimeSlotsForDay(day) {
      const runs = this.getRunsForDay(day)
      const times = new Set()
      runs.forEach(run => times.add(run.date))
      return Array.from(times).sort().map(time => ({ time }))
    },
    
    getRunsForSlotVenue(slot, venueId) {
      return this.filteredRuns.filter(run => {
        const runVenueId = run.venue ? run.venue.id : null
        return run.date === slot.time && runVenueId === venueId
      })
    },
    
    openRunModal(run) {
      this.selectedRun = run
    },
    
    closeRunModal() {
      this.selectedRun = null
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
  font-family: 'Orbitron', 'Courier New', monospace;
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
.convention-city {
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
}

.edit-schedule-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(255, 107, 53, 0.4);
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
  font-family: 'Orbitron', 'Courier New', monospace;
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
  min-height: 600px;
}

.timeline-scale {
  width: 60px;
  flex-shrink: 0;
  position: relative;
}

.timeline-hour {
  position: absolute;
  color: #666;
  font-size: 0.85rem;
  font-family: 'Courier New', monospace;
  transform: translateY(-50%);
}

.timeline-venues {
  flex: 1;
  display: flex;
  gap: 16px;
  overflow-x: auto;
  padding-bottom: 20px;
}

.timeline-venue {
  flex: 1;
  min-width: 200px;
  max-width: 300px;
}

.venue-header {
  position: sticky;
  top: 0;
  background: rgba(26, 26, 46, 0.95);
  padding: 12px 16px;
  border-radius: 8px 8px 0 0;
  border: 1px solid #ff6b3555;
  border-bottom: none;
  color: #00ccff;
  font-weight: 600;
  text-align: center;
  z-index: 1;
}

.venue-runs {
  position: relative;
  min-height: 600px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid #ff6b3533;
  border-radius: 0 0 8px 8px;
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
  font-family: 'Courier New', monospace;
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

.run-time-col {
  flex-shrink: 0;
  width: 80px;
  text-align: center;
}

.run-time-col .run-time {
  font-family: 'Courier New', monospace;
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

.run-venue,
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

/* ========== Сетка ========== */
.grid-view {
  max-width: 1400px;
  margin: 0 auto;
  overflow-x: auto;
}

.grid-header {
  display: grid;
  grid-auto-columns: minmax(150px, 1fr);
  grid-auto-flow: column;
  gap: 1px;
  background: #ff6b3533;
  padding: 1px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.grid-time-col,
.grid-venue-col {
  padding: 12px 16px;
  background: rgba(26, 26, 46, 0.95);
  color: #00ccff;
  font-weight: 600;
  text-align: center;
}

.grid-time-col {
  width: 80px;
}

.grid-day {
  display: grid;
  grid-auto-columns: minmax(150px, 1fr);
  grid-auto-flow: column;
  gap: 1px;
  background: #ff6b3522;
  padding: 1px;
  margin-top: 24px;
}

.grid-day-header {
  padding: 16px;
  background: rgba(26, 26, 46, 0.9);
}

.grid-time-cell {
  padding: 12px;
  background: rgba(10, 10, 10, 0.5);
  font-family: 'Courier New', monospace;
  color: #ff6b35;
  text-align: center;
  width: 80px;
}

.grid-cell {
  padding: 8px;
  background: rgba(0, 0, 0, 0.3);
  min-height: 60px;
}

.grid-run {
  padding: 8px 12px;
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border: 1px solid #ff6b3555;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: all 0.2s ease;
}

.grid-run:hover {
  border-color: #ff6b35;
}

.grid-run .run-name {
  font-size: 0.85rem;
  margin-bottom: 4px;
}

.grid-run .run-slots {
  font-size: 0.75rem;
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
  font-family: 'Courier New', monospace;
  font-weight: bold;
  margin-left: 8px;
}

.modal-content h2 {
  font-family: 'Orbitron', 'Courier New', monospace;
  color: #e0e0e0;
  font-size: 1.5rem;
  margin-bottom: 16px;
  padding-right: 40px;
}

.modal-venue {
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
</style>

