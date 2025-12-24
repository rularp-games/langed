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
      <!-- Фильтры -->
      <div class="filters">
        <div class="filter-group">
          <label>Город</label>
          <select v-model="selectedCity" @change="fetchRuns">
            <option value="">Все города</option>
            <option v-for="city in cities" :key="city" :value="city">
              {{ city }}
            </option>
          </select>
        </div>
        
        <div class="filter-group">
          <label>Период</label>
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
              <th>Конвент</th>
              <th>Статус</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="run in runs" 
              :key="run.id"
              :class="{ 'past-row': isPast(run.date) }"
            >
              <td class="date-cell">{{ formatDate(run.date) }}</td>
              <td class="time-cell">{{ formatTime(run.date) }}</td>
              <td class="name-cell">
                <span class="primary-text">{{ run.game.name }}</span>
                <span class="secondary-text">
                  {{ run.game.players_min }}–{{ run.game.players_max }} игроков
                </span>
              </td>
              <td class="city-cell">{{ run.city }}</td>
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
      <!-- Фильтры -->
      <div class="filters">
        <div class="filter-group">
          <label>Город</label>
          <select v-model="selectedConventionCity" @change="fetchConventions">
            <option value="">Все города</option>
            <option v-for="city in conventionCities" :key="city" :value="city">
              {{ city }}
            </option>
          </select>
        </div>
        
        <div class="filter-group">
          <label>Период</label>
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
          @click="selectedConvention = event"
        >
          <div class="convention-dates">
            {{ formatConventionDates(event.date_start, event.date_end) }}
          </div>
          <h2 class="convention-title">{{ event.convention_name }}</h2>
          <div class="convention-city">📍 {{ event.city }}</div>
          <div class="convention-stats">
            <span class="runs-count">
              {{ event.runs_count }} {{ pluralizeRuns(event.runs_count) }}
            </span>
            <span :class="['status-badge', isConventionPast(event.date_end) ? 'past' : 'upcoming']">
              {{ isConventionPast(event.date_end) ? 'Завершён' : getConventionStatus(event) }}
            </span>
          </div>
        </div>
      </div>
    </template>

    <!-- Модальное окно с деталями проведения конвента -->
    <div v-if="selectedConvention" class="modal-overlay" @click.self="selectedConvention = null">
      <div class="modal-content">
        <button class="modal-close" @click="selectedConvention = null">×</button>
        <div class="modal-dates">
          {{ formatConventionDates(selectedConvention.date_start, selectedConvention.date_end) }}
        </div>
        <h2>{{ selectedConvention.convention_name }}</h2>
        <div class="modal-city">📍 {{ selectedConvention.city }}</div>
        
        <div class="modal-section" v-if="selectedConvention.description">
          <h3>Описание</h3>
          <p>{{ selectedConvention.description }}</p>
        </div>
        
        <div class="modal-section" v-if="selectedConvention.games && selectedConvention.games.length > 0">
          <h3>Игры на конвенте ({{ selectedConvention.games.length }})</h3>
          <div class="modal-games-list">
            <div v-for="game in selectedConvention.games" :key="game.id" class="modal-game-item">
              <span class="modal-game-name">{{ game.name }}</span>
              <span class="modal-game-players">{{ game.players_min }}–{{ game.players_max }} игроков</span>
            </div>
          </div>
        </div>
        
        <div class="modal-section" v-if="selectedConvention.runs && selectedConvention.runs.length > 0">
          <h3>Прогоны на конвенте ({{ selectedConvention.runs.length }})</h3>
          <div class="modal-runs-list">
            <div v-for="run in selectedConvention.runs" :key="run.id" class="modal-run-item">
              <span class="modal-run-time">{{ formatTime(run.date) }}</span>
              <span class="modal-run-name">{{ run.game_name }}</span>
            </div>
          </div>
        </div>
        
        <div v-else class="modal-section">
          <p class="no-runs">Прогоны пока не добавлены</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AfishaPage',
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
      // Конвенты
      conventions: [],
      conventionCities: [],
      selectedConventionCity: '',
      conventionTimeFilter: 'upcoming',
      conventionsLoading: true,
      conventionsError: null,
      selectedConvention: null
    }
  },
  mounted() {
    this.fetchCities()
    this.fetchRuns()
    this.fetchConventionCities()
    this.fetchConventions()
  },
  methods: {
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
        this.runs = await response.json()
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
        this.conventions = await response.json()
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
    formatDate(dateStr) {
      const date = new Date(dateStr)
      return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: 'long',
        year: 'numeric'
      })
    },
    formatTime(dateStr) {
      const date = new Date(dateStr)
      return date.toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit'
      })
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
      return new Date(dateStr) < new Date()
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

/* ========== Фильтры ========== */
.filters {
  display: flex;
  gap: 32px;
  justify-content: center;
  align-items: flex-end;
  flex-wrap: wrap;
  margin-bottom: 40px;
  padding: 24px;
  background: rgba(26, 26, 46, 0.6);
  border-radius: 12px;
  border: 1px solid #ff6b3533;
  max-width: 900px;
  margin-left: auto;
  margin-right: auto;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-group label {
  color: #ff6b35;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.filter-group select {
  padding: 12px 20px;
  background: #0a0a0a;
  border: 2px solid #ff6b3555;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 1rem;
  cursor: pointer;
  min-width: 200px;
  transition: border-color 0.3s;
}

.filter-group select:hover,
.filter-group select:focus {
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
  font-family: 'Courier New', monospace;
  color: #ff6b35;
  font-weight: bold;
  white-space: nowrap;
}

.time-cell {
  font-family: 'Courier New', monospace;
  color: #00ccff;
  font-size: 1.1rem;
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
  font-family: 'Courier New', monospace;
  color: #ff6b35;
  font-size: 0.9rem;
  font-weight: bold;
  margin-bottom: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.convention-title {
  font-family: 'Orbitron', 'Courier New', monospace;
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

.runs-count {
  color: #00ccff;
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
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
  font-family: 'Courier New', monospace;
  color: #ff6b35;
  font-size: 1rem;
  font-weight: bold;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.modal-content h2 {
  font-family: 'Orbitron', 'Courier New', monospace;
  color: #e0e0e0;
  font-size: 1.8rem;
  margin-bottom: 8px;
  padding-right: 40px;
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
  font-family: 'Courier New', monospace;
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
  
  .filters {
    flex-direction: column;
    gap: 20px;
    align-items: stretch;
  }
  
  .filter-group select {
    min-width: 100%;
  }
  
  .toggle-buttons {
    flex-wrap: wrap;
  }
  
  .toggle-buttons button {
    flex: 1;
    min-width: 100px;
  }
  
  .toggle-buttons button:first-child {
    border-radius: 8px 8px 0 0;
  }
  
  .toggle-buttons button:last-child {
    border-radius: 0 0 8px 8px;
  }
  
  .toggle-buttons button:not(:last-child) {
    border-right: 2px solid #ff6b3555;
    border-bottom: none;
  }
  
  .data-table th,
  .data-table td {
    padding: 12px 10px;
    font-size: 0.9rem;
  }
  
  .conventions-grid {
    grid-template-columns: 1fr;
  }
}
</style>
