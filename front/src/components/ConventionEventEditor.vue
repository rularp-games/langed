<template>
  <div class="modal-overlay" @click.self="$emit('cancel')">
    <div class="modal-content event-editor-modal">
      <button class="modal-close" @click="$emit('cancel')">×</button>

      <h2>
        {{
          mode === "add"
            ? "Добавить проведение конвента"
            : "Редактировать проведение"
        }}
      </h2>

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
          <div
            v-if="showConventionDropdown && !lockConvention"
            class="dropdown-list"
          >
            <div
              v-for="conv in filteredConventionsList"
              :key="conv.id"
              class="dropdown-item"
              :class="{ selected: formData.convention_id === conv.id }"
              @mousedown.prevent="selectConvention(conv)"
            >
              <span class="dropdown-item-name">{{ conv.name }}</span>
            </div>
            <div
              v-if="filteredConventionsList.length === 0"
              class="dropdown-empty"
            >
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
              {{ city.name
              }}{{
                city.region && city.region.name ? ` (${city.region.name})` : ""
              }}
            </div>
            <div
              v-if="allowNewCity"
              class="dropdown-item dropdown-item-new"
              @mousedown.prevent="selectNewCity"
            >
              + Создать новый город
            </div>
            <div
              v-if="filteredCitiesList.length === 0 && citySearch"
              class="dropdown-empty"
            >
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
        <div
          v-if="formData.city_id && formData.city_id !== 'new'"
          class="form-group"
        >
          <label>Площадка (опционально)</label>
          <select v-model="formData.venue_id" class="form-input">
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
            <label
              >Дата начала *
              <span class="format-hint">(дд/мм/гггг)</span></label
            >
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
            <label
              >Дата окончания *
              <span class="format-hint">(дд/мм/гггг)</span></label
            >
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

        <!-- Настройки регистрации участников -->
        <div class="registration-settings">
          <div class="settings-header">
            <span class="settings-icon">📝</span>
            <span class="settings-label">Регистрация участников</span>
          </div>

          <div class="form-row">
            <div class="form-group half">
              <label>
                <input
                  type="checkbox"
                  v-model="formData.registration_open"
                  class="form-checkbox"
                />
                Регистрация открыта
              </label>
            </div>

            <div class="form-group half">
              <label>Лимит участников</label>
              <input
                v-model.number="formData.capacity"
                type="number"
                min="1"
                class="form-input"
                placeholder="Без ограничений"
              />
            </div>
          </div>

          <div
            v-if="mode === 'edit' && conventionEvent"
            class="registration-stats"
          >
            <span class="stat-item">
              ✅ Подтверждено: {{ conventionEvent.registrations_count || 0 }}
            </span>
            <span
              v-if="conventionEvent.pending_registrations_count > 0"
              class="stat-item stat-pending"
            >
              ⏳ Ожидает: {{ conventionEvent.pending_registrations_count }}
            </span>
          </div>
        </div>

        <!-- Секция управления регистрациями (только в режиме редактирования) -->
        <div
          v-if="mode === 'edit' && conventionEvent && canEdit"
          class="registrations-section"
        >
          <div class="registrations-header">
            <span class="registrations-icon">👥</span>
            <span class="registrations-label">Заявки участников</span>
            <button
              type="button"
              class="refresh-btn"
              @click="fetchRegistrations"
              :disabled="registrationsLoading"
            >
              {{ registrationsLoading ? "..." : "🔄" }}
            </button>
          </div>

          <div v-if="registrations.length === 0" class="no-registrations">
            Заявок пока нет
          </div>

          <div v-else class="registrations-list">
            <div
              v-for="reg in registrations"
              :key="reg.id"
              class="registration-item"
              :class="'status-' + reg.status"
            >
              <div class="reg-user">
                <span class="reg-user-name">{{ reg.user.display_name }}</span>
                <span class="reg-date">{{
                  formatRegDate(reg.created_at)
                }}</span>
              </div>

              <div class="reg-status">
                <select
                  :value="reg.status"
                  @change="
                    updateRegistrationStatus(reg.id, $event.target.value)
                  "
                  class="status-select"
                  :disabled="registrationsLoading"
                >
                  <option value="pending">⏳ Ожидает</option>
                  <option value="confirmed">✅ Подтверждена</option>
                  <option value="rejected">❌ Отклонена</option>
                  <option value="cancelled">🚫 Отменена</option>
                </select>
              </div>

              <div v-if="reg.comment" class="reg-comment">
                💬 {{ reg.comment }}
              </div>
            </div>
          </div>

          <div v-if="registrationsError" class="registrations-error">
            {{ registrationsError }}
          </div>
        </div>

        <!-- Секция управления организаторами (только в режиме редактирования) -->
        <div
          v-if="mode === 'edit' && conventionEvent"
          class="organizers-section"
        >
          <div class="organizers-header">
            <span class="organizers-icon">👤</span>
            <span class="organizers-label">{{
              organizers.length > 1 ? "Организаторы:" : "Организатор:"
            }}</span>
          </div>
          <div v-if="organizers.length > 0" class="organizers-list">
            <div
              v-for="organizer in organizers"
              :key="organizer.id"
              class="organizer-item"
            >
              <span class="organizer-name">{{ organizer.display_name }}</span>
              <button
                v-if="canEdit"
                class="organizer-remove-btn"
                @click="removeOrganizer(organizer)"
                title="Удалить организатора"
              >
                ×
              </button>
            </div>
          </div>
          <div v-else class="no-organizers">Организаторы не назначены</div>
          <!-- Форма добавления организатора с автодополнением -->
          <div v-if="canEdit" class="add-organizer-form">
            <div class="autocomplete-wrapper">
              <input
                v-model="newOrganizerUsername"
                type="text"
                class="add-organizer-input"
                placeholder="Начните вводить имя..."
                autocomplete="off"
                @input="searchOrganizers"
                @focus="showOrganizerDropdown = true"
                @blur="hideOrganizerDropdownDelayed"
                @keydown.enter.prevent="selectFirstOrganizer"
                @keydown.down.prevent="highlightNextOrganizer"
                @keydown.up.prevent="highlightPrevOrganizer"
              />
              <div
                v-if="
                  showOrganizerDropdown && organizerSearchResults.length > 0
                "
                class="user-dropdown"
              >
                <div
                  v-for="(user, idx) in organizerSearchResults"
                  :key="user.id"
                  class="user-dropdown-item"
                  :class="{ highlighted: highlightedOrganizerIndex === idx }"
                  @mousedown.prevent="selectOrganizer(user)"
                >
                  <span class="user-display-name">{{ user.display_name }}</span>
                  <span class="user-username">@{{ user.username }}</span>
                </div>
              </div>
              <div
                v-if="
                  showOrganizerDropdown &&
                  newOrganizerUsername &&
                  newOrganizerUsername.length >= 2 &&
                  organizerSearchResults.length === 0 &&
                  !organizerSearchLoading
                "
                class="user-dropdown user-dropdown-empty"
              >
                Пользователи не найдены
              </div>
            </div>
            <button
              class="add-organizer-btn"
              type="button"
              @click="addOrganizerFromSelected"
              :disabled="!selectedOrganizer || organizerLoading"
            >
              {{ organizerLoading ? "..." : "+" }}
            </button>
          </div>
          <div v-if="organizerError" class="organizer-error">
            {{ organizerError }}
          </div>
        </div>

        <div v-if="error" class="form-error">{{ error }}</div>

        <div class="form-actions">
          <button
            type="button"
            @click="$emit('cancel')"
            class="btn btn-secondary"
          >
            Отмена
          </button>
          <button type="submit" class="btn btn-primary" :disabled="loading">
            {{
              loading
                ? "Сохранение..."
                : mode === "add"
                ? "Добавить"
                : "Сохранить"
            }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script>
export default {
  name: "ConventionEventEditor",
  props: {
    // Режим: 'add' или 'edit'
    mode: {
      type: String,
      default: "add",
      validator: (v) => ["add", "edit"].includes(v),
    },
    // Данные существующего проведения для редактирования
    conventionEvent: {
      type: Object,
      default: null,
    },
    // ID конвента (если добавляем из контекста конвента)
    conventionId: {
      type: [Number, String],
      default: null,
    },
    // Заблокировать выбор конвента
    lockConvention: {
      type: Boolean,
      default: false,
    },
    // Название конвента для отображения (если lockConvention)
    conventionName: {
      type: String,
      default: "",
    },
    // Список конвентов
    conventions: {
      type: Array,
      default: () => [],
    },
    // Список городов
    cities: {
      type: Array,
      default: () => [],
    },
    // Разрешить создание нового города
    allowNewCity: {
      type: Boolean,
      default: true,
    },
    // CSRF токен
    csrfToken: {
      type: String,
      default: "",
    },
  },
  emits: ["save", "cancel", "error", "city-created", "organizer-changed"],
  data() {
    return {
      savedScrollY: 0,
      formData: {
        convention_id: null,
        city_id: null,
        newCityName: "",
        venue_id: null,
        date_start: "",
        date_end: "",
        // Настройки регистрации
        capacity: null,
        registration_open: false,
      },
      loading: false,
      error: null,
      conventionSearch: "",
      citySearch: "",
      showConventionDropdown: false,
      showCityDropdown: false,
      venuesList: [],
      // Управление организаторами
      organizers: [],
      newOrganizerUsername: "",
      organizerLoading: false,
      organizerError: null,
      // Автодополнение организаторов
      organizerSearchResults: [],
      organizerSearchLoading: false,
      showOrganizerDropdown: false,
      selectedOrganizer: null,
      highlightedOrganizerIndex: 0,
      organizerSearchDebounceTimer: null,
      // Управление регистрациями
      registrations: [],
      registrationsLoading: false,
      registrationsError: null,
    };
  },
  mounted() {
    // Сохраняем позицию прокрутки и блокируем прокрутку body
    this.savedScrollY = window.scrollY;
    document.body.classList.add("modal-open");
    document.body.style.top = `-${this.savedScrollY}px`;
  },
  beforeUnmount() {
    // Восстанавливаем прокрутку body
    const scrollY = this.savedScrollY;
    document.body.classList.remove("modal-open");
    document.body.style.top = "";
    requestAnimationFrame(() => {
      window.scrollTo(0, scrollY);
    });
  },
  computed: {
    sortedConventions() {
      return this.conventions
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name, "ru"));
    },
    filteredConventionsList() {
      if (!this.conventionSearch) {
        return this.sortedConventions;
      }
      const query = this.conventionSearch.toLowerCase();
      return this.sortedConventions.filter((c) =>
        c.name.toLowerCase().includes(query)
      );
    },
    filteredCitiesList() {
      const sortedCities = this.cities
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name, "ru"));
      if (!this.citySearch) {
        return sortedCities;
      }
      const query = this.citySearch.toLowerCase();
      return sortedCities.filter((c) => c.name.toLowerCase().includes(query));
    },
    selectedConventionName() {
      if (!this.formData.convention_id) return "";
      const conv = this.conventions.find(
        (c) => c.id === this.formData.convention_id
      );
      return conv ? conv.name : "";
    },
    selectedCityName() {
      if (!this.formData.city_id || this.formData.city_id === "new") return "";
      const city = this.cities.find((c) => c.id === this.formData.city_id);
      if (!city) return "";
      const regionName =
        city.region && city.region.name ? city.region.name : "";
      return regionName ? `${city.name} (${regionName})` : city.name;
    },
    // Форматированная дата начала для отображения (дд/мм/гггг)
    formattedDateStart() {
      if (!this.formData.date_start) return "";
      const parts = this.formData.date_start.split("-");
      if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
      }
      return this.formData.date_start;
    },
    // Форматированная дата окончания для отображения (дд/мм/гггг)
    formattedDateEnd() {
      if (!this.formData.date_end) return "";
      const parts = this.formData.date_end.split("-");
      if (parts.length === 3) {
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
      }
      return this.formData.date_end;
    },
    // Может ли текущий пользователь редактировать организаторов
    canEdit() {
      return this.conventionEvent && this.conventionEvent.can_edit;
    },
  },
  watch: {
    conventionEvent: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.mode === "edit") {
          this.initFromEvent(newVal);
        }
      },
    },
    conventionId: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.mode === "add") {
          this.formData.convention_id = parseInt(newVal, 10);
          // Устанавливаем название конвента в поиске
          const conv = this.conventions.find(
            (c) => c.id === this.formData.convention_id
          );
          if (conv) {
            this.conventionSearch = conv.name;
          } else if (this.conventionName) {
            this.conventionSearch = this.conventionName;
          }
        }
      },
    },
    conventionName: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.lockConvention) {
          this.conventionSearch = newVal;
        }
      },
    },
    conventions: {
      handler() {
        // Обновляем название конвента если оно ещё не установлено
        if (this.formData.convention_id && !this.conventionSearch) {
          const conv = this.conventions.find(
            (c) => c.id === this.formData.convention_id
          );
          if (conv) {
            this.conventionSearch = conv.name;
          }
        }
      },
    },
  },
  methods: {
    initFromEvent(event) {
      // Определяем city_id
      let cityId = null;
      let cityName = "";

      if (event.city_id) {
        cityId = event.city_id;
      } else if (event.city) {
        cityId = event.city.id;
        const regionName =
          event.city.region && event.city.region.name
            ? event.city.region.name
            : "";
        cityName = regionName
          ? `${event.city.name} (${regionName})`
          : event.city.name;
      }

      this.formData = {
        convention_id: event.convention_id || event.convention || null,
        city_id: cityId,
        newCityName: "",
        venue_id: event.venue_id || (event.venue && event.venue.id) || null,
        date_start: event.date_start || "",
        date_end: event.date_end || "",
        // Настройки регистрации
        capacity: event.capacity || null,
        registration_open: event.registration_open || false,
      };

      // Устанавливаем поисковые поля
      if (event.convention_name) {
        this.conventionSearch = event.convention_name;
      } else {
        const conv = this.conventions.find(
          (c) => c.id === this.formData.convention_id
        );
        if (conv) {
          this.conventionSearch = conv.name;
        }
      }

      this.citySearch = cityName || this.selectedCityName;

      // Загружаем площадки для города
      if (cityId) {
        this.fetchVenuesByCity(cityId);
      }

      // Инициализируем организаторов
      this.organizers = event.organizers || [];
      this.newOrganizerUsername = "";
      this.organizerError = null;

      // Загружаем регистрации если в режиме редактирования
      if (this.mode === "edit" && event.id) {
        this.fetchRegistrations();
      }
    },

    selectConvention(conv) {
      this.formData.convention_id = conv.id;
      this.conventionSearch = conv.name;
      this.showConventionDropdown = false;
    },

    selectCity(city) {
      this.formData.city_id = city.id;
      const regionName =
        city.region && city.region.name ? city.region.name : "";
      this.citySearch = regionName ? `${city.name} (${regionName})` : city.name;
      this.showCityDropdown = false;
      // Сбрасываем площадку
      this.formData.venue_id = null;
      this.fetchVenuesByCity(city.id);
    },

    selectNewCity() {
      this.formData.city_id = "new";
      this.citySearch = "";
      this.showCityDropdown = false;
      this.formData.venue_id = null;
      this.venuesList = [];
    },

    onConventionInputBlur() {
      setTimeout(() => {
        this.showConventionDropdown = false;
        if (
          this.formData.convention_id &&
          this.conventionSearch !== this.selectedConventionName
        ) {
          this.conventionSearch = this.selectedConventionName;
        }
      }, 200);
    },

    onCityInputBlur() {
      setTimeout(() => {
        this.showCityDropdown = false;
        if (
          this.formData.city_id &&
          this.formData.city_id !== "new" &&
          this.citySearch !== this.selectedCityName
        ) {
          this.citySearch = this.selectedCityName;
        }
      }, 200);
    },

    async fetchVenuesByCity(cityId) {
      if (!cityId) return;
      try {
        const response = await fetch(`/api/venues/?city=${cityId}`);
        if (response.ok) {
          this.venuesList = await response.json();
        }
      } catch (err) {
        console.error("Ошибка загрузки площадок:", err);
      }
    },

    parseDateInput(value) {
      // Парсим дд/мм/гггг в yyyy-mm-dd
      const parts = value.split("/");
      if (
        parts.length === 3 &&
        parts[0].length === 2 &&
        parts[1].length === 2 &&
        parts[2].length === 4
      ) {
        const day = parts[0];
        const month = parts[1];
        const year = parts[2];
        return `${year}-${month}-${day}`;
      }
      return null;
    },

    formatDateInputValue(event) {
      let value = event.target.value;
      // Оставляем только цифры и слэши
      value = value.replace(/[^\d/]/g, "");

      // Автоматически добавляем слэши
      if (value.length === 2 && !value.includes("/")) {
        value += "/";
      } else if (value.length === 5 && value.split("/").length === 2) {
        value += "/";
      }

      // Ограничиваем длину
      if (value.length > 10) {
        value = value.slice(0, 10);
      }

      event.target.value = value;
      return value;
    },

    handleDateStartInput(event) {
      const value = this.formatDateInputValue(event);
      const date = this.parseDateInput(value);
      if (date) {
        this.formData.date_start = date;
      }
    },

    handleDateEndInput(event) {
      const value = this.formatDateInputValue(event);
      const date = this.parseDateInput(value);
      if (date) {
        this.formData.date_end = date;
      }
    },

    validateDates() {
      if (this.formData.date_start && this.formData.date_end) {
        if (this.formData.date_end < this.formData.date_start) {
          this.formData.date_end = this.formData.date_start;
        }
      }
    },

    openDateStartPicker() {
      if (this.$refs.dateStartPickerInput) {
        this.$refs.dateStartPickerInput.showPicker();
      }
    },

    openDateEndPicker() {
      if (this.$refs.dateEndPickerInput) {
        this.$refs.dateEndPickerInput.showPicker();
      }
    },

    handleDateStartPickerChange(event) {
      const value = event.target.value;
      if (value) {
        this.formData.date_start = value;
        this.validateDates();
      }
    },

    handleDateEndPickerChange(event) {
      const value = event.target.value;
      if (value) {
        this.formData.date_end = value;
        this.validateDates();
      }
    },

    async submitForm() {
      this.loading = true;
      this.error = null;

      try {
        // Валидация
        if (!this.formData.convention_id) {
          throw new Error("Выберите конвент из списка");
        }

        if (!this.formData.date_start || !this.formData.date_end) {
          throw new Error("Укажите даты начала и окончания");
        }

        let cityId = this.formData.city_id;

        // Создание нового города если нужно
        if (cityId === "new" && this.formData.newCityName.trim()) {
          const cityResponse = await fetch("/api/cities/", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this.csrfToken,
            },
            body: JSON.stringify({ name: this.formData.newCityName.trim() }),
          });

          if (!cityResponse.ok) {
            throw new Error("Ошибка при создании города");
          }

          const newCity = await cityResponse.json();
          cityId = newCity.id;
          this.$emit("city-created", newCity);
        }

        if (!cityId || cityId === "new") {
          throw new Error("Выберите или создайте город");
        }

        // Формируем данные для API
        const eventData = {
          convention_id: this.formData.convention_id,
          city_id: cityId,
          date_start: this.formData.date_start,
          date_end: this.formData.date_end,
          // Настройки регистрации
          capacity: this.formData.capacity || null,
          registration_open: this.formData.registration_open,
        };

        if (this.formData.venue_id) {
          eventData.venue_id = this.formData.venue_id;
        }

        // Добавляем ID для редактирования
        if (this.mode === "edit" && this.conventionEvent) {
          eventData.id = this.conventionEvent.id;
        }

        // Эмитим событие с данными
        this.$emit("save", eventData);
      } catch (err) {
        this.error = err.message;
        this.$emit("error", err.message);
      } finally {
        this.loading = false;
      }
    },

    // === Управление организаторами с автодополнением ===

    // Поиск пользователей с debounce
    searchOrganizers() {
      const query = this.newOrganizerUsername;

      // Сбрасываем выбранного пользователя при изменении ввода
      this.selectedOrganizer = null;
      this.highlightedOrganizerIndex = 0;

      // Очищаем предыдущий таймер
      if (this.organizerSearchDebounceTimer) {
        clearTimeout(this.organizerSearchDebounceTimer);
      }

      if (!query || query.length < 2) {
        this.organizerSearchResults = [];
        return;
      }

      // Debounce 300ms
      this.organizerSearchDebounceTimer = setTimeout(() => {
        this.fetchOrganizers(query);
      }, 300);
    },

    async fetchOrganizers(query) {
      this.organizerSearchLoading = true;

      try {
        const response = await fetch(
          `/api/users/search/?q=${encodeURIComponent(query)}`
        );
        if (response.ok) {
          const users = await response.json();
          // Фильтруем уже добавленных организаторов
          const existingIds = (this.organizers || []).map((o) => o.id);
          this.organizerSearchResults = users.filter(
            (u) => !existingIds.includes(u.id)
          );
        }
      } catch (err) {
        console.error("Ошибка поиска пользователей:", err);
      } finally {
        this.organizerSearchLoading = false;
      }
    },

    hideOrganizerDropdownDelayed() {
      setTimeout(() => {
        this.showOrganizerDropdown = false;
      }, 200);
    },

    selectOrganizer(user) {
      this.newOrganizerUsername = user.display_name;
      this.selectedOrganizer = user;
      this.showOrganizerDropdown = false;
      this.organizerSearchResults = [];
      // Автоматически добавляем
      this.addOrganizerFromSelected();
    },

    selectFirstOrganizer() {
      if (this.organizerSearchResults.length > 0) {
        const idx = this.highlightedOrganizerIndex || 0;
        this.selectOrganizer(this.organizerSearchResults[idx]);
      }
    },

    highlightNextOrganizer() {
      if (this.organizerSearchResults.length === 0) return;
      this.highlightedOrganizerIndex = Math.min(
        this.highlightedOrganizerIndex + 1,
        this.organizerSearchResults.length - 1
      );
    },

    highlightPrevOrganizer() {
      this.highlightedOrganizerIndex = Math.max(
        this.highlightedOrganizerIndex - 1,
        0
      );
    },

    async addOrganizerFromSelected() {
      const user = this.selectedOrganizer;
      if (!user || !this.conventionEvent) {
        this.organizerError = "Выберите пользователя из списка";
        return;
      }

      this.organizerLoading = true;
      this.organizerError = null;

      try {
        const response = await fetch(
          `/api/convention-events/${this.conventionEvent.id}/add_organizer/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this.csrfToken,
            },
            body: JSON.stringify({ username: user.username }),
          }
        );

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || "Ошибка при добавлении организатора");
        }

        const updatedEvent = await response.json();
        this.organizers = updatedEvent.organizers || [];
        this.newOrganizerUsername = "";
        this.selectedOrganizer = null;
        this.$emit("organizer-changed", updatedEvent);
      } catch (err) {
        this.organizerError = err.message;
      } finally {
        this.organizerLoading = false;
      }
    },

    // Для обратной совместимости
    async addOrganizer() {
      if (!this.newOrganizerUsername.trim() || !this.conventionEvent) return;

      this.organizerLoading = true;
      this.organizerError = null;

      try {
        const response = await fetch(
          `/api/convention-events/${this.conventionEvent.id}/add_organizer/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this.csrfToken,
            },
            body: JSON.stringify({
              username: this.newOrganizerUsername.trim(),
            }),
          }
        );

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || "Ошибка при добавлении организатора");
        }

        const updatedEvent = await response.json();
        this.organizers = updatedEvent.organizers || [];
        this.newOrganizerUsername = "";
        this.$emit("organizer-changed", updatedEvent);
      } catch (err) {
        this.organizerError = err.message;
      } finally {
        this.organizerLoading = false;
      }
    },

    async removeOrganizer(organizer) {
      if (!this.conventionEvent) return;

      this.organizerLoading = true;
      this.organizerError = null;

      try {
        const response = await fetch(
          `/api/convention-events/${this.conventionEvent.id}/remove_organizer/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this.csrfToken,
            },
            body: JSON.stringify({ user_id: organizer.id }),
          }
        );

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || "Ошибка при удалении организатора");
        }

        const updatedEvent = await response.json();
        this.organizers = updatedEvent.organizers || [];
        this.$emit("organizer-changed", updatedEvent);
      } catch (err) {
        this.organizerError = err.message;
      } finally {
        this.organizerLoading = false;
      }
    },

    // === Управление регистрациями ===
    async fetchRegistrations() {
      if (!this.conventionEvent) return;

      this.registrationsLoading = true;
      this.registrationsError = null;

      try {
        const response = await fetch(
          `/api/convention-events/${this.conventionEvent.id}/registrations/`
        );

        if (!response.ok) {
          throw new Error("Ошибка при загрузке регистраций");
        }

        this.registrations = await response.json();
      } catch (err) {
        this.registrationsError = err.message;
      } finally {
        this.registrationsLoading = false;
      }
    },

    async updateRegistrationStatus(registrationId, newStatus) {
      if (!this.conventionEvent) return;

      this.registrationsLoading = true;
      this.registrationsError = null;

      try {
        const response = await fetch(
          `/api/convention-events/${this.conventionEvent.id}/update_registration/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": this.csrfToken,
            },
            body: JSON.stringify({
              registration_id: registrationId,
              status: newStatus,
            }),
          }
        );

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || "Ошибка при обновлении статуса");
        }

        // Обновляем список регистраций
        await this.fetchRegistrations();
      } catch (err) {
        this.registrationsError = err.message;
      } finally {
        this.registrationsLoading = false;
      }
    },

    formatRegDate(dateStr) {
      const date = new Date(dateStr);
      return date.toLocaleDateString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    },
  },
};
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
  max-width: 700px;
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
  font-family: "JetBrains Mono", monospace;
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
  font-family: "JetBrains Mono", monospace;
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

/* Секция организаторов */
.organizers-section {
  margin-top: 8px;
  padding: 16px;
  background: rgba(0, 204, 255, 0.08);
  border-radius: 8px;
  border-left: 3px solid #00ccff;
}

.organizers-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.organizers-icon {
  font-size: 1.2rem;
}

.organizers-label {
  color: #888;
  font-size: 0.9rem;
}

.organizers-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.organizer-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(0, 204, 255, 0.15);
  border-radius: 20px;
  border: 1px solid #00ccff55;
}

.organizer-name {
  color: #00ccff;
  font-weight: 600;
  font-size: 0.9rem;
}

.organizer-remove-btn {
  width: 18px;
  height: 18px;
  padding: 0;
  background: rgba(255, 68, 68, 0.3);
  border: none;
  border-radius: 50%;
  color: #ff6b6b;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.organizer-remove-btn:hover {
  background: #ff4444;
  color: #fff;
}

.no-organizers {
  color: #666;
  font-size: 0.9rem;
  margin-bottom: 12px;
}

.add-organizer-form {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.autocomplete-wrapper {
  position: relative;
  flex: 1;
}

.user-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #0a0a0a;
  border: 1px solid #00ccff;
  border-radius: 0 0 6px 6px;
  z-index: 100;
  max-height: 200px;
  overflow-y: auto;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
}

.user-dropdown-item {
  padding: 10px 12px;
  cursor: pointer;
  border-bottom: 1px solid #00ccff22;
  transition: background 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-dropdown-item:last-child {
  border-bottom: none;
}

.user-dropdown-item:hover,
.user-dropdown-item.highlighted {
  background: rgba(0, 204, 255, 0.15);
}

.user-display-name {
  color: #e0e0e0;
  font-weight: 600;
  font-size: 0.9rem;
}

.user-username {
  color: #00ccff;
  font-size: 0.8rem;
}

.user-dropdown-empty {
  padding: 12px;
  color: #666;
  text-align: center;
  font-size: 0.85rem;
}

.add-organizer-input {
  flex: 1;
  padding: 8px 12px;
  background: rgba(10, 10, 10, 0.6);
  border: 1px solid #00ccff44;
  border-radius: 6px;
  color: #e0e0e0;
  font-size: 0.9rem;
}

.add-organizer-input::placeholder {
  color: #555;
}

.add-organizer-input:focus {
  outline: none;
  border-color: #00ccff;
}

.add-organizer-btn {
  padding: 8px 14px;
  background: rgba(0, 204, 255, 0.2);
  border: 1px solid #00ccff;
  border-radius: 6px;
  color: #00ccff;
  font-size: 1.1rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.2s ease;
}

.add-organizer-btn:hover:not(:disabled) {
  background: #00ccff;
  color: #0a0a0a;
}

.add-organizer-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.organizer-error {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(255, 68, 68, 0.15);
  border: 1px solid #ff4444;
  border-radius: 6px;
  color: #ff6b6b;
  font-size: 0.85rem;
}

/* Секция настроек регистрации */
.registration-settings {
  margin-top: 8px;
  padding: 16px;
  background: rgba(0, 204, 255, 0.08);
  border-radius: 8px;
  border-left: 3px solid #00ccff;
}

.settings-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.settings-icon {
  font-size: 1.2rem;
}

.settings-label {
  color: #00ccff;
  font-size: 0.95rem;
  font-weight: 600;
}

.registration-settings .form-row {
  margin-bottom: 0;
}

.registration-settings label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #e0e0e0;
  cursor: pointer;
}

.form-checkbox {
  width: 18px;
  height: 18px;
  accent-color: #00ccff;
}

.registration-stats {
  display: flex;
  gap: 16px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #00ccff33;
}

.stat-item {
  font-size: 0.9rem;
  color: #4caf50;
}

.stat-pending {
  color: #ffaa00;
}

/* Секция управления регистрациями */
.registrations-section {
  margin-top: 8px;
  padding: 16px;
  background: rgba(255, 170, 0, 0.08);
  border-radius: 8px;
  border-left: 3px solid #ffaa00;
}

.registrations-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.registrations-icon {
  font-size: 1.2rem;
}

.registrations-label {
  color: #ffaa00;
  font-size: 0.95rem;
  font-weight: 600;
  flex: 1;
}

.refresh-btn {
  padding: 4px 10px;
  background: transparent;
  border: 1px solid #ffaa0066;
  border-radius: 4px;
  color: #ffaa00;
  cursor: pointer;
  transition: all 0.2s ease;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(255, 170, 0, 0.2);
  border-color: #ffaa00;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-registrations {
  color: #666;
  font-size: 0.9rem;
}

.registrations-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.registration-item {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
  border-left: 3px solid #888;
}

.registration-item.status-pending {
  border-left-color: #ffaa00;
}

.registration-item.status-confirmed {
  border-left-color: #4caf50;
}

.registration-item.status-rejected {
  border-left-color: #ff4444;
}

.registration-item.status-cancelled {
  border-left-color: #666;
  opacity: 0.6;
}

.reg-user {
  flex: 1;
  min-width: 150px;
}

.reg-user-name {
  display: block;
  color: #e0e0e0;
  font-weight: 500;
}

.reg-date {
  display: block;
  color: #666;
  font-size: 0.8rem;
  margin-top: 2px;
}

.reg-status {
  flex-shrink: 0;
}

.status-select {
  padding: 6px 10px;
  background: rgba(10, 10, 10, 0.6);
  border: 1px solid #555;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 0.85rem;
  cursor: pointer;
}

.status-select:focus {
  outline: none;
  border-color: #ffaa00;
}

.reg-comment {
  width: 100%;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 4px;
  color: #aaa;
  font-size: 0.85rem;
}

.registrations-error {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(255, 68, 68, 0.15);
  border: 1px solid #ff4444;
  border-radius: 6px;
  color: #ff6b6b;
  font-size: 0.85rem;
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
