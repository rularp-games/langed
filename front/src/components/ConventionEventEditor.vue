<template>
  <div class="modal-overlay" @click.self="$emit('cancel')">
    <div class="modal-content event-editor-modal">
      <button class="modal-close" @click="$emit('cancel')">×</button>
      
      <h2>{{ mode === 'add' ? 'Добавить проведение конвента' : 'Редактировать проведение' }}</h2>
      
      <form @submit.prevent="submitForm" class="event-form">
        <!-- Конвент -->
        <div class="form-group searchable-select">
          <label>Конвент *</label>
          <input 
            v-if="!lockConvention"
            v-model="conventionSearch"
            type="text"
            class="form-input"
            placeholder="Введите название конвента..."
            autocomplete="off"
            @focus="showConventionDropdown = true"
            @blur="onConventionInputBlur"
            @keydown.enter.prevent
          />
          <input 
            v-else
            type="text"
            class="form-input"
            :value="conventionSearch"
            disabled
          />
          <div v-if="showConventionDropdown && !lockConvention" class="dropdown-list">
            <div 
              v-for="conv in filteredConventionsList" 
              :key="conv.id" 
              class="dropdown-item"
              :class="{ selected: formData.convention_id === conv.id }"
              @mousedown.prevent="selectConvention(conv)"
            >
              <span class="dropdown-item-name">{{ conv.name }}</span>
            </div>
            <div v-if="filteredConventionsList.length === 0" class="dropdown-empty">
              Конвенты не найдены
            </div>
          </div>
        </div>
        
        <!-- Город -->
        <div class="form-group searchable-select">
          <label>Город *</label>
          <input 
            v-model="citySearch"
            type="text"
            class="form-input"
            placeholder="Введите название города..."
            autocomplete="off"
            @focus="showCityDropdown = true"
            @blur="onCityInputBlur"
            @keydown.enter.prevent
          />
          <div v-if="showCityDropdown" class="dropdown-list">
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
        <div v-if="formData.city_id && formData.city_id !== 'new'" class="form-group">
          <label>Площадка (опционально)</label>
          <select 
            v-model="formData.venue_id"
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
        
        <!-- Дата начала и окончания -->
        <div class="form-row">
          <div class="form-group half">
            <label>Дата начала * <span class="format-hint">(дд/мм/гггг)</span></label>
            <div class="date-picker-wrapper">
              <input 
                :value="formattedDateStart"
                @input="handleDateStartInput"
                @blur="validateDates"
                type="text" 
                required
                class="form-input date-input"
                placeholder="дд/мм/гггг"
                maxlength="10"
              />
              <input 
                ref="dateStartPickerInput"
                type="date"
                class="date-picker-native"
                :value="formData.date_start"
                @change="handleDateStartPickerChange"
              />
              <button 
                type="button" 
                class="date-picker-btn"
                @click="openDateStartPicker"
                title="Открыть календарь"
              >
                📅
              </button>
            </div>
          </div>
          
          <div class="form-group half">
            <label>Дата окончания * <span class="format-hint">(дд/мм/гггг)</span></label>
            <div class="date-picker-wrapper">
              <input 
                :value="formattedDateEnd"
                @input="handleDateEndInput"
                @blur="validateDates"
                type="text" 
                required
                class="form-input date-input"
                placeholder="дд/мм/гггг"
                maxlength="10"
              />
              <input 
                ref="dateEndPickerInput"
                type="date"
                class="date-picker-native"
                :value="formData.date_end"
                :min="formData.date_start"
                @change="handleDateEndPickerChange"
              />
              <button 
                type="button" 
                class="date-picker-btn"
                @click="openDateEndPicker"
                title="Открыть календарь"
              >
                📅
              </button>
            </div>
          </div>
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
  name: 'ConventionEventEditor',
  props: {
    // Режим: 'add' или 'edit'
    mode: {
      type: String,
      default: 'add',
      validator: v => ['add', 'edit'].includes(v)
    },
    // Данные существующего проведения для редактирования
    conventionEvent: {
      type: Object,
      default: null
    },
    // ID конвента (если добавляем из контекста конвента)
    conventionId: {
      type: [Number, String],
      default: null
    },
    // Заблокировать выбор конвента
    lockConvention: {
      type: Boolean,
      default: false
    },
    // Название конвента для отображения (если lockConvention)
    conventionName: {
      type: String,
      default: ''
    },
    // Список конвентов
    conventions: {
      type: Array,
      default: () => []
    },
    // Список городов
    cities: {
      type: Array,
      default: () => []
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
    }
  },
  emits: ['save', 'cancel', 'error', 'city-created'],
  data() {
    return {
      formData: {
        convention_id: null,
        city_id: null,
        newCityName: '',
        venue_id: null,
        date_start: '',
        date_end: ''
      },
      loading: false,
      error: null,
      conventionSearch: '',
      citySearch: '',
      showConventionDropdown: false,
      showCityDropdown: false,
      venuesList: []
    }
  },
  computed: {
    sortedConventions() {
      return this.conventions.slice().sort((a, b) => a.name.localeCompare(b.name, 'ru'))
    },
    filteredConventionsList() {
      if (!this.conventionSearch) {
        return this.sortedConventions
      }
      const query = this.conventionSearch.toLowerCase()
      return this.sortedConventions.filter(c => c.name.toLowerCase().includes(query))
    },
    filteredCitiesList() {
      const sortedCities = this.cities.slice().sort((a, b) => a.name.localeCompare(b.name, 'ru'))
      if (!this.citySearch) {
        return sortedCities
      }
      const query = this.citySearch.toLowerCase()
      return sortedCities.filter(c => c.name.toLowerCase().includes(query))
    },
    selectedConventionName() {
      if (!this.formData.convention_id) return ''
      const conv = this.conventions.find(c => c.id === this.formData.convention_id)
      return conv ? conv.name : ''
    },
    selectedCityName() {
      if (!this.formData.city_id || this.formData.city_id === 'new') return ''
      const city = this.cities.find(c => c.id === this.formData.city_id)
      if (!city) return ''
      const regionName = city.region && city.region.name ? city.region.name : ''
      return regionName ? `${city.name} (${regionName})` : city.name
    },
    // Форматированная дата начала для отображения (дд/мм/гггг)
    formattedDateStart() {
      if (!this.formData.date_start) return ''
      const parts = this.formData.date_start.split('-')
      if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`
      }
      return this.formData.date_start
    },
    // Форматированная дата окончания для отображения (дд/мм/гггг)
    formattedDateEnd() {
      if (!this.formData.date_end) return ''
      const parts = this.formData.date_end.split('-')
      if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`
      }
      return this.formData.date_end
    }
  },
  watch: {
    conventionEvent: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.mode === 'edit') {
          this.initFromEvent(newVal)
        }
      }
    },
    conventionId: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.mode === 'add') {
          this.formData.convention_id = parseInt(newVal, 10)
          // Устанавливаем название конвента в поиске
          const conv = this.conventions.find(c => c.id === this.formData.convention_id)
          if (conv) {
            this.conventionSearch = conv.name
          } else if (this.conventionName) {
            this.conventionSearch = this.conventionName
          }
        }
      }
    },
    conventionName: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.lockConvention) {
          this.conventionSearch = newVal
        }
      }
    },
    conventions: {
      handler() {
        // Обновляем название конвента если оно ещё не установлено
        if (this.formData.convention_id && !this.conventionSearch) {
          const conv = this.conventions.find(c => c.id === this.formData.convention_id)
          if (conv) {
            this.conventionSearch = conv.name
          }
        }
      }
    }
  },
  methods: {
    initFromEvent(event) {
      // Определяем city_id
      let cityId = null
      let cityName = ''
      
      if (event.city_id) {
        cityId = event.city_id
      } else if (event.city) {
        cityId = event.city.id
        const regionName = event.city.region && event.city.region.name ? event.city.region.name : ''
        cityName = regionName ? `${event.city.name} (${regionName})` : event.city.name
      }
      
      this.formData = {
        convention_id: event.convention_id || event.convention || null,
        city_id: cityId,
        newCityName: '',
        venue_id: event.venue_id || (event.venue && event.venue.id) || null,
        date_start: event.date_start || '',
        date_end: event.date_end || ''
      }
      
      // Устанавливаем поисковые поля
      if (event.convention_name) {
        this.conventionSearch = event.convention_name
      } else {
        const conv = this.conventions.find(c => c.id === this.formData.convention_id)
        if (conv) {
          this.conventionSearch = conv.name
        }
      }
      
      this.citySearch = cityName || this.selectedCityName
      
      // Загружаем площадки для города
      if (cityId) {
        this.fetchVenuesByCity(cityId)
      }
    },
    
    selectConvention(conv) {
      this.formData.convention_id = conv.id
      this.conventionSearch = conv.name
      this.showConventionDropdown = false
    },
    
    selectCity(city) {
      this.formData.city_id = city.id
      const regionName = city.region && city.region.name ? city.region.name : ''
      this.citySearch = regionName ? `${city.name} (${regionName})` : city.name
      this.showCityDropdown = false
      // Сбрасываем площадку
      this.formData.venue_id = null
      this.fetchVenuesByCity(city.id)
    },
    
    selectNewCity() {
      this.formData.city_id = 'new'
      this.citySearch = ''
      this.showCityDropdown = false
      this.formData.venue_id = null
      this.venuesList = []
    },
    
    onConventionInputBlur() {
      setTimeout(() => {
        this.showConventionDropdown = false
        if (this.formData.convention_id && this.conventionSearch !== this.selectedConventionName) {
          this.conventionSearch = this.selectedConventionName
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
    
    parseDateInput(value) {
      // Парсим дд/мм/гггг в yyyy-mm-dd
      const parts = value.split('/')
      if (parts.length === 3 && parts[0].length === 2 && parts[1].length === 2 && parts[2].length === 4) {
        const day = parts[0]
        const month = parts[1]
        const year = parts[2]
        return `${year}-${month}-${day}`
      }
      return null
    },
    
    formatDateInputValue(event) {
      let value = event.target.value
      // Оставляем только цифры и слэши
      value = value.replace(/[^\d/]/g, '')
      
      // Автоматически добавляем слэши
      if (value.length === 2 && !value.includes('/')) {
        value += '/'
      } else if (value.length === 5 && value.split('/').length === 2) {
        value += '/'
      }
      
      // Ограничиваем длину
      if (value.length > 10) {
        value = value.slice(0, 10)
      }
      
      event.target.value = value
      return value
    },
    
    handleDateStartInput(event) {
      const value = this.formatDateInputValue(event)
      const date = this.parseDateInput(value)
      if (date) {
        this.formData.date_start = date
      }
    },
    
    handleDateEndInput(event) {
      const value = this.formatDateInputValue(event)
      const date = this.parseDateInput(value)
      if (date) {
        this.formData.date_end = date
      }
    },
    
    validateDates() {
      if (this.formData.date_start && this.formData.date_end) {
        if (this.formData.date_end < this.formData.date_start) {
          this.formData.date_end = this.formData.date_start
        }
      }
    },
    
    openDateStartPicker() {
      if (this.$refs.dateStartPickerInput) {
        this.$refs.dateStartPickerInput.showPicker()
      }
    },
    
    openDateEndPicker() {
      if (this.$refs.dateEndPickerInput) {
        this.$refs.dateEndPickerInput.showPicker()
      }
    },
    
    handleDateStartPickerChange(event) {
      const value = event.target.value
      if (value) {
        this.formData.date_start = value
        this.validateDates()
      }
    },
    
    handleDateEndPickerChange(event) {
      const value = event.target.value
      if (value) {
        this.formData.date_end = value
        this.validateDates()
      }
    },
    
    async submitForm() {
      this.loading = true
      this.error = null
      
      try {
        // Валидация
        if (!this.formData.convention_id) {
          throw new Error('Выберите конвент из списка')
        }
        
        if (!this.formData.date_start || !this.formData.date_end) {
          throw new Error('Укажите даты начала и окончания')
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
        
        // Формируем данные для API
        const eventData = {
          convention_id: this.formData.convention_id,
          city_id: cityId,
          date_start: this.formData.date_start,
          date_end: this.formData.date_end
        }
        
        if (this.formData.venue_id) {
          eventData.venue_id = this.formData.venue_id
        }
        
        // Добавляем ID для редактирования
        if (this.mode === 'edit' && this.conventionEvent) {
          eventData.id = this.conventionEvent.id
        }
        
        // Эмитим событие с данными
        this.$emit('save', eventData)
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

.event-form {
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

/* Date inputs */
.format-hint {
  font-size: 0.75rem;
  color: #666;
  font-weight: normal;
  text-transform: none;
}

.date-picker-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}

.date-picker-wrapper .date-input {
  width: 100%;
  padding-right: 44px;
  box-sizing: border-box;
}

.date-picker-native {
  position: absolute;
  right: 40px;
  top: 0;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.date-picker-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 4px;
  line-height: 1;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.date-picker-btn:hover {
  opacity: 1;
}

.date-input {
  font-family: 'Courier New', monospace;
  letter-spacing: 0.05em;
}

.date-input::placeholder {
  letter-spacing: normal;
  font-family: inherit;
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
