<template>
  <div class="schedule-editor">
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

    <!-- Редактор -->
    <template v-else-if="schedule">
      <!-- Шапка -->
      <div class="editor-header">
        <div class="header-info">
          <h1>Редактор расписания</h1>
          <h2 class="convention-name">{{ schedule.convention_name }}</h2>
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
        </div>
        
        <div class="header-actions">
          <router-link :to="`/schedule/${eventId}`" class="btn btn-secondary">
            👁️ Просмотр
          </router-link>
          <router-link to="/conventions" class="btn btn-outline">
            ← К конвентам
          </router-link>
        </div>
      </div>

      <!-- Панель инструментов -->
      <div class="editor-toolbar">
        <div class="toolbar-left">
          <button @click="openAddRunModal" class="add-run-btn">
            <span class="add-icon">+</span>
            Добавить прогон
          </button>
          <button @click="openAddCommonEventModal" class="add-common-event-btn">
            <span class="add-icon">+</span>
            Общее событие
          </button>
        </div>
        
        <div class="toolbar-right">
          <select v-model="selectedDay" class="control-select">
            <option value="">Все дни</option>
            <option v-for="day in days" :key="day" :value="day">
              {{ formatDayOption(day) }}
            </option>
          </select>
          
          <div class="runs-count">
            {{ schedule.runs.length }} {{ pluralizeRuns(schedule.runs.length) }}
            <template v-if="schedule.common_events && schedule.common_events.length > 0">
              + {{ schedule.common_events.length }} {{ pluralizeEvents(schedule.common_events.length) }}
            </template>
          </div>
        </div>
      </div>

      <!-- Список прогонов -->
      <div v-if="filteredRuns.length === 0 && filteredCommonEvents.length === 0" class="empty-schedule">
        <p v-if="schedule.runs.length === 0 && (!schedule.common_events || schedule.common_events.length === 0)">Расписание пока пусто. Добавьте первый прогон!</p>
        <p v-else>Нет событий на выбранный день</p>
      </div>

      <div v-else class="runs-editor">
        <div v-for="day in filteredDays" :key="day" class="editor-day">
          <div class="day-header">
            <span class="day-name">{{ formatDayName(day) }}</span>
            <span class="day-date">{{ formatDayDate(day) }}</span>
            <span class="day-runs-count">
              {{ getRunsForDay(day).length }} {{ pluralizeRuns(getRunsForDay(day).length) }}
              <template v-if="getCommonEventsForDay(day).length > 0">
                + {{ getCommonEventsForDay(day).length }} {{ pluralizeEvents(getCommonEventsForDay(day).length) }}
              </template>
            </span>
          </div>
          
          <!-- Общие события -->
          <div v-if="getCommonEventsForDay(day).length > 0" class="day-common-events">
            <div 
              v-for="event in getCommonEventsForDay(day)" 
              :key="'common-' + event.id"
              class="common-event-card"
            >
              <div class="run-time-block">
                <span class="run-time common-event-time">{{ formatTime(event.date_local || event.date) }}</span>
                <span class="run-duration">{{ formatDuration(event.duration) }}</span>
              </div>
              
              <div class="run-main">
                <div class="run-name">{{ event.name }}</div>
                <div class="common-event-badge">📢 Общее событие</div>
                <div v-if="event.description" class="common-event-description-short">{{ event.description }}</div>
              </div>
              
              <div class="run-actions">
                <button 
                  @click="openEditCommonEventModal(event)"
                  class="action-btn edit-btn"
                  title="Редактировать"
                >
                  ✏️
                </button>
                <button 
                  @click="confirmDeleteCommonEvent(event)"
                  class="action-btn delete-btn"
                  title="Удалить"
                >
                  🗑️
                </button>
              </div>
            </div>
          </div>
          
          <div class="day-runs">
            <div 
              v-for="run in getRunsForDay(day)" 
              :key="run.id"
              class="run-card"
              :class="{ 'run-full': run.is_full }"
            >
              <div class="run-time-block">
                <span class="run-time">{{ formatTime(run.date_local || run.date) }}</span>
                <span class="run-duration">{{ formatDuration(run.duration) }}</span>
              </div>
              
              <div class="run-main">
                <div class="run-name">{{ run.game_name }}</div>
                <div class="run-details">
                  <span v-if="run.rooms && run.rooms.length" class="run-rooms">📍 {{ run.rooms.map(r => r.name).join(', ') }}</span>
                </div>
                <!-- Секция управления мастерами -->
                <div class="run-masters-section">
                  <span class="masters-label">👤 Мастера:</span>
                  <div class="masters-list">
                    <div 
                      v-for="master in (run.masters || [])" 
                      :key="master.id" 
                      class="master-item"
                    >
                      <span class="master-name">{{ master.display_name }}</span>
                      <button 
                        v-if="run.masters && run.masters.length > 1"
                        class="master-remove-btn"
                        @click.stop="removeMaster(run, master)"
                        title="Удалить мастера"
                      >
                        ×
                      </button>
                    </div>
                    <div v-if="!run.masters || run.masters.length === 0" class="no-masters">
                      Нет мастеров
                    </div>
                  </div>
                  <!-- Форма добавления мастера с автодополнением -->
                  <div class="add-master-form" @click.stop>
                    <div class="autocomplete-wrapper">
                      <input 
                        v-model="masterInputs[run.id]"
                        type="text"
                        class="add-master-input"
                        placeholder="Начните вводить имя..."
                        autocomplete="off"
                        @input="searchUsers(run.id)"
                        @focus="showUserDropdown[run.id] = true"
                        @blur="hideUserDropdownDelayed(run.id)"
                        @keydown.enter.prevent="selectFirstUser(run)"
                        @keydown.down.prevent="highlightNextUser(run.id)"
                        @keydown.up.prevent="highlightPrevUser(run.id)"
                      />
                      <div 
                        v-if="showUserDropdown[run.id] && userSearchResults[run.id] && userSearchResults[run.id].length > 0" 
                        class="user-dropdown"
                      >
                        <div 
                          v-for="(user, idx) in userSearchResults[run.id]" 
                          :key="user.id"
                          class="user-dropdown-item"
                          :class="{ highlighted: highlightedUserIndex[run.id] === idx }"
                          @mousedown.prevent="selectUser(run, user)"
                        >
                          <span class="user-display-name">{{ user.display_name }}</span>
                          <span class="user-username">@{{ user.username }}</span>
                        </div>
                      </div>
                      <div 
                        v-if="showUserDropdown[run.id] && masterInputs[run.id] && masterInputs[run.id].length >= 2 && (!userSearchResults[run.id] || userSearchResults[run.id].length === 0) && !userSearchLoading[run.id]" 
                        class="user-dropdown user-dropdown-empty"
                      >
                        Пользователи не найдены
                      </div>
                    </div>
                    <button 
                      class="add-master-btn"
                      @click.stop="addMasterFromSelected(run)"
                      :disabled="!selectedUsers[run.id] || masterLoading[run.id]"
                    >
                      {{ masterLoading[run.id] ? '...' : '+' }}
                    </button>
                  </div>
                  <div v-if="masterErrors[run.id]" class="master-error">{{ masterErrors[run.id] }}</div>
                </div>
              </div>
              
              <div class="run-status">
                <span 
                  class="run-slots" 
                  :class="{ 'slots-full': run.is_full, 'clickable': run.registered_count > 0 || getPendingCount(run) > 0 }"
                  @click="toggleRegistrations(run.id)"
                  :title="(run.registered_count > 0 || getPendingCount(run) > 0) ? 'Показать участников' : ''"
                >
                  {{ run.registered_count }}/{{ run.effective_max_players }}
                  <span v-if="getPendingCount(run) > 0" class="pending-count">+{{ getPendingCount(run) }} заявок</span>
                </span>
                <span v-if="run.is_full" class="full-badge">МЕСТ НЕТ</span>
              </div>
              
              <div class="run-actions">
                <button 
                  @click="openEditRunModal(run)"
                  class="action-btn edit-btn"
                  title="Редактировать"
                >
                  ✏️
                </button>
                <button 
                  @click="confirmDeleteRun(run)"
                  class="action-btn delete-btn"
                  title="Удалить"
                >
                  🗑️
                </button>
              </div>
              
              <!-- Секция регистраций -->
              <div v-if="expandedRuns[run.id] && run.registrations && run.registrations.length > 0" class="run-registrations">
                <div class="registrations-header">
                  <span class="registrations-title">Участники</span>
                  <button class="close-registrations" @click="toggleRegistrations(run.id)">×</button>
                </div>
                <div class="registrations-list">
                  <div 
                    v-for="reg in sortRegistrations(run.registrations)" 
                    :key="reg.id"
                    class="registration-item"
                    :class="{
                      'reg-pending': reg.status === 'pending',
                      'reg-confirmed': reg.status === 'confirmed',
                      'reg-waitlist': reg.status === 'waitlist',
                      'reg-cancelled': reg.status === 'cancelled',
                      'reg-technician': reg.is_technician
                    }"
                  >
                    <span class="reg-icon">{{ reg.is_technician ? '🎭' : '👤' }}</span>
                    <span class="reg-name">{{ reg.user.display_name }}</span>
                    <span v-if="reg.role_preference !== 'any'" class="reg-role">
                      {{ reg.role_preference === 'female' ? '♀' : '♂' }}
                    </span>
                    <span class="reg-status-badge" :class="'status-' + reg.status">
                      {{ getStatusLabel(reg.status) }}
                    </span>
                    <!-- Кнопки управления -->
                    <div v-if="reg.status !== 'cancelled'" class="reg-actions">
                      <button 
                        v-if="reg.status === 'pending' || reg.status === 'waitlist'"
                        class="reg-action-btn confirm-btn"
                        @click.stop="updateRunRegistration(run.id, reg.id, 'confirmed')"
                        :disabled="registrationUpdateLoading === reg.id"
                        title="Подтвердить"
                      >
                        ✓
                      </button>
                      <button 
                        v-if="reg.status === 'confirmed'"
                        class="reg-action-btn pending-btn"
                        @click.stop="updateRunRegistration(run.id, reg.id, 'pending')"
                        :disabled="registrationUpdateLoading === reg.id"
                        title="Вернуть в ожидание"
                      >
                        ⏳
                      </button>
                      <button 
                        class="reg-action-btn reject-btn"
                        @click.stop="updateRunRegistration(run.id, reg.id, 'cancelled')"
                        :disabled="registrationUpdateLoading === reg.id"
                        title="Отклонить"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Модальное окно добавления/редактирования прогона -->
    <RunEditor
      v-if="showRunEditor"
      :mode="runEditorMode"
      :run="runEditorRun"
      :convention-event-id="parseInt(eventId)"
      :lock-convention="true"
      :lock-game="runEditorMode === 'edit'"
      :convention-name="schedule ? schedule.convention_name : ''"
      :games="games"
      :cities="[]"
      :convention-events="[]"
      :available-rooms="availableRooms"
      :convention-venue="schedule && schedule.venue ? { id: schedule.venue.id, name: schedule.venue.name } : null"
      :date-constraints="{ min: schedule ? schedule.date_start : '', max: schedule ? schedule.date_end : '' }"
      :allow-new-city="false"
      :csrf-token="csrfToken"
      :default-city="schedule && schedule.city ? { id: schedule.city.id, name: schedule.city.name, timezone: schedule.city.timezone || schedule.city_timezone, region: schedule.city.region } : null"
      :default-timezone="schedule ? schedule.city_timezone : 'Europe/Moscow'"
      :default-date="schedule ? schedule.date_start : ''"
      @save="handleRunSave"
      @cancel="closeRunEditor"
      @error="handleRunError"
    />

    <!-- Модальное окно подтверждения удаления -->
    <DeleteConfirmModal
      v-if="showDeleteConfirm"
      :title="deleteType === 'run' ? 'Удалить прогон?' : 'Удалить общее событие?'"
      :message="deleteMessage"
      :loading="deleteLoading"
      @confirm="executeDelete"
      @cancel="cancelDelete"
    />

    <!-- Модальное окно добавления/редактирования общего события -->
    <div v-if="showCommonEventEditor" class="modal-overlay" @click.self="closeCommonEventEditor">
      <div class="modal-content common-event-editor-modal">
        <button class="modal-close" @click="closeCommonEventEditor">×</button>
        
        <h2>{{ commonEventEditorMode === 'add' ? 'Добавить общее событие' : 'Редактировать событие' }}</h2>
        
        <form @submit.prevent="saveCommonEvent" class="common-event-form">
          <div class="form-group">
            <label>Название *</label>
            <input 
              v-model="commonEventForm.name" 
              type="text" 
              class="form-input"
              placeholder="Например: Ужин, Завтрак, Заезд..."
              required
            />
          </div>
          
          <div class="form-row">
            <div class="form-group half">
              <label>Дата * <span class="format-hint">(дд/мм/гггг)</span></label>
              <div class="date-picker-wrapper">
                <input 
                  :value="formattedCommonEventDate"
                  @input="handleCommonEventDateInput"
                  @blur="validateCommonEventDate"
                  type="text" 
                  required
                  class="form-input date-input"
                  placeholder="дд/мм/гггг"
                  maxlength="10"
                />
                <input 
                  ref="commonEventDatePickerInput"
                  type="date"
                  class="date-picker-native"
                  :value="commonEventForm.date"
                  :min="schedule ? schedule.date_start : ''"
                  :max="schedule ? schedule.date_end : ''"
                  @change="handleCommonEventDatePickerChange"
                />
                <button 
                  type="button" 
                  class="date-picker-btn"
                  @click="openCommonEventDatePicker"
                  title="Открыть календарь"
                >
                  📅
                </button>
              </div>
            </div>
            
            <div class="form-group half">
              <label>Время *</label>
              <input 
                v-model="commonEventForm.time" 
                type="text" 
                required
                class="form-input time-input"
                placeholder="чч:мм"
                maxlength="5"
                @input="handleCommonEventTimeInput"
                @blur="validateCommonEventTime"
              />
            </div>
          </div>
          
          <div class="form-group">
            <label>Длительность (минут) *</label>
            <input 
              v-model.number="commonEventForm.duration" 
              type="number" 
              class="form-input"
              min="5"
              max="1440"
              required
            />
          </div>
          
          <div class="form-group">
            <label>Описание</label>
            <textarea 
              v-model="commonEventForm.description" 
              class="form-textarea"
              rows="3"
              placeholder="Дополнительная информация о событии..."
            ></textarea>
          </div>
          
          <div v-if="commonEventError" class="form-error">
            {{ commonEventError }}
          </div>
          
          <div class="form-actions">
            <button type="button" @click="closeCommonEventEditor" class="btn btn-secondary">
              Отмена
            </button>
            <button type="submit" class="btn btn-primary" :disabled="commonEventLoading">
              {{ commonEventLoading ? 'Сохранение...' : 'Сохранить' }}
            </button>
          </div>
        </form>
      </div>
    </div>

  </div>
</template>

<script>
import RunEditor from './RunEditor.vue'
import DeleteConfirmModal from './DeleteConfirmModal.vue'

export default {
  name: 'ScheduleEditor',
  components: {
    RunEditor,
    DeleteConfirmModal
  },
  props: {
    eventId: {
      type: [String, Number],
      required: true
    }
  },
  emits: ['close', 'view', 'updated'],
  data() {
    return {
      schedule: null,
      loading: true,
      error: null,
      selectedDay: '',
      games: [],
      rooms: [],
      
      // Единый редактор прогона
      showRunEditor: false,
      runEditorMode: 'add',
      runEditorRun: null,
      runEditorLoading: false,
      
      // Удаление
      showDeleteConfirm: false,
      deleteTarget: null,
      deleteLoading: false,
      
      // Управление мастерами
      masterInputs: {},
      masterLoading: {},
      masterErrors: {},
      
      // Автодополнение пользователей
      userSearchResults: {},
      userSearchLoading: {},
      showUserDropdown: {},
      selectedUsers: {},
      highlightedUserIndex: {},
      searchDebounceTimers: {},
      
      // Редактор общих событий
      showCommonEventEditor: false,
      commonEventEditorMode: 'add',
      commonEventForm: {
        id: null,
        name: '',
        date: '',
        time: '',
        duration: 60,
        description: ''
      },
      commonEventLoading: false,
      commonEventError: null,
      
      // Тип удаления
      deleteType: 'run',
      
      // Управление регистрациями
      expandedRuns: {},
      registrationUpdateLoading: null
    }
  },
  computed: {
    csrfToken() {
      const match = document.cookie.match(/csrftoken=([^;]+)/)
      return match ? match[1] : ''
    },
    deleteMessage() {
      if (this.deleteType === 'common') {
        return `Событие "${this.deleteTarget?.name}" будет удалено из расписания.`
      }
      let message = `Прогон "${this.deleteTarget?.game_name}" будет удалён из расписания.`
      if (this.deleteTarget?.registered_count > 0) {
        message += ` Внимание: на этот прогон записано ${this.deleteTarget.registered_count} игроков!`
      }
      return message
    },
    availableRooms() {
      // Если у конвента указана площадка, показываем только её помещения
      if (this.schedule && this.schedule.venue_rooms && this.schedule.venue_rooms.length > 0) {
        return this.schedule.venue_rooms
      }
      // Иначе показываем все помещения
      return this.rooms
    },
    days() {
      if (!this.schedule) return []
      const daysSet = new Set()
      
      // Добавляем все дни конвента
      const start = new Date(this.schedule.date_start)
      const end = new Date(this.schedule.date_end)
      for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
        daysSet.add(d.toISOString().split('T')[0])
      }
      
      return Array.from(daysSet).sort()
    },
    filteredDays() {
      if (this.selectedDay) {
        return [this.selectedDay]
      }
      // Показываем только дни с прогонами или общими событиями
      return this.days.filter(day => 
        this.getRunsForDay(day).length > 0 || this.getCommonEventsForDay(day).length > 0
      )
    },
    filteredRuns() {
      if (!this.schedule || !this.schedule.runs) return []
      let runs = this.schedule.runs
      
      if (this.selectedDay) {
        runs = runs.filter(run => {
          const localDate = run.date_local || run.date
          return localDate && localDate.startsWith(this.selectedDay)
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
          return dateStr && dateStr.startsWith(this.selectedDay)
        })
      }
      
      // Сортируем по локальной дате
      return events.sort((a, b) => {
        const dateA = a.date_local || a.date
        const dateB = b.date_local || b.date
        return dateA.localeCompare(dateB)
      })
    },
    // Форматированная дата общего события для отображения (дд/мм/гггг)
    formattedCommonEventDate() {
      if (!this.commonEventForm.date) return ''
      const parts = this.commonEventForm.date.split('-')
      if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`
      }
      return this.commonEventForm.date
    }
  },
  mounted() {
    this.fetchSchedule()
    this.fetchGames()
    this.fetchRooms()
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
    
    async fetchGames() {
      try {
        const response = await fetch('/api/games/')
        if (response.ok) {
          this.games = await response.json()
        }
      } catch (err) {
        console.error('Ошибка загрузки игр:', err)
      }
    },
    
    async fetchRooms() {
      try {
        const response = await fetch('/api/rooms/')
        if (response.ok) {
          this.rooms = await response.json()
        }
      } catch (err) {
        console.error('Ошибка загрузки помещений:', err)
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
      // Для date_local просто парсим как локальное время
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
    
    // Получить локальную дату прогона (используем date_local если есть)
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
    
    pluralizeRuns(count) {
      const mod10 = count % 10
      const mod100 = count % 100
      if (mod100 >= 11 && mod100 <= 14) return 'прогонов'
      if (mod10 === 1) return 'прогон'
      if (mod10 >= 2 && mod10 <= 4) return 'прогона'
      return 'прогонов'
    },
    
    pluralizeEvents(count) {
      const mod10 = count % 10
      const mod100 = count % 100
      if (mod100 >= 11 && mod100 <= 14) return 'событий'
      if (mod10 === 1) return 'событие'
      if (mod10 >= 2 && mod10 <= 4) return 'события'
      return 'событий'
    },
    
    getCommonEventsForDay(day) {
      if (!this.schedule || !this.schedule.common_events) return []
      return this.schedule.common_events.filter(event => {
        const dateStr = event.date_local || event.date
        return dateStr && dateStr.startsWith(day)
      }).sort((a, b) => {
        const dateA = a.date_local || a.date
        const dateB = b.date_local || b.date
        return dateA.localeCompare(dateB)
      })
    },
    
    getRunsForDay(day) {
      return this.filteredRuns.filter(run => {
        const localDate = this.getRunLocalDate(run)
        return localDate && localDate.startsWith(day)
      })
    },
    
    // === Добавление/Редактирование прогона через RunEditor ===
    openAddRunModal() {
      this.runEditorMode = 'add'
      this.runEditorRun = null
      this.showRunEditor = true
    },
    
    openEditRunModal(run) {
      this.runEditorMode = 'edit'
      this.runEditorRun = run
      this.showRunEditor = true
    },
    
    closeRunEditor() {
      this.showRunEditor = false
      this.runEditorRun = null
    },
    
    async handleRunSave(runData) {
      this.runEditorLoading = true
      
      try {
        if (this.runEditorMode === 'add') {
          // Добавление нового прогона
          const data = {
            game_id: runData.game_id,
            date: runData.date,
            duration: runData.duration,
            room_ids: runData.room_ids || [],
            max_players: runData.max_players || null,
            registration_open: runData.registration_open
          }
          
          const response = await fetch(`/api/convention-events/${this.eventId}/add_run/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(data)
          })
          
          if (!response.ok) {
            const errData = await response.json()
            throw new Error(errData.error || errData.detail || 'Ошибка при добавлении прогона')
          }
        } else {
          // Редактирование прогона
          const data = {
            run_id: runData.id,
            date: runData.date,
            duration: runData.duration,
            room_ids: runData.room_ids || [],
            max_players: runData.max_players || null,
            registration_open: runData.registration_open
          }
          
          const response = await fetch(`/api/convention-events/${this.eventId}/update_run/`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(data)
          })
          
          if (!response.ok) {
            const errData = await response.json()
            throw new Error(errData.error || errData.detail || 'Ошибка при сохранении прогона')
          }
        }
        
        // Обновляем расписание
        await this.fetchSchedule()
        this.$emit('updated')
        this.closeRunEditor()
      } catch (err) {
        // Ошибка будет показана в компоненте RunEditor
        console.error('Ошибка сохранения прогона:', err.message)
      } finally {
        this.runEditorLoading = false
      }
    },
    
    handleRunError(errorMessage) {
      console.error('RunEditor error:', errorMessage)
    },
    
    // === Управление мастерами с автодополнением ===
    
    // Поиск пользователей с debounce
    searchUsers(runId) {
      const query = this.masterInputs[runId]
      
      // Сбрасываем выбранного пользователя при изменении ввода
      this.selectedUsers[runId] = null
      this.highlightedUserIndex[runId] = 0
      
      // Очищаем предыдущий таймер
      if (this.searchDebounceTimers[runId]) {
        clearTimeout(this.searchDebounceTimers[runId])
      }
      
      if (!query || query.length < 2) {
        this.userSearchResults[runId] = []
        return
      }
      
      // Debounce 300ms
      this.searchDebounceTimers[runId] = setTimeout(() => {
        this.fetchUsers(runId, query)
      }, 300)
    },
    
    async fetchUsers(runId, query) {
      this.userSearchLoading[runId] = true
      
      try {
        const response = await fetch(`/api/users/search/?q=${encodeURIComponent(query)}`)
        if (response.ok) {
          const users = await response.json()
          // Фильтруем уже добавленных мастеров
          const run = this.schedule.runs.find(r => r.id === runId)
          const existingMasterIds = (run?.masters || []).map(m => m.id)
          this.userSearchResults[runId] = users.filter(u => !existingMasterIds.includes(u.id))
        }
      } catch (err) {
        console.error('Ошибка поиска пользователей:', err)
      } finally {
        this.userSearchLoading[runId] = false
      }
    },
    
    hideUserDropdownDelayed(runId) {
      // Задержка для обработки клика по выпадающему списку
      setTimeout(() => {
        this.showUserDropdown[runId] = false
      }, 200)
    },
    
    selectUser(run, user) {
      this.masterInputs[run.id] = user.display_name
      this.selectedUsers[run.id] = user
      this.showUserDropdown[run.id] = false
      this.userSearchResults[run.id] = []
      // Автоматически добавляем мастера
      this.addMasterFromSelected(run)
    },
    
    selectFirstUser(run) {
      const users = this.userSearchResults[run.id]
      if (users && users.length > 0) {
        const idx = this.highlightedUserIndex[run.id] || 0
        this.selectUser(run, users[idx])
      }
    },
    
    highlightNextUser(runId) {
      const users = this.userSearchResults[runId]
      if (!users || users.length === 0) return
      const current = this.highlightedUserIndex[runId] || 0
      this.highlightedUserIndex[runId] = Math.min(current + 1, users.length - 1)
    },
    
    highlightPrevUser(runId) {
      const current = this.highlightedUserIndex[runId] || 0
      this.highlightedUserIndex[runId] = Math.max(current - 1, 0)
    },
    
    async addMasterFromSelected(run) {
      const user = this.selectedUsers[run.id]
      if (!user) {
        this.masterErrors[run.id] = 'Выберите пользователя из списка'
        return
      }
      
      this.masterLoading[run.id] = true
      this.masterErrors[run.id] = null
      
      try {
        const response = await fetch(`/api/runs/${run.id}/add_master/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({ username: user.username })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при добавлении мастера')
        }
        
        // Обновляем расписание
        await this.fetchSchedule()
        this.masterInputs[run.id] = ''
        this.selectedUsers[run.id] = null
      } catch (err) {
        this.masterErrors[run.id] = err.message
      } finally {
        this.masterLoading[run.id] = false
      }
    },
    
    // Для обратной совместимости (если вызывается старый метод)
    async addMaster(run) {
      const username = this.masterInputs[run.id]
      if (!username || !username.trim()) return
      
      this.masterLoading[run.id] = true
      this.masterErrors[run.id] = null
      
      try {
        const response = await fetch(`/api/runs/${run.id}/add_master/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({ username: username.trim() })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при добавлении мастера')
        }
        
        // Обновляем расписание
        await this.fetchSchedule()
        this.masterInputs[run.id] = ''
      } catch (err) {
        this.masterErrors[run.id] = err.message
      } finally {
        this.masterLoading[run.id] = false
      }
    },
    
    async removeMaster(run, master) {
      this.masterLoading[run.id] = true
      this.masterErrors[run.id] = null
      
      try {
        const response = await fetch(`/api/runs/${run.id}/remove_master/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({ user_id: master.id })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при удалении мастера')
        }
        
        // Обновляем расписание
        await this.fetchSchedule()
      } catch (err) {
        this.masterErrors[run.id] = err.message
      } finally {
        this.masterLoading[run.id] = false
      }
    },
    
    // === Удаление прогона ===
    confirmDeleteRun(run) {
      this.deleteTarget = run
      this.deleteType = 'run'
      this.showDeleteConfirm = true
    },
    
    cancelDelete() {
      this.showDeleteConfirm = false
      this.deleteTarget = null
      this.deleteType = 'run'
    },
    
    async executeDelete() {
      if (!this.deleteTarget) return
      
      this.deleteLoading = true
      
      try {
        let url, errorMessage
        
        if (this.deleteType === 'common') {
          url = `/api/convention-events/${this.eventId}/remove_common_event/?common_event_id=${this.deleteTarget.id}`
          errorMessage = 'Ошибка при удалении события'
        } else {
          url = `/api/convention-events/${this.eventId}/remove_run/?run_id=${this.deleteTarget.id}`
          errorMessage = 'Ошибка при удалении прогона'
        }
        
        const response = await fetch(url, {
          method: 'DELETE',
          headers: {
            'X-CSRFToken': this.csrfToken
          }
        })
        
        if (!response.ok && response.status !== 204) {
          const errData = await response.json()
          throw new Error(errData.error || errorMessage)
        }
        
        // Обновляем расписание
        await this.fetchSchedule()
        this.$emit('updated')
        this.cancelDelete()
      } catch (err) {
        alert(err.message)
      } finally {
        this.deleteLoading = false
      }
    },
    
    // === Общие события ===
    openAddCommonEventModal() {
      this.commonEventEditorMode = 'add'
      this.commonEventForm = {
        id: null,
        name: '',
        date: this.schedule ? this.schedule.date_start : '',
        time: '12:00',
        duration: 60,
        description: ''
      }
      this.commonEventError = null
      this.showCommonEventEditor = true
    },
    
    openEditCommonEventModal(event) {
      this.commonEventEditorMode = 'edit'
      
      // Парсим дату и время из локальной даты
      const dateStr = event.date_local || event.date
      let date = ''
      let time = '12:00'
      if (dateStr) {
        const parts = dateStr.split('T')
        date = parts[0]
        if (parts.length === 2) {
          time = parts[1].slice(0, 5)
        }
      }
      
      this.commonEventForm = {
        id: event.id,
        name: event.name,
        date: date,
        time: time,
        duration: event.duration,
        description: event.description || ''
      }
      this.commonEventError = null
      this.showCommonEventEditor = true
    },
    
    closeCommonEventEditor() {
      this.showCommonEventEditor = false
      this.commonEventError = null
    },
    
    async saveCommonEvent() {
      this.commonEventLoading = true
      this.commonEventError = null
      
      try {
        const dateTime = `${this.commonEventForm.date}T${this.commonEventForm.time}:00`
        
        const data = {
          name: this.commonEventForm.name,
          date: dateTime,
          duration: this.commonEventForm.duration,
          description: this.commonEventForm.description
        }
        
        let url, method
        
        if (this.commonEventEditorMode === 'add') {
          url = `/api/convention-events/${this.eventId}/add_common_event/`
          method = 'POST'
        } else {
          url = `/api/convention-events/${this.eventId}/update_common_event/`
          method = 'PATCH'
          data.common_event_id = this.commonEventForm.id
        }
        
        const response = await fetch(url, {
          method: method,
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify(data)
        })
        
        if (!response.ok) {
          const errData = await response.json()
          const errorMessage = errData.date?.[0] || errData.error || errData.detail || 'Ошибка при сохранении события'
          throw new Error(errorMessage)
        }
        
        // Обновляем расписание
        await this.fetchSchedule()
        this.$emit('updated')
        this.closeCommonEventEditor()
      } catch (err) {
        this.commonEventError = err.message
      } finally {
        this.commonEventLoading = false
      }
    },
    
    confirmDeleteCommonEvent(event) {
      this.deleteTarget = event
      this.deleteType = 'common'
      this.showDeleteConfirm = true
    },
    
    // === Обработка даты и времени для общего события ===
    handleCommonEventDateInput(event) {
      let value = event.target.value
      // Оставляем только цифры и слэши
      value = value.replace(/[^\d/]/g, '')
      
      // Автоматически добавляем слэши
      if (value.length === 2 && !value.includes('/')) {
        value += '/'
      } else if (value.length === 5 && value.split('/').length === 2) {
        value += '/'
      }
      
      // Ограничиваем длину
      if (value.length > 10) {
        value = value.slice(0, 10)
      }
      
      event.target.value = value
      
      // Парсим дд/мм/гггг в yyyy-mm-dd
      const parts = value.split('/')
      if (parts.length === 3 && parts[0].length === 2 && parts[1].length === 2 && parts[2].length === 4) {
        const day = parts[0]
        const month = parts[1]
        const year = parts[2]
        this.commonEventForm.date = `${year}-${month}-${day}`
      }
    },
    
    validateCommonEventDate() {
      if (!this.commonEventForm.date) return
      
      // Проверяем ограничения по дате
      if (this.schedule) {
        if (this.schedule.date_start && this.commonEventForm.date < this.schedule.date_start) {
          this.commonEventForm.date = this.schedule.date_start
        }
        if (this.schedule.date_end && this.commonEventForm.date > this.schedule.date_end) {
          this.commonEventForm.date = this.schedule.date_end
        }
      }
    },
    
    openCommonEventDatePicker() {
      if (this.$refs.commonEventDatePickerInput) {
        this.$refs.commonEventDatePickerInput.showPicker()
      }
    },
    
    handleCommonEventDatePickerChange(event) {
      const value = event.target.value
      if (value) {
        this.commonEventForm.date = value
        this.validateCommonEventDate()
      }
    },
    
    handleCommonEventTimeInput(event) {
      let value = event.target.value
      // Оставляем только цифры и двоеточие
      value = value.replace(/[^\d:]/g, '')
      
      // Автоматически добавляем двоеточие после двух цифр
      if (value.length === 2 && !value.includes(':')) {
        value += ':'
      }
      
      // Ограничиваем длину
      if (value.length > 5) {
        value = value.slice(0, 5)
      }
      
      event.target.value = value
      this.commonEventForm.time = value
    },
    
    validateCommonEventTime() {
      if (!this.commonEventForm.time) return
      
      const parts = this.commonEventForm.time.split(':')
      if (parts.length === 2) {
        let hours = parseInt(parts[0], 10) || 0
        let minutes = parseInt(parts[1], 10) || 0
        
        // Ограничиваем значения
        if (hours > 23) hours = 23
        if (hours < 0) hours = 0
        if (minutes > 59) minutes = 59
        if (minutes < 0) minutes = 0
        
        this.commonEventForm.time = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
      }
    },
    
    // === Управление регистрациями ===
    toggleRegistrations(runId) {
      this.expandedRuns[runId] = !this.expandedRuns[runId]
    },
    
    getPendingCount(run) {
      if (!run.registrations) return 0
      return run.registrations.filter(r => r.status === 'pending').length
    },
    
    sortRegistrations(registrations) {
      if (!registrations) return []
      // Сортируем: pending первыми, потом confirmed, потом waitlist, потом cancelled
      // Игротехники в конце каждой группы
      return [...registrations].sort((a, b) => {
        const statusOrder = { pending: 0, confirmed: 1, waitlist: 2, cancelled: 3 }
        if (a.is_technician !== b.is_technician) {
          return a.is_technician ? 1 : -1
        }
        return (statusOrder[a.status] || 0) - (statusOrder[b.status] || 0)
      })
    },
    
    getStatusLabel(status) {
      const labels = {
        pending: 'Заявка',
        confirmed: 'Подтв.',
        waitlist: 'Ожидание',
        cancelled: 'Отклонён'
      }
      return labels[status] || status
    },
    
    async updateRunRegistration(runId, registrationId, newStatus) {
      this.registrationUpdateLoading = registrationId
      
      try {
        const response = await fetch(`/api/runs/${runId}/update_registration/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({
            registration_id: registrationId,
            status: newStatus
          })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при обновлении статуса')
        }
        
        // Обновляем расписание
        await this.fetchSchedule()
      } catch (err) {
        alert(err.message)
      } finally {
        this.registrationUpdateLoading = null
      }
    }
  }
}
</script>

<style scoped>
/* ========== Базовые стили ========== */
.schedule-editor {
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
  cursor: pointer;
  border-radius: 8px;
}

.retry-btn:hover {
  background: #ff6b35;
  color: #0a0a0a;
}

/* ========== Шапка ========== */
.editor-header {
  max-width: 1200px;
  margin: 0 auto 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  flex-wrap: wrap;
}

.header-info h1 {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.2rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 8px;
}

.convention-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 2rem;
  color: #ff6b35;
  text-shadow: 0 0 20px rgba(255, 107, 53, 0.5);
  margin-bottom: 12px;
}

.convention-meta {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.convention-dates,
.convention-city,
.convention-venue {
  color: #00ccff;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* ========== Панель инструментов ========== */
.editor-toolbar {
  max-width: 1200px;
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

.toolbar-left {
  display: flex;
  gap: 12px;
}

.add-run-btn {
  display: flex;
  align-items: center;
  gap: 8px;
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

.add-run-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(255, 107, 53, 0.4);
}

.add-common-event-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: linear-gradient(145deg, #00ccff, #00a8d6);
  border: none;
  border-radius: 8px;
  color: #0a0a0a;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.add-common-event-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 204, 255, 0.4);
}

.add-icon {
  font-size: 1.2rem;
  font-weight: bold;
}

.toolbar-right {
  display: flex;
  gap: 16px;
  align-items: center;
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

.runs-count {
  color: #00ccff;
  font-weight: 600;
}

/* ========== Пустое расписание ========== */
.empty-schedule {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
  padding: 80px 40px;
  color: #666;
  font-size: 1.2rem;
}

/* ========== Редактор прогонов ========== */
.runs-editor {
  max-width: 1200px;
  margin: 0 auto;
}

.editor-day {
  margin-bottom: 40px;
}

.day-header {
  display: flex;
  gap: 16px;
  align-items: baseline;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid #ff6b3555;
}

.day-name {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.4rem;
  color: #ff6b35;
  text-transform: capitalize;
}

.day-date {
  color: #888;
  font-size: 1rem;
}

.day-runs-count {
  color: #00ccff;
  font-size: 0.9rem;
  margin-left: auto;
}

.day-common-events {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.common-event-card {
  display: flex;
  gap: 20px;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(145deg, rgba(0, 204, 255, 0.1), rgba(0, 180, 220, 0.05));
  border: 1px solid #00ccff55;
  border-left: 3px solid #00ccff;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.common-event-card:hover {
  border-color: #00ccff88;
  background: linear-gradient(145deg, rgba(0, 204, 255, 0.15), rgba(0, 180, 220, 0.1));
}

.common-event-time {
  color: #00ccff !important;
}

.common-event-badge {
  display: inline-block;
  font-size: 0.8rem;
  color: #00ccff;
  margin-top: 4px;
}

.common-event-description-short {
  font-size: 0.85rem;
  color: #888;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 400px;
}

.day-runs {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.run-card {
  display: flex;
  gap: 20px;
  align-items: center;
  flex-wrap: wrap;
  padding: 16px 20px;
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border: 1px solid #ff6b3533;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.run-card:hover {
  border-color: #ff6b3588;
}

.run-card.run-full {
  opacity: 0.6;
}

.run-time-block {
  flex-shrink: 0;
  width: 80px;
  text-align: center;
}

.run-time {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.1rem;
  color: #ff6b35;
  font-weight: bold;
  display: block;
}

.run-duration {
  font-size: 0.8rem;
  color: #666;
  display: block;
  margin-top: 4px;
}

.run-main {
  flex: 1;
}

.run-name {
  font-weight: 600;
  color: #e0e0e0;
  font-size: 1.1rem;
  margin-bottom: 6px;
}

.run-details {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.run-rooms {
  font-size: 0.9rem;
  color: #888;
}

/* Секция управления мастерами */
.run-masters-section {
  margin-top: 10px;
  padding: 10px 12px;
  background: rgba(0, 204, 255, 0.05);
  border-radius: 8px;
  border-left: 2px solid #00ccff55;
}

.masters-label {
  font-size: 0.85rem;
  color: #888;
  margin-bottom: 8px;
  display: block;
}

.masters-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.master-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgba(0, 204, 255, 0.15);
  border-radius: 16px;
  border: 1px solid #00ccff44;
}

.master-name {
  color: #00ccff;
  font-weight: 600;
  font-size: 0.85rem;
}

.master-remove-btn {
  width: 16px;
  height: 16px;
  padding: 0;
  background: rgba(255, 68, 68, 0.3);
  border: none;
  border-radius: 50%;
  color: #ff6b6b;
  font-size: 0.9rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.master-remove-btn:hover {
  background: #ff4444;
  color: #fff;
}

.no-masters {
  color: #666;
  font-size: 0.85rem;
}

.add-master-form {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}

.autocomplete-wrapper {
  position: relative;
  flex: 1;
}

.user-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #0a0a0a;
  border: 1px solid #00ccff;
  border-radius: 0 0 6px 6px;
  z-index: 100;
  max-height: 200px;
  overflow-y: auto;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
}

.user-dropdown-item {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid #00ccff22;
  transition: background 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-dropdown-item:last-child {
  border-bottom: none;
}

.user-dropdown-item:hover,
.user-dropdown-item.highlighted {
  background: rgba(0, 204, 255, 0.15);
}

.user-display-name {
  color: #e0e0e0;
  font-weight: 600;
  font-size: 0.9rem;
}

.user-username {
  color: #00ccff;
  font-size: 0.8rem;
}

.user-dropdown-empty {
  padding: 12px;
  color: #666;
  text-align: center;
  font-size: 0.85rem;
}

.add-master-input {
  flex: 1;
  padding: 6px 10px;
  background: rgba(10, 10, 10, 0.6);
  border: 1px solid #00ccff44;
  border-radius: 6px;
  color: #e0e0e0;
  font-size: 0.85rem;
}

.add-master-input::placeholder {
  color: #555;
}

.add-master-input:focus {
  outline: none;
  border-color: #00ccff;
}

.add-master-btn {
  padding: 6px 12px;
  background: rgba(0, 204, 255, 0.2);
  border: 1px solid #00ccff;
  border-radius: 6px;
  color: #00ccff;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s ease;
}

.add-master-btn:hover:not(:disabled) {
  background: #00ccff;
  color: #0a0a0a;
}

.add-master-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.master-error {
  margin-top: 6px;
  padding: 6px 10px;
  background: rgba(255, 68, 68, 0.15);
  border: 1px solid #ff4444;
  border-radius: 6px;
  color: #ff6b6b;
  font-size: 0.8rem;
}

.form-hint {
  font-size: 0.8rem;
  color: #666;
  margin-top: 4px;
}

.run-status {
  flex-shrink: 0;
  text-align: right;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.run-slots {
  font-size: 1.1rem;
  font-weight: 600;
  color: #00ccff;
}

.run-slots.slots-full {
  color: #ff4444;
}

.run-slots.clickable {
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 16px;
  transition: background 0.2s ease;
}

.run-slots.clickable:hover {
  background: rgba(0, 204, 255, 0.15);
}

.pending-count {
  font-size: 0.75rem;
  color: #ff9800;
  margin-left: 6px;
}

.full-badge {
  font-size: 0.7rem;
  padding: 2px 6px;
  background: #ff4444;
  color: #fff;
  border-radius: 4px;
  text-transform: uppercase;
}

.run-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.action-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 1px solid;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  transition: all 0.2s ease;
  background: transparent;
}

.action-btn.edit-btn {
  border-color: #00ccff55;
  color: #00ccff;
}

.action-btn.edit-btn:hover {
  background: rgba(0, 204, 255, 0.2);
  border-color: #00ccff;
}

.action-btn.delete-btn {
  border-color: #ff444455;
  color: #ff4444;
}

.action-btn.delete-btn:hover {
  background: rgba(255, 68, 68, 0.2);
  border-color: #ff4444;
}

/* ========== Модальные окна (для удаления) ========== */
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
  max-width: 550px;
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
}

.modal-close:hover {
  transform: scale(1.2);
}

.modal-content h2 {
  font-family: 'JetBrains Mono', monospace;
  color: #e0e0e0;
  font-size: 1.5rem;
  margin-bottom: 24px;
  padding-right: 40px;
}

.form-actions {
  display: flex;
  gap: 16px;
  justify-content: flex-end;
  margin-top: 12px;
  padding-top: 20px;
  border-top: 1px solid #ff6b3533;
}

.btn {
  padding: 12px 28px;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background: linear-gradient(145deg, #ff6b35, #e55a2b);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 107, 53, 0.35);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  border: 2px solid #666;
  color: #aaa;
}

.btn-secondary:hover {
  border-color: #888;
  color: #ccc;
}

.btn-outline {
  background: transparent;
  border: 2px solid #ff6b3566;
  color: #ff6b35;
}

.btn-outline:hover {
  border-color: #ff6b35;
  background: rgba(255, 107, 53, 0.1);
}

/* ========== Модальное окно общего события ========== */
.common-event-editor-modal {
  border-color: #00ccff;
  box-shadow: 0 0 60px rgba(0, 204, 255, 0.3);
}

.common-event-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  color: #00ccff;
  font-size: 0.9rem;
  font-weight: 600;
}

.form-input, .form-textarea {
  padding: 12px 16px;
  background: #0a0a0a;
  border: 2px solid #00ccff55;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 1rem;
  transition: border-color 0.2s ease;
}

.form-input:focus, .form-textarea:focus {
  outline: none;
  border-color: #00ccff;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row .form-group {
  flex: 1;
}

.form-error {
  padding: 12px 16px;
  background: rgba(255, 68, 68, 0.15);
  border: 1px solid #ff4444;
  border-radius: 8px;
  color: #ff6b6b;
  font-size: 0.9rem;
}

/* Date and Time inputs */
.format-hint {
  font-size: 0.75rem;
  color: #666;
  font-weight: normal;
  text-transform: none;
}

.date-picker-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}

.date-picker-wrapper .date-input {
  width: 100%;
  padding-right: 44px;
  box-sizing: border-box;
}

.date-picker-native {
  position: absolute;
  right: 40px;
  top: 0;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.date-picker-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 4px;
  line-height: 1;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.date-picker-btn:hover {
  opacity: 1;
}

.date-input,
.time-input {
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: 0.05em;
}

.date-input::placeholder,
.time-input::placeholder {
  letter-spacing: normal;
  font-family: inherit;
}

.form-group.half {
  flex: 1;
}

/* ========== Секция регистраций ========== */
.run-registrations {
  width: 100%;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ff6b3533;
}

.registrations-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.registrations-title {
  color: #00ccff;
  font-weight: 600;
  font-size: 0.95rem;
}

.close-registrations {
  background: none;
  border: none;
  color: #888;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 4px;
  line-height: 1;
}

.close-registrations:hover {
  color: #fff;
}

.registrations-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.registration-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  border-left: 3px solid #666;
  position: relative;
}

.registration-item.reg-pending {
  border-left-color: #ff9800;
  background: rgba(255, 152, 0, 0.08);
}

.registration-item.reg-confirmed {
  border-left-color: #4caf50;
}

.registration-item.reg-waitlist {
  border-left-color: #ffc107;
  opacity: 0.7;
}

.registration-item.reg-cancelled {
  border-left-color: #666;
  opacity: 0.4;
  text-decoration: line-through;
}

.registration-item.reg-technician {
  border-left-style: dashed;
}

.reg-icon {
  font-size: 1rem;
}

.reg-name {
  flex: 1;
  color: #e0e0e0;
  font-weight: 500;
}

.reg-role {
  color: #00ccff;
  font-size: 0.9rem;
}

.reg-status-badge {
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: bold;
  text-transform: uppercase;
}

.reg-status-badge.status-pending {
  background: rgba(255, 152, 0, 0.2);
  color: #ff9800;
}

.reg-status-badge.status-confirmed {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.reg-status-badge.status-waitlist {
  background: rgba(255, 193, 7, 0.2);
  color: #ffc107;
}

.reg-status-badge.status-cancelled {
  background: rgba(136, 136, 136, 0.2);
  color: #888;
}

.reg-actions {
  display: flex;
  gap: 4px;
}

.reg-action-btn {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  transition: all 0.2s ease;
}

.reg-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.reg-action-btn.confirm-btn {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.reg-action-btn.confirm-btn:hover:not(:disabled) {
  background: #4caf50;
  color: #fff;
}

.reg-action-btn.pending-btn {
  background: rgba(255, 152, 0, 0.2);
  color: #ff9800;
}

.reg-action-btn.pending-btn:hover:not(:disabled) {
  background: #ff9800;
  color: #fff;
}

.reg-action-btn.reject-btn {
  background: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

.reg-action-btn.reject-btn:hover:not(:disabled) {
  background: #f44336;
  color: #fff;
}

/* ========== Адаптив ========== */
@media (max-width: 768px) {
  .editor-header {
    flex-direction: column;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
  
  .editor-toolbar {
    flex-direction: column;
    gap: 16px;
  }
  
  .toolbar-left {
    flex-direction: column;
    width: 100%;
  }
  
  .add-run-btn,
  .add-common-event-btn {
    width: 100%;
    justify-content: center;
  }
  
  .toolbar-right {
    width: 100%;
    flex-wrap: wrap;
  }
  
  .control-select {
    flex: 1;
  }
  
  .run-card {
    flex-wrap: wrap;
  }
  
  .run-time-block {
    width: auto;
    text-align: left;
  }
  
  .run-status {
    width: 100%;
    flex-direction: row;
    justify-content: flex-start;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #ff6b3522;
    gap: 12px;
  }
  
  .run-actions {
    width: 100%;
    justify-content: flex-end;
    margin-top: 12px;
  }
  
  .form-row {
    flex-direction: column;
  }
  
  .form-actions {
    flex-direction: column-reverse;
  }
  
  .btn {
    width: 100%;
    text-align: center;
  }
}
</style>

