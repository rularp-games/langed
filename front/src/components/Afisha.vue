<template>
  <div class="afisha-page">
    <div class="afisha-header">
      <h1>Афиша</h1>
      <p class="subtitle">Расписание прогонов</p>
    </div>

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
      <table class="runs-table">
        <thead>
          <tr>
            <th>Дата</th>
            <th>Время</th>
            <th>Игра</th>
            <th>Город</th>
            <th>Статус</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="run in runs" 
            :key="run.id"
            :class="{ 'past-run': isPast(run.date) }"
          >
            <td class="date-cell">{{ formatDate(run.date) }}</td>
            <td class="time-cell">{{ formatTime(run.date) }}</td>
            <td class="game-cell">
              <span class="game-name">{{ run.game.name }}</span>
              <span class="players-info">
                {{ run.game.players_min }}–{{ run.game.players_max }} игроков
              </span>
            </td>
            <td class="city-cell">{{ run.city }}</td>
            <td class="status-cell">
              <span :class="['status-badge', isPast(run.date) ? 'past' : 'upcoming']">
                {{ isPast(run.date) ? 'Завершён' : 'Предстоит' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AfishaPage',
  data() {
    return {
      runs: [],
      cities: [],
      selectedCity: '',
      timeFilter: 'upcoming',
      loading: true,
      error: null
    }
  },
  mounted() {
    this.fetchCities()
    this.fetchRuns()
  },
  methods: {
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
    isPast(dateStr) {
      return new Date(dateStr) < new Date()
    }
  }
}
</script>

<style scoped>
.afisha-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%);
  padding: 40px 20px;
  color: #e0e0e0;
}

.afisha-header {
  text-align: center;
  margin-bottom: 40px;
}

.afisha-header h1 {
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

/* Фильтры */
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

/* Загрузка */
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

/* Таблица */
.table-container {
  max-width: 1200px;
  margin: 0 auto;
  overflow-x: auto;
}

.runs-table {
  width: 100%;
  border-collapse: collapse;
  background: rgba(26, 26, 46, 0.8);
  border-radius: 12px;
  overflow: hidden;
}

.runs-table thead {
  background: linear-gradient(90deg, #ff6b35, #ff8c5a);
}

.runs-table th {
  padding: 16px 20px;
  text-align: left;
  color: #0a0a0a;
  font-weight: bold;
  text-transform: uppercase;
  font-size: 0.85rem;
  letter-spacing: 0.05em;
}

.runs-table tbody tr {
  border-bottom: 1px solid #ffffff10;
  transition: background 0.2s;
}

.runs-table tbody tr:hover {
  background: rgba(255, 107, 53, 0.1);
}

.runs-table tbody tr.past-run {
  opacity: 0.6;
}

.runs-table td {
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

.game-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.game-name {
  color: #e0e0e0;
  font-weight: 600;
  font-size: 1.05rem;
}

.players-info {
  color: #666;
  font-size: 0.85rem;
}

.city-cell {
  color: #aaa;
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

/* Адаптив */
@media (max-width: 768px) {
  .afisha-header h1 {
    font-size: 2rem;
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
  
  .runs-table th,
  .runs-table td {
    padding: 12px 10px;
    font-size: 0.9rem;
  }
}
</style>

