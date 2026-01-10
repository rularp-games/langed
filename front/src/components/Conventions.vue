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
    <div v-else class="conventions-grid">
      <div 
        v-for="convention in filteredConventions" 
        :key="convention.id" 
        class="convention-card"
        @click="openConvention(convention)"
      >
        <div class="convention-info">
          <h2 class="convention-title">{{ convention.name }}</h2>
          <div v-if="convention.organizers && convention.organizers.length > 0" class="convention-organizers">
            <span class="organizers-icon">👤</span>
            <span class="organizers-names">{{ convention.organizers.map(o => o.display_name).join(', ') }}</span>
          </div>
          <p v-if="convention.description" class="convention-description">
            {{ truncateText(convention.description, 100) }}
          </p>
          <div class="convention-stats">
            <div class="stat">
              <span class="stat-label">Проведений</span>
              <span class="stat-value">{{ convention.events_count }}</span>
            </div>
            <div v-if="convention.links && convention.links.length > 0" class="stat">
              <span class="stat-label">Ссылки</span>
              <span class="stat-value">{{ convention.links.length }}</span>
            </div>
          </div>
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
    </div>

    <!-- Модальное окно с деталями конвента -->
    <div v-if="selectedConvention" class="modal-overlay" @click.self="closeConventionModal">
      <div class="modal-content">
        <button class="modal-close" @click="closeConventionModal">×</button>
        <div class="modal-header-row">
          <h2>{{ selectedConvention.name }}</h2>
          <div class="header-actions">
            <button 
              v-if="selectedConvention.can_edit" 
              class="edit-btn" 
              @click="startEditingConvention"
              title="Редактировать"
            >
              ✏️
            </button>
            <button 
              v-if="selectedConvention.can_edit" 
              class="delete-btn" 
              @click="confirmDeleteConvention"
              title="Удалить"
            >
              🗑️
            </button>
            <button class="copy-link-btn" @click="copyConventionLink" :title="linkCopied ? 'Скопировано!' : 'Скопировать ссылку'">
              <span v-if="linkCopied">✓</span>
              <span v-else>🔗</span>
            </button>
          </div>
        </div>
        
        <div class="modal-section">
          <div class="section-header">
            <h3>{{ selectedConvention.organizers && selectedConvention.organizers.length > 1 ? 'Организаторы' : 'Организатор' }}</h3>
            <button 
              v-if="selectedConvention.can_edit && !isManagingOrganizers" 
              @click="isManagingOrganizers = true"
              class="btn-add-inline"
            >
              + Добавить
            </button>
          </div>
          <div class="organizers-list">
            <div 
              v-for="organizer in selectedConvention.organizers" 
              :key="organizer.id"
              class="organizer-item"
            >
              <span class="organizer-name">👤 {{ organizer.display_name }}</span>
              <button 
                v-if="selectedConvention.can_edit && selectedConvention.organizers.length > 1"
                class="organizer-remove"
                @click="removeOrganizer(organizer.id)"
                title="Удалить организатора"
              >
                ×
              </button>
            </div>
          </div>
          <div v-if="isManagingOrganizers" class="add-organizer-form">
            <input 
              v-model="newOrganizerUsername"
              type="text"
              class="form-input"
              placeholder="Имя пользователя"
              @keydown.enter.prevent="addOrganizer"
            />
            <div class="add-organizer-actions">
              <button @click="isManagingOrganizers = false" class="btn btn-secondary btn-sm">Отмена</button>
              <button @click="addOrganizer" class="btn btn-primary btn-sm" :disabled="!newOrganizerUsername || addOrganizerLoading">
                {{ addOrganizerLoading ? '...' : 'Добавить' }}
              </button>
            </div>
            <p v-if="addOrganizerError" class="form-error-inline">{{ addOrganizerError }}</p>
          </div>
        </div>
        
        <div class="modal-section" v-if="selectedConvention.description">
          <h3>Описание</h3>
          <p>{{ selectedConvention.description }}</p>
        </div>
        
        <div class="modal-section">
          <div class="section-header">
            <h3>Ссылки</h3>
            <button 
              v-if="selectedConvention.can_edit && !isManagingLinks" 
              @click="isManagingLinks = true"
              class="btn-add-inline"
            >
              + Добавить
            </button>
          </div>
          <div v-if="selectedConvention.links && selectedConvention.links.length > 0" class="links-list-editable">
            <div 
              v-for="link in selectedConvention.links" 
              :key="link.id"
              class="link-item-editable"
              :class="'link-type-' + link.link_type"
            >
              <a 
                :href="link.url"
                target="_blank"
                rel="noopener noreferrer"
                class="link-content"
                @click.stop
              >
                <span class="link-icon">{{ getLinkIcon(link.link_type) }}</span>
                <span class="link-title">{{ link.display_title }}</span>
              </a>
              <button 
                v-if="selectedConvention.can_edit"
                class="link-remove"
                @click="removeLink(link.id)"
                title="Удалить ссылку"
              >
                ×
              </button>
            </div>
          </div>
          <p v-else-if="!isManagingLinks" class="no-links">Ссылки не добавлены</p>
          <div v-if="isManagingLinks" class="add-link-form">
            <div class="form-group">
              <label>URL *</label>
              <input 
                v-model="newLink.url"
                type="url"
                class="form-input"
                placeholder="https://..."
              />
            </div>
            <div class="form-row">
              <div class="form-group half">
                <label>Тип</label>
                <select v-model="newLink.link_type" class="form-input">
                  <option 
                    v-for="type in linkTypes" 
                    :key="type.value" 
                    :value="type.value"
                  >
                    {{ type.label }}
                  </option>
                </select>
              </div>
              <div class="form-group half">
                <label>Название (опционально)</label>
                <input 
                  v-model="newLink.title"
                  type="text"
                  class="form-input"
                  placeholder="Название"
                />
              </div>
            </div>
            <div class="add-link-actions">
              <button @click="cancelAddLink" class="btn btn-secondary btn-sm">Отмена</button>
              <button @click="addLink" class="btn btn-primary btn-sm" :disabled="!newLink.url || addLinkLoading">
                {{ addLinkLoading ? '...' : 'Добавить' }}
              </button>
            </div>
            <p v-if="addLinkError" class="form-error-inline">{{ addLinkError }}</p>
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
              @click="openConventionEventModal(event)"
            >
              <div class="event-header-row">
                <div class="event-dates">
                  {{ formatConventionDates(event.date_start, event.date_end) }}
                </div>
                <div class="event-actions">
                  <button 
                    v-if="event.can_edit"
                    class="edit-btn-small" 
                    @click.stop="startEditingEvent(event)"
                    title="Редактировать проведение"
                  >
                    ✏️
                  </button>
                  <button 
                    v-if="event.can_edit"
                    class="delete-btn-small" 
                    @click.stop="confirmDeleteEvent(event)"
                    title="Удалить проведение"
                  >
                    🗑️
                  </button>
                  <button 
                    class="copy-link-btn-small" 
                    @click="copyEventLink(event)" 
                    :title="eventLinkCopied === event.id ? 'Скопировано!' : 'Скопировать ссылку на проведение'"
                  >
                    <span v-if="eventLinkCopied === event.id">✓</span>
                    <span v-else>🔗</span>
                  </button>
                </div>
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
              
              <!-- Блок регистрации на конвент -->
              <div class="event-registration" @click.stop>
                <div class="event-reg-info">
                  <span class="event-participants">
                    👥 {{ event.registrations_count || 0 }}{{ event.capacity ? ` / ${event.capacity}` : '' }}
                  </span>
                  <span v-if="!event.registration_open" class="event-reg-closed">закрыта</span>
                  <span v-else-if="event.is_full" class="event-reg-full">мест нет</span>
                </div>
                
                <!-- Статус регистрации текущего пользователя -->
                <div v-if="getUserRegistration(event)" class="event-user-reg">
                  <span v-if="getUserRegistration(event).status === 'pending'" class="reg-status-pending">
                    ⏳ Ожидает
                  </span>
                  <span v-else-if="getUserRegistration(event).status === 'confirmed'" class="reg-status-confirmed">
                    ✅ Участник
                  </span>
                  <span v-else-if="getUserRegistration(event).status === 'rejected'" class="reg-status-rejected">
                    ❌ Отклонена
                  </span>
                  <button 
                    v-if="getUserRegistration(event).status !== 'rejected'"
                    @click.stop="unregisterFromEvent(event)"
                    class="btn-unreg-small"
                    :disabled="eventRegLoading === event.id"
                  >
                    {{ eventRegLoading === event.id ? '...' : '×' }}
                  </button>
                </div>
                
                <!-- Кнопка регистрации -->
                <button 
                  v-else-if="event.registration_open && !event.is_full && isAuthenticated"
                  @click.stop="registerForEvent(event)"
                  class="btn-reg-small"
                  :disabled="eventRegLoading === event.id"
                >
                  {{ eventRegLoading === event.id ? '...' : '📝 Участвовать' }}
                </button>
                
                <!-- Для неавторизованных -->
                <a 
                  v-else-if="event.registration_open && !event.is_full && !isAuthenticated" 
                  href="/oidc/authenticate/"
                  class="btn-reg-small btn-login"
                  @click.stop
                >
                  Войти
                </a>
              </div>
              
              <div class="event-schedule-actions">
                <router-link 
                  :to="`/schedule/${event.id}`" 
                  class="schedule-link"
                  @click.stop
                >
                  📅 Расписание
                </router-link>
                <router-link 
                  v-if="event.can_edit"
                  :to="`/schedule/${event.id}/edit`" 
                  class="schedule-edit-link"
                  @click.stop
                >
                  ✏️ Редактировать расписание
                </router-link>
              </div>
            </div>
          </div>
          <p v-else class="no-events">Проведения пока не запланированы</p>
        </div>
      </div>
    </div>

    <!-- Модальное окно добавления/редактирования конвента через ConventionEditor -->
    <ConventionEditor
      v-if="showConventionEditor && isAuthenticated"
      :mode="conventionEditorMode"
      :convention="conventionEditorConvention"
      :csrf-token="csrfToken"
      @save="handleConventionSave"
      @cancel="closeConventionEditor"
      @error="handleConventionError"
    />

    <!-- Модальное окно импорта CSV конвентов -->
    <div v-if="showCsvImportModal && isAuthenticated" class="modal-overlay" @click.self="closeCsvImportModal">
      <div class="modal-content add-convention-modal">
        <button class="modal-close" @click="closeCsvImportModal">×</button>
        
        <h2>Импорт конвентов из CSV</h2>
        
        <div class="csv-import-form">
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
            <button type="button" @click="closeCsvImportModal" class="btn btn-secondary">Закрыть</button>
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

    <!-- Модальное окно добавления/редактирования проведения конвента через ConventionEventEditor -->
    <ConventionEventEditor
      v-if="showConventionEventEditor && isAuthenticated"
      :mode="conventionEventEditorMode"
      :convention-event="conventionEventEditorData"
      :convention-id="conventionEventEditorConventionId"
      :convention-name="conventionEventEditorConventionName"
      :lock-convention="conventionEventEditorMode === 'edit'"
      :conventions="conventions"
      :cities="cities"
      :csrf-token="csrfToken"
      @save="handleConventionEventSave"
      @cancel="closeConventionEventEditor"
      @error="handleConventionEventError"
      @city-created="handleCityCreated"
    />

    <!-- Модальное окно подтверждения удаления -->
    <DeleteConfirmModal
      v-if="showDeleteConfirm"
      :title="deleteType === 'convention' ? 'Удалить конвент?' : 'Удалить проведение?'"
      :message="deleteType === 'convention' 
        ? `Это действие нельзя отменить. Конвент '${deleteTarget?.name}' и все его проведения будут удалены.`
        : 'Это действие нельзя отменить. Проведение конвента и все связанные прогоны будут удалены.'"
      :loading="deleteLoading"
      @confirm="executeDelete"
      @cancel="cancelDelete"
    />

    <!-- Модальное окно с деталями проведения конвента -->
    <ConventionEventModal
      v-if="selectedConventionEvent"
      :event="selectedConventionEvent"
      @close="closeConventionEventModal"
    />
  </div>
</template>

<script>
import ConventionEditor from './ConventionEditor.vue'
import ConventionEventEditor from './ConventionEventEditor.vue'
import DeleteConfirmModal from './DeleteConfirmModal.vue'
import ConventionEventModal from './ConventionEventModal.vue'

export default {
  name: 'ConventionsPage',
  components: {
    ConventionEditor,
    ConventionEventEditor,
    DeleteConfirmModal,
    ConventionEventModal
  },
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
      // CSV импорт
      addLoading: false,
      addError: null,
      csvFile: null,
      csvResult: null,
      showCsvImportModal: false,
      // ConventionEditor
      showConventionEditor: false,
      conventionEditorMode: 'add',
      conventionEditorConvention: null,
      // Для проведений конвентов
      cities: [],
      linkCopied: false,
      eventLinkCopied: false,
      // Редактирование проведения конвента через ConventionEventEditor
      showConventionEventEditor: false,
      conventionEventEditorMode: 'add',
      conventionEventEditorData: null,
      conventionEventEditorConventionId: null,
      conventionEventEditorConventionName: '',
      // Удаление
      showDeleteConfirm: false,
      deleteTarget: null,
      deleteType: null,
      deleteLoading: false,
      // Управление организаторами
      isManagingOrganizers: false,
      newOrganizerUsername: '',
      addOrganizerLoading: false,
      addOrganizerError: null,
      // Управление ссылками
      isManagingLinks: false,
      newLink: {
        url: '',
        link_type: 'other',
        title: ''
      },
      addLinkLoading: false,
      addLinkError: null,
      linkTypes: [
        { value: 'vk', label: 'ВКонтакте' },
        { value: 'telegram', label: 'Telegram' },
        { value: 'website', label: 'Сайт' },
        { value: 'discord', label: 'Discord' },
        { value: 'youtube', label: 'YouTube' },
        { value: 'other', label: 'Другое' }
      ],
      // Модальное окно проведения конвента
      selectedConventionEvent: null,
      // Регистрация на конвент
      eventRegLoading: null,
      eventUserRegistrations: {}  // { eventId: registration }
    }
  },
  watch: {
    // Реагируем на изменение параметра conventionId в URL
    conventionId: {
      handler(newId, oldId) {
        // Не реагируем если значение не изменилось или модальное окно уже открыто с этим конвентом
        if (!newId || newId === oldId) return
        if (this.selectedConvention && this.selectedConvention.id === parseInt(newId, 10)) return
        if (this.conventions.length > 0) {
          this.openConventionById(newId)
        }
      },
      immediate: false
    },
    // Реагируем на изменение параметра eventId в URL
    eventId: {
      handler(newId, oldId) {
        // Не реагируем если значение не изменилось
        if (!newId || newId === oldId) return
        if (this.conventions.length > 0) {
          this.openEventById(newId)
        }
      },
      immediate: false
    },
    // Реагируем на загрузку списка конвентов (только один раз при первой загрузке)
    conventions: {
      handler(newVal, oldVal) {
        // Открываем модальное окно только при первичной загрузке (oldVal был пустым)
        const wasEmpty = !oldVal || oldVal.length === 0
        if (wasEmpty && this.conventions.length > 0 && !this.selectedConvention) {
          if (this.eventId) {
            this.openEventById(this.eventId)
          } else if (this.conventionId) {
            this.openConventionById(this.conventionId)
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
            // Передаём skipUrlUpdate=true, чтобы избежать бесконечного цикла редиректов
            await this.openConvention(convention, true)
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
      this.isManagingOrganizers = false
      this.newOrganizerUsername = ''
      this.addOrganizerError = null
      this.isManagingLinks = false
      this.newLink = { url: '', link_type: 'other', title: '' }
      this.addLinkError = null
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
    async openConvention(convention, skipUrlUpdate = false) {
      this.selectedConvention = convention
      // Обновляем URL при открытии модального окна (если не передан флаг skipUrlUpdate)
      if (!skipUrlUpdate) {
        this.updateUrlWithConvention(convention.id)
      }
      // Загрузить проведения этого конвента
      try {
        const response = await fetch(`/api/convention-events/?convention=${convention.id}`)
        if (response.ok) {
          this.conventionEvents = await response.json()
          // Собираем регистрации текущего пользователя
          this.updateUserRegistrationsCache()
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
      this.conventionEditorMode = 'add'
      this.conventionEditorConvention = null
      this.showConventionEditor = true
    },
    closeConventionEditor() {
      this.showConventionEditor = false
      this.conventionEditorConvention = null
    },
    async handleConventionSave(conventionData) {
      try {
        let response
        if (this.conventionEditorMode === 'add') {
          response = await fetch('/api/conventions/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(conventionData)
          })
        } else {
          response = await fetch(`/api/conventions/${conventionData.id}/`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(conventionData)
          })
        }
        
        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error('Необходима авторизация для сохранения конвента')
          }
          const data = await response.json()
          throw new Error(data.detail || data.name?.[0] || 'Ошибка при сохранении')
        }
        
        const savedConvention = await response.json()
        
        if (this.conventionEditorMode === 'add') {
          this.conventions.unshift(savedConvention)
        } else {
          const index = this.conventions.findIndex(c => c.id === savedConvention.id)
          if (index !== -1) {
            this.conventions.splice(index, 1, savedConvention)
          }
          if (this.selectedConvention && this.selectedConvention.id === savedConvention.id) {
            this.selectedConvention = savedConvention
          }
        }
        
        this.closeConventionEditor()
      } catch (err) {
        alert(err.message)
      }
    },
    handleConventionError(error) {
      console.error('Convention error:', error)
    },
    openCsvImportModal() {
      this.csvFile = null
      this.csvResult = null
      this.addError = null
      this.showCsvImportModal = true
    },
    closeCsvImportModal() {
      this.showCsvImportModal = false
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
    // === Проведения конвентов через ConventionEventEditor ===
    getConventionName(conventionId) {
      const convention = this.conventions.find(c => c.id === conventionId)
      return convention ? convention.name : ''
    },
    openAddEventModal(convention = null) {
      this.conventionEventEditorMode = 'add'
      this.conventionEventEditorData = null
      this.conventionEventEditorConventionId = convention ? convention.id : null
      this.conventionEventEditorConventionName = convention ? convention.name : ''
      this.showConventionEventEditor = true
    },
    startEditingEvent(event) {
      this.conventionEventEditorMode = 'edit'
      this.conventionEventEditorData = event
      this.conventionEventEditorConventionId = event.convention
      this.conventionEventEditorConventionName = this.getConventionName(event.convention)
      this.showConventionEventEditor = true
    },
    closeConventionEventEditor() {
      this.showConventionEventEditor = false
      this.conventionEventEditorData = null
    },
    handleCityCreated(newCity) {
      this.cities.push(newCity)
    },
    async handleConventionEventSave(eventData) {
      try {
        let response
        if (this.conventionEventEditorMode === 'add') {
          response = await fetch('/api/convention-events/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(eventData)
          })
        } else {
          response = await fetch(`/api/convention-events/${eventData.id}/`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(eventData)
          })
        }
        
        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error(this.conventionEventEditorMode === 'add' 
              ? 'Необходима авторизация для добавления проведения' 
              : 'Нет прав для редактирования этого проведения')
          }
          const data = await response.json()
          throw new Error(data.detail || data.non_field_errors?.[0] || 'Ошибка при сохранении')
        }
        
        // Обновляем список
        await this.fetchConventions()
        if (this.selectedConvention) {
          await this.openConvention(this.selectedConvention)
        }
        this.closeConventionEventEditor()
      } catch (err) {
        alert(err.message)
      }
    },
    handleConventionEventError(error) {
      console.error('Convention event error:', error)
    },
    
    // === Редактирование конвента (через ConventionEditor) ===
    startEditingConvention() {
      if (!this.selectedConvention) return
      
      this.conventionEditorMode = 'edit'
      this.conventionEditorConvention = this.selectedConvention
      this.showConventionEditor = true
    },
    
    // === Удаление ===
    confirmDeleteConvention() {
      this.deleteTarget = this.selectedConvention
      this.deleteType = 'convention'
      this.showDeleteConfirm = true
    },
    confirmDeleteEvent(event) {
      this.deleteTarget = event
      this.deleteType = 'event'
      this.showDeleteConfirm = true
    },
    cancelDelete() {
      this.showDeleteConfirm = false
      this.deleteTarget = null
      this.deleteType = null
    },
    async executeDelete() {
      if (!this.deleteTarget || !this.deleteType) return
      
      this.deleteLoading = true
      
      try {
        const url = this.deleteType === 'convention' 
          ? `/api/conventions/${this.deleteTarget.id}/`
          : `/api/convention-events/${this.deleteTarget.id}/`
        
        const response = await fetch(url, {
          method: 'DELETE',
          headers: {
            'X-CSRFToken': this.csrfToken
          }
        })
        
        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error('Нет прав для удаления')
          }
          throw new Error('Ошибка при удалении')
        }
        
        if (this.deleteType === 'convention') {
          // Закрываем модальное окно и обновляем список
          this.closeConventionModal()
          await this.fetchConventions()
        } else {
          // Обновляем проведения конвента
          await this.fetchConventions()
          if (this.selectedConvention) {
            await this.openConvention(this.selectedConvention)
          }
        }
        
        this.cancelDelete()
      } catch (err) {
        alert(err.message)
      } finally {
        this.deleteLoading = false
      }
    },
    
    // === Управление организаторами ===
    async addOrganizer() {
      if (!this.newOrganizerUsername || !this.selectedConvention) return
      
      this.addOrganizerLoading = true
      this.addOrganizerError = null
      
      try {
        const response = await fetch(`/api/conventions/${this.selectedConvention.id}/add_organizer/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({ username: this.newOrganizerUsername })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при добавлении организатора')
        }
        
        const updatedConvention = await response.json()
        this.selectedConvention = updatedConvention
        
        // Обновляем список конвентов
        const index = this.conventions.findIndex(c => c.id === updatedConvention.id)
        if (index !== -1) {
          this.conventions.splice(index, 1, updatedConvention)
        }
        
        this.newOrganizerUsername = ''
        this.isManagingOrganizers = false
      } catch (err) {
        this.addOrganizerError = err.message
      } finally {
        this.addOrganizerLoading = false
      }
    },
    async removeOrganizer(userId) {
      if (!this.selectedConvention) return
      
      try {
        const response = await fetch(`/api/conventions/${this.selectedConvention.id}/remove_organizer/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({ user_id: userId })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при удалении организатора')
        }
        
        const updatedConvention = await response.json()
        this.selectedConvention = updatedConvention
        
        // Обновляем список конвентов
        const index = this.conventions.findIndex(c => c.id === updatedConvention.id)
        if (index !== -1) {
          this.conventions.splice(index, 1, updatedConvention)
        }
      } catch (err) {
        alert(err.message)
      }
    },
    
    // === Управление ссылками ===
    cancelAddLink() {
      this.isManagingLinks = false
      this.newLink = { url: '', link_type: 'other', title: '' }
      this.addLinkError = null
    },
    async addLink() {
      if (!this.newLink.url || !this.selectedConvention) return
      
      this.addLinkLoading = true
      this.addLinkError = null
      
      try {
        const response = await fetch('/api/convention-links/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({
            convention_id: this.selectedConvention.id,
            url: this.newLink.url,
            link_type: this.newLink.link_type,
            title: this.newLink.title
          })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || data.url?.[0] || 'Ошибка при добавлении ссылки')
        }
        
        const newLinkData = await response.json()
        
        // Добавляем ссылку в список
        if (!this.selectedConvention.links) {
          this.selectedConvention.links = []
        }
        this.selectedConvention.links.push(newLinkData)
        
        // Обновляем список конвентов
        await this.fetchConventions()
        
        this.cancelAddLink()
      } catch (err) {
        this.addLinkError = err.message
      } finally {
        this.addLinkLoading = false
      }
    },
    async removeLink(linkId) {
      if (!this.selectedConvention) return
      
      try {
        const response = await fetch(`/api/convention-links/${linkId}/`, {
          method: 'DELETE',
          headers: {
            'X-CSRFToken': this.csrfToken
          }
        })
        
        if (!response.ok) {
          throw new Error('Ошибка при удалении ссылки')
        }
        
        // Удаляем ссылку из списка
        this.selectedConvention.links = this.selectedConvention.links.filter(l => l.id !== linkId)
        
        // Обновляем список конвентов
        await this.fetchConventions()
      } catch (err) {
        alert(err.message)
      }
    },
    
    // === Модальное окно проведения конвента ===
    openConventionEventModal(event) {
      this.selectedConventionEvent = event
    },
    closeConventionEventModal() {
      this.selectedConventionEvent = null
    },
    
    // === Регистрация на конвент ===
    getUserRegistration(event) {
      // Проверяем, есть ли у пользователя регистрация на это проведение
      // API возвращает current_user_registration если пользователь авторизован
      return this.eventUserRegistrations[event.id] || null
    },
    
    async registerForEvent(event) {
      if (!this.isAuthenticated) return
      
      this.eventRegLoading = event.id
      
      try {
        const response = await fetch(`/api/convention-events/${event.id}/register/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({ comment: '' })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при регистрации')
        }
        
        const result = await response.json()
        
        // Сохраняем регистрацию
        this.eventUserRegistrations[event.id] = result.registration
        
        // Обновляем данные события
        await this.refreshConventionEvents()
        
      } catch (err) {
        alert(err.message)
      } finally {
        this.eventRegLoading = null
      }
    },
    
    async unregisterFromEvent(event) {
      if (!confirm('Отменить регистрацию на конвент?')) return
      
      this.eventRegLoading = event.id
      
      try {
        const response = await fetch(`/api/convention-events/${event.id}/unregister/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          }
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при отмене регистрации')
        }
        
        // Удаляем регистрацию из кэша
        delete this.eventUserRegistrations[event.id]
        
        // Обновляем данные события
        await this.refreshConventionEvents()
        
      } catch (err) {
        alert(err.message)
      } finally {
        this.eventRegLoading = null
      }
    },
    
    async refreshConventionEvents() {
      if (!this.selectedConvention) return
      
      try {
        const response = await fetch(`/api/convention-events/?convention=${this.selectedConvention.id}`)
        if (response.ok) {
          this.conventionEvents = await response.json()
          // Обновляем кэш регистраций
          this.updateUserRegistrationsCache()
        }
      } catch (err) {
        console.error('Ошибка обновления проведений:', err)
      }
    },
    
    updateUserRegistrationsCache() {
      // Собираем current_user_registration из всех событий
      for (const event of this.conventionEvents) {
        if (event.current_user_registration) {
          this.eventUserRegistrations[event.id] = event.current_user_registration
        } else {
          delete this.eventUserRegistrations[event.id]
        }
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
  font-family: 'JetBrains Mono', monospace;
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

/* ========== Сетка конвентов ========== */
.conventions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.convention-card {
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border: 1px solid #ff6b3533;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
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
  z-index: 1;
  pointer-events: none;
}

.convention-card:hover::before {
  left: 100%;
}

.convention-card:hover {
  transform: translateY(-5px);
  border-color: #ff6b35;
  box-shadow: 0 10px 40px rgba(255, 107, 53, 0.2);
}

.convention-info {
  padding: 24px;
}

.convention-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.4rem;
  color: #ff6b35;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ff6b3533;
}

.convention-description {
  color: #aaa;
  line-height: 1.6;
  margin: 0 0 16px 0;
  font-size: 0.9rem;
}

.convention-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  color: #888;
  font-size: 0.9rem;
}

.stat-value {
  color: #00ccff;
  font-family: 'JetBrains Mono', monospace;
  font-weight: bold;
}

/* Организаторы в карточке конвента */
.convention-organizers {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ff6b3522;
}

.organizers-icon {
  font-size: 1rem;
  opacity: 0.8;
}

.convention-organizers .organizers-names {
  color: #aaa;
  font-size: 0.9rem;
}

/* Организаторы в модальном окне */
.modal-organizers {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(0, 204, 255, 0.08);
  border-radius: 8px;
  border-left: 3px solid #00ccff;
}

.modal-organizers .organizers-icon {
  font-size: 1.2rem;
}

.modal-organizers .organizers-label {
  color: #888;
  font-size: 0.9rem;
}

.modal-organizers .organizers-names {
  color: #00ccff;
  font-weight: 600;
}

.convention-links-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ff6b3533;
}

.link-preview-item {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #ff6b3533;
  border-radius: 8px;
  font-size: 1.1rem;
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
  margin-left: 4px;
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
  font-family: 'JetBrains Mono', monospace;
  color: #e0e0e0;
  font-size: 1.8rem;
  margin-bottom: 24px;
  padding-right: 40px;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.copy-link-btn,
.edit-btn {
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

.copy-link-btn:hover,
.edit-btn:hover {
  background: rgba(0, 204, 255, 0.2);
  border-color: #00ccff;
  transform: scale(1.1);
}

.edit-btn {
  background: rgba(255, 107, 53, 0.1);
  border-color: #ff6b3555;
  color: #ff6b35;
}

.edit-btn:hover {
  background: rgba(255, 107, 53, 0.2);
  border-color: #ff6b35;
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
  transition: all 0.3s;
  cursor: pointer;
}

.event-item:hover {
  background: rgba(255, 107, 53, 0.1);
  transform: translateX(4px);
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

.event-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.edit-btn-small {
  background: rgba(255, 107, 53, 0.1);
  border: 1px solid #ff6b3544;
  color: #ff6b35;
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

.edit-btn-small:hover {
  background: rgba(255, 107, 53, 0.2);
  border-color: #ff6b35;
  transform: scale(1.1);
}

.delete-btn,
.delete-btn-small {
  background: rgba(255, 68, 68, 0.1);
  border: 1px solid #ff444455;
  color: #ff4444;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.delete-btn {
  width: 36px;
  height: 36px;
  font-size: 1rem;
}

.delete-btn-small {
  width: 28px;
  height: 28px;
  font-size: 0.8rem;
  border-radius: 6px;
}

.delete-btn:hover,
.delete-btn-small:hover {
  background: rgba(255, 68, 68, 0.2);
  border-color: #ff4444;
  transform: scale(1.1);
}

/* Управление организаторами */
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

.organizers-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.organizer-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: rgba(0, 204, 255, 0.08);
  border-radius: 8px;
  border-left: 3px solid #00ccff;
}

.organizer-name {
  color: #00ccff;
  font-weight: 500;
}

.organizer-remove {
  background: rgba(255, 68, 68, 0.2);
  border: none;
  color: #ff4444;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  line-height: 1;
  transition: all 0.2s ease;
}

.organizer-remove:hover {
  background: #ff4444;
  color: #fff;
}

.add-organizer-form {
  padding: 16px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  border: 1px solid #ff6b3533;
}

.add-organizer-form .form-input {
  margin-bottom: 12px;
}

.add-organizer-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-sm {
  padding: 8px 16px;
  font-size: 0.9rem;
}

.form-error-inline {
  color: #ff6b6b;
  font-size: 0.85rem;
  margin-top: 8px;
}

/* Управление ссылками */
.links-list-editable {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 12px;
}

.link-item-editable {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid #ff6b3533;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.link-item-editable:hover {
  border-color: #ff6b3566;
}

.link-content {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #ccc;
  text-decoration: none;
  font-size: 0.9rem;
}

.link-content:hover {
  color: #fff;
}

.link-remove {
  background: rgba(255, 68, 68, 0.2);
  border: none;
  color: #ff4444;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  line-height: 1;
  transition: all 0.2s ease;
  margin-left: 8px;
}

.link-remove:hover {
  background: #ff4444;
  color: #fff;
}

.no-links {
  color: #666;
  font-style: italic;
}

.add-link-form {
  padding: 16px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  border: 1px solid #ff6b3533;
  margin-top: 12px;
}

.add-link-form .form-group {
  margin-bottom: 12px;
}

.add-link-form .form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.add-link-form .form-group.half {
  flex: 1;
  margin-bottom: 0;
}

.add-link-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.event-dates {
  font-family: 'JetBrains Mono', monospace;
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
  margin-bottom: 12px;
}

.games-count, .runs-count {
  color: #00ccff;
  font-size: 0.85rem;
}

/* Блок регистрации в карточке проведения */
.event-registration {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 10px;
  padding: 10px 12px;
  background: rgba(0, 204, 255, 0.08);
  border-radius: 6px;
  border-left: 2px solid #00ccff;
}

.event-reg-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.event-participants {
  color: #00ccff;
  font-weight: 600;
  font-size: 0.9rem;
}

.event-reg-closed {
  padding: 2px 8px;
  background: #666;
  color: #ccc;
  border-radius: 10px;
  font-size: 0.75rem;
}

.event-reg-full {
  padding: 2px 8px;
  background: #ff4444;
  color: #fff;
  border-radius: 10px;
  font-size: 0.75rem;
}

.event-user-reg {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.reg-status-pending {
  color: #ffaa00;
  font-size: 0.85rem;
  font-weight: 500;
}

.reg-status-confirmed {
  color: #4caf50;
  font-size: 0.85rem;
  font-weight: 500;
}

.reg-status-rejected {
  color: #ff4444;
  font-size: 0.85rem;
  font-weight: 500;
}

.btn-unreg-small {
  width: 22px;
  height: 22px;
  padding: 0;
  background: rgba(255, 68, 68, 0.2);
  border: 1px solid #ff444466;
  border-radius: 50%;
  color: #ff6b6b;
  font-size: 0.9rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.btn-unreg-small:hover:not(:disabled) {
  background: #ff4444;
  color: #fff;
}

.btn-unreg-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-reg-small {
  margin-left: auto;
  padding: 6px 12px;
  background: linear-gradient(145deg, #00ccff, #0099cc);
  border: none;
  border-radius: 6px;
  color: #fff;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-reg-small:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(0, 204, 255, 0.4);
}

.btn-reg-small:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-reg-small.btn-login {
  background: transparent;
  border: 1px solid #00ccff;
  color: #00ccff;
  text-decoration: none;
}

.btn-reg-small.btn-login:hover {
  background: rgba(0, 204, 255, 0.15);
}

.event-schedule-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid #ff6b3522;
}

.schedule-link,
.schedule-edit-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 6px;
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 600;
  transition: all 0.2s ease;
}

.schedule-link {
  background: rgba(0, 204, 255, 0.1);
  border: 1px solid #00ccff55;
  color: #00ccff;
}

.schedule-link:hover {
  background: rgba(0, 204, 255, 0.2);
  border-color: #00ccff;
  transform: translateY(-1px);
}

.schedule-edit-link {
  background: rgba(255, 107, 53, 0.1);
  border: 1px solid #ff6b3555;
  color: #ff6b35;
}

.schedule-edit-link:hover {
  background: rgba(255, 107, 53, 0.2);
  border-color: #ff6b35;
  transform: translateY(-1px);
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
  
  .conventions-grid {
    grid-template-columns: 1fr;
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


