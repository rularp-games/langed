<template>
  <div class="modal-overlay" @click.self="$emit('cancel')">
    <div class="modal-content run-editor-modal">
      <button class="modal-close" @click="$emit('cancel')">×</button>

      <h2>{{ mode === "add" ? "Добавить прогон" : "Редактировать прогон" }}</h2>

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
          <div
            v-if="showGameDropdown && !(mode === 'edit' && lockGame)"
            class="dropdown-list"
          >
            <div
              v-for="game in filteredGamesList"
              :key="game.id"
              class="dropdown-item"
              :class="{ selected: formData.game_id === game.id }"
              @mousedown.prevent="selectGame(game)"
            >
              <span class="dropdown-item-name">{{ game.name }}</span>
              <span class="dropdown-item-info"
                >{{ game.players_min }}–{{ game.players_max }} игроков</span
              >
            </div>
            <div v-if="filteredGamesList.length === 0" class="dropdown-empty">
              Игры не найдены
            </div>
          </div>
        </div>

        <!-- Проведение конвента (если не заблокировано) -->
        <div
          v-if="
            !lockConvention && conventionEvents && conventionEvents.length > 0
          "
          class="form-group"
        >
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
              {{ event.convention_name }} —
              {{ event.city_name || (event.city && event.city.name) }} ({{
                formatDates(event.date_start, event.date_end)
              }})
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
          <div
            v-if="
              showCityDropdown &&
              !lockConvention &&
              !formData.convention_event_id
            "
            class="dropdown-list"
          >
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
          <p
            v-if="formData.convention_event_id || lockConvention"
            class="form-hint"
          >
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
        <div
          v-if="formData.city_id && formData.city_id !== 'new'"
          class="form-group"
        >
          <label>Площадка</label>
          <!-- Режим только для чтения (когда игра на конвенте) -->
          <input
            v-if="isVenueReadonly"
            type="text"
            class="form-input"
            :value="selectedVenueName || 'Не указана'"
            disabled
          />
          <!-- Режим выбора -->
          <select
            v-else
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
          <p v-if="isVenueReadonly" class="form-hint">
            Площадка определяется проведением конвента
          </p>
        </div>

        <!-- Помещения -->
        <div v-if="roomsList.length > 0" class="form-group searchable-select">
          <label>Помещения</label>
          <div class="form-input rooms-select" @click="toggleRoomsDropdown">
            <span
              v-if="formData.room_ids.length === 0"
              class="rooms-placeholder"
            >
              Выберите помещения...
            </span>
            <span v-else class="rooms-selected">
              {{ selectedRoomsText }}
            </span>
            <span class="rooms-arrow">▼</span>
          </div>
          <div v-if="showRoomsDropdown" class="dropdown-list rooms-dropdown">
            <div
              v-for="room in roomsList"
              :key="room.id"
              class="dropdown-item rooms-item"
              :class="{ selected: formData.room_ids.includes(room.id) }"
              @mousedown.prevent="toggleRoom(room.id)"
            >
              <span class="room-checkbox">{{
                formData.room_ids.includes(room.id) ? "☑" : "☐"
              }}</span>
              <span class="dropdown-item-name"
                >{{ room.name }}{{ room.blackbox ? " [blackbox]" : "" }}</span
              >
            </div>
            <div v-if="roomsList.length === 0" class="dropdown-empty">
              Помещения не найдены
            </div>
          </div>
        </div>

        <!-- Дата и время -->
        <div class="form-row">
          <div class="form-group half">
            <label>Дата * <span class="format-hint">(дд/мм/гггг)</span></label>
            <div class="date-picker-wrapper">
              <input
                :value="formattedDate"
                @input="handleDateInput"
                @blur="validateDate"
                type="text"
                required
                class="form-input date-input"
                placeholder="дд/мм/гггг"
                maxlength="10"
              />
              <input
                ref="datePickerInput"
                type="date"
                class="date-picker-native"
                :value="formData.date"
                :min="dateConstraints.min"
                :max="dateConstraints.max"
                @change="handleDatePickerChange"
              />
              <button
                type="button"
                class="date-picker-btn"
                @click="openDatePicker"
                title="Открыть календарь"
              >
                📅
              </button>
            </div>
          </div>

          <div class="form-group half">
            <label
              >Время *
              <span v-if="timezoneLabel" class="timezone-label"
                >({{ timezoneLabel }})</span
              ></label
            >
            <input
              v-model="formData.time"
              type="text"
              required
              class="form-input time-input"
              placeholder="чч:мм"
              maxlength="5"
              @input="handleTimeInput"
              @blur="validateTime"
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
              :placeholder="
                selectedGameMaxPlayers
                  ? `Из игры: ${selectedGameMaxPlayers}`
                  : 'Из игры'
              "
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

        <!-- Секция управления мастерами (только в режиме редактирования) -->
        <div v-if="mode === 'edit' && run" class="form-group masters-section">
          <label>Мастера</label>
          <div class="masters-list">
            <div 
              v-for="master in currentMasters" 
              :key="master.id" 
              class="master-item"
            >
              <span class="master-name">{{ master.display_name }}</span>
              <button 
                type="button"
                class="master-remove-btn"
                @click.stop="removeMaster(master)"
                title="Удалить мастера"
                :disabled="masterLoading"
              >
                ×
              </button>
            </div>
            <div v-if="currentMasters.length === 0" class="no-masters">
              Нет мастеров
            </div>
          </div>
          <!-- Форма добавления мастера с автодополнением -->
          <div class="add-master-form">
            <div class="autocomplete-wrapper searchable-select">
              <input 
                v-model="masterInput"
                type="text"
                class="form-input add-master-input"
                placeholder="Начните вводить имя..."
                autocomplete="off"
                @input="searchUsers"
                @focus="showUserDropdown = true"
                @blur="hideUserDropdownDelayed"
                @keydown.enter.prevent="selectFirstUser"
                @keydown.down.prevent="highlightNextUser"
                @keydown.up.prevent="highlightPrevUser"
              />
              <div 
                v-if="showUserDropdown && userSearchResults.length > 0" 
                class="dropdown-list user-dropdown"
              >
                <div 
                  v-for="(user, idx) in userSearchResults" 
                  :key="user.id"
                  class="dropdown-item user-dropdown-item"
                  :class="{ highlighted: highlightedUserIndex === idx }"
                  @mousedown.prevent="selectUser(user)"
                >
                  <span class="user-display-name">{{ user.display_name }}</span>
                  <span class="user-username">@{{ user.username }}</span>
                </div>
              </div>
              <div 
                v-if="showUserDropdown && masterInput && masterInput.length >= 2 && userSearchResults.length === 0 && !userSearchLoading" 
                class="dropdown-list user-dropdown user-dropdown-empty"
              >
                <div class="dropdown-empty">Пользователи не найдены</div>
              </div>
            </div>
            <button 
              type="button"
              class="btn btn-add-master"
              @click.stop="addMasterFromSelected"
              :disabled="!selectedUser || masterLoading"
            >
              {{ masterLoading ? '...' : '+' }}
            </button>
          </div>
          <div v-if="masterError" class="master-error">{{ masterError }}</div>
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
  name: "RunEditor",
  props: {
    // Режим: 'add' или 'edit'
    mode: {
      type: String,
      default: "add",
      validator: (v) => ["add", "edit"].includes(v),
    },
    // Данные существующего прогона для редактирования
    run: {
      type: Object,
      default: null,
    },
    // ID проведения конвента (если редактируем в контексте расписания конвента)
    conventionEventId: {
      type: [Number, String],
      default: null,
    },
    // Заблокировать выбор конвента
    lockConvention: {
      type: Boolean,
      default: false,
    },
    // Заблокировать изменение игры при редактировании
    lockGame: {
      type: Boolean,
      default: false,
    },
    // Название конвента для отображения (если lockConvention)
    conventionName: {
      type: String,
      default: "",
    },
    // Список игр
    games: {
      type: Array,
      default: () => [],
    },
    // Список городов
    cities: {
      type: Array,
      default: () => [],
    },
    // Список проведений конвентов
    conventionEvents: {
      type: Array,
      default: () => [],
    },
    // Помещения, доступные для выбора (если lockConvention - помещения площадки конвента)
    availableRooms: {
      type: Array,
      default: () => [],
    },
    // Площадка конвента (для режима lockConvention)
    conventionVenue: {
      type: Object,
      default: null,
    },
    // Ограничения по датам
    dateConstraints: {
      type: Object,
      default: () => ({ min: "", max: "" }),
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
    // Город по умолчанию (для контекста конвента)
    defaultCity: {
      type: Object,
      default: null,
    },
    // Таймзона по умолчанию
    defaultTimezone: {
      type: String,
      default: "Europe/Moscow",
    },
    // Дата по умолчанию
    defaultDate: {
      type: String,
      default: "",
    },
  },
  emits: ["save", "cancel", "error", "city-created", "masters-updated"],
  mounted() {
    // Сохраняем позицию прокрутки и блокируем прокрутку body
    this.savedScrollY = window.scrollY;
    document.body.classList.add("modal-open");
    document.body.style.top = `-${this.savedScrollY}px`;
    document.addEventListener("click", this.handleDocumentClick);
  },
  beforeUnmount() {
    // Восстанавливаем прокрутку body
    const scrollY = this.savedScrollY;
    document.body.classList.remove("modal-open");
    document.body.style.top = "";
    requestAnimationFrame(() => {
      window.scrollTo(0, scrollY);
    });
    document.removeEventListener("click", this.handleDocumentClick);
  },
  data() {
    return {
      savedScrollY: 0,
      formData: {
        game_id: null,
        convention_event_id: null,
        city_id: null,
        city_timezone: "Europe/Moscow",
        newCityName: "",
        venue_id: null,
        room_ids: [],
        date: "",
        time: "12:00",
        duration: 180,
        max_players: null,
        registration_open: true,
      },
      loading: false,
      error: null,
      gameSearch: "",
      citySearch: "",
      showGameDropdown: false,
      showCityDropdown: false,
      showRoomsDropdown: false,
      venuesList: [],
      roomsList: [],
      // Управление мастерами
      masterInput: "",
      masterLoading: false,
      masterError: null,
      userSearchResults: [],
      userSearchLoading: false,
      showUserDropdown: false,
      selectedUser: null,
      highlightedUserIndex: 0,
      searchDebounceTimer: null,
      localMasters: [],
    };
  },
  computed: {
    sortedGames() {
      return this.games
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name, "ru"));
    },
    sortedConventionEvents() {
      return this.conventionEvents.slice().sort((a, b) => {
        const nameA = a.convention_name || "";
        const nameB = b.convention_name || "";
        return nameA.localeCompare(nameB, "ru");
      });
    },
    filteredGamesList() {
      if (!this.gameSearch) {
        return this.sortedGames;
      }
      const query = this.gameSearch.toLowerCase();
      return this.sortedGames.filter((g) =>
        g.name.toLowerCase().includes(query)
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
    selectedGameName() {
      if (!this.formData.game_id) return "";
      const game = this.games.find((g) => g.id === this.formData.game_id);
      return game ? game.name : "";
    },
    selectedGameMaxPlayers() {
      if (!this.formData.game_id) return null;
      const game = this.games.find((g) => g.id === this.formData.game_id);
      return game ? game.players_max : null;
    },
    selectedCityName() {
      if (!this.formData.city_id || this.formData.city_id === "new") return "";
      const city = this.cities.find((c) => c.id === this.formData.city_id);
      if (!city) return "";
      const regionName =
        city.region && city.region.name ? city.region.name : "";
      return regionName ? `${city.name} (${regionName})` : city.name;
    },
    timezoneLabel() {
      return this.getTimezoneAbbr(this.formData.city_timezone);
    },
    selectedRoomsText() {
      if (this.formData.room_ids.length === 0) return "";
      const selectedRooms = this.roomsList.filter((r) =>
        this.formData.room_ids.includes(r.id)
      );
      return selectedRooms.map((r) => r.name).join(", ");
    },
    isVenueReadonly() {
      // Площадка только для чтения, если игра проводится на конвенте
      return (
        this.lockConvention ||
        (this.formData.convention_event_id && this.hasConventionVenue)
      );
    },
    hasConventionVenue() {
      // Проверяем, есть ли у выбранного конвента площадка
      if (this.conventionVenue) return true;
      if (this.formData.convention_event_id) {
        const event = this.conventionEvents.find(
          (e) => e.id === this.formData.convention_event_id
        );
        return event && event.venue && event.venue.id;
      }
      return false;
    },
    selectedVenueName() {
      if (!this.formData.venue_id) return null;
      const venue = this.venuesList.find(
        (v) => v.id === this.formData.venue_id
      );
      if (venue) return venue.name;
      // Проверяем conventionVenue
      if (
        this.conventionVenue &&
        this.conventionVenue.id === this.formData.venue_id
      ) {
        return this.conventionVenue.name;
      }
      return null;
    },
    // Текущие мастера прогона
    currentMasters() {
      return this.localMasters;
    },
    // Форматированная дата для отображения (дд/мм/гггг)
    formattedDate: {
      get() {
        if (!this.formData.date) return "";
        const parts = this.formData.date.split("-");
        if (parts.length === 3) {
          return `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
        return this.formData.date;
      },
      set(val) {
        // Парсим дд/мм/гггг в yyyy-mm-dd
        const parts = val.replace(/[^\d/]/g, "").split("/");
        if (
          parts.length === 3 &&
          parts[0].length === 2 &&
          parts[1].length === 2 &&
          parts[2].length === 4
        ) {
          this.formData.date = `${parts[2]}-${parts[1]}-${parts[0]}`;
        }
      },
    },
  },
  watch: {
    run: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.mode === "edit") {
          this.initFromRun(newVal);
        }
      },
    },
    conventionEventId: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.lockConvention) {
          this.formData.convention_event_id = newVal;
        }
      },
    },
    defaultCity: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.lockConvention) {
          this.formData.city_id = newVal.id;
          this.formData.city_timezone = newVal.timezone || "Europe/Moscow";
          const regionName =
            newVal.region && newVal.region.name ? newVal.region.name : "";
          this.citySearch = regionName
            ? `${newVal.name} (${regionName})`
            : newVal.name;
        }
      },
    },
    defaultDate: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.mode === "add") {
          this.formData.date = newVal;
        }
      },
    },
    defaultTimezone: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.mode === "add") {
          this.formData.city_timezone = newVal;
        }
      },
    },
    availableRooms: {
      immediate: true,
      handler(newVal) {
        if (this.lockConvention && newVal && newVal.length > 0) {
          this.roomsList = newVal;
        }
      },
    },
    conventionVenue: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.lockConvention) {
          this.formData.venue_id = newVal.id;
          // Добавляем площадку в venuesList для отображения имени
          if (!this.venuesList.find((v) => v.id === newVal.id)) {
            this.venuesList = [{ id: newVal.id, name: newVal.name }];
          }
        }
      },
    },
  },
  methods: {
    initFromRun(run) {
      // Парсим дату и время
      let runDate = "";
      let runTime = "12:00";

      // Используем date_local если доступна (формат YYYY-MM-DDTHH:MM:SS)
      const dateStr = run.date_local || run.date;
      if (dateStr) {
        const parts = dateStr.split("T");
        if (parts.length >= 1) {
          runDate = parts[0];
        }
        if (parts.length >= 2) {
          runTime = parts[1].slice(0, 5);
        }
      }

      // Определяем convention_event_id
      const conventionEventId = this.lockConvention
        ? this.conventionEventId
        : run.convention_event_id || run.convention_event || null;

      // Находим проведение конвента, если есть
      let conventionEvent = null;
      if (
        conventionEventId &&
        this.conventionEvents &&
        this.conventionEvents.length > 0
      ) {
        conventionEvent = this.conventionEvents.find(
          (e) => e.id === conventionEventId
        );
      }

      // Определяем city_id
      let cityId = null;
      let cityTimezone = "Europe/Moscow";
      let cityName = "";

      // При lockConvention берём город из defaultCity (город конвента)
      if (this.lockConvention && this.defaultCity) {
        cityId = this.defaultCity.id;
        cityTimezone = this.defaultCity.timezone || "Europe/Moscow";
        const regionName =
          this.defaultCity.region && this.defaultCity.region.name
            ? this.defaultCity.region.name
            : "";
        cityName = regionName
          ? `${this.defaultCity.name} (${regionName})`
          : this.defaultCity.name;
      } else if (conventionEvent && conventionEvent.city) {
        // Если есть проведение конвента - берём город из него
        cityId = conventionEvent.city.id;
        cityTimezone = conventionEvent.city.timezone || "Europe/Moscow";
        const regionName =
          conventionEvent.city.region && conventionEvent.city.region.name
            ? conventionEvent.city.region.name
            : "";
        cityName = regionName
          ? `${conventionEvent.city.name} (${regionName})`
          : conventionEvent.city.name;
      } else if (run.city_id) {
        cityId = run.city_id;
      } else if (run.city) {
        // Ищем город по названию
        const city = this.cities.find((c) => c.name === run.city);
        if (city) {
          cityId = city.id;
          cityTimezone = city.timezone || "Europe/Moscow";
        }
      }

      // Определяем venue и rooms
      let venueId = null;
      let roomIds = [];
      if (run.rooms && run.rooms.length > 0) {
        roomIds = run.rooms.map((r) => r.id);
        // Площадка берётся из первого помещения
        if (run.rooms[0].venue_id) {
          venueId = run.rooms[0].venue_id;
        }
      }

      this.formData = {
        game_id: run.game_id || (run.game && run.game.id) || null,
        convention_event_id: conventionEventId,
        city_id: cityId,
        city_timezone: run.city_timezone || cityTimezone,
        newCityName: "",
        venue_id: venueId,
        room_ids: roomIds,
        date: runDate,
        time: runTime,
        duration: run.duration || 180,
        max_players: run.max_players || null,
        registration_open: run.registration_open !== false,
      };

      // Устанавливаем поисковые поля
      this.gameSearch = run.game_name || (run.game && run.game.name) || "";
      this.citySearch = cityName || this.selectedCityName || run.city || "";

      // Инициализируем список мастеров
      this.localMasters = run.masters ? [...run.masters] : [];

      // Загружаем площадки и помещения
      if (cityId) {
        if (this.lockConvention && this.conventionVenue) {
          // Для конвента используем площадку конвента (режим lockConvention)
          this.formData.venue_id = this.conventionVenue.id;
          this.venuesList = [
            { id: this.conventionVenue.id, name: this.conventionVenue.name },
          ];
          // roomsList уже заполнен из availableRooms через watcher
        } else if (
          conventionEvent &&
          conventionEvent.venue &&
          conventionEvent.venue.id
        ) {
          // Если прогон привязан к проведению конвента с площадкой - используем её
          this.formData.venue_id = conventionEvent.venue.id;
          this.venuesList = [
            { id: conventionEvent.venue.id, name: conventionEvent.venue.name },
          ];
          // Загружаем помещения площадки конвента
          this.fetchRoomsByVenue(conventionEvent.venue.id);
        } else {
          this.fetchVenuesByCity(cityId).then(() => {
            if (venueId) {
              this.fetchRoomsByVenue(venueId);
            }
          });
        }
      }
    },

    selectGame(game) {
      this.formData.game_id = game.id;
      this.gameSearch = game.name;
      this.showGameDropdown = false;
    },

    selectCity(city) {
      this.formData.city_id = city.id;
      this.formData.city_timezone = city.timezone || "Europe/Moscow";
      const regionName =
        city.region && city.region.name ? city.region.name : "";
      this.citySearch = regionName ? `${city.name} (${regionName})` : city.name;
      this.showCityDropdown = false;
      // Сбрасываем площадку и помещения
      this.formData.venue_id = null;
      this.formData.room_ids = [];
      this.roomsList = [];
      this.fetchVenuesByCity(city.id);
    },

    selectNewCity() {
      this.formData.city_id = "new";
      this.citySearch = "";
      this.showCityDropdown = false;
      this.formData.venue_id = null;
      this.formData.room_ids = [];
      this.venuesList = [];
      this.roomsList = [];
    },

    onGameInputBlur() {
      setTimeout(() => {
        this.showGameDropdown = false;
        if (
          this.formData.game_id &&
          this.gameSearch !== this.selectedGameName
        ) {
          this.gameSearch = this.selectedGameName;
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

    toggleRoomsDropdown() {
      this.showRoomsDropdown = !this.showRoomsDropdown;
    },

    toggleRoom(roomId) {
      const index = this.formData.room_ids.indexOf(roomId);
      if (index === -1) {
        this.formData.room_ids.push(roomId);
      } else {
        this.formData.room_ids.splice(index, 1);
      }
    },

    handleDocumentClick(event) {
      // Закрываем dropdown помещений при клике вне его
      if (
        this.showRoomsDropdown &&
        !event.target.closest(".rooms-dropdown") &&
        !event.target.closest(".rooms-select")
      ) {
        this.showRoomsDropdown = false;
      }
    },

    onConventionEventChange() {
      if (this.formData.convention_event_id) {
        const event = this.conventionEvents.find(
          (e) => e.id === this.formData.convention_event_id
        );
        if (event && event.city) {
          this.formData.city_id = event.city.id;
          this.formData.city_timezone = event.city.timezone || "Europe/Moscow";
          const regionName =
            event.city.region && event.city.region.name
              ? event.city.region.name
              : "";
          this.citySearch = regionName
            ? `${event.city.name} (${regionName})`
            : event.city.name;

          // Сбрасываем помещения
          this.formData.room_ids = [];
          this.roomsList = [];

          // Если у конвента указана площадка - устанавливаем её
          if (event.venue && event.venue.id) {
            this.formData.venue_id = event.venue.id;
            this.venuesList = [{ id: event.venue.id, name: event.venue.name }];
            // Загружаем помещения площадки конвента
            this.fetchRoomsByVenue(event.venue.id);
          } else {
            // Загружаем площадки города
            this.formData.venue_id = null;
            this.fetchVenuesByCity(event.city.id);
          }
        }
      } else {
        this.formData.city_id = null;
        this.formData.city_timezone = "Europe/Moscow";
        this.citySearch = "";
        this.formData.venue_id = null;
        this.formData.room_ids = [];
        this.venuesList = [];
        this.roomsList = [];
      }
    },

    onVenueChange() {
      this.formData.room_ids = [];
      if (this.formData.venue_id) {
        this.fetchRoomsByVenue(this.formData.venue_id);
      } else {
        this.roomsList = [];
      }
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

    async fetchRoomsByVenue(venueId) {
      if (!venueId) return;
      try {
        const response = await fetch(`/api/rooms/?venue=${venueId}`);
        if (response.ok) {
          this.roomsList = await response.json();
        }
      } catch (err) {
        console.error("Ошибка загрузки помещений:", err);
      }
    },

    getTimezoneAbbr(timezone) {
      if (!timezone) return "";
      const abbrs = {
        "Europe/Kaliningrad": "UTC+2",
        "Europe/Moscow": "MSK",
        "Europe/Samara": "UTC+4",
        "Asia/Yekaterinburg": "UTC+5",
        "Asia/Omsk": "UTC+6",
        "Asia/Krasnoyarsk": "UTC+7",
        "Asia/Irkutsk": "UTC+8",
        "Asia/Yakutsk": "UTC+9",
        "Asia/Vladivostok": "UTC+10",
        "Asia/Magadan": "UTC+11",
        "Asia/Kamchatka": "UTC+12",
      };
      return abbrs[timezone] || timezone;
    },

    formatDates(start, end) {
      const formatDate = (dateStr) => {
        const d = new Date(dateStr);
        const day = String(d.getDate()).padStart(2, "0");
        const month = String(d.getMonth() + 1).padStart(2, "0");
        const year = d.getFullYear();
        return `${day}/${month}/${year}`;
      };
      return `${formatDate(start)} — ${formatDate(end)}`;
    },

    handleDateInput(event) {
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
        this.formData.date = `${year}-${month}-${day}`;
      }
    },

    validateDate() {
      if (!this.formData.date) return;

      // Проверяем ограничения по дате
      if (
        this.dateConstraints.min &&
        this.formData.date < this.dateConstraints.min
      ) {
        this.formData.date = this.dateConstraints.min;
      }
      if (
        this.dateConstraints.max &&
        this.formData.date > this.dateConstraints.max
      ) {
        this.formData.date = this.dateConstraints.max;
      }
    },

    openDatePicker() {
      // Открываем нативный date picker
      if (this.$refs.datePickerInput) {
        this.$refs.datePickerInput.showPicker();
      }
    },

    handleDatePickerChange(event) {
      const value = event.target.value;
      if (value) {
        this.formData.date = value;
        this.validateDate();
      }
    },

    handleTimeInput(event) {
      let value = event.target.value;
      // Оставляем только цифры и двоеточие
      value = value.replace(/[^\d:]/g, "");

      // Автоматически добавляем двоеточие после двух цифр
      if (value.length === 2 && !value.includes(":")) {
        value += ":";
      }

      // Ограничиваем длину
      if (value.length > 5) {
        value = value.slice(0, 5);
      }

      event.target.value = value;
      this.formData.time = value;
    },

    validateTime() {
      if (!this.formData.time) return;

      const parts = this.formData.time.split(":");
      if (parts.length === 2) {
        let hours = parseInt(parts[0], 10) || 0;
        let minutes = parseInt(parts[1], 10) || 0;

        // Ограничиваем значения
        if (hours > 23) hours = 23;
        if (hours < 0) hours = 0;
        if (minutes > 59) minutes = 59;
        if (minutes < 0) minutes = 0;

        this.formData.time = `${String(hours).padStart(2, "0")}:${String(
          minutes
        ).padStart(2, "0")}`;
      }
    },

    // eslint-disable-next-line no-unused-vars
    convertToTimezone(date, time, timezone) {
      // Создаём строку даты-времени и конвертируем в ISO
      const dateTimeStr = `${date}T${time}:00`;

      // Для простоты используем локальную дату-время
      // Бэкенд должен обрабатывать таймзону на своей стороне
      return dateTimeStr;
    },

    async submitForm() {
      this.loading = true;
      this.error = null;

      try {
        // Валидация
        if (!this.formData.game_id) {
          throw new Error("Выберите игру из списка");
        }

        if (!this.formData.date || !this.formData.time) {
          throw new Error("Укажите дату и время");
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

        // Формируем дату-время
        const dateTime = `${this.formData.date}T${this.formData.time}:00`;

        // Формируем данные для API
        const runData = {
          game_id: this.formData.game_id,
          city_id: cityId,
          date: dateTime,
          duration: this.formData.duration,
          max_players: this.formData.max_players || null,
          registration_open: this.formData.registration_open,
        };

        if (this.formData.convention_event_id) {
          runData.convention_event_id = this.formData.convention_event_id;
        }

        if (this.formData.room_ids && this.formData.room_ids.length > 0) {
          runData.room_ids = this.formData.room_ids;
        }

        // Добавляем ID для редактирования
        if (this.mode === "edit" && this.run) {
          runData.id = this.run.id;
        }

        // Эмитим событие с данными
        this.$emit("save", runData);
      } catch (err) {
        this.error = err.message;
        this.$emit("error", err.message);
      } finally {
        this.loading = false;
      }
    },

    // === Управление мастерами ===
    
    // Поиск пользователей с debounce
    searchUsers() {
      const query = this.masterInput;
      
      // Сбрасываем выбранного пользователя при изменении ввода
      this.selectedUser = null;
      this.highlightedUserIndex = 0;
      
      // Очищаем предыдущий таймер
      if (this.searchDebounceTimer) {
        clearTimeout(this.searchDebounceTimer);
      }
      
      if (!query || query.length < 2) {
        this.userSearchResults = [];
        return;
      }
      
      // Debounce 300ms
      this.searchDebounceTimer = setTimeout(() => {
        this.fetchUsers(query);
      }, 300);
    },
    
    async fetchUsers(query) {
      this.userSearchLoading = true;
      
      try {
        const response = await fetch(`/api/users/search/?q=${encodeURIComponent(query)}`);
        if (response.ok) {
          const users = await response.json();
          // Фильтруем уже добавленных мастеров
          const existingMasterIds = this.localMasters.map(m => m.id);
          this.userSearchResults = users.filter(u => !existingMasterIds.includes(u.id));
        }
      } catch (err) {
        console.error('Ошибка поиска пользователей:', err);
      } finally {
        this.userSearchLoading = false;
      }
    },
    
    hideUserDropdownDelayed() {
      // Задержка для обработки клика по выпадающему списку
      setTimeout(() => {
        this.showUserDropdown = false;
      }, 200);
    },
    
    selectUser(user) {
      this.masterInput = user.display_name;
      this.selectedUser = user;
      this.showUserDropdown = false;
      this.userSearchResults = [];
      // Автоматически добавляем мастера
      this.addMasterFromSelected();
    },
    
    selectFirstUser() {
      if (this.userSearchResults.length > 0) {
        const idx = this.highlightedUserIndex || 0;
        this.selectUser(this.userSearchResults[idx]);
      }
    },
    
    highlightNextUser() {
      if (this.userSearchResults.length === 0) return;
      this.highlightedUserIndex = Math.min(this.highlightedUserIndex + 1, this.userSearchResults.length - 1);
    },
    
    highlightPrevUser() {
      this.highlightedUserIndex = Math.max(this.highlightedUserIndex - 1, 0);
    },
    
    async addMasterFromSelected() {
      const user = this.selectedUser;
      if (!user) {
        this.masterError = 'Выберите пользователя из списка';
        return;
      }
      
      this.masterLoading = true;
      this.masterError = null;
      
      try {
        const response = await fetch(`/api/runs/${this.run.id}/add_master/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({ username: user.username })
        });
        
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || 'Ошибка при добавлении мастера');
        }
        
        // Добавляем мастера в локальный список
        this.localMasters.push({
          id: user.id,
          display_name: user.display_name,
          username: user.username
        });
        
        this.masterInput = '';
        this.selectedUser = null;
        this.$emit('masters-updated');
      } catch (err) {
        this.masterError = err.message;
      } finally {
        this.masterLoading = false;
      }
    },
    
    async removeMaster(master) {
      this.masterLoading = true;
      this.masterError = null;
      
      try {
        const response = await fetch(`/api/runs/${this.run.id}/remove_master/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.csrfToken
          },
          body: JSON.stringify({ user_id: master.id })
        });
        
        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.error || 'Ошибка при удалении мастера');
        }
        
        // Удаляем мастера из локального списка
        const index = this.localMasters.findIndex(m => m.id === master.id);
        if (index !== -1) {
          this.localMasters.splice(index, 1);
        }
        
        this.$emit('masters-updated');
      } catch (err) {
        this.masterError = err.message;
      } finally {
        this.masterLoading = false;
      }
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

/* Rooms dropdown */
.rooms-select {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.rooms-placeholder {
  color: #555;
}

.rooms-selected {
  color: #e0e0e0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rooms-arrow {
  color: #ff6b35;
  font-size: 0.8rem;
  margin-left: 8px;
  transition: transform 0.2s;
}

.rooms-dropdown {
  border-top: 2px solid #ff6b35;
}

.rooms-item {
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.room-checkbox {
  font-size: 1.1rem;
  color: #ff6b35;
}

/* Date and Time inputs */
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

.date-input,
.time-input {
  font-family: "JetBrains Mono", monospace;
  letter-spacing: 0.05em;
}

.date-input::placeholder,
.time-input::placeholder {
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

/* Masters section */
.masters-section {
  padding-top: 10px;
  border-top: 1px solid #ff6b3533;
}

.masters-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.master-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255, 107, 53, 0.15);
  border: 1px solid #ff6b3544;
  border-radius: 20px;
  padding: 6px 12px;
}

.master-name {
  color: #e0e0e0;
  font-size: 0.9rem;
}

.master-remove-btn {
  background: none;
  border: none;
  color: #ff6b6b;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  opacity: 0.7;
  transition: opacity 0.2s, transform 0.2s;
}

.master-remove-btn:hover:not(:disabled) {
  opacity: 1;
  transform: scale(1.2);
}

.master-remove-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.no-masters {
  color: #666;
  font-style: italic;
  font-size: 0.9rem;
}

.add-master-form {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.autocomplete-wrapper {
  flex: 1;
  position: relative;
}

.add-master-input {
  width: 100%;
  box-sizing: border-box;
}

.user-dropdown {
  border-top: 2px solid #ff6b35;
}

.user-dropdown-item {
  flex-direction: row !important;
  align-items: center;
  gap: 10px;
}

.user-dropdown-item.highlighted {
  background: rgba(255, 107, 53, 0.25);
}

.user-display-name {
  font-weight: 600;
  color: #e0e0e0;
}

.user-username {
  font-size: 0.85rem;
  color: #888;
}

.user-dropdown-empty .dropdown-empty {
  border-bottom: none;
}

.btn-add-master {
  padding: 12px 16px;
  background: linear-gradient(145deg, #ff6b35, #e55a2b);
  color: #fff;
  min-width: 44px;
  font-size: 1.2rem;
  font-weight: bold;
}

.btn-add-master:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(255, 107, 53, 0.35);
}

.btn-add-master:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.master-error {
  margin-top: 8px;
  background: rgba(255, 68, 68, 0.15);
  border: 1px solid #ff4444;
  border-radius: 6px;
  padding: 8px 12px;
  color: #ff6b6b;
  font-size: 0.9rem;
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
