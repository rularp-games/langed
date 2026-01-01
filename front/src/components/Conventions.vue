<template>
  <div class="page">
    <div class="page-header">
      <h1>Конвенты</h1>
      <p class="subtitle">Каталог конвентов кабинетных ролевых игр</p>
    </div>

    <!-- Панель управления -->
    <div class="controls-bar">
      <div class="controls-filters">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Поиск..."
          class="control-search"
        />
      </div>
      <button v-if="isAuthenticated" @click="openAddModal" class="add-btn">
        <span class="add-icon">+</span>
        Добавить конвент
      </button>
    </div>

    <!-- Загрузка -->
    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>Загрузка...</p>
    </div>

    <!-- Ошибка -->
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="fetchConventions" class="retry-btn">Повторить</button>
    </div>

    <!-- Пустой список -->
    <div v-else-if="filteredConventions.length === 0" class="empty">
      <p v-if="searchQuery">Конвенты не найдены по запросу "{{ searchQuery }}"</p>
      <p v-else>Конвенты пока не добавлены</p>
    </div>

    <!-- Список конвентов -->
    <div v-else class="conventions-list">
      <div 
        v-for="convention in filteredConventions" 
        :key="convention.id" 
        class="convention-card"
        @click="openConvention(convention)"
      >
        <div class="convention-header">
          <h2 class="convention-title">{{ convention.name }}</h2>
          <span class="events-count">
            {{ convention.events_count }} {{ pluralizeEvents(convention.events_count) }}
          </span>
        </div>
        <div v-if="convention.organizer" class="convention-organizer">
          <span class="organizer-icon">👤</span>
          <span class="organizer-name">{{ convention.organizer.display_name }}</span>
        </div>
        <p v-if="convention.description" class="convention-description">
          {{ truncateText(convention.description, 150) }}
        </p>
        <p v-else class="no-description">Описание отсутствует</p>
        <div v-if="convention.links && convention.links.length > 0" class="convention-links-preview">
          <a 
            v-for="link in convention.links.slice(0, 4)" 
            :key="link.id"
            :href="link.url"
            target="_blank"
            rel="noopener noreferrer"
            class="link-preview-item"
            :title="link.display_title"
            @click.stop
          >{{ getLinkIcon(link.link_type) }}</a>
          <span v-if="convention.links.length > 4" class="links-more">+{{ convention.links.length - 4 }}</span>
        </div>
      </div>
    </div>

    <!-- Модальное окно с деталями конвента -->
    <div v-if="selectedConvention" class="modal-overlay" @click.self="closeConventionModal">
      <div class="modal-content">
        <button class="modal-close" @click="closeConventionModal">×</button>
        <div class="modal-header-row">
          <h2>{{ selectedConvention.name }}</h2>
          <button class="copy-link-btn" @click="copyConventionLink" :title="linkCopied ? 'Скопировано!' : 'Скопировать ссылку'">
            <span v-if="linkCopied">✓</span>
            <span v-else>🔗</span>
          </button>
        </div>
        
        <div v-if="selectedConvention.organizer" class="modal-organizer">
          <span class="organizer-icon">👤</span>
          <span class="organizer-label">Организатор:</span>
          <span class="organizer-name">{{ selectedConvention.organizer.display_name }}</span>
        </div>
        
        <div class="modal-section" v-if="selectedConvention.description">
          <h3>Описание</h3>
          <p>{{ selectedConvention.description }}</p>
        </div>
        
        <div class="modal-section" v-if="selectedConvention.links && selectedConvention.links.length > 0">
          <h3>Ссылки</h3>
          <div class="links-list">
            <a 
              v-for="link in selectedConvention.links" 
              :key="link.id"
              :href="link.url"
              target="_blank"
              rel="noopener noreferrer"
              class="link-item"
              :class="'link-type-' + link.link_type"
              @click.stop
            >
              <span class="link-icon">{{ getLinkIcon(link.link_type) }}</span>
              <span class="link-title">{{ link.display_title }}</span>
            </a>
          </div>
        </div>
        
        <div class="modal-section">
          <div class="section-header">
            <h3>Проведения конвента</h3>
            <button 
              v-if="isAuthenticated" 
              @click="openAddEventModal(selectedConvention)" 
              class="btn-add-inline"
            >
              + Добавить
            </button>
          </div>
          <div v-if="conventionEvents.length > 0" class="events-list">
            <div 
              v-for="event in conventionEvents" 
              :key="event.id" 
              class="event-item"
              :class="{ 'past-event': isEventPast(event.date_end) }"
            >
              <div class="event-header-row">
                <div class="event-dates">
                  {{ formatConventionDates(event.date_start, event.date_end) }}
                </div>
                <button 
                  class="copy-link-btn-small" 
                  @click="copyEventLink(event)" 
                  :title="eventLinkCopied === event.id ? 'Скопировано!' : 'Скопировать ссылку на проведение'"
                >
                  <span v-if="eventLinkCopied === event.id">✓</span>
                  <span v-else>🔗</span>
                </button>
              </div>
              <div class="event-city">📍 {{ event.city_name || (event.city && event.city.name) }}</div>
              <div class="event-stats">
                <span class="games-count" v-if="event.games && event.games.length > 0">
                  🎮 {{ event.games.length }} {{ pluralizeGames(event.games.length) }}
                </span>
                <span class="runs-count" v-if="event.runs_count > 0">
                  🎯 {{ event.runs_count }} {{ pluralizeRuns(event.runs_count) }}
                </span>
              </div>
            </div>
          </div>
          <p v-else class="no-events">Проведения пока не запланированы</p>
        </div>
      </div>
    </div>

    <!-- Модальное окно добавления конвента -->
    <div v-if="showAddModal && isAuthenticated" class="modal-overlay" @click.self="closeAddModal">
      <div class="modal-content add-convention-modal">
        <button class="modal-close" @click="closeAddModal">×</button>
        
        <h2>Добавить конвент</h2>
        
        <!-- Переключатель режима -->
        <div class="mode-switcher">
          <button 
            type="button" 
            :class="['mode-btn', { active: addMode === 'single' }]"
            @click="addMode = 'single'"
          >
            Один конвент
          </button>
          <button 
            type="button" 
            :class="['mode-btn', { active: addMode === 'csv' }]"
            @click="addMode = 'csv'"
          >
            Импорт из CSV
          </button>
        </div>
        
        <!-- Форма одного конвента -->
        <form v-if="addMode === 'single'" @submit.prevent="submitConvention" class="add-form">
          <div class="form-group">
            <label for="conv-name">Название *</label>
            <input 
              id="conv-name"
              v-model="newConvention.name" 
              type="text" 
              required
              class="form-input"
              placeholder="Введите название конвента"
            />
          </div>
          
          <div class="form-group">
            <label for="conv-description">Описание</label>
            <textarea 
              id="conv-description"
              v-model="newConvention.description"
              class="form-input form-textarea"
              placeholder="Описание конвента"
              rows="3"
            ></textarea>
          </div>
          
          <div v-if="addError" class="form-error">{{ addError }}</div>
          
          <div class="form-actions">
            <button type="button" @click="closeAddModal" class="btn btn-secondary">Отмена</button>
            <button type="submit" class="btn btn-primary" :disabled="addLoading">
              <span v-if="addLoading">Сохранение...</span>
              <span v-else>Добавить</span>
            </button>
          </div>
        </form>
        
        <!-- Форма импорта CSV -->
        <div v-else class="csv-import-form">
          <div class="csv-upload">
            <label class="csv-dropzone" for="csv-file" :class="{ 'has-file': csvFile }">
              <span class="csv-icon">📄</span>
              <span v-if="csvFile" class="csv-filename">{{ csvFile.name }}</span>
              <span v-else class="csv-text">Выберите CSV файл</span>
              <span class="csv-hint">Формат: название мероприятия, город, дата начала, дата конца</span>
            </label>
            <input 
              id="csv-file"
              type="file"
              accept=".csv"
              @change="onCsvChange"
              class="csv-input"
            />
            <button 
              v-if="csvFile" 
              type="button" 
              @click="removeCsv" 
              class="csv-remove"
            >
              Удалить файл
            </button>
          </div>
          
          <div v-if="addError" class="form-error">{{ addError }}</div>
          
          <div v-if="csvResult" class="csv-result">
            <p class="csv-result-success">
              Конвентов создано: {{ csvResult.conventions_created }}
            </p>
            <p class="csv-result-success">
              Проведений создано: {{ csvResult.events_created }}
            </p>
            <p v-if="csvResult.events_skipped > 0" class="csv-result-skipped">
              Пропущено (уже существуют): {{ csvResult.events_skipped }}
            </p>
          </div>
          
          <div class="form-actions">
            <button type="button" @click="closeAddModal" class="btn btn-secondary">Закрыть</button>
            <button 
              type="button" 
              @click="submitCsv" 
              class="btn btn-primary" 
              :disabled="addLoading || !csvFile"
            >
              <span v-if="addLoading">Импорт...</span>
              <span v-else>Импортировать</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно добавления проведения конвента -->
    <div v-if="showAddEventModal && isAuthenticated" class="modal-overlay" @click.self="closeAddEventModal">
      <div class="modal-content add-event-modal">
        <button class="modal-close" @click="closeAddEventModal">×</button>
        
        <h2>Добавить проведение конвента</h2>
        
        <form @submit.prevent="submitEvent" class="add-form">
          <div class="form-group">
            <label for="event-convention">Конвент *</label>
            <select 
              id="event-convention"
              v-model="newEvent.convention_id" 
              required
              class="form-input"
            >
              <option :value="null" disabled>Выберите конвент</option>
              <option 
                v-for="conv in conventions" 
                :key="conv.id" 
                :value="conv.id"
              >
                {{ conv.name }}
              </option>
            </select>
          </div>
          
          <div class="form-group">
            <label for="event-city">Город *</label>
            <select 
              id="event-city"
              v-model="newEvent.city_id" 
              required
              class="form-input"
            >
              <option :value="null" disabled>Выберите город</option>
              <option 
                v-for="city in cities" 
                :key="city.id" 
                :value="city.id"
              >
                {{ city.name }}{{ city.region && city.region.name ? ` (${city.region.name})` : '' }}
              </option>
              <option value="new">+ Создать новый город</option>
            </select>
          </div>
          
          <div v-if="newEvent.city_id === 'new'" class="form-group">
            <label for="new-city-name">Название нового города *</label>
            <input 
              id="new-city-name"
              v-model="newEvent.newCityName" 
              type="text" 
              required
              class="form-input"
              placeholder="Введите название города"
            />
          </div>
          
          <div class="form-row">
            <div class="form-group half">
              <label for="event-date-start">Дата начала *</label>
              <input 
                id="event-date-start"
                v-model="newEvent.date_start" 
                type="date" 
                required
                class="form-input"
              />
            </div>
            
            <div class="form-group half">
              <label for="event-date-end">Дата окончания *</label>
              <input 
                id="event-date-end"
                v-model="newEvent.date_end" 
                type="date" 
                required
                class="form-input"
              />
            </div>
          </div>
          
          <div v-if="addEventError" class="form-error">{{ addEventError }}</div>
          
          <div class="form-actions">
            <button type="button" @click="closeAddEventModal" class="btn btn-secondary">Отмена</button>
            <button type="submit" class="btn btn-primary" :disabled="addEventLoading">
              <span v-if="addEventLoading">Сохранение...</span>
              <span v-else>Добавить</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConventionsPage',
  inject: ['getUser'],
  props: {
    conventionId: {
      type: [String, Number],
      default: null
    },
    eventId: {
      type: [String, Number],
      default: null
    }
  },
  data() {
    return {
      conventions: [],
      loading: true,
      error: null,
      searchQuery: '',
      selectedConvention: null,
      conventionEvents: [],
      showAddModal: false,
      addMode: 'single',
      addLoading: false,
      addError: null,
      newConvention: { name: '', description: '' },
      csvFile: null,
      csvResult: null,
      // Для добавления проведения конвента
      showAddEventModal: false,
      addEventLoading: false,
      addEventError: null,
      cities: [],
      newEvent: {
        convention_id: null,
        city_id: null,
        newCityName: '',
        date_start: '',
        date_end: ''
      },
      linkCopied: false,
      eventLinkCopied: false
    }
  },
  watch: {
    // Реагируем на изменение параметра conventionId в URL
    conventionId: {
      handler(newId) {
        if (newId && this.conventions.length > 0) {
          this.openConventionById(newId)
        }
      },
      immediate: false
    },
    // Реагируем на изменение параметра eventId в URL
    eventId: {
      handler(newId) {
        if (newId && this.conventions.length > 0) {
          this.openEventById(newId)
        }
      },
      immediate: false
    },
    // Реагируем на загрузку списка конвентов
    conventions: {
      handler() {
        if (this.conventions.length > 0 && !this.selectedConvention) {
          if (this.conventionId) {
            this.openConventionById(this.conventionId)
          } else if (this.eventId) {
            this.openEventById(this.eventId)
          }
        }
      }
    }
  },
  computed: {
    isAuthenticated() {
      const user = this.getUser()
      return user && user.is_authenticated
    },
    csrfToken() {
      const match = document.cookie.match(/csrftoken=([^;]+)/)
      return match ? match[1] : ''
    },
    filteredConventions() {
      let result = this.conventions
      if (this.searchQuery) {
        const query = this.searchQuery.toLowerCase()
        result = result.filter(c => 
          c.name.toLowerCase().includes(query) ||
          (c.description && c.description.toLowerCase().includes(query))
        )
      }
      return result.slice().sort((a, b) => a.name.localeCompare(b.name, 'ru'))
    }
  },
  mounted() {
    this.fetchConventions()
    this.fetchCities()
  },
  methods: {
    openConventionById(id) {
      const convId = parseInt(id, 10)
      const convention = this.conventions.find(c => c.id === convId)
      if (convention) {
        this.openConvention(convention)
        this.updateUrlWithConvention(convention.id)
      }
    },
    async openEventById(id) {
      const eventId = parseInt(id, 10)
      // Ищем конвент, у которого есть это проведение
      try {
        const response = await fetch(`/api/convention-events/${eventId}/`)
        if (response.ok) {
          const event = await response.json()
          // Найдём конвент
          const convention = this.conventions.find(c => c.id === event.convention)
          if (convention) {
            await this.openConvention(convention)
            this.updateUrlWithEvent(eventId)
          }
        }
      } catch (err) {
        console.error('Ошибка загрузки проведения:', err)
      }
    },
    closeConventionModal() {
      this.selectedConvention = null
      this.conventionEvents = []
      this.linkCopied = false
      this.eventLinkCopied = false
      this.updateUrlWithConvention(null)
    },
    updateUrlWithConvention(conventionId) {
      const query = { ...this.$route.query }
      if (conventionId) {
        query.id = conventionId
        delete query.event
      } else {
        delete query.id
        delete query.event
      }
      this.$router.replace({ query }).catch(() => {})
    },
    updateUrlWithEvent(eventId) {
      const query = { ...this.$route.query }
      if (eventId) {
        query.event = eventId
        delete query.id
      } else {
        delete query.event
      }
      this.$router.replace({ query }).catch(() => {})
    },
    copyConventionLink() {
      if (!this.selectedConvention) return
      const url = `${window.location.origin}/conventions?id=${this.selectedConvention.id}`
      navigator.clipboard.writeText(url).then(() => {
        this.linkCopied = true
        setTimeout(() => {
          this.linkCopied = false
        }, 2000)
      }).catch(err => {
        console.error('Ошибка копирования:', err)
      })
    },
    copyEventLink(event) {
      const url = `${window.location.origin}/conventions?event=${event.id}`
      navigator.clipboard.writeText(url).then(() => {
        this.eventLinkCopied = event.id
        setTimeout(() => {
          this.eventLinkCopied = false
        }, 2000)
      }).catch(err => {
        console.error('Ошибка копирования:', err)
      })
    },
    async fetchConventions() {
      this.loading = true
      this.error = null
      try {
        const response = await fetch('/api/conventions/')
        if (!response.ok) {
          throw new Error('Ошибка загрузки данных')
        }
        this.conventions = await response.json()
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    },
    async openConvention(convention) {
      this.selectedConvention = convention
      // Загрузить проведения этого конвента
      try {
        const response = await fetch(`/api/convention-events/?convention=${convention.id}`)
        if (response.ok) {
          this.conventionEvents = await response.json()
        }
      } catch (err) {
        console.error('Ошибка загрузки проведений:', err)
        this.conventionEvents = []
      }
    },
    truncateText(text, maxLength) {
      if (text.length <= maxLength) return text
      return text.substring(0, maxLength) + '...'
    },
    formatConventionDates(startStr, endStr) {
      const start = new Date(startStr)
      const end = new Date(endStr)
      const startDay = start.getDate()
      const endDay = end.getDate()
      const month = start.toLocaleDateString('ru-RU', { month: 'long' })
      const year = start.getFullYear()
      
      if (start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear()) {
        return `${startDay}–${endDay} ${month} ${year}`
      }
      const startFormatted = start.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' })
      const endFormatted = end.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' })
      return `${startFormatted} — ${endFormatted}`
    },
    isEventPast(dateEndStr) {
      const endDate = new Date(dateEndStr)
      endDate.setHours(23, 59, 59, 999)
      return endDate < new Date()
    },
    pluralizeEvents(count) {
      const mod10 = count % 10
      const mod100 = count % 100
      if (mod100 >= 11 && mod100 <= 14) return 'проведений'
      if (mod10 === 1) return 'проведение'
      if (mod10 >= 2 && mod10 <= 4) return 'проведения'
      return 'проведений'
    },
    pluralizeGames(count) {
      const mod10 = count % 10
      const mod100 = count % 100
      if (mod100 >= 11 && mod100 <= 14) return 'игр'
      if (mod10 === 1) return 'игра'
      if (mod10 >= 2 && mod10 <= 4) return 'игры'
      return 'игр'
    },
    pluralizeRuns(count) {
      const mod10 = count % 10
      const mod100 = count % 100
      if (mod100 >= 11 && mod100 <= 14) return 'прогонов'
      if (mod10 === 1) return 'прогон'
      if (mod10 >= 2 && mod10 <= 4) return 'прогона'
      return 'прогонов'
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
    openAddModal() {
      this.newConvention = { name: '', description: '' }
      this.addMode = 'single'
      this.addError = null
      this.csvFile = null
      this.csvResult = null
      this.showAddModal = true
    },
    closeAddModal() {
      this.showAddModal = false
      this.addError = null
      this.csvFile = null
      this.csvResult = null
    },
    onCsvChange(event) {
      const file = event.target.files[0]
      if (!file) return
      this.csvFile = file
      this.csvResult = null
      this.addError = null
    },
    removeCsv() {
      this.csvFile = null
      this.csvResult = null
      const input = document.getElementById('csv-file')
      if (input) input.value = ''
    },
    async submitConvention() {
      this.addLoading = true
      this.addError = null
      
      try {
        const response = await fetch('/api/conventions/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify(this.newConvention)
        })
        
        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error('Необходима авторизация для добавления конвента')
          }
          const data = await response.json()
          throw new Error(data.detail || data.name?.[0] || 'Ошибка при сохранении')
        }
        
        const createdConvention = await response.json()
        this.conventions.unshift(createdConvention)
        this.closeAddModal()
      } catch (err) {
        this.addError = err.message
      } finally {
        this.addLoading = false
      }
    },
    async submitCsv() {
      if (!this.csvFile) return
      
      this.addLoading = true
      this.addError = null
      this.csvResult = null
      
      try {
        const formData = new FormData()
        formData.append('file', this.csvFile)
        
        const response = await fetch('/api/conventions/import_csv/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.csrfToken
          },
          body: formData
        })
        
        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error('Необходима авторизация для импорта')
          }
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при импорте')
        }
        
        const result = await response.json()
        this.csvResult = result
        
        // Обновляем список конвентов
        await this.fetchConventions()
        
        // Очищаем файл
        this.csvFile = null
        const input = document.getElementById('csv-file')
        if (input) input.value = ''
      } catch (err) {
        this.addError = err.message
      } finally {
        this.addLoading = false
      }
    },
    
    // === Проведения конвентов ===
    async fetchCities() {
      try {
        const response = await fetch('/api/cities/')
        if (response.ok) {
          this.cities = await response.json()
        }
      } catch (err) {
        console.error('Ошибка загрузки городов:', err)
      }
    },
    openAddEventModal(convention = null) {
      this.newEvent = {
        convention_id: convention ? convention.id : null,
        city_id: null,
        newCityName: '',
        date_start: '',
        date_end: ''
      }
      this.addEventError = null
      this.showAddEventModal = true
    },
    closeAddEventModal() {
      this.showAddEventModal = false
      this.addEventError = null
    },
    async submitEvent() {
      this.addEventLoading = true
      this.addEventError = null
      
      try {
        let cityId = this.newEvent.city_id
        
        // Если выбрано создание нового города
        if (cityId === 'new' && this.newEvent.newCityName.trim()) {
          const cityResponse = await fetch('/api/cities/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify({ name: this.newEvent.newCityName.trim() })
          })
          
          if (!cityResponse.ok) {
            throw new Error('Ошибка при создании города')
          }
          
          const newCity = await cityResponse.json()
          cityId = newCity.id
          this.cities.push(newCity)
        }
        
        if (!cityId || cityId === 'new') {
          throw new Error('Выберите или создайте город')
        }
        
        const eventData = {
          convention_id: this.newEvent.convention_id,
          city_id: cityId,
          date_start: this.newEvent.date_start,
          date_end: this.newEvent.date_end
        }
        
        const response = await fetch('/api/convention-events/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify(eventData)
        })
        
        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error('Необходима авторизация для добавления проведения')
          }
          const data = await response.json()
          throw new Error(data.detail || data.non_field_errors?.[0] || 'Ошибка при сохранении')
        }
        
        // Обновляем список
        await this.fetchConventions()
        if (this.selectedConvention) {
          await this.openConvention(this.selectedConvention)
        }
        this.closeAddEventModal()
      } catch (err) {
        this.addEventError = err.message
      } finally {
        this.addEventLoading = false
      }
    }
  }
}
</script>

<style scoped>
/* ========== Базовые стили страницы ========== */
.page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%);
  padding: 40px 20px;
  color: #e0e0e0;
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
}

.page-header h1 {
  font-family: 'Orbitron', 'Courier New', monospace;
  font-size: 3rem;
  color: #ff6b35;
  text-shadow: 0 0 20px rgba(255, 107, 53, 0.5);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.subtitle {
  color: #888;
  font-size: 1.1rem;
  letter-spacing: 0.1em;
}

/* ========== Панель управления ========== */
.controls-bar {
  display: flex;
  gap: 16px;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 40px;
  padding: 16px 24px;
  background: rgba(26, 26, 46, 0.6);
  border-radius: 12px;
  border: 1px solid #ff6b3533;
  max-width: 1000px;
  margin-left: auto;
  margin-right: auto;
}

.controls-filters {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
  flex: 1;
}

.control-search {
  flex: 1;
  min-width: 200px;
  padding: 12px 20px;
  background: #0a0a0a;
  border: 2px solid #ff6b3555;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 1rem;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.control-search::placeholder {
  color: #666;
}

.control-search:focus {
  outline: none;
  border-color: #ff6b35;
  box-shadow: 0 0 15px rgba(255, 107, 53, 0.2);
}

.add-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: linear-gradient(145deg, #ff6b35, #e55a2b);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.add-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(255, 107, 53, 0.4);
}

.add-btn:active {
  transform: translateY(0);
}

.add-icon {
  font-size: 1.2rem;
  font-weight: bold;
}

/* ========== Загрузка / Ошибка / Пустой список ========== */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
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

.empty {
  text-align: center;
  padding: 60px;
  color: #666;
  font-size: 1.2rem;
}

/* ========== Список конвентов ========== */
.conventions-list {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.convention-card {
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border: 1px solid #ff6b3533;
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.convention-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 107, 53, 0.1), transparent);
  transition: left 0.5s;
}

.convention-card:hover::before {
  left: 100%;
}

.convention-card:hover {
  transform: translateY(-3px);
  border-color: #ff6b35;
  box-shadow: 0 10px 40px rgba(255, 107, 53, 0.2);
}

.convention-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.convention-title {
  font-family: 'Orbitron', 'Courier New', monospace;
  font-size: 1.4rem;
  color: #e0e0e0;
  margin: 0;
}

.events-count {
  color: #00ccff;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
  padding: 4px 12px;
  background: rgba(0, 204, 255, 0.1);
  border-radius: 20px;
  border: 1px solid rgba(0, 204, 255, 0.3);
}

.convention-description {
  color: #aaa;
  line-height: 1.6;
  margin: 0;
}

.no-description {
  color: #555;
  font-style: italic;
  margin: 0;
}

/* Организатор в карточке конвента */
.convention-organizer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.organizer-icon {
  font-size: 0.9rem;
  opacity: 0.8;
}

.convention-organizer .organizer-name {
  color: #00ccff;
  font-size: 0.9rem;
}

/* Организатор в модальном окне */
.modal-organizer {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(0, 204, 255, 0.08);
  border-radius: 8px;
  border-left: 3px solid #00ccff;
}

.modal-organizer .organizer-icon {
  font-size: 1.2rem;
}

.modal-organizer .organizer-label {
  color: #888;
  font-size: 0.9rem;
}

.modal-organizer .organizer-name {
  color: #00ccff;
  font-weight: 600;
}

.convention-links-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #ff6b3522;
}

.link-preview-item {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #ff6b3533;
  border-radius: 6px;
  font-size: 1rem;
  text-decoration: none;
  transition: all 0.2s ease;
}

.link-preview-item:hover {
  background: rgba(255, 107, 53, 0.2);
  border-color: #ff6b35;
  transform: scale(1.1);
}

.links-more {
  color: #888;
  font-size: 0.85rem;
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
  max-width: 700px;
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

.modal-header-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 24px;
}

.modal-header-row h2 {
  flex: 1;
  margin-bottom: 0;
  padding-right: 0;
}

.modal-content h2 {
  font-family: 'Orbitron', 'Courier New', monospace;
  color: #e0e0e0;
  font-size: 1.8rem;
  margin-bottom: 24px;
  padding-right: 40px;
}

.copy-link-btn {
  background: rgba(0, 204, 255, 0.1);
  border: 1px solid #00ccff55;
  color: #00ccff;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.copy-link-btn:hover {
  background: rgba(0, 204, 255, 0.2);
  border-color: #00ccff;
  transform: scale(1.1);
}

.copy-link-btn-small {
  background: rgba(0, 204, 255, 0.1);
  border: 1px solid #00ccff44;
  color: #00ccff;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.copy-link-btn-small:hover {
  background: rgba(0, 204, 255, 0.2);
  border-color: #00ccff;
  transform: scale(1.1);
}

.modal-section {
  margin-bottom: 24px;
}

.modal-section h3 {
  color: #ff6b35;
  font-size: 1rem;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.modal-section p {
  color: #ccc;
  line-height: 1.6;
  white-space: pre-wrap;
}

/* ========== Список проведений ========== */
.events-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.event-item {
  padding: 16px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  border-left: 3px solid #ff6b35;
  transition: opacity 0.3s;
}

.event-item.past-event {
  opacity: 0.5;
  border-left-color: #666;
}

.event-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.event-dates {
  font-family: 'Courier New', monospace;
  color: #ff6b35;
  font-size: 0.9rem;
  font-weight: bold;
}

.event-city {
  color: #aaa;
  margin-bottom: 8px;
}

.event-stats {
  display: flex;
  gap: 16px;
}

.games-count, .runs-count {
  color: #00ccff;
  font-size: 0.85rem;
}

.no-events {
  color: #666;
  font-style: italic;
}

/* ========== Ссылки конвента ========== */
.links-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.link-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #ff6b3533;
  border-radius: 8px;
  color: #ccc;
  text-decoration: none;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.link-item:hover {
  background: rgba(255, 107, 53, 0.15);
  border-color: #ff6b35;
  color: #fff;
  transform: translateY(-2px);
}

.link-icon {
  font-size: 1rem;
}

.link-title {
  color: inherit;
}

/* Типы ссылок */
.link-type-vk:hover {
  background: rgba(0, 119, 255, 0.2);
  border-color: #0077ff;
}

.link-type-telegram:hover {
  background: rgba(0, 136, 204, 0.2);
  border-color: #0088cc;
}

.link-type-discord:hover {
  background: rgba(114, 137, 218, 0.2);
  border-color: #7289da;
}

.link-type-youtube:hover {
  background: rgba(255, 0, 0, 0.2);
  border-color: #ff0000;
}

/* Скроллбар */
.modal-content::-webkit-scrollbar {
  width: 8px;
}

.modal-content::-webkit-scrollbar-track {
  background: #0a0a0a;
}

.modal-content::-webkit-scrollbar-thumb {
  background: #ff6b35;
  border-radius: 4px;
}

/* ========== Форма добавления конвента ========== */
.add-convention-modal {
  max-width: 550px;
}

.add-convention-modal h2 {
  margin-bottom: 20px;
}

/* Переключатель режима */
.mode-switcher {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  padding: 4px;
  background: rgba(10, 10, 10, 0.5);
  border-radius: 10px;
}

.mode-btn {
  flex: 1;
  padding: 10px 16px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #888;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.mode-btn:hover {
  color: #ccc;
}

.mode-btn.active {
  background: linear-gradient(145deg, #ff6b35, #e55a2b);
  color: #fff;
}

.add-form, .csv-import-form {
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
  color: #ff6b35;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.form-input {
  padding: 12px 16px;
  background: rgba(10, 10, 10, 0.6);
  border: 2px solid #ff6b3544;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 1rem;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.form-input::placeholder {
  color: #555;
}

.form-input:focus {
  outline: none;
  border-color: #ff6b35;
  box-shadow: 0 0 15px rgba(255, 107, 53, 0.15);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
  font-family: inherit;
}

.form-error {
  background: rgba(255, 68, 68, 0.15);
  border: 1px solid #ff4444;
  border-radius: 8px;
  padding: 12px 16px;
  color: #ff6b6b;
  font-size: 0.95rem;
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

.btn-primary {
  background: linear-gradient(145deg, #ff6b35, #e55a2b);
  border: none;
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

/* CSV импорт */
.csv-upload {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.csv-input {
  display: none;
}

.csv-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 24px;
  background: rgba(10, 10, 10, 0.4);
  border: 2px dashed #ff6b3555;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.csv-dropzone:hover {
  border-color: #ff6b35;
  background: rgba(255, 107, 53, 0.05);
}

.csv-dropzone.has-file {
  border-color: #00ccff;
  background: rgba(0, 204, 255, 0.05);
}

.csv-icon {
  font-size: 3rem;
  opacity: 0.7;
}

.csv-text {
  color: #aaa;
  font-size: 1rem;
}

.csv-filename {
  color: #00ccff;
  font-size: 1rem;
  font-weight: 600;
}

.csv-hint {
  color: #666;
  font-size: 0.85rem;
  text-align: center;
}

.csv-remove {
  align-self: center;
  padding: 8px 20px;
  background: transparent;
  border: 1px solid #ff4444;
  border-radius: 6px;
  color: #ff4444;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.csv-remove:hover {
  background: #ff4444;
  color: #fff;
}

.csv-result {
  background: rgba(0, 204, 255, 0.1);
  border: 1px solid #00ccff55;
  border-radius: 8px;
  padding: 16px;
}

.csv-result-success {
  color: #00ccff;
  font-size: 1rem;
  margin-bottom: 4px;
}

.csv-result-skipped {
  color: #888;
  font-size: 0.9rem;
}

/* ========== Заголовок секции ========== */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-header h3 {
  margin-bottom: 0;
}

.btn-add-inline {
  padding: 6px 14px;
  background: transparent;
  border: 1px solid #00ccff;
  border-radius: 6px;
  color: #00ccff;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-add-inline:hover {
  background: #00ccff;
  color: #0a0a0a;
}

/* ========== Форма добавления проведения ========== */
.add-event-modal {
  max-width: 550px;
}

.add-event-modal h2 {
  margin-bottom: 20px;
}

.form-row {
  display: flex;
  gap: 20px;
}

.form-group.half {
  flex: 1;
}

/* ========== Адаптив ========== */
@media (max-width: 768px) {
  .page-header h1 {
    font-size: 2rem;
  }
  
  .controls-bar {
    flex-direction: column;
    gap: 16px;
  }
  
  .controls-filters {
    width: 100%;
  }
  
  .control-search {
    width: 100%;
    min-width: 100%;
  }
  
  .add-btn {
    width: 100%;
    justify-content: center;
  }
  
  .convention-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .convention-title {
    font-size: 1.2rem;
  }
  
  .form-actions {
    flex-direction: column-reverse;
  }
  
  .form-row {
    flex-direction: column;
  }
  
  .btn {
    width: 100%;
    text-align: center;
  }
}
</style>


