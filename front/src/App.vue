<template>
  <div id="app">
    <nav>
      <div class="nav-links">
        <router-link to="/">Home</router-link> |
        <router-link to="/cyberwordly">Cyberwordly</router-link> |
        <router-link to="/games">Игры</router-link>
      </div>
      <div class="user-info">
        <template v-if="user && user.is_authenticated">
          <span class="username">{{ user.username }}</span>
          <a href="/oidc/logout/" class="auth-btn logout-btn">Выйти</a>
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
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  background-color: #000000;
  margin: 0;
  padding: 0;
}

#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  min-height: 100vh;
  background-color: #000000;
}

nav {
  padding: 20px;
  background-color: #000000;
  z-index: 100;
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-links a {
  color: #00ff00;
  text-decoration: none;
  margin: 0 10px;
  font-weight: bold;
}

.nav-links a.router-link-active {
  color: #42b983;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.username {
  color: #00ff00;
  font-weight: bold;
}

.auth-btn {
  padding: 6px 14px;
  border-radius: 4px;
  text-decoration: none;
  font-weight: bold;
  transition: all 0.2s ease;
}

.login-btn {
  background-color: #00ff00;
  color: #000000;
}

.login-btn:hover {
  background-color: #00cc00;
}

.logout-btn {
  background-color: transparent;
  border: 1px solid #ff4444;
  color: #ff4444;
}

.logout-btn:hover {
  background-color: #ff4444;
  color: #000000;
}
</style>
