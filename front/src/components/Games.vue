<template>
  <div class="page">
    <div class="page-header">
      <h1>Игры</h1>
      <p class="subtitle">Каталог кабинетных ролевых игр</p>
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
        Добавить игру
      </button>
    </div>
    
    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>Загрузка...</p>
    </div>
    
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="fetchGames" class="retry-btn">Повторить</button>
    </div>
    
    <div v-else-if="filteredGames.length === 0" class="empty">
      <p v-if="searchQuery">Игры не найдены по запросу "{{ searchQuery }}"</p>
      <p v-else>Игры пока не добавлены</p>
    </div>
    
    <div v-else class="games-grid">
      <div 
        v-for="game in filteredGames" 
        :key="game.id" 
        class="game-card"
        :class="{ 'has-poster': game.poster_url }"
        @click="selectedGame = game"
      >
        <div v-if="game.poster_url" class="game-poster">
          <img :src="game.poster_url" :alt="game.name" />
        </div>
        <div class="game-info">
          <h2 class="game-title">{{ game.name }}</h2>
          <div class="game-stats">
            <div class="stat">
              <span class="stat-label">Игроки</span>
              <span class="stat-value">{{ game.players_min }} – {{ game.players_max }}</span>
            </div>
            <div class="stat">
              <span class="stat-label">Жен. роли</span>
              <span class="stat-value">{{ game.female_roles_min }} – {{ game.female_roles_max }}</span>
            </div>
            <div class="stat">
              <span class="stat-label">Муж. роли</span>
              <span class="stat-value">{{ game.male_roles_min }} – {{ game.male_roles_max }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно с деталями игры -->
    <div v-if="selectedGame" class="modal-overlay" @click.self="selectedGame = null">
      <div class="modal-content" :class="{ 'with-poster': selectedGame.poster_url }">
        <button class="modal-close" @click="selectedGame = null">×</button>
        
        <div v-if="selectedGame.poster_url" class="modal-poster">
          <img :src="selectedGame.poster_url" :alt="selectedGame.name" />
        </div>
        
        <div class="modal-body">
          <h2>{{ selectedGame.name }}</h2>
          
          <div class="modal-section" v-if="selectedGame.announcement">
            <h3>Анонс</h3>
            <p>{{ selectedGame.announcement }}</p>
          </div>
          
          <div class="modal-section" v-if="selectedGame.red_flags">
            <h3>Красные флаги</h3>
            <p class="red-flags">{{ selectedGame.red_flags }}</p>
          </div>
          
          <div class="modal-stats">
            <div class="modal-stat">
              <span class="modal-stat-label">Игроки</span>
              <span class="modal-stat-value">{{ selectedGame.players_min }} – {{ selectedGame.players_max }}</span>
            </div>
            <div class="modal-stat">
              <span class="modal-stat-label">Женские роли</span>
              <span class="modal-stat-value">{{ selectedGame.female_roles_min }} – {{ selectedGame.female_roles_max }}</span>
            </div>
            <div class="modal-stat">
              <span class="modal-stat-label">Мужские роли</span>
              <span class="modal-stat-value">{{ selectedGame.male_roles_min }} – {{ selectedGame.male_roles_max }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно добавления игры -->
    <div v-if="showAddModal && isAuthenticated" class="modal-overlay" @click.self="closeAddModal">
      <div class="modal-content add-game-modal">
        <button class="modal-close" @click="closeAddModal">×</button>
        
        <div class="modal-body">
          <h2>Добавить игру</h2>
          
          <!-- Переключатель режима -->
          <div class="mode-switcher">
            <button 
              type="button" 
              :class="['mode-btn', { active: addMode === 'single' }]"
              @click="addMode = 'single'"
            >
              Одну игру
            </button>
            <button 
              type="button" 
              :class="['mode-btn', { active: addMode === 'csv' }]"
              @click="addMode = 'csv'"
            >
              Импорт из CSV
            </button>
          </div>
          
          <!-- Форма одной игры -->
          <form v-if="addMode === 'single'" @submit.prevent="submitGame" class="add-game-form">
            <div class="form-group">
              <label for="game-name">Название *</label>
              <input 
                id="game-name"
                v-model="newGame.name" 
                type="text" 
                required
                class="form-input"
                placeholder="Введите название игры"
              />
            </div>

            <div class="form-group">
              <label>Постер</label>
              <div class="poster-upload">
                <div v-if="posterPreview" class="poster-preview">
                  <img :src="posterPreview" alt="Превью постера" />
                  <button type="button" @click="removePoster" class="poster-remove">×</button>
                </div>
                <label v-else class="poster-dropzone" for="game-poster">
                  <span class="poster-icon">🖼</span>
                  <span class="poster-text">Нажмите для выбора изображения</span>
                  <span class="poster-hint">JPG, PNG до 5 МБ</span>
                </label>
                <input 
                  id="game-poster"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  @change="onPosterChange"
                  class="poster-input"
                />
              </div>
            </div>
            
            <div class="form-group">
              <label for="game-announcement">Анонс</label>
              <textarea 
                id="game-announcement"
                v-model="newGame.announcement"
                class="form-input form-textarea"
                placeholder="Описание игры"
                rows="3"
              ></textarea>
            </div>
            
            <div class="form-group">
              <label for="game-red-flags">Красные флаги</label>
              <textarea 
                id="game-red-flags"
                v-model="newGame.red_flags"
                class="form-input form-textarea"
                placeholder="Предупреждения о контенте"
                rows="2"
              ></textarea>
            </div>
            
            <div class="form-row">
              <div class="form-group half">
                <label>Игроки</label>
                <div class="range-inputs">
                  <input 
                    v-model.number="newGame.players_min" 
                    type="number" 
                    min="1"
                    class="form-input small"
                    placeholder="Мин"
                  />
                  <span class="range-separator">–</span>
                  <input 
                    v-model.number="newGame.players_max" 
                    type="number" 
                    min="1"
                    class="form-input small"
                    placeholder="Макс"
                  />
                </div>
              </div>
            </div>
            
            <div class="form-row">
              <div class="form-group half">
                <label>Женские роли</label>
                <div class="range-inputs">
                  <input 
                    v-model.number="newGame.female_roles_min" 
                    type="number" 
                    min="0"
                    class="form-input small"
                    placeholder="Мин"
                  />
                  <span class="range-separator">–</span>
                  <input 
                    v-model.number="newGame.female_roles_max" 
                    type="number" 
                    min="0"
                    class="form-input small"
                    placeholder="Макс"
                  />
                </div>
              </div>
              
              <div class="form-group half">
                <label>Мужские роли</label>
                <div class="range-inputs">
                  <input 
                    v-model.number="newGame.male_roles_min" 
                    type="number" 
                    min="0"
                    class="form-input small"
                    placeholder="Мин"
                  />
                  <span class="range-separator">–</span>
                  <input 
                    v-model.number="newGame.male_roles_max" 
                    type="number" 
                    min="0"
                    class="form-input small"
                    placeholder="Макс"
                  />
                </div>
              </div>
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
                <span class="csv-hint">Формат: название, анонс, красные флаги</span>
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
              <p class="csv-result-success">Создано игр: {{ csvResult.created }}</p>
              <p v-if="csvResult.skipped > 0" class="csv-result-skipped">
                Пропущено (уже существуют): {{ csvResult.skipped }}
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
    </div>
  </div>
</template>

<script>
export default {
  name: 'GamesPage',
  inject: ['getUser'],
  data() {
    return {
      games: [],
      loading: true,
      error: null,
      searchQuery: '',
      selectedGame: null,
      showAddModal: false,
      addLoading: false,
      addError: null,
      newGame: this.getEmptyGame(),
      posterFile: null,
      posterPreview: null,
      addMode: 'single',
      csvFile: null,
      csvResult: null
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
    filteredGames() {
      let result = this.games
      if (this.searchQuery) {
        const query = this.searchQuery.toLowerCase()
        result = result.filter(g => 
          g.name.toLowerCase().includes(query) ||
          (g.announcement && g.announcement.toLowerCase().includes(query))
        )
      }
      return result.slice().sort((a, b) => a.name.localeCompare(b.name, 'ru'))
    }
  },
  mounted() {
    this.fetchGames()
  },
  methods: {
    getEmptyGame() {
      return {
        name: '',
        announcement: '',
        red_flags: '',
        players_min: 1,
        players_max: 10,
        female_roles_min: 0,
        female_roles_max: 0,
        male_roles_min: 0,
        male_roles_max: 0
      }
    },
    async fetchGames() {
      this.loading = true
      this.error = null
      try {
        const response = await fetch('/api/games/')
        if (!response.ok) {
          throw new Error('Ошибка загрузки данных')
        }
        this.games = await response.json()
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    },
    openAddModal() {
      this.newGame = this.getEmptyGame()
      this.posterFile = null
      this.posterPreview = null
      this.addError = null
      this.addMode = 'single'
      this.csvFile = null
      this.csvResult = null
      this.showAddModal = true
    },
    closeAddModal() {
      this.showAddModal = false
      this.addError = null
      this.posterFile = null
      this.posterPreview = null
      this.csvFile = null
      this.csvResult = null
    },
    onPosterChange(event) {
      const file = event.target.files[0]
      if (!file) return
      
      // Проверка размера (5 МБ)
      if (file.size > 5 * 1024 * 1024) {
        this.addError = 'Файл слишком большой. Максимум 5 МБ'
        event.target.value = ''
        return
      }
      
      this.posterFile = file
      this.posterPreview = URL.createObjectURL(file)
    },
    removePoster() {
      if (this.posterPreview) {
        URL.revokeObjectURL(this.posterPreview)
      }
      this.posterFile = null
      this.posterPreview = null
      // Сбросить input
      const input = document.getElementById('game-poster')
      if (input) input.value = ''
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
        
        const response = await fetch('/api/games/import_csv/', {
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
        
        // Добавляем новые игры в список
        if (result.games && result.games.length > 0) {
          this.games = [...result.games, ...this.games]
        }
        
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
    async submitGame() {
      this.addLoading = true
      this.addError = null
      
      try {
        const formData = new FormData()
        formData.append('name', this.newGame.name)
        formData.append('announcement', this.newGame.announcement || '')
        formData.append('red_flags', this.newGame.red_flags || '')
        formData.append('players_min', this.newGame.players_min)
        formData.append('players_max', this.newGame.players_max)
        formData.append('female_roles_min', this.newGame.female_roles_min)
        formData.append('female_roles_max', this.newGame.female_roles_max)
        formData.append('male_roles_min', this.newGame.male_roles_min)
        formData.append('male_roles_max', this.newGame.male_roles_max)
        
        if (this.posterFile) {
          formData.append('poster', this.posterFile)
        }
        
        const response = await fetch('/api/games/', {
          method: 'POST',
          headers: {
            'X-CSRFToken': this.csrfToken
          },
          body: formData
        })
        
        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error('Необходима авторизация для добавления игры')
          }
          const data = await response.json()
          throw new Error(data.detail || data.name?.[0] || 'Ошибка при сохранении')
        }
        
        const createdGame = await response.json()
        this.games.unshift(createdGame)
        this.closeAddModal()
      } catch (err) {
        this.addError = err.message
      } finally {
        this.addLoading = false
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

/* ========== Сетка игр ========== */
.games-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.game-card {
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

.game-card:not(.has-poster) {
  padding: 24px;
}

.game-card::before {
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

.game-card:hover::before {
  left: 100%;
}

.game-card:hover {
  transform: translateY(-5px);
  border-color: #ff6b35;
  box-shadow: 0 10px 40px rgba(255, 107, 53, 0.2);
}

.game-poster {
  width: 100%;
  height: 200px;
  overflow: hidden;
  position: relative;
}

.game-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.game-card:hover .game-poster img {
  transform: scale(1.05);
}

.game-info {
  padding: 24px;
}

.game-title {
  font-family: 'Orbitron', 'Courier New', monospace;
  font-size: 1.4rem;
  color: #ff6b35;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ff6b3533;
}

.game-stats {
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
  font-family: 'Courier New', monospace;
  font-weight: bold;
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
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 0 60px rgba(255, 107, 53, 0.3);
}

.modal-content:not(.with-poster) {
  padding: 32px;
}

.modal-poster {
  width: 100%;
  max-height: 300px;
  overflow: hidden;
  border-radius: 14px 14px 0 0;
}

.modal-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.modal-body {
  padding: 32px;
}

.modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(0, 0, 0, 0.6);
  border: none;
  color: #ff6b35;
  font-size: 2rem;
  cursor: pointer;
  line-height: 1;
  transition: transform 0.2s;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.modal-close:hover {
  transform: scale(1.2);
}

.modal-content h2 {
  font-family: 'Orbitron', 'Courier New', monospace;
  color: #ff6b35;
  font-size: 1.8rem;
  margin-bottom: 24px;
  padding-right: 40px;
}

.modal-content:not(.with-poster) h2 {
  padding-right: 40px;
}

.modal-section {
  margin-bottom: 24px;
}

.modal-section h3 {
  color: #ff6b35;
  font-size: 1rem;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.modal-section p {
  color: #ccc;
  line-height: 1.6;
  white-space: pre-wrap;
}

.red-flags {
  color: #ff6b6b !important;
  background: rgba(255, 107, 107, 0.1);
  padding: 12px;
  border-radius: 8px;
  border-left: 3px solid #ff6b6b;
}

.modal-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-top: 24px;
  padding-top: 24px;
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
  font-family: 'Courier New', monospace;
  font-size: 1.2rem;
  font-weight: bold;
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

/* ========== Форма добавления игры ========== */
.add-game-modal {
  padding: 32px;
  max-width: 550px;
}

.add-game-modal h2 {
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

.add-game-form, .csv-import-form {
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
  min-height: 60px;
  font-family: inherit;
}

.form-row {
  display: flex;
  gap: 20px;
}

.form-group.half {
  flex: 1;
}

.range-inputs {
  display: flex;
  align-items: center;
  gap: 12px;
}

.range-separator {
  color: #888;
  font-size: 1.2rem;
}

.form-input.small {
  width: 80px;
  text-align: center;
}

/* Загрузка постера */
.poster-upload {
  position: relative;
}

.poster-input {
  display: none;
}

.poster-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px 24px;
  background: rgba(10, 10, 10, 0.4);
  border: 2px dashed #ff6b3555;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.poster-dropzone:hover {
  border-color: #ff6b35;
  background: rgba(255, 107, 53, 0.05);
}

.poster-icon {
  font-size: 2.5rem;
  opacity: 0.7;
}

.poster-text {
  color: #aaa;
  font-size: 0.95rem;
}

.poster-hint {
  color: #666;
  font-size: 0.8rem;
}

.poster-preview {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  max-height: 200px;
}

.poster-preview img {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
  border-radius: 12px;
}

.poster-remove {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 32px;
  height: 32px;
  background: rgba(255, 68, 68, 0.9);
  border: none;
  border-radius: 50%;
  color: #fff;
  font-size: 1.4rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: transform 0.2s, background 0.2s;
}

.poster-remove:hover {
  transform: scale(1.1);
  background: #ff4444;
}

/* CSV импорт */
.csv-import-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

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
  
  .games-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-stats {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .form-row {
    flex-direction: column;
    gap: 20px;
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
