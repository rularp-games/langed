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
        @click="openGameModal(game)"
      >
        <div v-if="game.poster_url" class="game-poster">
          <img :src="game.poster_url" :alt="game.name" />
        </div>
        <div class="game-info">
          <h2 class="game-title">{{ game.name }}</h2>
          <div v-if="game.creators && game.creators.length > 0" class="game-creators">
            <span class="creators-icon">👤</span>
            <span class="creators-names">{{ game.creators.map(c => c.display_name).join(', ') }}</span>
          </div>
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
            <div class="stat">
              <span class="stat-label">Игротехники</span>
              <span class="stat-value">{{ game.technicians }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно с деталями игры -->
    <div v-if="selectedGame" class="modal-overlay" @click.self="closeGameModal">
      <div class="modal-content" :class="{ 'with-poster': selectedGame.poster_url }">
        <button class="modal-close" @click="closeGameModal">×</button>
        
        <div v-if="selectedGame.poster_url" class="modal-poster">
          <img :src="selectedGame.poster_url" :alt="selectedGame.name" />
        </div>
        
        <div class="modal-body">
          <div class="modal-header-row">
            <h2>{{ selectedGame.name }}</h2>
            <div class="header-actions">
              <button 
                v-if="selectedGame.can_edit" 
                class="edit-btn" 
                @click="startEditingGame"
                title="Редактировать"
              >
                ✏️
              </button>
              <button 
                v-if="selectedGame.can_edit" 
                class="delete-btn" 
                @click="showDeleteConfirm = true"
                title="Удалить"
              >
                🗑️
              </button>
              <button class="copy-link-btn" @click="copyGameLink" :title="linkCopied ? 'Скопировано!' : 'Скопировать ссылку'">
                <span v-if="linkCopied">✓</span>
                <span v-else>🔗</span>
              </button>
            </div>
          </div>
          
          <div v-if="selectedGame.creators && selectedGame.creators.length > 0" class="modal-creators">
            <span class="creators-icon">👤</span>
            <span class="creators-label">{{ selectedGame.creators.length > 1 ? 'Создатели:' : 'Создатель:' }}</span>
            <span class="creators-names">{{ selectedGame.creators.map(c => c.display_name).join(', ') }}</span>
          </div>
          
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
            <div class="modal-stat">
              <span class="modal-stat-label">Игротехники</span>
              <span class="modal-stat-value">{{ selectedGame.technicians }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно добавления игры (одиночная) -->
    <GameEditor
      v-if="showAddModal && addMode === 'single'"
      mode="add"
      @saved="onGameAdded"
      @cancel="closeAddModal"
    />

    <!-- Модальное окно импорта CSV -->
    <div v-if="showAddModal && addMode === 'csv' && isAuthenticated" class="modal-overlay" @click.self="closeAddModal">
      <div class="modal-content add-game-modal">
        <button class="modal-close" @click="closeAddModal">×</button>
        
        <div class="modal-body">
          <h2>Импорт игр из CSV</h2>
          
          <!-- Форма импорта CSV -->
          <div class="csv-import-form">
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

    <!-- Модальное окно редактирования игры -->
    <GameEditor
      v-if="isEditingGame"
      mode="edit"
      :game="selectedGame"
      @saved="onGameEdited"
      @cancel="cancelEditingGame"
    />

    <!-- Модальное окно подтверждения удаления -->
    <DeleteConfirmModal
      v-if="showDeleteConfirm"
      title="Удалить игру?"
      :message="`Это действие нельзя отменить. Игра '${selectedGame?.name}' будет удалена. Все прогоны этой игры также будут удалены.`"
      :loading="deleteLoading"
      @confirm="deleteGame"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>

<script>
import DeleteConfirmModal from './DeleteConfirmModal.vue'
import GameEditor from './GameEditor.vue'

export default {
  name: 'GamesPage',
  components: {
    DeleteConfirmModal,
    GameEditor
  },
  inject: ['getUser'],
  props: {
    gameId: {
      type: [String, Number],
      default: null
    }
  },
  data() {
    return {
      games: [],
      loading: true,
      error: null,
      searchQuery: '',
      selectedGame: null,
      showAddModal: false,
      addMode: 'single',
      // CSV импорт
      addLoading: false,
      addError: null,
      csvFile: null,
      csvResult: null,
      linkCopied: false,
      // Редактирование игры
      isEditingGame: false,
      // Удаление
      showDeleteConfirm: false,
      deleteLoading: false
    }
  },
  watch: {
    // Реагируем на изменение параметра gameId в URL
    gameId: {
      handler(newId) {
        if (newId && this.games.length > 0) {
          this.openGameById(newId)
        }
      },
      immediate: false
    },
    // Реагируем на загрузку списка игр
    games: {
      handler() {
        if (this.gameId && this.games.length > 0 && !this.selectedGame) {
          this.openGameById(this.gameId)
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
    openGameById(id) {
      const gameId = parseInt(id, 10)
      const game = this.games.find(g => g.id === gameId)
      if (game) {
        this.selectedGame = game
        this.updateUrlWithGame(game.id)
      }
    },
    openGameModal(game) {
      this.selectedGame = game
      this.updateUrlWithGame(game.id)
    },
    closeGameModal() {
      this.selectedGame = null
      this.linkCopied = false
      this.updateUrlWithGame(null)
    },
    updateUrlWithGame(gameId) {
      const query = { ...this.$route.query }
      if (gameId) {
        query.id = gameId
      } else {
        delete query.id
      }
      this.$router.replace({ query }).catch(() => {})
    },
    copyGameLink() {
      if (!this.selectedGame) return
      const url = `${window.location.origin}/games?id=${this.selectedGame.id}`
      navigator.clipboard.writeText(url).then(() => {
        this.linkCopied = true
        setTimeout(() => {
          this.linkCopied = false
        }, 2000)
      }).catch(err => {
        console.error('Ошибка копирования:', err)
      })
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
      this.addError = null
      this.addMode = 'single'
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
    
    // === Редактирование игры ===
    startEditingGame() {
      if (!this.selectedGame) return
      this.isEditingGame = true
    },
    cancelEditingGame() {
      this.isEditingGame = false
    },
    onGameAdded(savedGame) {
      this.games.unshift(savedGame)
      this.closeAddModal()
    },
    onGameEdited(updatedGame) {
      const index = this.games.findIndex(g => g.id === updatedGame.id)
      if (index !== -1) {
        this.games.splice(index, 1, updatedGame)
      }
      this.selectedGame = updatedGame
      this.isEditingGame = false
    },
    
    // === Удаление игры ===
    async deleteGame() {
      if (!this.selectedGame) return
      
      this.deleteLoading = true
      
      try {
        const response = await fetch(`/api/games/${this.selectedGame.id}/`, {
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
        
        // Удаляем из списка
        const index = this.games.findIndex(g => g.id === this.selectedGame.id)
        if (index !== -1) {
          this.games.splice(index, 1)
        }
        
        this.showDeleteConfirm = false
        this.closeGameModal()
      } catch (err) {
        alert(err.message)
      } finally {
        this.deleteLoading = false
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
  font-family: 'JetBrains Mono', monospace;
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
  font-family: 'JetBrains Mono', monospace;
  font-weight: bold;
}

/* Создатели в карточке игры */
.game-creators {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ff6b3522;
}

.creators-icon {
  font-size: 1rem;
  opacity: 0.8;
}

.game-creators .creators-names {
  color: #aaa;
  font-size: 0.9rem;
}

/* Создатели в модальном окне */
.modal-creators {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(0, 204, 255, 0.08);
  border-radius: 8px;
  border-left: 3px solid #00ccff;
}

.modal-creators .creators-icon {
  font-size: 1.2rem;
}

.modal-creators .creators-label {
  color: #888;
  font-size: 0.9rem;
}

.modal-creators .creators-names {
  color: #00ccff;
  font-weight: 600;
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

.modal-header-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 24px;
}

.modal-header-row h2 {
  flex: 1;
  margin-bottom: 0;
}

.modal-content h2 {
  font-family: 'JetBrains Mono', monospace;
  color: #ff6b35;
  font-size: 1.8rem;
  margin-bottom: 24px;
  padding-right: 40px;
}

.modal-content:not(.with-poster) h2 {
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
  grid-template-columns: repeat(4, 1fr);
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
  font-family: 'JetBrains Mono', monospace;
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
