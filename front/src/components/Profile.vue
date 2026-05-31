<template>
  <div class="profile-page">
    <div class="profile-container">
      <div class="profile-header">
        <div class="avatar">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="8" r="4"/>
            <path d="M4 20c0-4 4-6 8-6s8 2 8 6"/>
          </svg>
        </div>
        <h1>{{ user?.display_name || user?.username || 'Профиль' }}</h1>
      </div>

      <div class="profile-content" v-if="user && user.is_authenticated">
        <div class="info-section">
          <h2>Основная информация</h2>
          <div class="info-grid">
            <div class="info-item">
              <span class="label">Имя пользователя</span>
              <span class="value">{{ user.username }}</span>
            </div>
            <div class="info-item" v-if="user.first_name || user.last_name">
              <span class="label">Полное имя</span>
              <span class="value">{{ user.first_name }} {{ user.last_name }}</span>
            </div>
            <div class="info-item" v-if="user.email">
              <span class="label">Email</span>
              <span class="value">{{ user.email }}</span>
            </div>
            <div class="info-item" v-if="user.is_staff">
              <span class="label">Роль</span>
              <span class="value staff-badge">Администратор</span>
            </div>
          </div>
        </div>

        <div class="actions-section">
          <h2>Настройки аккаунта</h2>
          <div class="action-buttons">
            <a 
              href="https://auth.rularp.games/keycloak/auth/realms/LARP/account/" 
              target="_blank" 
              class="action-btn primary"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              Управление аккаунтом
            </a>
            <form action="/oidc/logout/" method="POST" class="logout-form">
              <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken" />
              <button type="submit" class="action-btn danger">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                  <polyline points="16 17 21 12 16 7"/>
                  <line x1="21" y1="12" x2="9" y2="12"/>
                </svg>
                Выйти из аккаунта
              </button>
            </form>
          </div>
        </div>
      </div>

      <div class="not-authenticated" v-else>
        <p>Вы не авторизованы</p>
        <a href="/oidc/authenticate/" class="action-btn primary">Войти</a>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'UserProfile',
  inject: ['getUser'],
  computed: {
    user() {
      return this.getUser()
    },
    csrfToken() {
      const match = document.cookie.match(/csrftoken=([^;]+)/)
      return match ? match[1] : ''
    }
  }
}
</script>

<style scoped>
.profile-page {
  min-height: calc(100vh - 80px);
  padding: 40px 24px;
}

.profile-container {
  max-width: 700px;
  margin: 0 auto;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 40px;
  padding-bottom: 24px;
  border-bottom: 1px solid #ff6b3533;
}

.avatar {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #ff6b35, #ff8c5a);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar svg {
  width: 48px;
  height: 48px;
  color: #0a0a0a;
}

.profile-header h1 {
  color: #fff;
  font-size: 1.8rem;
  font-weight: 700;
  margin: 0;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.info-section, .actions-section {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #ff6b3533;
  border-radius: 12px;
  padding: 24px;
}

.info-section h2, .actions-section h2 {
  color: #ff6b35;
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0 0 20px 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-grid {
  display: grid;
  gap: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  color: #888;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-item .value {
  color: #fff;
  font-size: 1.1rem;
}

.staff-badge {
  display: inline-block;
  background: linear-gradient(90deg, #ff6b35, #ff8c5a);
  color: #0a0a0a !important;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85rem !important;
  font-weight: 600;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px 24px;
  border-radius: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.9rem;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s ease;
  border: none;
}

.action-btn.primary {
  background: linear-gradient(90deg, #ff6b35, #ff8c5a);
  color: #0a0a0a;
}

.action-btn.primary:hover {
  box-shadow: 0 0 20px rgba(255, 107, 53, 0.4);
  transform: translateY(-2px);
}

.action-btn.danger {
  background: transparent;
  border: 1px solid #ff4444;
  color: #ff4444;
}

.action-btn.danger:hover {
  background: #ff4444;
  color: #0a0a0a;
}

.logout-form {
  display: contents;
}

.not-authenticated {
  text-align: center;
  padding: 60px 24px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #ff6b3533;
  border-radius: 12px;
}

.not-authenticated p {
  color: #888;
  font-size: 1.1rem;
  margin-bottom: 24px;
}

@media (max-width: 600px) {
  .profile-header {
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }
  
  .avatar {
    width: 64px;
    height: 64px;
  }
  
  .avatar svg {
    width: 36px;
    height: 36px;
  }
  
  .profile-header h1 {
    font-size: 1.4rem;
  }
}
</style>
