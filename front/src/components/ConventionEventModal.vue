<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <button class="modal-close" @click="$emit('close')">×</button>
      <div class="modal-dates">
        {{ formatConventionDates(event.date_start, event.date_end) }}
      </div>
      <div class="modal-header-row">
        <h2>{{ event.convention_name }}</h2>
        <button class="copy-link-btn" @click="copyEventLink" :title="linkCopied ? 'Скопировано!' : 'Скопировать ссылку'">
          <span v-if="linkCopied">✓</span>
          <span v-else>🔗</span>
        </button>
      </div>
      <div class="modal-city">📍 {{ event.city_name || (event.city && event.city.name) }}</div>
      
      <div class="modal-section" v-if="event.organizers && event.organizers.length > 0">
        <h3>{{ event.organizers.length > 1 ? 'Организаторы' : 'Организатор' }}</h3>
        <div class="modal-organizers">
          <span class="organizers-icon">👤</span>
          <span class="organizers-names">{{ event.organizers.map(o => o.display_name).join(', ') }}</span>
        </div>
      </div>
      
      <div class="modal-section" v-if="event.description">
        <h3>Описание</h3>
        <p>{{ event.description }}</p>
      </div>
      
      <div class="modal-section" v-if="event.links && event.links.length > 0">
        <h3>Ссылки</h3>
        <div class="links-list">
          <a 
            v-for="link in event.links" 
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
      
      <!-- Блок регистрации на конвент -->
      <div class="modal-section registration-section">
        <h3>Участие</h3>
        <div class="registration-block">
          <div class="registration-stats">
            <span class="participants-count">
              👥 {{ event.registrations_count || 0 }}{{ event.capacity ? ` / ${event.capacity}` : '' }} участников
            </span>
            <span v-if="event.is_full" class="full-badge">Мест нет</span>
            <span v-if="!event.registration_open" class="closed-badge">Регистрация закрыта</span>
          </div>
          
          <!-- Статус регистрации текущего пользователя -->
          <div v-if="userRegistration" class="user-registration">
            <span v-if="userRegistration.status === 'pending'" class="reg-status status-pending">
              ⏳ Заявка ожидает подтверждения
            </span>
            <span v-else-if="userRegistration.status === 'confirmed'" class="reg-status status-confirmed">
              ✅ Вы зарегистрированы
            </span>
            <span v-else-if="userRegistration.status === 'rejected'" class="reg-status status-rejected">
              ❌ Заявка отклонена
            </span>
            <button 
              v-if="userRegistration.status !== 'rejected'"
              @click="unregister"
              class="btn-unregister"
              :disabled="loading"
            >
              {{ loading ? '...' : 'Отменить' }}
            </button>
          </div>
          
          <!-- Кнопка регистрации -->
          <button 
            v-else-if="event.registration_open && !event.is_full && isAuthenticated"
            @click="showRegistrationForm = true"
            class="btn-register"
            v-show="!showRegistrationForm"
          >
            📝 Зарегистрироваться
          </button>
          
          <!-- Форма регистрации -->
          <div v-if="showRegistrationForm && !userRegistration" class="registration-form">
            <div class="form-group">
              <label>Комментарий (опционально)</label>
              <textarea 
                v-model="comment"
                placeholder="Любая дополнительная информация..."
                rows="2"
                class="form-textarea"
              ></textarea>
            </div>
            <div class="form-actions">
              <button @click="showRegistrationForm = false" class="btn-cancel">Отмена</button>
              <button @click="register" class="btn-submit" :disabled="loading">
                {{ loading ? 'Отправка...' : 'Отправить заявку' }}
              </button>
            </div>
          </div>
          
          <!-- Сообщение для неавторизованных -->
          <span v-else-if="event.registration_open && !event.is_full && !isAuthenticated" class="login-hint">
            <a href="/oidc/authenticate/">Войдите</a>, чтобы зарегистрироваться
          </span>
          
          <div v-if="error" class="registration-error">{{ error }}</div>
        </div>
      </div>
      
      <!-- Ссылки на расписание -->
      <div class="modal-section schedule-links-section">
        <h3>Расписание</h3>
        <div class="schedule-links">
          <router-link 
            :to="`/schedule/${event.id}`" 
            class="schedule-link"
          >
            📅 Посмотреть расписание
          </router-link>
          <router-link 
            v-if="event.can_edit"
            :to="`/schedule/${event.id}/edit`" 
            class="schedule-edit-link"
          >
            ✏️ Редактировать расписание
          </router-link>
        </div>
      </div>
      
      <div class="modal-section" v-if="event.games && event.games.length > 0">
        <h3>Игры на конвенте ({{ event.games.length }})</h3>
        <div class="modal-games-list">
          <div v-for="game in sortedGames" :key="game.id" class="modal-game-item">
            <span class="modal-game-name">{{ game.name }}</span>
            <span class="modal-game-players">{{ game.players_min }}–{{ game.players_max }} игроков</span>
          </div>
        </div>
      </div>
      
      <div v-if="!event.games || event.games.length === 0" class="modal-section">
        <p class="no-runs">Игры пока не добавлены</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ConventionEventModal',
  props: {
    event: {
      type: Object,
      required: true
    },
    isAuthenticated: {
      type: Boolean,
      default: false
    },
    csrfToken: {
      type: String,
      default: ''
    }
  },
  emits: ['close', 'registration-changed'],
  data() {
    return {
      linkCopied: false,
      showRegistrationForm: false,
      comment: '',
      loading: false,
      error: null,
      userRegistration: null
    }
  },
  watch: {
    event: {
      immediate: true,
      handler(newEvent) {
        if (newEvent && newEvent.current_user_registration) {
          this.userRegistration = newEvent.current_user_registration
        } else {
          this.userRegistration = null
        }
      }
    }
  },
  computed: {
    sortedGames() {
      if (!this.event || !this.event.games) {
        return []
      }
      return this.event.games.slice().sort((a, b) => a.name.localeCompare(b.name, 'ru'))
    }
  },
  methods: {
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
    copyEventLink() {
      if (!this.event) return
      const url = `${window.location.origin}/?event=${this.event.id}`
      navigator.clipboard.writeText(url).then(() => {
        this.linkCopied = true
        setTimeout(() => {
          this.linkCopied = false
        }, 2000)
      }).catch(err => {
        console.error('Ошибка копирования:', err)
      })
    },
    
    async register() {
      this.loading = true
      this.error = null
      
      try {
        const response = await fetch(`/api/convention-events/${this.event.id}/register/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({ comment: this.comment })
        })
        
        if (!response.ok) {
          const data = await response.json()
          throw new Error(data.error || 'Ошибка при регистрации')
        }
        
        const result = await response.json()
        this.userRegistration = result.registration
        this.showRegistrationForm = false
        this.comment = ''
        this.$emit('registration-changed')
        
      } catch (err) {
        this.error = err.message
      } finally {
        this.loading = false
      }
    },
    
    async unregister() {
      if (!confirm('Отменить регистрацию на конвент?')) return
      
      this.loading = true
      this.error = null
      
      try {
        const response = await fetch(`/api/convention-events/${this.event.id}/unregister/`, {
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
        
        this.userRegistration = null
        this.$emit('registration-changed')
        
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

/* Организаторы */
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

/* Ссылки */
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

/* Список игр */
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

/* Блок регистрации */
.registration-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #00ccff33;
}

.registration-block {
  padding: 16px;
  background: rgba(0, 204, 255, 0.06);
  border-radius: 10px;
  border-left: 3px solid #00ccff;
}

.registration-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.participants-count {
  color: #00ccff;
  font-weight: 600;
}

.full-badge {
  padding: 3px 10px;
  background: #ff4444;
  color: #fff;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
}

.closed-badge {
  padding: 3px 10px;
  background: #666;
  color: #ccc;
  border-radius: 12px;
  font-size: 0.8rem;
}

.user-registration {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.reg-status {
  font-weight: 500;
}

.status-pending {
  color: #ffaa00;
}

.status-confirmed {
  color: #4caf50;
}

.status-rejected {
  color: #ff4444;
}

.btn-unregister {
  padding: 6px 14px;
  background: transparent;
  border: 1px solid #ff444466;
  border-radius: 6px;
  color: #ff6b6b;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-unregister:hover:not(:disabled) {
  background: rgba(255, 68, 68, 0.15);
  border-color: #ff4444;
}

.btn-unregister:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-register {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: linear-gradient(145deg, #00ccff, #0099cc);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-register:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 204, 255, 0.4);
}

.registration-form {
  margin-top: 12px;
  padding: 16px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.form-group {
  margin-bottom: 12px;
}

.form-group label {
  display: block;
  color: #00ccff;
  font-size: 0.85rem;
  margin-bottom: 6px;
}

.form-textarea {
  width: 100%;
  padding: 10px 14px;
  background: rgba(10, 10, 10, 0.6);
  border: 1px solid #00ccff44;
  border-radius: 6px;
  color: #e0e0e0;
  font-size: 0.95rem;
  resize: vertical;
  font-family: inherit;
}

.form-textarea::placeholder {
  color: #555;
}

.form-textarea:focus {
  outline: none;
  border-color: #00ccff;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-cancel {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #666;
  border-radius: 6px;
  color: #aaa;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: #888;
}

.btn-submit {
  padding: 8px 20px;
  background: linear-gradient(145deg, #00ccff, #0099cc);
  border: none;
  border-radius: 6px;
  color: #fff;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-submit:hover:not(:disabled) {
  box-shadow: 0 4px 15px rgba(0, 204, 255, 0.4);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.login-hint {
  color: #888;
  font-size: 0.95rem;
}

.login-hint a {
  color: #00ccff;
  text-decoration: none;
}

.login-hint a:hover {
  text-decoration: underline;
}

.registration-error {
  margin-top: 10px;
  padding: 8px 12px;
  background: rgba(255, 68, 68, 0.15);
  border: 1px solid #ff4444;
  border-radius: 6px;
  color: #ff6b6b;
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
  .modal-content {
    padding: 24px;
  }
  
  .modal-content h2 {
    font-size: 1.4rem;
  }
  
  .schedule-links {
    flex-direction: column;
  }
  
  .schedule-link,
  .schedule-edit-link {
    width: 100%;
    justify-content: center;
  }
}
</style>
