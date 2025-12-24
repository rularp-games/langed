<template>
  <div class="games-page">
    <div class="games-header">
      <h1>Игры</h1>
    </div>
    
    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>Загрузка...</p>
    </div>
    
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="fetchGames" class="retry-btn">Повторить</button>
    </div>
    
    <div v-else-if="games.length === 0" class="empty">
      <p>Игры не найдены</p>
    </div>
    
    <div v-else class="games-grid">
      <div 
        v-for="game in games" 
        :key="game.id" 
        class="game-card"
        @click="selectedGame = game"
      >
        <h2 class="game-title">{{ game.name }}</h2>
        <div class="game-stats">
          <div class="stat">
            <span class="stat-label">Игроки</span>
            <span class="stat-value">{{ game.players_min }} - {{ game.players_max }}</span>
          </div>
          <div class="stat">
            <span class="stat-label">Жен. роли</span>
            <span class="stat-value">{{ game.female_roles_min }} - {{ game.female_roles_max }}</span>
          </div>
          <div class="stat">
            <span class="stat-label">Муж. роли</span>
            <span class="stat-value">{{ game.male_roles_min }} - {{ game.male_roles_max }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно с деталями игры -->
    <div v-if="selectedGame" class="modal-overlay" @click.self="selectedGame = null">
      <div class="modal-content">
        <button class="modal-close" @click="selectedGame = null">×</button>
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
            <span class="modal-stat-value">{{ selectedGame.players_min }} - {{ selectedGame.players_max }}</span>
          </div>
          <div class="modal-stat">
            <span class="modal-stat-label">Женские роли</span>
            <span class="modal-stat-value">{{ selectedGame.female_roles_min }} - {{ selectedGame.female_roles_max }}</span>
          </div>
          <div class="modal-stat">
            <span class="modal-stat-label">Мужские роли</span>
            <span class="modal-stat-value">{{ selectedGame.male_roles_min }} - {{ selectedGame.male_roles_max }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GamesPage',
  data() {
    return {
      games: [],
      loading: true,
      error: null,
      selectedGame: null
    }
  },
  mounted() {
    this.fetchGames()
  },
  methods: {
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
    }
  }
}
</script>

<style scoped>
.games-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%);
  padding: 40px 20px;
  color: #e0e0e0;
}

.games-header {
  text-align: center;
  margin-bottom: 40px;
}

.games-header h1 {
  font-family: 'Orbitron', 'Courier New', monospace;
  font-size: 3rem;
  color: #00ff88;
  text-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
  letter-spacing: 0.3em;
  text-transform: uppercase;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: #00ff88;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 3px solid #1a1a2e;
  border-top-color: #00ff88;
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
  border: 2px solid #00ff88;
  color: #00ff88;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s;
}

.retry-btn:hover {
  background: #00ff88;
  color: #0a0a0a;
}

.empty {
  text-align: center;
  padding: 60px;
  color: #666;
  font-size: 1.2rem;
}

.games-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.game-card {
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border: 1px solid #00ff8833;
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.game-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(0, 255, 136, 0.1), transparent);
  transition: left 0.5s;
}

.game-card:hover::before {
  left: 100%;
}

.game-card:hover {
  transform: translateY(-5px);
  border-color: #00ff88;
  box-shadow: 0 10px 40px rgba(0, 255, 136, 0.2);
}

.game-title {
  font-family: 'Orbitron', 'Courier New', monospace;
  font-size: 1.4rem;
  color: #00ff88;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #00ff8833;
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

/* Модальное окно */
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
  border: 2px solid #00ff88;
  border-radius: 16px;
  padding: 32px;
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  position: relative;
  box-shadow: 0 0 60px rgba(0, 255, 136, 0.3);
}

.modal-close {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  color: #00ff88;
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
  color: #00ff88;
  font-size: 1.8rem;
  margin-bottom: 24px;
  padding-right: 40px;
}

.modal-section {
  margin-bottom: 24px;
}

.modal-section h3 {
  color: #00ccff;
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
  border-top: 1px solid #00ff8833;
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
  background: #00ff88;
  border-radius: 4px;
}
</style>

