<template>
  <div class="page">
    <div class="page-header">
      <h1>Конвенты</h1>
      <p class="subtitle">Каталог ролевых конвентов</p>
    </div>

    <!-- Поиск -->
    <div class="search-container">
      <input 
        v-model="searchQuery" 
        type="text" 
        placeholder="Поиск по названию..."
        class="search-input"
      />
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
        <p v-if="convention.description" class="convention-description">
          {{ truncateText(convention.description, 150) }}
        </p>
        <p v-else class="no-description">Описание отсутствует</p>
      </div>
    </div>

    <!-- Модальное окно с деталями конвента -->
    <div v-if="selectedConvention" class="modal-overlay" @click.self="selectedConvention = null">
      <div class="modal-content">
        <button class="modal-close" @click="selectedConvention = null">×</button>
        <h2>{{ selectedConvention.name }}</h2>
        
        <div class="modal-section" v-if="selectedConvention.description">
          <h3>Описание</h3>
          <p>{{ selectedConvention.description }}</p>
        </div>
        
        <div class="modal-section">
          <h3>Проведения конвента</h3>
          <div v-if="conventionEvents.length > 0" class="events-list">
            <div 
              v-for="event in conventionEvents" 
              :key="event.id" 
              class="event-item"
              :class="{ 'past-event': isEventPast(event.date_end) }"
            >
              <div class="event-dates">
                {{ formatConventionDates(event.date_start, event.date_end) }}
              </div>
              <div class="event-city">📍 {{ event.city }}</div>
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
  </div>
</template>

<script>
export default {
  name: 'ConventionsPage',
  data() {
    return {
      conventions: [],
      loading: true,
      error: null,
      searchQuery: '',
      selectedConvention: null,
      conventionEvents: []
    }
  },
  computed: {
    filteredConventions() {
      if (!this.searchQuery) {
        return this.conventions
      }
      const query = this.searchQuery.toLowerCase()
      return this.conventions.filter(c => 
        c.name.toLowerCase().includes(query) ||
        (c.description && c.description.toLowerCase().includes(query))
      )
    }
  },
  mounted() {
    this.fetchConventions()
  },
  methods: {
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

/* ========== Поиск ========== */
.search-container {
  max-width: 600px;
  margin: 0 auto 40px;
}

.search-input {
  width: 100%;
  padding: 16px 24px;
  background: rgba(26, 26, 46, 0.8);
  border: 2px solid #ff6b3555;
  border-radius: 12px;
  color: #e0e0e0;
  font-size: 1.1rem;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.search-input::placeholder {
  color: #666;
}

.search-input:focus {
  outline: none;
  border-color: #ff6b35;
  box-shadow: 0 0 20px rgba(255, 107, 53, 0.2);
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

.modal-content h2 {
  font-family: 'Orbitron', 'Courier New', monospace;
  color: #e0e0e0;
  font-size: 1.8rem;
  margin-bottom: 24px;
  padding-right: 40px;
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

.event-dates {
  font-family: 'Courier New', monospace;
  color: #ff6b35;
  font-size: 0.9rem;
  font-weight: bold;
  margin-bottom: 6px;
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
  
  .convention-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .convention-title {
    font-size: 1.2rem;
  }
}
</style>

