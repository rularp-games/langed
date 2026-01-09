<template>
  <div class="page">
    <div class="page-header">
      <h1>Афиша</h1>
      <p class="subtitle">Расписание прогонов и конвентов</p>
    </div>

    <!-- Переключатель табов -->
    <div class="tabs">
      <button 
        :class="{ active: activeTab === 'runs' }" 
        @click="activeTab = 'runs'"
      >
        Прогоны
      </button>
      <button 
        :class="{ active: activeTab === 'conventions' }" 
        @click="activeTab = 'conventions'"
      >
        Конвенты
      </button>
    </div>

    <!-- ========== ПРОГОНЫ ========== -->
    <template v-if="activeTab === 'runs'">
      <!-- Панель управления -->
      <div class="controls-bar">
        <div class="controls-filters">
          <select v-model="selectedCity" @change="fetchRuns" class="control-select">
            <option value="">Все города</option>
            <option v-for="city in cities" :key="city" :value="city">
              {{ city }}
            </option>
          </select>
          
          <div class="toggle-buttons">
            <button 
              :class="{ active: timeFilter === 'upcoming' }" 
              @click="setTimeFilter('upcoming')"
            >
              Предстоящие
            </button>
            <button 
              :class="{ active: timeFilter === 'past' }" 
              @click="setTimeFilter('past')"
            >
              Прошедшие
            </button>
            <button 
              :class="{ active: timeFilter === '' }" 
              @click="setTimeFilter('')"
            >
              Все
            </button>
          </div>
        </div>
        
        <button v-if="isAuthenticated" @click="openAddRunModal" class="add-btn">
          <span class="add-icon">+</span>
          Добавить прогон
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
        <button @click="fetchRuns" class="retry-btn">Повторить</button>
      </div>

      <!-- Пустой список -->
      <div v-else-if="runs.length === 0" class="empty">
        <p>Прогоны не найдены</p>
      </div>

      <!-- Таблица прогонов -->
      <div v-else class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Дата</th>
              <th>Время</th>
              <th>Игра</th>
              <th>Город</th>
              <th>Площадка</th>
              <th>Конвент</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="run in runs" 
              :key="run.id"
              :class="{ 'past-row': isPast(run.date) }"
              @click="openRunModal(run)"
              class="clickable-row"
            >
              <td class="date-cell">{{ formatDateLocal(run.date_local || run.date) }}</td>
              <td class="time-cell">
                {{ formatTimeLocal(run.date_local || run.date) }}
                <span class="timezone-hint">{{ getTimezoneAbbr(run.city_timezone) }}</span>
              </td>
              <td class="name-cell">
                <span class="primary-text">{{ run.game.name }}</span>
                <span class="secondary-text">
                  {{ run.game.players_min }}–{{ run.game.players_max }} игроков
                </span>
              </td>
              <td class="city-cell">{{ run.city }}</td>
              <td class="venue-cell">
                <span v-if="run.venue_name">{{ run.venue_name }}</span>
                <span v-else class="no-data">—</span>
              </td>
              <td class="convention-cell">
                <span v-if="run.convention_name" class="convention-badge">
                  {{ run.convention_name }}
                </span>
                <span v-else class="no-data">—</span>
              </td>
              <td class="status-cell">
                <span :class="['status-badge', isPast(run.date) ? 'past' : 'upcoming']">
                  {{ isPast(run.date) ? 'Завершён' : 'Предстоит' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- ========== КОНВЕНТЫ ========== -->
    <template v-if="activeTab === 'conventions'">
      <!-- Панель управления -->
      <div class="controls-bar">
        <div class="controls-filters">
          <select v-model="selectedConventionCity" @change="fetchConventions" class="control-select">
            <option value="">Все города</option>
            <option v-for="city in conventionCities" :key="city" :value="city">
              {{ city }}
            </option>
          </select>
          
          <div class="toggle-buttons">
            <button 
              :class="{ active: conventionTimeFilter === 'upcoming' }" 
              @click="setConventionTimeFilter('upcoming')"
            >
              Предстоящие
            </button>
            <button 
              :class="{ active: conventionTimeFilter === 'past' }" 
              @click="setConventionTimeFilter('past')"
            >
              Прошедшие
            </button>
            <button 
              :class="{ active: conventionTimeFilter === '' }" 
              @click="setConventionTimeFilter('')"
            >
              Все
            </button>
          </div>
        </div>
        
        <button v-if="isAuthenticated" @click="openAddEventModal" class="add-btn">
          <span class="add-icon">+</span>
          Добавить проведение
        </button>
      </div>

      <!-- Загрузка -->
      <div v-if="conventionsLoading" class="loading">
        <div class="loading-spinner"></div>
        <p>Загрузка...</p>
      </div>

      <!-- Ошибка -->
      <div v-else-if="conventionsError" class="error">
        <p>{{ conventionsError }}</p>
        <button @click="fetchConventions" class="retry-btn">Повторить</button>
      </div>

      <!-- Пустой список -->
      <div v-else-if="conventions.length === 0" class="empty">
        <p>Конвенты не найдены</p>
      </div>

      <!-- Карточки проведений конвентов -->
      <div v-else class="conventions-grid">
        <div 
          v-for="event in conventions" 
          :key="event.id" 
          class="convention-card"
          :class="{ 'past-card': isConventionPast(event.date_end) }"
          @click="openConventionModal(event)"
        >
          <div class="convention-dates">
            {{ formatConventionDates(event.date_start, event.date_end) }}
          </div>
          <h2 class="convention-title">{{ event.convention_name }}</h2>
          <div class="convention-city">📍 {{ event.city_name || (event.city && event.city.name) }}</div>
          <div class="convention-stats">
            <span class="games-count">
              {{ event.games ? event.games.length : 0 }} {{ pluralizeGames(event.games ? event.games.length : 0) }}
            </span>
            <span :class="['status-badge', isConventionPast(event.date_end) ? 'past' : 'upcoming']">
              {{ isConventionPast(event.date_end) ? 'Завершён' : getConventionStatus(event) }}
            </span>
          </div>
          <div v-if="event.links && event.links.length > 0" class="convention-links-preview">
            <a 
              v-for="link in event.links.slice(0, 4)" 
              :key="link.id"
              :href="link.url"
              target="_blank"
              rel="noopener noreferrer"
              class="link-preview-item"
              :title="link.display_title"
              @click.stop
            >{{ getLinkIcon(link.link_type) }}</a>
            <span v-if="event.links.length > 4" class="links-more">+{{ event.links.length - 4 }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- Модальное окно с деталями прогона -->
    <div v-if="selectedRun" class="modal-overlay" @click.self="closeRunModal">
      <div class="modal-content run-modal">
        <button class="modal-close" @click="closeRunModal">×</button>
        <div class="modal-run-date">
          {{ formatDateLocal(selectedRun.date_local || selectedRun.date) }}
          <span class="modal-run-time">{{ formatTimeLocal(selectedRun.date_local || selectedRun.date) }}</span>
          <span class="timezone-hint">{{ getTimezoneAbbr(selectedRun.city_timezone) }}</span>
        </div>
        <div class="modal-header-row">
          <h2>{{ selectedRun.game.name }}</h2>
          <div class="header-actions">
            <button 
              v-if="selectedRun.can_edit" 
              class="edit-btn" 
              @click="startEditingRun"
              title="Редактировать"
            >
              ✏️
            </button>
            <button 
              v-if="selectedRun.can_edit" 
              class="delete-btn" 
              @click="confirmDeleteRun"
              title="Удалить"
            >
              🗑️
            </button>
            <button class="copy-link-btn" @click="copyRunLink" :title="runLinkCopied ? 'Скопировано!' : 'Скопировать ссылку'">
              <span v-if="runLinkCopied">✓</span>
              <span v-else>🔗</span>
            </button>
          </div>
        </div>
        <div class="modal-city">📍 {{ selectedRun.city }}</div>
        
        <div class="modal-section" v-if="selectedRun.venue_name || (selectedRun.rooms && selectedRun.rooms.length > 0)">
          <h3>Площадка</h3>
          <p v-if="selectedRun.venue_name" class="venue-name">🏢 {{ selectedRun.venue_name }}</p>
          <p v-if="selectedRun.rooms && selectedRun.rooms.length > 0" class="rooms-list">
            🚪 {{ selectedRun.rooms.map(r => r.name + (r.blackbox ? ' [blackbox]' : '')).join(', ') }}
          </p>
        </div>
        
        <div class="modal-section" v-if="selectedRun.convention_name">
          <h3>Конвент</h3>
          <p class="convention-badge-lg">{{ selectedRun.convention_name }}</p>
        </div>
        
        <div class="modal-section">
          <div class="section-header">
            <h3>{{ selectedRun.masters && selectedRun.masters.length > 1 ? 'Мастера' : 'Мастер' }}</h3>
            <button 
              v-if="selectedRun.can_edit && !isManagingMasters" 
              @click="isManagingMasters = true"
              class="btn-add-inline"
            >
              + Добавить
            </button>
          </div>
          <div class="masters-list">
            <div 
              v-for="master in selectedRun.masters" 
              :key="master.id"
              class="master-item"
            >
              <span class="master-name">👤 {{ master.display_name }}</span>
              <button 
                v-if="selectedRun.can_edit && selectedRun.masters.length > 1"
                class="master-remove"
                @click="removeMaster(master.id)"
                title="Удалить мастера"
              >
                ×
              </button>
            </div>
          </div>
          <div v-if="isManagingMasters" class="add-master-form">
            <input 
              v-model="newMasterUsername"
              type="text"
              class="form-input"
              placeholder="Имя пользователя"
              @keydown.enter.prevent="addMaster"
            />
            <div class="add-master-actions">
              <button @click="isManagingMasters = false" class="btn btn-secondary btn-sm">Отмена</button>
              <button @click="addMaster" class="btn btn-primary btn-sm" :disabled="!newMasterUsername || addMasterLoading">
                {{ addMasterLoading ? '...' : 'Добавить' }}
              </button>
            </div>
            <p v-if="addMasterError" class="form-error-inline">{{ addMasterError }}</p>
          </div>
        </div>
        
        <!-- Секция регистрации -->
        <div class="modal-section registration-section" v-if="!isPast(selectedRun.date)">
          <div class="section-header">
            <h3>Запись на игру</h3>
            <div class="registration-stats">
              <span class="registration-count" :class="{ 'full': selectedRun.is_full }">
                {{ selectedRun.registered_count || 0 }} / {{ selectedRun.effective_max_players || selectedRun.game.players_max }}
              </span>
              <span v-if="selectedRun.is_full" class="full-badge">Мест нет</span>
            </div>
          </div>
          
          <!-- Форма регистрации / статус регистрации -->
          <div v-if="isAuthenticated">
            <!-- Уже зарегистрирован -->
            <div v-if="selectedRun.current_user_registration" class="user-registration">
              <div class="registration-status-card">
                <span class="registration-status-icon">✓</span>
                <div class="registration-status-info">
                  <span class="registration-status-text">
                    {{ selectedRun.current_user_registration.is_technician ? 'Вы записаны как игротехник' : 'Вы записаны на игру' }}
                  </span>
                  <span class="registration-role">
                    {{ getRolePreferenceText(selectedRun.current_user_registration.role_preference) }}
                  </span>
                  <span v-if="selectedRun.current_user_registration.status === 'waitlist'" class="waitlist-badge">
                    В листе ожидания
                  </span>
                </div>
                <button 
                  @click="unregisterFromRun"
                  class="btn btn-danger btn-sm"
                  :disabled="registrationLoading"
                >
                  {{ registrationLoading ? '...' : 'Отменить' }}
                </button>
              </div>
            </div>
            
            <!-- Форма записи -->
            <div v-else-if="selectedRun.registration_open" class="registration-form">
              <div class="form-row">
                <div class="form-group half">
                  <label>Предпочтение по роли</label>
                  <select v-model="registrationData.role_preference" class="form-input">
                    <option value="any">Любая</option>
                    <option value="female">Женская</option>
                    <option value="male">Мужская</option>
                  </select>
                </div>
                <div class="form-group half">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="registrationData.is_technician" />
                    <span>Записаться как игротехник</span>
                  </label>
                </div>
              </div>
              <div class="form-group">
                <label>Комментарий (опционально)</label>
                <textarea 
                  v-model="registrationData.comment"
                  class="form-input form-textarea"
                  placeholder="Дополнительная информация для мастера"
                  rows="2"
                ></textarea>
              </div>
              <div v-if="registrationError" class="form-error">{{ registrationError }}</div>
              <button 
                @click="registerForRun"
                class="btn btn-primary btn-register"
                :disabled="registrationLoading"
              >
                {{ registrationLoading ? 'Запись...' : (selectedRun.is_full && !registrationData.is_technician ? 'Записаться в лист ожидания' : 'Записаться') }}
              </button>
            </div>
            
            <!-- Регистрация закрыта -->
            <div v-else class="registration-closed">
              <p>Регистрация на этот прогон закрыта</p>
            </div>
          </div>
          
          <!-- Не авторизован -->
          <div v-else class="registration-login">
            <p>Чтобы записаться на игру, <a href="/oidc/authenticate/">войдите</a> в систему</p>
          </div>
          
          <!-- Список участников -->
          <div v-if="selectedRun.registrations && selectedRun.registrations.length > 0" class="participants-list">
            <div class="participants-header">
              <h4>Участники ({{ selectedRun.registrations.filter(r => r.status === 'confirmed' && !r.is_technician).length }})</h4>
            </div>
            <div class="participants-grid">
              <div 
                v-for="reg in sortedRegistrations" 
                :key="reg.id"
                class="participant-item"
                :class="{ 
                  'technician': reg.is_technician,
                  'waitlist': reg.status === 'waitlist',
                  'cancelled': reg.status === 'cancelled'
                }"
              >
                <span class="participant-icon">{{ reg.is_technician ? '🎭' : '👤' }}</span>
                <span class="participant-name">{{ reg.user.display_name }}</span>
                <span class="participant-role" v-if="!reg.is_technician && reg.role_preference !== 'any'">
                  {{ reg.role_preference === 'female' ? '♀' : '♂' }}
                </span>
                <span v-if="reg.status === 'waitlist'" class="participant-waitlist">ожидание</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="modal-stats">
          <div class="modal-stat">
            <span class="modal-stat-label">Игроки</span>
            <span class="modal-stat-value">{{ selectedRun.game.players_min }} – {{ selectedRun.game.players_max }}</span>
          </div>
          <div class="modal-stat">
            <span class="modal-stat-label">Жен. роли</span>
            <span class="modal-stat-value">{{ selectedRun.game.female_roles_min }} – {{ selectedRun.game.female_roles_max }}</span>
          </div>
          <div class="modal-stat">
            <span class="modal-stat-label">Муж. роли</span>
            <span class="modal-stat-value">{{ selectedRun.game.male_roles_min }} – {{ selectedRun.game.male_roles_max }}</span>
          </div>
          <div class="modal-stat" v-if="selectedRun.duration">
            <span class="modal-stat-label">Длительность</span>
            <span class="modal-stat-value">{{ formatDuration(selectedRun.duration) }}</span>
          </div>
        </div>
        
        <div :class="['modal-status', isPast(selectedRun.date) ? 'past' : 'upcoming']">
          {{ isPast(selectedRun.date) ? 'Завершён' : 'Предстоит' }}
        </div>
      </div>
    </div>

    <!-- Модальное окно с деталями проведения конвента -->
    <div v-if="selectedConvention" class="modal-overlay" @click.self="closeConventionModal">
      <div class="modal-content">
        <button class="modal-close" @click="closeConventionModal">×</button>
        <div class="modal-dates">
          {{ formatConventionDates(selectedConvention.date_start, selectedConvention.date_end) }}
        </div>
        <div class="modal-header-row">
          <h2>{{ selectedConvention.convention_name }}</h2>
          <button class="copy-link-btn" @click="copyEventLink" :title="eventLinkCopied ? 'Скопировано!' : 'Скопировать ссылку'">
            <span v-if="eventLinkCopied">✓</span>
            <span v-else>🔗</span>
          </button>
        </div>
        <div class="modal-city">📍 {{ selectedConvention.city_name || (selectedConvention.city && selectedConvention.city.name) }}</div>
        
        <div class="modal-section" v-if="selectedConvention.organizers && selectedConvention.organizers.length > 0">
          <h3>{{ selectedConvention.organizers.length > 1 ? 'Организаторы' : 'Организатор' }}</h3>
          <div class="modal-organizers">
            <span class="organizers-icon">👤</span>
            <span class="organizers-names">{{ selectedConvention.organizers.map(o => o.display_name).join(', ') }}</span>
          </div>
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
        
        <div class="modal-section" v-if="selectedConvention.games && selectedConvention.games.length > 0">
          <h3>Игры на конвенте ({{ selectedConvention.games.length }})</h3>
          <div class="modal-games-list">
            <div v-for="game in sortedConventionGames" :key="game.id" class="modal-game-item">
              <span class="modal-game-name">{{ game.name }}</span>
              <span class="modal-game-players">{{ game.players_min }}–{{ game.players_max }} игроков</span>
            </div>
          </div>
        </div>
        
        <!-- Ссылки на расписание -->
        <div class="modal-section schedule-links-section">
          <h3>Расписание</h3>
          <div class="schedule-links">
            <router-link 
              :to="`/schedule/${selectedConvention.id}`" 
              class="schedule-link"
            >
              📅 Посмотреть расписание
            </router-link>
            <router-link 
              v-if="selectedConvention.can_edit"
              :to="`/schedule/${selectedConvention.id}/edit`" 
              class="schedule-edit-link"
            >
              ✏️ Редактировать расписание
            </router-link>
          </div>
        </div>
        
        <div v-if="!selectedConvention.games || selectedConvention.games.length === 0" class="modal-section">
          <p class="no-runs">Игры пока не добавлены</p>
        </div>
      </div>
    </div>

    <!-- Модальное окно добавления проведения конвента -->
    <div v-if="showAddEventModal" class="modal-overlay" @click.self="closeAddEventModal">
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
                v-for="conv in allConventions" 
                :key="conv.id" 
                :value="conv.id"
              >
                {{ conv.name }}
              </option>
            </select>
          </div>
          
          <div class="form-group searchable-select">
            <label for="event-city">Город *</label>
            <input 
              id="event-city"
              v-model="eventCitySearch"
              type="text"
              class="form-input"
              placeholder="Введите название города..."
              autocomplete="off"
              @focus="showEventCityDropdown = true"
              @blur="onEventCityInputBlur"
              @keydown.enter.prevent
            />
            <div v-if="showEventCityDropdown" class="dropdown-list">
              <div 
                v-for="city in filteredEventCitiesList" 
                :key="city.id" 
                class="dropdown-item"
                :class="{ selected: newEvent.city_id === city.id }"
                @mousedown.prevent="selectEventCity(city)"
              >
                {{ city.name }}{{ city.region && city.region.name ? ` (${city.region.name})` : '' }}
              </div>
              <div 
                class="dropdown-item dropdown-item-new"
                @mousedown.prevent="selectNewEventCity"
              >
                + Создать новый город
              </div>
              <div v-if="filteredEventCitiesList.length === 0 && eventCitySearch" class="dropdown-empty">
                Города не найдены
              </div>
            </div>
            <input type="hidden" :value="newEvent.city_id" required />
          </div>
          
          <div v-if="newEvent.city_id === 'new'" class="form-group">
            <label for="new-event-city-name">Название нового города *</label>
            <input 
              id="new-event-city-name"
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

    <!-- Модальное окно добавления/редактирования прогона -->
    <RunEditor
      v-if="showRunEditor"
      :mode="runEditorMode"
      :run="runEditorRun"
      :convention-event-id="runEditorRun ? runEditorRun.convention_event : null"
      :lock-convention="false"
      :lock-game="false"
      :games="games"
      :cities="allCities"
      :convention-events="runEditorMode === 'add' ? conventionEvents : allConventionEvents"
      :allow-new-city="true"
      :csrf-token="csrfToken"
      @save="handleRunEditorSave"
      @cancel="closeRunEditor"
      @error="handleRunEditorError"
      @city-created="onCityCreated"
    />

    <!-- Модальное окно подтверждения удаления -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="cancelDelete">
      <div class="modal-content delete-confirm-modal">
        <button class="modal-close" @click="cancelDelete">×</button>
        
        <h2>Удалить {{ deleteType === 'run' ? 'прогон' : 'проведение конвента' }}?</h2>
        
        <p class="delete-warning">
          Это действие нельзя отменить. 
          <template v-if="deleteType === 'run'">
            Прогон будет удалён из расписания.
          </template>
          <template v-else>
            Проведение конвента и все связанные прогоны будут удалены.
          </template>
        </p>
        
        <div class="form-actions">
          <button type="button" @click="cancelDelete" class="btn btn-secondary">Отмена</button>
          <button type="button" @click="executeDelete" class="btn btn-danger" :disabled="deleteLoading">
            <span v-if="deleteLoading">Удаление...</span>
            <span v-else>Удалить</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import RunEditor from './RunEditor.vue'

export default {
  name: 'AfishaPage',
  components: {
    RunEditor
  },
  inject: ['getUser'],
  props: {
    runId: {
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
      activeTab: 'runs',
      // Прогоны
      runs: [],
      cities: [],
      selectedCity: '',
      timeFilter: 'upcoming',
      loading: true,
      error: null,
      selectedRun: null,
      runLinkCopied: false,
      // Конвенты
      conventions: [],
      conventionCities: [],
      selectedConventionCity: '',
      conventionTimeFilter: 'upcoming',
      conventionsLoading: true,
      conventionsError: null,
      selectedConvention: null,
      eventLinkCopied: false,
      // Данные для формы прогона
      games: [],
      allCities: [],
      conventionEvents: [],
      // Единый редактор прогона
      showRunEditor: false,
      runEditorMode: 'add',
      runEditorRun: null,
      runEditorLoading: false,
      // Для добавления проведения конвента
      showAddEventModal: false,
      addEventLoading: false,
      addEventError: null,
      allConventions: [],
      newEvent: {
        convention_id: null,
        city_id: null,
        newCityName: '',
        date_start: '',
        date_end: ''
      },
      eventCitySearch: '',
      showEventCityDropdown: false,
      // Для редактирования прогона - все проведения конвентов
      allConventionEvents: [],
      // Удаление
      showDeleteConfirm: false,
      deleteTarget: null,
      deleteType: null,
      deleteLoading: false,
      // Управление мастерами
      isManagingMasters: false,
      newMasterUsername: '',
      addMasterLoading: false,
      addMasterError: null,
      // Регистрация на прогон
      registrationLoading: false,
      registrationError: null,
      registrationData: {
        role_preference: 'any',
        is_technician: false,
        comment: ''
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
    sortedGames() {
      return this.games.slice().sort((a, b) => a.name.localeCompare(b.name, 'ru'))
    },
    sortedConventionGames() {
      if (!this.selectedConvention || !this.selectedConvention.games) {
        return []
      }
      return this.selectedConvention.games.slice().sort((a, b) => a.name.localeCompare(b.name, 'ru'))
    },
    sortedRegistrations() {
      if (!this.selectedRun || !this.selectedRun.registrations) {
        return []
      }
      // Сортируем: сначала confirmed игроки, потом technicians, потом waitlist
      return this.selectedRun.registrations.slice().sort((a, b) => {
        const statusOrder = { confirmed: 0, pending: 1, waitlist: 2, cancelled: 3 }
        if (a.is_technician !== b.is_technician) {
          return a.is_technician ? 1 : -1
        }
        const statusDiff = (statusOrder[a.status] || 0) - (statusOrder[b.status] || 0)
        if (statusDiff !== 0) return statusDiff
        return 0
      })
    },
    sortedCities() {
      return this.allCities.slice().sort((a, b) => a.name.localeCompare(b.name, 'ru'))
    },
    filteredEventCitiesList() {
      if (!this.eventCitySearch) {
        return this.sortedCities
      }
      const query = this.eventCitySearch.toLowerCase()
      return this.sortedCities.filter(c => {
        const regionName = c.region && c.region.name ? c.region.name : ''
        return c.name.toLowerCase().includes(query) || 
          regionName.toLowerCase().includes(query)
      })
    },
    selectedEventCityName() {
      if (!this.newEvent.city_id) return ''
      if (this.newEvent.city_id === 'new') return ''
      const city = this.allCities.find(c => c.id === this.newEvent.city_id)
      if (!city) return ''
      const regionName = city.region && city.region.name ? city.region.name : ''
      return regionName ? `${city.name} (${regionName})` : city.name
    }
  },
  watch: {
    // Реагируем на изменение параметра runId в URL
    runId: {
      handler(newId) {
        if (newId) {
          this.activeTab = 'runs'
          this.openRunById(newId)
        }
      },
      immediate: false
    },
    // Реагируем на изменение параметра eventId в URL
    eventId: {
      handler(newId) {
        if (newId) {
          this.activeTab = 'conventions'
          this.openEventById(newId)
        }
      },
      immediate: false
    },
    // Реагируем на загрузку прогонов
    runs: {
      handler() {
        if (this.runId && this.runs.length > 0 && !this.selectedRun) {
          this.openRunById(this.runId)
        }
      }
    },
    // Реагируем на загрузку проведений конвентов
    conventions: {
      handler() {
        if (this.eventId && this.conventions.length > 0 && !this.selectedConvention) {
          this.openEventById(this.eventId)
        }
      }
    }
  },
  mounted() {
    this.fetchCities()
    this.fetchRuns()
    this.fetchConventionCities()
    this.fetchConventions()
    this.fetchGames()
    this.fetchAllCities()
    this.fetchConventionEvents()
    this.fetchAllConventions()
    this.fetchAllConventionEvents()
  },
  methods: {
    // === Работа с URL ===
    async openRunById(id) {
      const runId = parseInt(id, 10)
      // Сначала ищем в уже загруженных прогонах
      let run = this.runs.find(r => r.id === runId)
      if (!run) {
        // Если не нашли, загружаем с сервера
        try {
          const response = await fetch(`/api/runs/${runId}/`)
          if (response.ok) {
            run = await response.json()
          }
        } catch (err) {
          console.error('Ошибка загрузки прогона:', err)
        }
      }
      if (run) {
        this.selectedRun = run
        this.updateUrlWithRun(run.id)
      }
    },
    openEventById(id) {
      const eventId = parseInt(id, 10)
      const event = this.conventions.find(e => e.id === eventId)
      if (event) {
        this.selectedConvention = event
        this.updateUrlWithEvent(event.id)
      }
    },
    openRunModal(run) {
      this.selectedRun = run
      this.updateUrlWithRun(run.id)
    },
    closeRunModal() {
      this.selectedRun = null
      this.runLinkCopied = false
      this.isManagingMasters = false
      this.newMasterUsername = ''
      this.addMasterError = null
      this.updateUrlWithRun(null)
    },
    openConventionModal(event) {
      this.selectedConvention = event
      this.updateUrlWithEvent(event.id)
    },
    closeConventionModal() {
      this.selectedConvention = null
      this.eventLinkCopied = false
      this.updateUrlWithEvent(null)
    },
    updateUrlWithRun(runId) {
      const query = { ...this.$route.query }
      if (runId) {
        query.run = runId
        delete query.event
      } else {
        delete query.run
      }
      this.$router.replace({ query }).catch(() => {})
    },
    updateUrlWithEvent(eventId) {
      const query = { ...this.$route.query }
      if (eventId) {
        query.event = eventId
        delete query.run
      } else {
        delete query.event
      }
      this.$router.replace({ query }).catch(() => {})
    },
    copyRunLink() {
      if (!this.selectedRun) return
      const url = `${window.location.origin}/?run=${this.selectedRun.id}`
      navigator.clipboard.writeText(url).then(() => {
        this.runLinkCopied = true
        setTimeout(() => {
          this.runLinkCopied = false
        }, 2000)
      }).catch(err => {
        console.error('Ошибка копирования:', err)
      })
    },
    copyEventLink() {
      if (!this.selectedConvention) return
      const url = `${window.location.origin}/?event=${this.selectedConvention.id}`
      navigator.clipboard.writeText(url).then(() => {
        this.eventLinkCopied = true
        setTimeout(() => {
          this.eventLinkCopied = false
        }, 2000)
      }).catch(err => {
        console.error('Ошибка копирования:', err)
      })
    },
    
    // === Прогоны ===
    async fetchCities() {
      try {
        const response = await fetch('/api/runs/cities/')
        if (response.ok) {
          this.cities = await response.json()
        }
      } catch (err) {
        console.error('Ошибка загрузки городов:', err)
      }
    },
    async fetchRuns() {
      this.loading = true
      this.error = null
      try {
        const params = new URLSearchParams()
        if (this.selectedCity) {
          params.append('city', this.selectedCity)
        }
        if (this.timeFilter) {
          params.append('time', this.timeFilter)
        }
        
        const url = '/api/runs/' + (params.toString() ? '?' + params.toString() : '')
        const response = await fetch(url)
        
        if (!response.ok) {
          throw new Error('Ошибка загрузки данных')
        }
        const runsData = await response.json()
        // Прямая сортировка по дате (от ранних к поздним)
        this.runs = runsData.sort((a, b) => new Date(a.date) - new Date(b.date))
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    },
    setTimeFilter(filter) {
      this.timeFilter = filter
      this.fetchRuns()
    },
    
    // === Конвенты (проведения) ===
    async fetchConventionCities() {
      try {
        const response = await fetch('/api/convention-events/cities/')
        if (response.ok) {
          this.conventionCities = await response.json()
        }
      } catch (err) {
        console.error('Ошибка загрузки городов конвентов:', err)
      }
    },
    async fetchConventions() {
      this.conventionsLoading = true
      this.conventionsError = null
      try {
        const params = new URLSearchParams()
        if (this.selectedConventionCity) {
          params.append('city', this.selectedConventionCity)
        }
        if (this.conventionTimeFilter) {
          params.append('time', this.conventionTimeFilter)
        }
        
        const url = '/api/convention-events/' + (params.toString() ? '?' + params.toString() : '')
        const response = await fetch(url)
        
        if (!response.ok) {
          throw new Error('Ошибка загрузки данных')
        }
        const conventionsData = await response.json()
        // Обратная сортировка по дате начала (от недавних к давним)
        this.conventions = conventionsData.sort((a, b) => new Date(b.date_start) - new Date(a.date_start))
      } catch (err) {
        this.conventionsError = err.message
      } finally {
        this.conventionsLoading = false
      }
    },
    setConventionTimeFilter(filter) {
      this.conventionTimeFilter = filter
      this.fetchConventions()
    },
    
    // === Форматирование ===
    formatDateLocal(dateStr) {
      // dateStr может быть date_local (без таймзоны) или date (ISO с Z)
      // Для date_local парсим напрямую, чтобы избежать преобразования браузером
      if (dateStr && !dateStr.endsWith('Z') && !dateStr.includes('+')) {
        // Локальная дата без таймзоны - парсим напрямую
        const parts = dateStr.split('T')
        if (parts.length >= 1) {
          // Создаём дату с полуднем, чтобы избежать проблем со смещением часовых поясов
          const date = new Date(parts[0] + 'T12:00:00')
          const options = {
            day: '2-digit',
            month: 'long',
            year: 'numeric'
          }
          return date.toLocaleDateString('ru-RU', options)
        }
      }
      // Fallback для даты с таймзоной
      const date = new Date(dateStr)
      const options = {
        day: '2-digit',
        month: 'long',
        year: 'numeric'
      }
      return date.toLocaleDateString('ru-RU', options)
    },
    formatTimeLocal(dateStr) {
      // dateStr может быть date_local (без таймзоны) или date (ISO с Z)
      // Для date_local парсим напрямую
      if (dateStr && !dateStr.endsWith('Z') && !dateStr.includes('+')) {
        // Локальная дата без таймзоны - извлекаем время напрямую
        const parts = dateStr.split('T')
        if (parts.length === 2) {
          return parts[1].slice(0, 5) // Возвращаем HH:MM
        }
      }
      // Fallback для даты с таймзоной
      const date = new Date(dateStr)
      return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
    },
    formatDate(dateStr, timezone) {
      const date = new Date(dateStr)
      const tz = timezone || 'Europe/Moscow'
      const options = {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
        timeZone: tz
      }
      return date.toLocaleDateString('ru-RU', options)
    },
    formatTime(dateStr, timezone) {
      const date = new Date(dateStr)
      const tz = timezone || 'Europe/Moscow'
      const options = {
        hour: '2-digit',
        minute: '2-digit',
        timeZone: tz
      }
      return date.toLocaleTimeString('ru-RU', options)
    },
    getTimezoneAbbr(timezone) {
      // Возвращает сокращённое название таймзоны (UTC offset)
      const tz = timezone || 'Europe/Moscow'
      const tzMap = {
        'Europe/Kaliningrad': 'UTC+2',
        'Europe/Moscow': 'МСК',
        'Europe/Samara': 'UTC+4',
        'Asia/Yekaterinburg': 'UTC+5',
        'Asia/Omsk': 'UTC+6',
        'Asia/Krasnoyarsk': 'UTC+7',
        'Asia/Irkutsk': 'UTC+8',
        'Asia/Yakutsk': 'UTC+9',
        'Asia/Vladivostok': 'UTC+10',
        'Asia/Magadan': 'UTC+11',
        'Asia/Kamchatka': 'UTC+12'
      }
      return tzMap[tz] || 'МСК'
    },
    getTimezoneOffset(timezone) {
      // Возвращает смещение таймзоны в формате +HH:MM
      const tz = timezone || 'Europe/Moscow'
      const offsetMap = {
        'Europe/Kaliningrad': '+02:00',
        'Europe/Moscow': '+03:00',
        'Europe/Samara': '+04:00',
        'Asia/Yekaterinburg': '+05:00',
        'Asia/Omsk': '+06:00',
        'Asia/Krasnoyarsk': '+07:00',
        'Asia/Irkutsk': '+08:00',
        'Asia/Yakutsk': '+09:00',
        'Asia/Vladivostok': '+10:00',
        'Asia/Magadan': '+11:00',
        'Asia/Kamchatka': '+12:00'
      }
      return offsetMap[tz] || '+03:00'
    },
    convertToTimezone(dateStr, timeStr, timezone) {
      // Создаём ISO строку с правильным смещением таймзоны
      const offset = this.getTimezoneOffset(timezone)
      return `${dateStr}T${timeStr}:00${offset}`
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
      return `${this.formatDate(startStr)} — ${this.formatDate(endStr)}`
    },
    isPast(dateStr) {
      // Если дата без таймзоны, добавляем Z чтобы парсить как UTC
      let date = dateStr
      if (date && !date.endsWith('Z') && !date.includes('+')) {
        date = date + 'Z'
      }
      return new Date(date) < new Date()
    },
    isConventionPast(dateEndStr) {
      const endDate = new Date(dateEndStr)
      endDate.setHours(23, 59, 59, 999)
      return endDate < new Date()
    },
    getConventionStatus(convention) {
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      const start = new Date(convention.date_start)
      const end = new Date(convention.date_end)
      end.setHours(23, 59, 59, 999)
      
      if (today >= start && today <= end) {
        return 'Идёт сейчас'
      }
      return 'Скоро'
    },
    pluralizeRuns(count) {
      const mod10 = count % 10
      const mod100 = count % 100
      
      if (mod100 >= 11 && mod100 <= 14) {
        return 'прогонов'
      }
      if (mod10 === 1) {
        return 'прогон'
      }
      if (mod10 >= 2 && mod10 <= 4) {
        return 'прогона'
      }
      return 'прогонов'
    },
    pluralizeGames(count) {
      const mod10 = count % 10
      const mod100 = count % 100
      
      if (mod100 >= 11 && mod100 <= 14) {
        return 'игр'
      }
      if (mod10 === 1) {
        return 'игра'
      }
      if (mod10 >= 2 && mod10 <= 4) {
        return 'игры'
      }
      return 'игр'
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
    
    // === Добавление прогона ===
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
    async fetchAllCities() {
      try {
        const response = await fetch('/api/cities/')
        if (response.ok) {
          this.allCities = await response.json()
        }
      } catch (err) {
        console.error('Ошибка загрузки городов:', err)
      }
    },
    async fetchConventionEvents() {
      try {
        const response = await fetch('/api/convention-events/?time=upcoming')
        if (response.ok) {
          this.conventionEvents = await response.json()
        }
      } catch (err) {
        console.error('Ошибка загрузки проведений конвентов:', err)
      }
    },
    // === Добавление/Редактирование прогона через RunEditor ===
    openAddRunModal() {
      this.runEditorMode = 'add'
      this.runEditorRun = null
      this.showRunEditor = true
    },
    
    startEditingRun() {
      if (!this.selectedRun) return
      this.runEditorMode = 'edit'
      this.runEditorRun = this.selectedRun
      this.showRunEditor = true
    },
    
    closeRunEditor() {
      this.showRunEditor = false
      this.runEditorRun = null
    },
    
    onCityCreated(newCity) {
      // Добавляем созданный город в список
      this.allCities.push(newCity)
    },
    
    async handleRunEditorSave(runData) {
      this.runEditorLoading = true
      
      try {
        if (this.runEditorMode === 'add') {
          // Добавление нового прогона
          const response = await fetch('/api/runs/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(runData)
          })
          
          if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
              throw new Error('Необходима авторизация для добавления прогона')
            }
            const data = await response.json()
            throw new Error(data.detail || data.non_field_errors?.[0] || 'Ошибка при сохранении')
          }
          
          // Обновляем списки
          await this.fetchRuns()
          await this.fetchCities()
        } else {
          // Редактирование прогона
          const response = await fetch(`/api/runs/${runData.id}/`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify(runData)
          })
          
          if (!response.ok) {
            if (response.status === 401 || response.status === 403) {
              throw new Error('Нет прав для редактирования этого прогона')
            }
            const data = await response.json()
            throw new Error(data.detail || data.non_field_errors?.[0] || 'Ошибка при сохранении')
          }
          
          const updatedRun = await response.json()
          
          // Обновляем список и выбранный прогон
          await this.fetchRuns()
          this.selectedRun = updatedRun
        }
        
        this.closeRunEditor()
      } catch (err) {
        console.error('Ошибка сохранения прогона:', err.message)
      } finally {
        this.runEditorLoading = false
      }
    },
    
    handleRunEditorError(errorMessage) {
      console.error('RunEditor error:', errorMessage)
    },
    
    // === Добавление проведения конвента ===
    async fetchAllConventions() {
      try {
        const response = await fetch('/api/conventions/')
        if (response.ok) {
          this.allConventions = await response.json()
        }
      } catch (err) {
        console.error('Ошибка загрузки конвентов:', err)
      }
    },
    openAddEventModal() {
      this.newEvent = {
        convention_id: null,
        city_id: null,
        newCityName: '',
        date_start: '',
        date_end: ''
      }
      this.eventCitySearch = ''
      this.showEventCityDropdown = false
      this.addEventError = null
      this.showAddEventModal = true
    },
    closeAddEventModal() {
      this.showAddEventModal = false
      this.addEventError = null
    },
    selectEventCity(city) {
      this.newEvent.city_id = city.id
      const regionName = city.region && city.region.name ? city.region.name : ''
      this.eventCitySearch = regionName ? `${city.name} (${regionName})` : city.name
      this.showEventCityDropdown = false
    },
    selectNewEventCity() {
      this.newEvent.city_id = 'new'
      this.eventCitySearch = ''
      this.showEventCityDropdown = false
    },
    onEventCityInputBlur() {
      setTimeout(() => {
        this.showEventCityDropdown = false
        if (this.newEvent.city_id && this.newEvent.city_id !== 'new' && this.eventCitySearch !== this.selectedEventCityName) {
          this.eventCitySearch = this.selectedEventCityName
        }
      }, 200)
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
          this.allCities.push(newCity)
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
        
        // Обновляем списки
        await this.fetchConventions()
        await this.fetchConventionEvents()
        this.closeAddEventModal()
      } catch (err) {
        this.addEventError = err.message
      } finally {
        this.addEventLoading = false
      }
    },
    
    // === Редактирование прогона ===
    async fetchAllConventionEvents() {
      try {
        const response = await fetch('/api/convention-events/')
        if (response.ok) {
          this.allConventionEvents = await response.json()
        }
      } catch (err) {
        console.error('Ошибка загрузки всех проведений конвентов:', err)
      }
    },
    
    // === Удаление ===
    confirmDeleteRun() {
      this.deleteTarget = this.selectedRun
      this.deleteType = 'run'
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
        const url = this.deleteType === 'run' 
          ? `/api/runs/${this.deleteTarget.id}/`
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
        
        // Обновляем списки
        if (this.deleteType === 'run') {
          this.closeRunModal()
          await this.fetchRuns()
          await this.fetchCities()
        } else {
          this.closeConventionModal()
          await this.fetchConventions()
          await this.fetchConventionCities()
        }
        
        this.cancelDelete()
      } catch (err) {
        alert(err.message)
      } finally {
        this.deleteLoading = false
      }
    },
    
    // === Управление мастерами ===
    async addMaster() {
      if (!this.newMasterUsername || !this.selectedRun) return
      
      this.addMasterLoading = true
      this.addMasterError = null
      
      try {
        const response = await fetch(`/api/runs/${this.selectedRun.id}/add_master/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({ username: this.newMasterUsername })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при добавлении мастера')
        }
        
        const updatedRun = await response.json()
        this.selectedRun = updatedRun
        this.newMasterUsername = ''
        this.isManagingMasters = false
        
        // Обновляем список прогонов
        await this.fetchRuns()
      } catch (err) {
        this.addMasterError = err.message
      } finally {
        this.addMasterLoading = false
      }
    },
    async removeMaster(userId) {
      if (!this.selectedRun) return
      
      try {
        const response = await fetch(`/api/runs/${this.selectedRun.id}/remove_master/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({ user_id: userId })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при удалении мастера')
        }
        
        const updatedRun = await response.json()
        this.selectedRun = updatedRun
        
        // Обновляем список прогонов
        await this.fetchRuns()
      } catch (err) {
        alert(err.message)
      }
    },
    
    // Регистрация на прогон
    async registerForRun() {
      if (!this.selectedRun) return
      
      this.registrationLoading = true
      this.registrationError = null
      
      try {
        const response = await fetch(`/api/runs/${this.selectedRun.id}/register/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({
            role_preference: this.registrationData.role_preference,
            is_technician: this.registrationData.is_technician,
            comment: this.registrationData.comment
          })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при регистрации')
        }
        
        const result = await response.json()
        this.selectedRun = result.run
        
        // Сбрасываем форму
        this.registrationData = {
          role_preference: 'any',
          is_technician: false,
          comment: ''
        }
        
        // Обновляем список прогонов
        await this.fetchRuns()
      } catch (err) {
        this.registrationError = err.message
      } finally {
        this.registrationLoading = false
      }
    },
    
    async unregisterFromRun() {
      if (!this.selectedRun) return
      
      this.registrationLoading = true
      this.registrationError = null
      
      try {
        const response = await fetch(`/api/runs/${this.selectedRun.id}/unregister/`, {
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
        
        const result = await response.json()
        this.selectedRun = result.run
        
        // Обновляем список прогонов
        await this.fetchRuns()
      } catch (err) {
        this.registrationError = err.message
      } finally {
        this.registrationLoading = false
      }
    },
    
    getRolePreferenceText(role) {
      const roles = {
        'any': 'Любая роль',
        'female': 'Женская роль',
        'male': 'Мужская роль'
      }
      return roles[role] || role
    },
    
    formatDuration(minutes) {
      if (!minutes) return ''
      const hours = Math.floor(minutes / 60)
      const mins = minutes % 60
      if (hours === 0) return `${mins} мин`
      if (mins === 0) return `${hours} ч`
      return `${hours} ч ${mins} мин`
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

/* ========== Табы ========== */
.tabs {
  display: flex;
  justify-content: center;
  gap: 0;
  margin-bottom: 32px;
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}

.tabs button {
  flex: 1;
  padding: 14px 28px;
  background: #0a0a0a;
  border: 2px solid #ff6b3555;
  color: #888;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.tabs button:first-child {
  border-radius: 8px 0 0 8px;
}

.tabs button:last-child {
  border-radius: 0 8px 8px 0;
  border-left: none;
}

.tabs button:hover {
  color: #ff6b35;
}

.tabs button.active {
  background: linear-gradient(90deg, #ff6b35, #ff8c5a);
  border-color: #ff6b35;
  color: #0a0a0a;
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

.control-select {
  padding: 12px 20px;
  background: #0a0a0a;
  border: 2px solid #ff6b3555;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 1rem;
  cursor: pointer;
  min-width: 180px;
  transition: border-color 0.3s;
}

.control-select:hover,
.control-select:focus {
  border-color: #ff6b35;
  outline: none;
}

.toggle-buttons {
  display: flex;
  gap: 0;
}

.toggle-buttons button {
  padding: 12px 20px;
  background: #0a0a0a;
  border: 2px solid #ff6b3555;
  color: #888;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.3s;
}

.toggle-buttons button:first-child {
  border-radius: 8px 0 0 8px;
}

.toggle-buttons button:last-child {
  border-radius: 0 8px 8px 0;
}

.toggle-buttons button:not(:last-child) {
  border-right: none;
}

.toggle-buttons button:hover {
  color: #ff6b35;
}

.toggle-buttons button.active {
  background: #ff6b35;
  border-color: #ff6b35;
  color: #0a0a0a;
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

/* ========== Таблица данных ========== */
.table-container {
  max-width: 1200px;
  margin: 0 auto;
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  background: rgba(26, 26, 46, 0.8);
  border-radius: 12px;
  overflow: hidden;
}

.data-table thead {
  background: linear-gradient(90deg, #ff6b35, #ff8c5a);
}

.data-table th {
  padding: 16px 20px;
  text-align: left;
  color: #0a0a0a;
  font-weight: bold;
  text-transform: uppercase;
  font-size: 0.85rem;
  letter-spacing: 0.05em;
}

.data-table tbody tr {
  border-bottom: 1px solid #ffffff10;
  transition: background 0.2s;
}

.data-table tbody tr:hover {
  background: rgba(255, 107, 53, 0.1);
}

.data-table tbody tr.past-row {
  opacity: 0.6;
}

.data-table td {
  padding: 16px 20px;
  vertical-align: middle;
}

.date-cell {
  font-family: 'JetBrains Mono', monospace;
  color: #ff6b35;
  font-weight: bold;
  white-space: nowrap;
}

.time-cell {
  font-family: 'JetBrains Mono', monospace;
  color: #00ccff;
  font-size: 1.1rem;
}

.timezone-hint {
  display: inline-block;
  margin-left: 6px;
  font-size: 0.7rem;
  color: #666;
  vertical-align: middle;
}

.name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.primary-text {
  color: #e0e0e0;
  font-weight: 600;
  font-size: 1.05rem;
}

.secondary-text {
  color: #666;
  font-size: 0.85rem;
}

.city-cell {
  color: #aaa;
}

.venue-cell {
  color: #888;
  font-size: 0.9rem;
}

.venue-name {
  color: #00ccff;
  margin: 0;
}

.rooms-list {
  color: #888;
  font-size: 0.9rem;
  margin: 4px 0 0 0;
}

.convention-cell {
  min-width: 120px;
}

.convention-badge {
  display: inline-block;
  padding: 4px 10px;
  background: rgba(255, 107, 53, 0.15);
  color: #ff8c5a;
  border-radius: 4px;
  font-size: 0.85rem;
  border: 1px solid #ff6b3533;
}

.no-data {
  color: #444;
}

.status-cell {
  text-align: center;
}

.status-badge {
  display: inline-block;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-badge.upcoming {
  background: rgba(0, 255, 136, 0.2);
  color: #00ff88;
  border: 1px solid #00ff8855;
}

.status-badge.past {
  background: rgba(136, 136, 136, 0.2);
  color: #888;
  border: 1px solid #88888855;
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
  transform: translateY(-5px);
  border-color: #ff6b35;
  box-shadow: 0 10px 40px rgba(255, 107, 53, 0.2);
}

.convention-card.past-card {
  opacity: 0.6;
}

.convention-dates {
  font-family: 'JetBrains Mono', monospace;
  color: #ff6b35;
  font-size: 0.9rem;
  font-weight: bold;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.convention-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.4rem;
  color: #e0e0e0;
  margin-bottom: 8px;
}

.convention-city {
  color: #888;
  font-size: 0.95rem;
  margin-bottom: 16px;
}

.convention-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid #ff6b3522;
}

.runs-count, .games-count {
  color: #00ccff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
}

/* ========== Ссылки на карточках конвентов ========== */
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

/* ========== Ссылки в модальном окне ========== */
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
  max-width: 600px;
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

.modal-dates {
  font-family: 'JetBrains Mono', monospace;
  color: #ff6b35;
  font-size: 1rem;
  font-weight: bold;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.modal-header-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
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
  margin-bottom: 8px;
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

.delete-btn {
  background: rgba(255, 68, 68, 0.1);
  border: 1px solid #ff444455;
  color: #ff4444;
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

.delete-btn:hover {
  background: rgba(255, 68, 68, 0.2);
  border-color: #ff4444;
  transform: scale(1.1);
}

/* Модальное окно удаления */
.delete-confirm-modal {
  max-width: 450px;
  text-align: center;
}

.delete-confirm-modal h2 {
  color: #ff4444;
  padding-right: 0;
}

.delete-warning {
  color: #aaa;
  line-height: 1.6;
  margin-bottom: 24px;
}

.btn-danger {
  background: linear-gradient(145deg, #ff4444, #cc3333);
  border: none;
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(255, 68, 68, 0.35);
}

.btn-danger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Управление мастерами */
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

.masters-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.master-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: rgba(0, 204, 255, 0.08);
  border-radius: 8px;
  border-left: 3px solid #00ccff;
}

.master-name {
  color: #00ccff;
  font-weight: 500;
}

.master-remove {
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

.master-remove:hover {
  background: #ff4444;
  color: #fff;
}

.add-master-form {
  padding: 16px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  border: 1px solid #ff6b3533;
}

.add-master-form .form-input {
  margin-bottom: 12px;
}

.add-master-actions {
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

/* Модальное окно прогона */
.run-modal {
  max-width: 500px;
}

.modal-run-date {
  font-family: 'JetBrains Mono', monospace;
  color: #ff6b35;
  font-size: 1rem;
  font-weight: bold;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.modal-run-time {
  color: #00ccff;
  font-size: 1.2rem;
  margin-left: 12px;
}

.modal-status {
  margin-top: 20px;
  padding: 12px;
  border-radius: 8px;
  text-align: center;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.modal-status.upcoming {
  background: rgba(0, 255, 136, 0.15);
  color: #00ff88;
  border: 1px solid #00ff8844;
}

.modal-status.past {
  background: rgba(136, 136, 136, 0.15);
  color: #888;
  border: 1px solid #88888844;
}

/* ========== Секция регистрации ========== */
.registration-section {
  margin-top: 20px;
  padding: 20px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  border: 1px solid #ff6b3533;
}

.registration-section .section-header {
  margin-bottom: 16px;
}

.registration-stats {
  display: flex;
  align-items: center;
  gap: 12px;
}

.registration-count {
  font-family: 'JetBrains Mono', monospace;
  color: #00ff88;
  font-size: 1.1rem;
  font-weight: bold;
}

.registration-count.full {
  color: #ff6b6b;
}

.full-badge {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Статус регистрации пользователя */
.user-registration {
  margin-bottom: 16px;
}

.registration-status-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: rgba(0, 255, 136, 0.1);
  border: 1px solid #00ff8844;
  border-radius: 10px;
}

.registration-status-icon {
  font-size: 1.5rem;
  color: #00ff88;
}

.registration-status-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.registration-status-text {
  color: #00ff88;
  font-weight: bold;
}

.registration-role {
  color: #aaa;
  font-size: 0.9rem;
}

.waitlist-badge {
  display: inline-block;
  background: rgba(255, 193, 7, 0.2);
  color: #ffc107;
  padding: 3px 8px;
  border-radius: 8px;
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
}

/* Форма регистрации */
.registration-form {
  margin-bottom: 16px;
}

.registration-form .form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.registration-form .form-group.half {
  flex: 1;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding-top: 24px;
  color: #e0e0e0;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: #ff6b35;
}

.btn-register {
  width: 100%;
  padding: 14px;
  font-size: 1rem;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Закрытая регистрация */
.registration-closed {
  text-align: center;
  padding: 20px;
  color: #888;
}

.registration-login {
  text-align: center;
  padding: 20px;
  color: #aaa;
}

.registration-login a {
  color: #00ccff;
  text-decoration: none;
}

.registration-login a:hover {
  text-decoration: underline;
}

/* Список участников */
.participants-list {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #ffffff15;
}

.participants-header {
  margin-bottom: 12px;
}

.participants-header h4 {
  color: #aaa;
  font-size: 0.9rem;
  font-weight: normal;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0;
}

.participants-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.participant-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 20px;
  font-size: 0.85rem;
}

.participant-item.technician {
  background: rgba(156, 39, 176, 0.15);
  border: 1px solid #9c27b044;
}

.participant-item.waitlist {
  opacity: 0.6;
}

.participant-item.cancelled {
  opacity: 0.4;
  text-decoration: line-through;
}

.participant-icon {
  font-size: 0.9rem;
}

.participant-name {
  color: #e0e0e0;
}

.participant-role {
  color: #00ccff;
  font-size: 0.8rem;
}

.participant-waitlist {
  color: #ffc107;
  font-size: 0.7rem;
  text-transform: uppercase;
}

.modal-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  gap: 16px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #ff6b3533;
}

.modal-stat {
  text-align: center;
}

.modal-stat-label {
  display: block;
  color: #888;
  font-size: 0.8rem;
  margin-bottom: 4px;
}

.modal-stat-value {
  color: #00ccff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.1rem;
  font-weight: bold;
}

.convention-badge-lg {
  display: inline-block;
  padding: 8px 16px;
  background: rgba(255, 107, 53, 0.15);
  color: #ff8c5a;
  border-radius: 8px;
  font-size: 1rem;
  border: 1px solid #ff6b3544;
}

.clickable-row {
  cursor: pointer;
}

.modal-city {
  color: #888;
  font-size: 1rem;
  margin-bottom: 24px;
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

.modal-games-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.modal-game-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  border-left: 3px solid #00ccff;
}

.modal-game-name {
  color: #e0e0e0;
  font-weight: 600;
}

.modal-game-players {
  color: #888;
  font-size: 0.85rem;
}

/* Ссылки на расписание */
.schedule-links-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #ff6b3533;
}

.schedule-links {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.schedule-link,
.schedule-edit-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: 8px;
  text-decoration: none;
  font-size: 0.95rem;
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
  transform: translateY(-2px);
}

.schedule-edit-link {
  background: rgba(255, 107, 53, 0.1);
  border: 1px solid #ff6b3555;
  color: #ff6b35;
}

.schedule-edit-link:hover {
  background: rgba(255, 107, 53, 0.2);
  border-color: #ff6b35;
  transform: translateY(-2px);
}

.modal-runs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.modal-run-item {
  display: flex;
  gap: 16px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  border-left: 3px solid #ff6b35;
}

.modal-run-time {
  font-family: 'JetBrains Mono', monospace;
  color: #00ccff;
  font-weight: bold;
  min-width: 50px;
}

.modal-run-name {
  color: #e0e0e0;
}

.no-runs {
  color: #666;
  font-style: italic;
}

/* Мастера в модальном окне прогона */
.modal-masters {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(0, 204, 255, 0.08);
  border-radius: 8px;
  border-left: 3px solid #00ccff;
}

.masters-icon {
  font-size: 1.2rem;
}

.masters-names {
  color: #00ccff;
  font-weight: 600;
}

/* Организаторы в модальном окне проведения конвента */
.modal-organizers {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(0, 204, 255, 0.08);
  border-radius: 8px;
  border-left: 3px solid #00ccff;
}

.organizers-icon {
  font-size: 1.2rem;
}

.organizers-names {
  color: #00ccff;
  font-weight: 600;
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

.add-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 24px;
  background: linear-gradient(145deg, #ff6b35, #e55a2b);
  border: none;
  border-radius: 12px;
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
  font-size: 1.4rem;
  font-weight: bold;
}

/* ========== Модальное окно добавления прогона ========== */
.add-run-modal,
.add-event-modal {
  max-width: 550px;
  padding: 32px;
}

.add-run-modal h2 {
  font-family: 'JetBrains Mono', monospace;
  margin-bottom: 24px;
  padding-right: 40px;
}

.add-form {
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

.timezone-label {
  color: #00ccff;
  font-size: 0.75rem;
  margin-left: 4px;
  text-transform: none;
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

.form-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-hint {
  color: #888;
  font-size: 0.8rem;
  margin-top: 4px;
}

/* Searchable Select */
.searchable-select {
  position: relative;
}

.dropdown-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 250px;
  overflow-y: auto;
  background: #1a1a2e;
  border: 2px solid #ff6b35;
  border-top: none;
  border-radius: 0 0 8px 8px;
  z-index: 100;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4);
}

.dropdown-item {
  padding: 12px 16px;
  color: #e0e0e0;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid #ff6b3522;
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item:hover {
  background: rgba(255, 107, 53, 0.2);
}

.dropdown-item.selected {
  background: rgba(255, 107, 53, 0.3);
  color: #ff6b35;
}

.dropdown-item-new {
  color: #00ccff;
  font-style: italic;
}

.dropdown-item-new:hover {
  background: rgba(0, 204, 255, 0.2);
}

.dropdown-empty {
  padding: 12px 16px;
  color: #888;
  font-style: italic;
  text-align: center;
}

.dropdown-list::-webkit-scrollbar {
  width: 6px;
}

.dropdown-list::-webkit-scrollbar-track {
  background: #0a0a0a;
}

.dropdown-list::-webkit-scrollbar-thumb {
  background: #ff6b35;
  border-radius: 3px;
}

.form-row {
  display: flex;
  gap: 20px;
}

.form-group.half {
  flex: 1;
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

/* ========== Адаптив ========== */
@media (max-width: 768px) {
  .page-header h1 {
    font-size: 2rem;
  }
  
  .tabs {
    max-width: 100%;
  }
  
  .tabs button {
    padding: 12px 16px;
    font-size: 0.9rem;
  }
  
  .controls-bar {
    flex-direction: column;
    gap: 16px;
  }
  
  .controls-filters {
    width: 100%;
    flex-direction: column;
    gap: 12px;
  }
  
  .control-select {
    width: 100%;
    min-width: 100%;
  }
  
  .add-btn {
    width: 100%;
    justify-content: center;
  }
  
  .toggle-buttons {
    width: 100%;
  }
  
  .toggle-buttons button {
    flex: 1;
    padding: 10px 12px;
    font-size: 0.85rem;
  }
  
  .data-table th,
  .data-table td {
    padding: 12px 10px;
    font-size: 0.9rem;
  }
  
  .conventions-grid {
    grid-template-columns: 1fr;
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
