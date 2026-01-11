<template>
  <div id="app">
    <nav>
      <div class="nav-links">
        <router-link to="/">Афиша</router-link>
        <router-link to="/games">Игры</router-link>
        <router-link to="/conventions">Конвенты</router-link>
        <router-link to="/venues">Площадки</router-link>
      </div>
      <div class="user-info">
        <template v-if="user && user.is_authenticated">
          <a href="https://auth.rularp.games/keycloak/auth/realms/LARP/account/" target="_blank" class="username">{{ user.first_name }} {{ user.last_name }}</a>
          <form action="/oidc/logout/" method="POST" class="logout-form">
            <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken" />
            <button type="submit" class="auth-btn logout-btn">Выйти</button>
          </form>
        </template>
        <template v-else>
          <a href="/oidc/authenticate/" class="auth-btn login-btn">Войти</a>
        </template>
      </div>
    </nav>
    <router-view/>
  </div>
</template>

<script>
export default {
  name: 'App',
  data() {
    return {
      user: null
    }
  },
  provide() {
    return {
      getUser: () => this.user
    }
  },
  computed: {
    csrfToken() {
      const match = document.cookie.match(/csrftoken=([^;]+)/)
      return match ? match[1] : ''
    }
  },
  async created() {
    await this.fetchUser()
  },
  methods: {
    async fetchUser() {
      try {
        const response = await fetch('/api/auth/user/')
        this.user = await response.json()
      } catch (error) {
        console.error('Failed to fetch user:', error)
        this.user = { is_authenticated: false }
      }
    }
  }
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%);
  margin: 0;
  padding: 0;
}

#app {
  font-family: 'JetBrains Mono', monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  min-height: 100vh;
  background: transparent;
}

nav {
  padding: 16px 24px;
  background: rgba(10, 10, 10, 0.95);
  border-bottom: 1px solid #ff6b3533;
  z-index: 100;
  position: sticky;
  top: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  backdrop-filter: blur(10px);
}

.nav-links {
  display: flex;
  gap: 8px;
}

.nav-links a {
  color: #888;
  text-decoration: none;
  padding: 10px 20px;
  font-weight: 600;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  border-radius: 6px;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.nav-links a:hover {
  color: #ff6b35;
  border-color: #ff6b3555;
}

.nav-links a.router-link-active,
.nav-links a.router-link-exact-active {
  background: linear-gradient(90deg, #ff6b35, #ff8c5a);
  color: #0a0a0a;
  border-color: #ff6b35;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.username {
  color: #ff6b35;
  font-weight: 600;
  font-size: 0.9rem;
  letter-spacing: 0.05em;
  text-decoration: none;
  transition: color 0.2s ease;
}

.username:hover {
  color: #ff8c5a;
  text-decoration: underline;
}

.auth-btn {
  padding: 8px 18px;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  transition: all 0.3s ease;
}

.login-btn {
  background: linear-gradient(90deg, #ff6b35, #ff8c5a);
  color: #0a0a0a;
  border: none;
}

.login-btn:hover {
  box-shadow: 0 0 20px rgba(255, 107, 53, 0.4);
  transform: translateY(-1px);
}

.logout-form {
  display: inline;
  margin: 0;
  padding: 0;
}

.logout-btn {
  background: transparent;
  border: 1px solid #ff4444;
  color: #ff4444;
  cursor: pointer;
  font-family: 'JetBrains Mono', monospace;
}

.logout-btn:hover {
  background: #ff4444;
  color: #0a0a0a;
}

@media (max-width: 768px) {
  nav {
    flex-direction: column;
    gap: 16px;
    padding: 16px;
  }
  
  .nav-links {
    flex-wrap: wrap;
    justify-content: center;
  }
  
  .nav-links a {
    padding: 8px 14px;
    font-size: 0.8rem;
  }
}
</style>
