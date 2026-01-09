<template>
  <div class="modal-overlay" @click.self="$emit('cancel')">
    <div class="modal-content run-editor-modal">
      <button class="modal-close" @click="$emit('cancel')">×</button>
      
      <h2>{{ mode === 'add' ? 'Добавить прогон' : 'Редактировать прогон' }}</h2>
      
      <form @submit.prevent="submitForm" class="run-form">
        <!-- Игра -->
        <div class="form-group searchable-select">
          <label>Игра *</label>
          <input 
            v-model="gameSearch"
            type="text"
            class="form-input"
            placeholder="Введите название игры..."
            autocomplete="off"
            :disabled="mode === 'edit' && lockGame"
            @focus="showGameDropdown = true"
            @blur="onGameInputBlur"
            @keydown.enter.prevent
          />
          <div v-if="showGameDropdown && !(mode === 'edit' && lockGame)" class="dropdown-list">
            <div 
              v-for="game in filteredGamesList" 
              :key="game.id" 
              class="dropdown-item"
              :class="{ selected: formData.game_id === game.id }"
              @mousedown.prevent="selectGame(game)"
            >
              <span class="dropdown-item-name">{{ game.name }}</span>
              <span class="dropdown-item-info">{{ game.players_min }}–{{ game.players_max }} игроков</span>
            </div>
            <div v-if="filteredGamesList.length === 0" class="dropdown-empty">
              Игры не найдены
            </div>
          </div>
        </div>

        <!-- Проведение конвента (если не заблокировано) -->
        <div v-if="!lockConvention && conventionEvents && conventionEvents.length > 0" class="form-group">
          <label>Проведение конвента (опционально)</label>
          <select 
            v-model="formData.convention_event_id"
            @change="onConventionEventChange"
            class="form-input"
          >
            <option :value="null">Без конвента (отдельный прогон)</option>
            <option 
              v-for="event in sortedConventionEvents" 
              :key="event.id" 
              :value="event.id"
            >
              {{ event.convention_name }} — {{ event.city_name || (event.city && event.city.name) }} ({{ formatDates(event.date_start, event.date_end) }})
            </option>
          </select>
        </div>

        <!-- Информация о конвенте (если заблокировано) -->
        <div v-if="lockConvention && conventionName" class="form-group">
          <label>Конвент</label>
          <input 
            type="text"
            class="form-input"
            :value="conventionName"
            disabled
          />
        </div>
        
        <!-- Город -->
        <div class="form-group searchable-select">
          <label>Город *</label>
          <input 
            v-if="!lockConvention && !formData.convention_event_id"
            v-model="citySearch"
            type="text"
            class="form-input"
            placeholder="Введите название города..."
            autocomplete="off"
            @focus="showCityDropdown = true"
            @blur="onCityInputBlur"
            @keydown.enter.prevent
          />
          <input 
            v-else
            type="text"
            class="form-input"
            :value="citySearch"
            disabled
          />
          <div v-if="showCityDropdown && !lockConvention && !formData.convention_event_id" class="dropdown-list">
            <div 
              v-for="city in filteredCitiesList" 
              :key="city.id" 
              class="dropdown-item"
              :class="{ selected: formData.city_id === city.id }"
              @mousedown.prevent="selectCity(city)"
            >
              {{ city.name }}{{ city.region && city.region.name ? ` (${city.region.name})` : '' }}
            </div>
            <div 
              v-if="allowNewCity"
              class="dropdown-item dropdown-item-new"
              @mousedown.prevent="selectNewCity"
            >
              + Создать новый город
            </div>
            <div v-if="filteredCitiesList.length === 0 && citySearch" class="dropdown-empty">
              Города не найдены
            </div>
          </div>
          <p v-if="formData.convention_event_id || lockConvention" class="form-hint">
            Город определяется проведением конвента
          </p>
        </div>
        
        <!-- Новый город -->
        <div v-if="formData.city_id === 'new'" class="form-group">
          <label>Название нового города *</label>
          <input 
            v-model="formData.newCityName" 
            type="text" 
            required
            class="form-input"
            placeholder="Введите название города"
          />
        </div>

        <!-- Площадка -->
        <div v-if="formData.city_id && formData.city_id !== 'new' && !lockConvention" class="form-group">
          <label>Площадка</label>
          <select 
            v-model="formData.venue_id"
            @change="onVenueChange"
            class="form-input"
          >
            <option :value="null">Не указана</option>
            <option 
              v-for="venue in venuesList" 
              :key="venue.id" 
              :value="venue.id"
            >
              {{ venue.name }}
            </option>
          </select>
        </div>
        
        <!-- Помещения -->
        <div v-if="roomsList.length > 0" class="form-group">
          <label>Помещения</label>
          <select 
            v-model="formData.room_ids"
            class="form-input"
            multiple
            :size="Math.min(roomsList.length, 4)"
          >
            <option 
              v-for="room in roomsList" 
              :key="room.id" 
              :value="room.id"
            >
              {{ room.name }}{{ room.blackbox ? ' [blackbox]' : '' }}
            </option>
          </select>
          <span class="form-hint">Зажмите Ctrl для выбора нескольких</span>
        </div>
        
        <!-- Дата и время -->
        <div class="form-row">
          <div class="form-group half">
            <label>Дата *</label>
            <input 
              v-model="formData.date" 
              type="date" 
              required
              class="form-input"
              :min="dateConstraints.min"
              :max="dateConstraints.max"
            />
          </div>
          
          <div class="form-group half">
            <label>Время * <span v-if="timezoneLabel" class="timezone-label">{{ timezoneLabel }}</span></label>
            <input 
              v-model="formData.time" 
              type="time" 
              required
              class="form-input"
            />
          </div>
        </div>
        
        <!-- Длительность и макс. игроков -->
        <div class="form-row">
          <div class="form-group half">
            <label>Длительность (мин) *</label>
            <input 
              v-model.number="formData.duration" 
              type="number" 
              required
              min="30"
              max="720"
              class="form-input"
            />
          </div>
          
          <div class="form-group half">
            <label>Макс. игроков</label>
            <input 
              v-model.number="formData.max_players" 
              type="number" 
              min="1"
              class="form-input"
              :placeholder="selectedGameMaxPlayers ? `Из игры: ${selectedGameMaxPlayers}` : 'Из игры'"
            />
          </div>
        </div>
        
        <!-- Регистрация -->
        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" v-model="formData.registration_open" />
            <span>Регистрация открыта</span>
          </label>
        </div>
        
        <div v-if="error" class="form-error">{{ error }}</div>
        
        <div class="form-actions">
          <button type="button" @click="$emit('cancel')" class="btn btn-secondary">Отмена</button>
          <button type="submit" class="btn btn-primary" :disabled="loading">
            {{ loading ? 'Сохранение...' : (mode === 'add' ? 'Добавить' : 'Сохранить') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RunEditor',
  props: {
    // Режим: 'add' или 'edit'
    mode: {
      type: String,
      default: 'add',
      validator: v => ['add', 'edit'].includes(v)
    },
    // Данные существующего прогона для редактирования
    run: {
      type: Object,
      default: null
    },
    // ID проведения конвента (если редактируем в контексте расписания конвента)
    conventionEventId: {
      type: [Number, String],
      default: null
    },
    // Заблокировать выбор конвента
    lockConvention: {
      type: Boolean,
      default: false
    },
    // Заблокировать изменение игры при редактировании
    lockGame: {
      type: Boolean,
      default: false
    },
    // Название конвента для отображения (если lockConvention)
    conventionName: {
      type: String,
      default: ''
    },
    // Список игр
    games: {
      type: Array,
      default: () => []
    },
    // Список городов
    cities: {
      type: Array,
      default: () => []
    },
    // Список проведений конвентов
    conventionEvents: {
      type: Array,
      default: () => []
    },
    // Помещения, доступные для выбора (если lockConvention - помещения площадки конвента)
    availableRooms: {
      type: Array,
      default: () => []
    },
    // Ограничения по датам
    dateConstraints: {
      type: Object,
      default: () => ({ min: '', max: '' })
    },
    // Разрешить создание нового города
    allowNewCity: {
      type: Boolean,
      default: true
    },
    // CSRF токен
    csrfToken: {
      type: String,
      default: ''
    },
    // Город по умолчанию (для контекста конвента)
    defaultCity: {
      type: Object,
      default: null
    },
    // Таймзона по умолчанию
    defaultTimezone: {
      type: String,
      default: 'Europe/Moscow'
    },
    // Дата по умолчанию
    defaultDate: {
      type: String,
      default: ''
    }
  },
  emits: ['save', 'cancel', 'error'],
  data() {
    return {
      formData: {
        game_id: null,
        convention_event_id: null,
        city_id: null,
        city_timezone: 'Europe/Moscow',
        newCityName: '',
        venue_id: null,
        room_ids: [],
        date: '',
        time: '12:00',
        duration: 180,
        max_players: null,
        registration_open: true
      },
      loading: false,
      error: null,
      gameSearch: '',
      citySearch: '',
      showGameDropdown: false,
      showCityDropdown: false,
      venuesList: [],
      roomsList: []
    }
  },
  computed: {
    sortedGames() {
      return this.games.slice().sort((a, b) => a.name.localeCompare(b.name, 'ru'))
    },
    sortedConventionEvents() {
      return this.conventionEvents.slice().sort((a, b) => {
        const nameA = a.convention_name || ''
        const nameB = b.convention_name || ''
        return nameA.localeCompare(nameB, 'ru')
      })
    },
    filteredGamesList() {
      if (!this.gameSearch) {
        return this.sortedGames
      }
      const query = this.gameSearch.toLowerCase()
      return this.sortedGames.filter(g => g.name.toLowerCase().includes(query))
    },
    filteredCitiesList() {
      const sortedCities = this.cities.slice().sort((a, b) => a.name.localeCompare(b.name, 'ru'))
      if (!this.citySearch) {
        return sortedCities
      }
      const query = this.citySearch.toLowerCase()
      return sortedCities.filter(c => c.name.toLowerCase().includes(query))
    },
    selectedGameName() {
      if (!this.formData.game_id) return ''
      const game = this.games.find(g => g.id === this.formData.game_id)
      return game ? game.name : ''
    },
    selectedGameMaxPlayers() {
      if (!this.formData.game_id) return null
      const game = this.games.find(g => g.id === this.formData.game_id)
      return game ? game.players_max : null
    },
    selectedCityName() {
      if (!this.formData.city_id || this.formData.city_id === 'new') return ''
      const city = this.cities.find(c => c.id === this.formData.city_id)
      if (!city) return ''
      const regionName = city.region && city.region.name ? city.region.name : ''
      return regionName ? `${city.name} (${regionName})` : city.name
    },
    timezoneLabel() {
      return this.getTimezoneAbbr(this.formData.city_timezone)
    }
  },
  watch: {
    run: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.mode === 'edit') {
          this.initFromRun(newVal)
        }
      }
    },
    conventionEventId: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.lockConvention) {
          this.formData.convention_event_id = newVal
        }
      }
    },
    defaultCity: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.lockConvention) {
          this.formData.city_id = newVal.id
          this.formData.city_timezone = newVal.timezone || 'Europe/Moscow'
          const regionName = newVal.region && newVal.region.name ? newVal.region.name : ''
          this.citySearch = regionName ? `${newVal.name} (${regionName})` : newVal.name
        }
      }
    },
    defaultDate: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.mode === 'add') {
          this.formData.date = newVal
        }
      }
    },
    defaultTimezone: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.mode === 'add') {
          this.formData.city_timezone = newVal
        }
      }
    },
    availableRooms: {
      immediate: true,
      handler(newVal) {
        if (this.lockConvention && newVal && newVal.length > 0) {
          this.roomsList = newVal
        }
      }
    }
  },
  methods: {
    initFromRun(run) {
      // Парсим дату и время
      let runDate = ''
      let runTime = '12:00'
      
      // Используем date_local если доступна (формат YYYY-MM-DDTHH:MM:SS)
      const dateStr = run.date_local || run.date
      if (dateStr) {
        const parts = dateStr.split('T')
        if (parts.length >= 1) {
          runDate = parts[0]
        }
        if (parts.length >= 2) {
          runTime = parts[1].slice(0, 5)
        }
      }
      
      // Определяем city_id
      let cityId = null
      let cityTimezone = 'Europe/Moscow'
      if (run.city_id) {
        cityId = run.city_id
      } else if (run.city) {
        // Ищем город по названию
        const city = this.cities.find(c => c.name === run.city)
        if (city) {
          cityId = city.id
          cityTimezone = city.timezone || 'Europe/Moscow'
        }
      }
      
      // Определяем venue и rooms
      let venueId = null
      let roomIds = []
      if (run.rooms && run.rooms.length > 0) {
        roomIds = run.rooms.map(r => r.id)
        // Площадка берётся из первого помещения
        if (run.rooms[0].venue_id) {
          venueId = run.rooms[0].venue_id
        }
      }
      
      this.formData = {
        game_id: run.game_id || (run.game && run.game.id) || null,
        convention_event_id: this.lockConvention ? this.conventionEventId : (run.convention_event_id || run.convention_event || null),
        city_id: cityId,
        city_timezone: run.city_timezone || cityTimezone,
        newCityName: '',
        venue_id: venueId,
        room_ids: roomIds,
        date: runDate,
        time: runTime,
        duration: run.duration || 180,
        max_players: run.max_players || null,
        registration_open: run.registration_open !== false
      }
      
      // Устанавливаем поисковые поля
      this.gameSearch = run.game_name || (run.game && run.game.name) || ''
      this.citySearch = this.selectedCityName || run.city || ''
      
      // Загружаем площадки и помещения
      if (cityId && !this.lockConvention) {
        this.fetchVenuesByCity(cityId).then(() => {
          if (venueId) {
            this.fetchRoomsByVenue(venueId)
          }
        })
      }
    },
    
    selectGame(game) {
      this.formData.game_id = game.id
      this.gameSearch = game.name
      this.showGameDropdown = false
    },
    
    selectCity(city) {
      this.formData.city_id = city.id
      this.formData.city_timezone = city.timezone || 'Europe/Moscow'
      const regionName = city.region && city.region.name ? city.region.name : ''
      this.citySearch = regionName ? `${city.name} (${regionName})` : city.name
      this.showCityDropdown = false
      // Сбрасываем площадку и помещения
      this.formData.venue_id = null
      this.formData.room_ids = []
      this.roomsList = []
      this.fetchVenuesByCity(city.id)
    },
    
    selectNewCity() {
      this.formData.city_id = 'new'
      this.citySearch = ''
      this.showCityDropdown = false
      this.formData.venue_id = null
      this.formData.room_ids = []
      this.venuesList = []
      this.roomsList = []
    },
    
    onGameInputBlur() {
      setTimeout(() => {
        this.showGameDropdown = false
        if (this.formData.game_id && this.gameSearch !== this.selectedGameName) {
          this.gameSearch = this.selectedGameName
        }
      }, 200)
    },
    
    onCityInputBlur() {
      setTimeout(() => {
        this.showCityDropdown = false
        if (this.formData.city_id && this.formData.city_id !== 'new' && this.citySearch !== this.selectedCityName) {
          this.citySearch = this.selectedCityName
        }
      }, 200)
    },
    
    onConventionEventChange() {
      if (this.formData.convention_event_id) {
        const event = this.conventionEvents.find(e => e.id === this.formData.convention_event_id)
        if (event && event.city) {
          this.formData.city_id = event.city.id
          this.formData.city_timezone = event.city.timezone || 'Europe/Moscow'
          const regionName = event.city.region && event.city.region.name ? event.city.region.name : ''
          this.citySearch = regionName ? `${event.city.name} (${regionName})` : event.city.name
          // Загружаем площадки
          this.formData.venue_id = null
          this.formData.room_ids = []
          this.roomsList = []
          this.fetchVenuesByCity(event.city.id)
        }
      } else {
        this.formData.city_id = null
        this.formData.city_timezone = 'Europe/Moscow'
        this.citySearch = ''
        this.formData.venue_id = null
        this.formData.room_ids = []
        this.venuesList = []
        this.roomsList = []
      }
    },
    
    onVenueChange() {
      this.formData.room_ids = []
      if (this.formData.venue_id) {
        this.fetchRoomsByVenue(this.formData.venue_id)
      } else {
        this.roomsList = []
      }
    },
    
    async fetchVenuesByCity(cityId) {
      if (!cityId) return
      try {
        const response = await fetch(`/api/venues/?city=${cityId}`)
        if (response.ok) {
          this.venuesList = await response.json()
        }
      } catch (err) {
        console.error('Ошибка загрузки площадок:', err)
      }
    },
    
    async fetchRoomsByVenue(venueId) {
      if (!venueId) return
      try {
        const response = await fetch(`/api/rooms/?venue=${venueId}`)
        if (response.ok) {
          this.roomsList = await response.json()
        }
      } catch (err) {
        console.error('Ошибка загрузки помещений:', err)
      }
    },
    
    getTimezoneAbbr(timezone) {
      if (!timezone) return ''
      const abbrs = {
        'Europe/Kaliningrad': 'UTC+2',
        'Europe/Moscow': 'MSK',
        'Europe/Samara': 'UTC+4',
        'Asia/Yekaterinburg': 'UTC+5',
        'Asia/Omsk': 'UTC+6',
        'Asia/Krasnoyarsk': 'UTC+7',
        'Asia/Irkutsk': 'UTC+8',
        'Asia/Yakutsk': 'UTC+9',
        'Asia/Vladivostok': 'UTC+10',
        'Asia/Magadan': 'UTC+11',
        'Asia/Kamchatka': 'UTC+12'
      }
      return abbrs[timezone] || timezone
    },
    
    formatDates(start, end) {
      const formatDate = (dateStr) => {
        const d = new Date(dateStr)
        const day = String(d.getDate()).padStart(2, '0')
        const month = String(d.getMonth() + 1).padStart(2, '0')
        const year = d.getFullYear()
        return `${day}/${month}/${year}`
      }
      return `${formatDate(start)} — ${formatDate(end)}`
    },
    
    // eslint-disable-next-line no-unused-vars
    convertToTimezone(date, time, timezone) {
      // Создаём строку даты-времени и конвертируем в ISO
      const dateTimeStr = `${date}T${time}:00`
      
      // Для простоты используем локальную дату-время
      // Бэкенд должен обрабатывать таймзону на своей стороне
      return dateTimeStr
    },
    
    async submitForm() {
      this.loading = true
      this.error = null
      
      try {
        // Валидация
        if (!this.formData.game_id) {
          throw new Error('Выберите игру из списка')
        }
        
        if (!this.formData.date || !this.formData.time) {
          throw new Error('Укажите дату и время')
        }
        
        let cityId = this.formData.city_id
        
        // Создание нового города если нужно
        if (cityId === 'new' && this.formData.newCityName.trim()) {
          const cityResponse = await fetch('/api/cities/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify({ name: this.formData.newCityName.trim() })
          })
          
          if (!cityResponse.ok) {
            throw new Error('Ошибка при создании города')
          }
          
          const newCity = await cityResponse.json()
          cityId = newCity.id
          this.$emit('city-created', newCity)
        }
        
        if (!cityId || cityId === 'new') {
          throw new Error('Выберите или создайте город')
        }
        
        // Формируем дату-время
        const dateTime = `${this.formData.date}T${this.formData.time}:00`
        
        // Формируем данные для API
        const runData = {
          game_id: this.formData.game_id,
          city_id: cityId,
          date: dateTime,
          duration: this.formData.duration,
          max_players: this.formData.max_players || null,
          registration_open: this.formData.registration_open
        }
        
        if (this.formData.convention_event_id) {
          runData.convention_event_id = this.formData.convention_event_id
        }
        
        if (this.formData.room_ids && this.formData.room_ids.length > 0) {
          runData.room_ids = this.formData.room_ids
        }
        
        // Добавляем ID для редактирования
        if (this.mode === 'edit' && this.run) {
          runData.id = this.run.id
        }
        
        // Эмитим событие с данными
        this.$emit('save', runData)
      } catch (err) {
        this.error = err.message
        this.$emit('error', err.message)
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
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
  max-width: 550px;
  width: 100%;
  max-height: 85vh;
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
  font-size: 1.5rem;
  margin-bottom: 24px;
  padding-right: 40px;
}

.run-form {
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

.form-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-row {
  display: flex;
  gap: 20px;
}

.form-group.half {
  flex: 1;
}

.form-hint {
  font-size: 0.8rem;
  color: #666;
  margin-top: 4px;
}

.timezone-label {
  font-size: 0.8rem;
  color: #00ccff;
  font-weight: normal;
  text-transform: none;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  color: #ccc;
  text-transform: none;
  letter-spacing: normal;
}

.checkbox-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.form-error {
  background: rgba(255, 68, 68, 0.15);
  border: 1px solid #ff4444;
  border-radius: 8px;
  padding: 12px 16px;
  color: #ff6b6b;
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
  border: none;
}

.btn-primary {
  background: linear-gradient(145deg, #ff6b35, #e55a2b);
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

.btn-secondary {
  background: transparent;
  border: 2px solid #666;
  color: #aaa;
}

.btn-secondary:hover {
  border-color: #888;
  color: #ccc;
}

/* Searchable select */
.searchable-select {
  position: relative;
}

.dropdown-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  max-height: 300px;
  overflow-y: auto;
  background: #0a0a0a;
  border: 2px solid #ff6b35;
  border-top: none;
  border-radius: 0 0 8px 8px;
  z-index: 100;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}

.dropdown-item {
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid #ff6b3522;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item:hover,
.dropdown-item.selected {
  background: rgba(255, 107, 53, 0.15);
}

.dropdown-item-name {
  font-weight: 600;
  color: #e0e0e0;
}

.dropdown-item-info {
  font-size: 0.85rem;
  color: #888;
}

.dropdown-item-new {
  color: #00ccff;
  font-weight: 600;
}

.dropdown-item-new:hover {
  background: rgba(0, 204, 255, 0.15);
}

.dropdown-empty {
  padding: 20px;
  text-align: center;
  color: #666;
}

/* Scrollbar */
.modal-content::-webkit-scrollbar,
.dropdown-list::-webkit-scrollbar {
  width: 8px;
}

.modal-content::-webkit-scrollbar-track,
.dropdown-list::-webkit-scrollbar-track {
  background: #0a0a0a;
}

.modal-content::-webkit-scrollbar-thumb,
.dropdown-list::-webkit-scrollbar-thumb {
  background: #ff6b35;
  border-radius: 4px;
}

/* Responsive */
@media (max-width: 768px) {
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
