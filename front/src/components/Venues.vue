<template>
  <div class="page">
    <div class="page-header">
      <h1>Площадки</h1>
      <p class="subtitle">Места проведения игр</p>
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
        <select v-model="selectedCity" class="control-select">
          <option value="">Все города</option>
          <option v-for="city in cities" :key="city.id" :value="city.id">
            {{ city.name }}
          </option>
        </select>
      </div>
      <button v-if="isAuthenticated" @click="openAddModal" class="add-btn">
        <span class="add-icon">+</span>
        Добавить площадку
      </button>
    </div>

    <div v-if="loading" class="loading">
      <div class="loading-spinner"></div>
      <p>Загрузка...</p>
    </div>

    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <button @click="fetchVenues" class="retry-btn">Повторить</button>
    </div>

    <div v-else-if="filteredVenues.length === 0" class="empty">
      <p v-if="searchQuery || selectedCity">Площадки не найдены</p>
      <p v-else>Площадки пока не добавлены</p>
    </div>

    <div v-else class="venues-grid">
      <div
        v-for="venue in filteredVenues"
        :key="venue.id"
        class="venue-card"
        @click="openVenueModal(venue)"
      >
        <div class="venue-info">
          <h2 class="venue-title">{{ venue.name }}</h2>
          <div class="venue-city">
            <span class="city-icon">📍</span>
            <span class="city-name">{{ venue.city?.name }}</span>
          </div>
          <div v-if="venue.address" class="venue-address">
            {{ venue.address }}
          </div>
          <div class="venue-stats">
            <div v-if="venue.capacity" class="stat">
              <span class="stat-label">Вместимость</span>
              <span class="stat-value">{{ venue.capacity }}</span>
            </div>
            <div v-if="venue.rooms && venue.rooms.length > 0" class="stat">
              <span class="stat-label">Помещений</span>
              <span class="stat-value">{{ venue.rooms.length }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно с деталями площадки -->
    <div
      v-if="selectedVenue"
      class="modal-overlay"
      @click.self="closeVenueModal"
    >
      <div class="modal-content">
        <button class="modal-close" @click="closeVenueModal">×</button>

        <div class="modal-body">
          <div class="modal-header-row">
            <h2>{{ selectedVenue.name }}</h2>
            <div class="header-actions">
              <button
                v-if="isAuthenticated"
                class="edit-btn"
                @click="startEditingVenue"
                title="Редактировать"
              >
                ✏️
              </button>
              <button
                v-if="isAuthenticated"
                class="delete-btn"
                @click="showDeleteConfirm = true"
                title="Удалить"
              >
                🗑️
              </button>
              <button
                class="copy-link-btn"
                @click="copyVenueLink"
                :title="linkCopied ? 'Скопировано!' : 'Скопировать ссылку'"
              >
                <span v-if="linkCopied">✓</span>
                <span v-else>🔗</span>
              </button>
            </div>
          </div>

          <div class="modal-city">
            <span class="city-icon">📍</span>
            <span class="city-name">{{ selectedVenue.city?.name }}</span>
          </div>

          <div class="modal-section" v-if="selectedVenue.address">
            <h3>Адрес</h3>
            <p>{{ selectedVenue.address }}</p>
          </div>

          <div class="modal-section" v-if="selectedVenue.description">
            <h3>Описание</h3>
            <p>{{ selectedVenue.description }}</p>
          </div>

          <div class="modal-stats" v-if="selectedVenue.capacity">
            <div class="modal-stat">
              <span class="modal-stat-label">Вместимость</span>
              <span class="modal-stat-value">{{ selectedVenue.capacity }}</span>
            </div>
          </div>

          <!-- Секция помещений -->
          <div class="modal-section rooms-section">
            <div class="rooms-header">
              <h3>Помещения</h3>
              <button
                v-if="isAuthenticated"
                @click="openAddRoomModal"
                class="add-room-btn"
                title="Добавить помещение"
              >
                +
              </button>
            </div>

            <div
              v-if="selectedVenue.rooms && selectedVenue.rooms.length > 0"
              class="rooms-list"
            >
              <div
                v-for="room in selectedVenue.rooms"
                :key="room.id"
                class="room-item"
              >
                <div class="room-info">
                  <span class="room-name">{{ room.name }}</span>
                  <span v-if="room.blackbox" class="room-badge blackbox"
                    >blackbox</span
                  >
                </div>
                <div v-if="isAuthenticated" class="room-actions">
                  <button
                    class="room-edit-btn"
                    @click="startEditingRoom(room)"
                    title="Редактировать"
                  >
                    ✏️
                  </button>
                  <button
                    class="room-delete-btn"
                    @click="confirmDeleteRoom(room)"
                    title="Удалить"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </div>
            <p v-else class="no-rooms">Помещения не добавлены</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно добавления помещения -->
    <div
      v-if="showAddRoomModal && isAuthenticated"
      class="modal-overlay"
      @click.self="closeAddRoomModal"
    >
      <div class="modal-content add-room-modal">
        <button class="modal-close" @click="closeAddRoomModal">×</button>

        <div class="modal-body">
          <h2>Добавить помещение</h2>

          <form @submit.prevent="submitRoom" class="add-room-form">
            <div class="form-group">
              <label for="room-name">Название *</label>
              <input
                id="room-name"
                v-model="newRoom.name"
                type="text"
                required
                class="form-input"
                placeholder="Например: Зал 1, Комната А"
              />
            </div>

            <div class="form-group checkbox-group">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="newRoom.blackbox"
                  class="checkbox-input"
                />
                <span class="checkbox-custom"></span>
                <span class="checkbox-text">Blackbox</span>
              </label>
            </div>

            <div v-if="addRoomError" class="form-error">{{ addRoomError }}</div>

            <div class="form-actions">
              <button
                type="button"
                @click="closeAddRoomModal"
                class="btn btn-secondary"
              >
                Отмена
              </button>
              <button
                type="submit"
                class="btn btn-primary"
                :disabled="addRoomLoading"
              >
                <span v-if="addRoomLoading">Сохранение...</span>
                <span v-else>Добавить</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Модальное окно редактирования помещения -->
    <div
      v-if="isEditingRoom"
      class="modal-overlay"
      @click.self="cancelEditingRoom"
    >
      <div class="modal-content add-room-modal">
        <button class="modal-close" @click="cancelEditingRoom">×</button>

        <div class="modal-body">
          <h2>Редактировать помещение</h2>

          <form @submit.prevent="submitEditRoom" class="add-room-form">
            <div class="form-group">
              <label for="edit-room-name">Название *</label>
              <input
                id="edit-room-name"
                v-model="editRoom.name"
                type="text"
                required
                class="form-input"
                placeholder="Например: Зал 1, Комната А"
              />
            </div>

            <div class="form-group checkbox-group">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  v-model="editRoom.blackbox"
                  class="checkbox-input"
                />
                <span class="checkbox-custom"></span>
                <span class="checkbox-text">Blackbox</span>
              </label>
            </div>

            <div v-if="editRoomError" class="form-error">
              {{ editRoomError }}
            </div>

            <div class="form-actions">
              <button
                type="button"
                @click="cancelEditingRoom"
                class="btn btn-secondary"
              >
                Отмена
              </button>
              <button
                type="submit"
                class="btn btn-primary"
                :disabled="editRoomLoading"
              >
                <span v-if="editRoomLoading">Сохранение...</span>
                <span v-else>Сохранить</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Модальное окно подтверждения удаления помещения -->
    <DeleteConfirmModal
      v-if="showDeleteRoomConfirm"
      title="Удалить помещение?"
      :message="`Помещение '${roomToDelete?.name}' будет удалено.`"
      :loading="deleteRoomLoading"
      @confirm="deleteRoom"
      @cancel="showDeleteRoomConfirm = false"
    />

    <!-- Модальное окно добавления площадки -->
    <VenueEditor
      v-if="showAddModal && isAuthenticated"
      mode="add"
      :cities="cities"
      @saved="onVenueAdded"
      @cancel="closeAddModal"
    />

    <!-- Модальное окно редактирования площадки -->
    <VenueEditor
      v-if="isEditingVenue"
      mode="edit"
      :venue="selectedVenue"
      :cities="cities"
      @saved="onVenueEdited"
      @cancel="cancelEditingVenue"
    />

    <!-- Модальное окно подтверждения удаления -->
    <DeleteConfirmModal
      v-if="showDeleteConfirm"
      title="Удалить площадку?"
      :message="`Это действие нельзя отменить. Площадка '${selectedVenue?.name}' будет удалена.`"
      :loading="deleteLoading"
      @confirm="deleteVenue"
      @cancel="showDeleteConfirm = false"
    />
  </div>
</template>

<script>
import DeleteConfirmModal from "./DeleteConfirmModal.vue";
import VenueEditor from "./VenueEditor.vue";

export default {
  name: "VenuesPage",
  components: {
    DeleteConfirmModal,
    VenueEditor,
  },
  inject: ["getUser"],
  props: {
    venueId: {
      type: [String, Number],
      default: null,
    },
  },
  data() {
    return {
      venues: [],
      cities: [],
      loading: true,
      error: null,
      searchQuery: "",
      selectedCity: "",
      selectedVenue: null,
      showAddModal: false,
      linkCopied: false,
      // Сохранение позиции прокрутки
      savedScrollY: 0,
      // Редактирование площадки
      isEditingVenue: false,
      // Удаление площадки
      showDeleteConfirm: false,
      deleteLoading: false,
      // Помещения
      showAddRoomModal: false,
      addRoomLoading: false,
      addRoomError: null,
      newRoom: this.getEmptyRoom(),
      isEditingRoom: false,
      editRoomLoading: false,
      editRoomError: null,
      editRoom: this.getEmptyRoom(),
      showDeleteRoomConfirm: false,
      deleteRoomLoading: false,
      roomToDelete: null,
    };
  },
  watch: {
    venueId: {
      handler(newId, oldId) {
        // Не реагируем если значение не изменилось или площадка уже выбрана
        if (!newId || newId === oldId) return;
        if (this.selectedVenue && this.selectedVenue.id === parseInt(newId, 10))
          return;
        if (this.venues.length > 0) {
          this.openVenueById(newId);
        }
      },
      immediate: false,
    },
    venues: {
      handler(newVal, oldVal) {
        // Открываем модальное окно только при первичной загрузке
        const wasEmpty = !oldVal || oldVal.length === 0;
        if (
          wasEmpty &&
          this.venueId &&
          this.venues.length > 0 &&
          !this.selectedVenue
        ) {
          this.openVenueById(this.venueId);
        }
      },
    },
    // Блокировка прокрутки при открытии модальных окон
    selectedVenue(newVal, oldVal) {
      if (newVal && !oldVal) {
        this.lockBodyScroll();
      } else if (!newVal && oldVal) {
        this.unlockBodyScroll();
      }
    },
    showAddModal(newVal, oldVal) {
      if (newVal && !oldVal) {
        this.lockBodyScroll();
      } else if (!newVal && oldVal) {
        this.unlockBodyScroll();
      }
    },
    showAddRoomModal(newVal, oldVal) {
      if (newVal && !oldVal) {
        this.lockBodyScroll();
      } else if (!newVal && oldVal) {
        this.unlockBodyScroll();
      }
    },
    isEditingRoom(newVal, oldVal) {
      if (newVal && !oldVal) {
        this.lockBodyScroll();
      } else if (!newVal && oldVal) {
        this.unlockBodyScroll();
      }
    },
    isEditingVenue(newVal, oldVal) {
      if (newVal && !oldVal) {
        this.lockBodyScroll();
      } else if (!newVal && oldVal) {
        this.unlockBodyScroll();
      }
    },
  },
  computed: {
    isAuthenticated() {
      const user = this.getUser();
      return user && user.is_authenticated;
    },
    csrfToken() {
      const match = document.cookie.match(/csrftoken=([^;]+)/);
      return match ? match[1] : "";
    },
    filteredVenues() {
      let result = this.venues;

      if (this.selectedCity) {
        result = result.filter(
          (v) => v.city?.id === parseInt(this.selectedCity)
        );
      }

      if (this.searchQuery) {
        const query = this.searchQuery.toLowerCase();
        result = result.filter(
          (v) =>
            v.name.toLowerCase().includes(query) ||
            (v.address && v.address.toLowerCase().includes(query)) ||
            (v.description && v.description.toLowerCase().includes(query))
        );
      }

      return result.slice().sort((a, b) => a.name.localeCompare(b.name, "ru"));
    },
  },
  mounted() {
    this.fetchData();
  },
  methods: {
    // === Блокировка прокрутки ===
    lockBodyScroll() {
      this.savedScrollY = window.scrollY;
      document.body.classList.add("modal-open");
      document.body.style.top = `-${this.savedScrollY}px`;
    },
    unlockBodyScroll() {
      const scrollY = this.savedScrollY;
      document.body.classList.remove("modal-open");
      document.body.style.top = "";
      requestAnimationFrame(() => {
        window.scrollTo(0, scrollY);
      });
    },

    async fetchData() {
      await Promise.all([this.fetchVenues(), this.fetchCities()]);
    },
    async fetchVenues() {
      this.loading = true;
      this.error = null;
      try {
        const response = await fetch("/api/venues/");
        if (!response.ok) {
          throw new Error("Ошибка загрузки данных");
        }
        this.venues = await response.json();
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },
    async fetchCities() {
      try {
        const response = await fetch("/api/cities/");
        if (response.ok) {
          this.cities = await response.json();
        }
      } catch (err) {
        console.error("Failed to fetch cities:", err);
      }
    },
    getEmptyRoom() {
      return {
        name: "",
        blackbox: false,
      };
    },
    openVenueById(id) {
      const venueId = parseInt(id, 10);
      const venue = this.venues.find((v) => v.id === venueId);
      if (venue) {
        this.selectedVenue = venue;
        this.updateUrlWithVenue(venue.id);
      }
    },
    openVenueModal(venue) {
      this.selectedVenue = venue;
      this.updateUrlWithVenue(venue.id);
    },
    closeVenueModal() {
      this.selectedVenue = null;
      this.linkCopied = false;
      this.updateUrlWithVenue(null);
    },
    updateUrlWithVenue(venueId) {
      const query = { ...this.$route.query };
      if (venueId) {
        query.id = venueId;
      } else {
        delete query.id;
      }
      this.$router.replace({ query }).catch(() => {});
    },
    copyVenueLink() {
      if (!this.selectedVenue) return;
      const url = `${window.location.origin}/venues?id=${this.selectedVenue.id}`;
      navigator.clipboard
        .writeText(url)
        .then(() => {
          this.linkCopied = true;
          setTimeout(() => {
            this.linkCopied = false;
          }, 2000);
        })
        .catch((err) => {
          console.error("Ошибка копирования:", err);
        });
    },
    openAddModal() {
      this.showAddModal = true;
    },
    closeAddModal() {
      this.showAddModal = false;
    },
    onVenueAdded(savedVenue) {
      this.venues.unshift(savedVenue);
      this.closeAddModal();
    },

    // === Редактирование ===
    startEditingVenue() {
      if (!this.selectedVenue) return;
      this.isEditingVenue = true;
    },
    cancelEditingVenue() {
      this.isEditingVenue = false;
    },
    onVenueEdited(updatedVenue) {
      const index = this.venues.findIndex((v) => v.id === updatedVenue.id);
      if (index !== -1) {
        this.venues.splice(index, 1, updatedVenue);
      }
      this.selectedVenue = updatedVenue;
      this.isEditingVenue = false;
    },

    // === Удаление площадки ===
    async deleteVenue() {
      if (!this.selectedVenue) return;

      this.deleteLoading = true;

      try {
        const response = await fetch(`/api/venues/${this.selectedVenue.id}/`, {
          method: "DELETE",
          headers: {
            "X-CSRFToken": this.csrfToken,
          },
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error("Нет прав для удаления");
          }
          throw new Error("Ошибка при удалении");
        }

        const index = this.venues.findIndex(
          (v) => v.id === this.selectedVenue.id
        );
        if (index !== -1) {
          this.venues.splice(index, 1);
        }

        this.showDeleteConfirm = false;
        this.closeVenueModal();
      } catch (err) {
        alert(err.message);
      } finally {
        this.deleteLoading = false;
      }
    },

    // === Помещения ===
    openAddRoomModal() {
      this.newRoom = this.getEmptyRoom();
      this.addRoomError = null;
      this.showAddRoomModal = true;
    },
    closeAddRoomModal() {
      this.showAddRoomModal = false;
      this.addRoomError = null;
    },
    async submitRoom() {
      if (!this.selectedVenue) return;

      this.addRoomLoading = true;
      this.addRoomError = null;

      try {
        const response = await fetch("/api/rooms/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this.csrfToken,
          },
          body: JSON.stringify({
            venue_id: this.selectedVenue.id,
            name: this.newRoom.name,
            blackbox: this.newRoom.blackbox,
          }),
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error("Необходима авторизация");
          }
          const data = await response.json();
          throw new Error(
            data.detail || data.name?.[0] || "Ошибка при сохранении"
          );
        }

        const createdRoom = await response.json();

        // Добавляем комнату в текущую площадку
        if (!this.selectedVenue.rooms) {
          this.selectedVenue.rooms = [];
        }
        this.selectedVenue.rooms.push(createdRoom);

        // Обновляем площадку в общем списке
        const venueIndex = this.venues.findIndex(
          (v) => v.id === this.selectedVenue.id
        );
        if (venueIndex !== -1) {
          this.venues[venueIndex] = { ...this.selectedVenue };
        }

        this.closeAddRoomModal();
      } catch (err) {
        this.addRoomError = err.message;
      } finally {
        this.addRoomLoading = false;
      }
    },

    // Редактирование помещения
    startEditingRoom(room) {
      this.editRoom = {
        id: room.id,
        name: room.name,
        blackbox: room.blackbox,
      };
      this.editRoomError = null;
      this.isEditingRoom = true;
    },
    cancelEditingRoom() {
      this.isEditingRoom = false;
      this.editRoomError = null;
    },
    async submitEditRoom() {
      this.editRoomLoading = true;
      this.editRoomError = null;

      try {
        const response = await fetch(`/api/rooms/${this.editRoom.id}/`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this.csrfToken,
          },
          body: JSON.stringify({
            name: this.editRoom.name,
            blackbox: this.editRoom.blackbox,
          }),
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error("Нет прав для редактирования");
          }
          const data = await response.json();
          throw new Error(
            data.detail || data.name?.[0] || "Ошибка при сохранении"
          );
        }

        const updatedRoom = await response.json();

        // Обновляем комнату в списке
        if (this.selectedVenue && this.selectedVenue.rooms) {
          const roomIndex = this.selectedVenue.rooms.findIndex(
            (r) => r.id === updatedRoom.id
          );
          if (roomIndex !== -1) {
            this.selectedVenue.rooms.splice(roomIndex, 1, updatedRoom);
          }
        }

        // Обновляем площадку в общем списке
        const venueIndex = this.venues.findIndex(
          (v) => v.id === this.selectedVenue.id
        );
        if (venueIndex !== -1) {
          this.venues[venueIndex] = { ...this.selectedVenue };
        }

        this.isEditingRoom = false;
      } catch (err) {
        this.editRoomError = err.message;
      } finally {
        this.editRoomLoading = false;
      }
    },

    // Удаление помещения
    confirmDeleteRoom(room) {
      this.roomToDelete = room;
      this.showDeleteRoomConfirm = true;
    },
    async deleteRoom() {
      if (!this.roomToDelete) return;

      this.deleteRoomLoading = true;

      try {
        const response = await fetch(`/api/rooms/${this.roomToDelete.id}/`, {
          method: "DELETE",
          headers: {
            "X-CSRFToken": this.csrfToken,
          },
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error("Нет прав для удаления");
          }
          throw new Error("Ошибка при удалении");
        }

        // Удаляем комнату из списка
        if (this.selectedVenue && this.selectedVenue.rooms) {
          const roomIndex = this.selectedVenue.rooms.findIndex(
            (r) => r.id === this.roomToDelete.id
          );
          if (roomIndex !== -1) {
            this.selectedVenue.rooms.splice(roomIndex, 1);
          }
        }

        // Обновляем площадку в общем списке
        const venueIndex = this.venues.findIndex(
          (v) => v.id === this.selectedVenue.id
        );
        if (venueIndex !== -1) {
          this.venues[venueIndex] = { ...this.selectedVenue };
        }

        this.showDeleteRoomConfirm = false;
        this.roomToDelete = null;
      } catch (err) {
        alert(err.message);
      } finally {
        this.deleteRoomLoading = false;
      }
    },
  },
};
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
  font-family: "JetBrains Mono", monospace;
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

.control-select {
  padding: 12px 20px;
  background: #0a0a0a;
  border: 2px solid #ff6b3555;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 1rem;
  cursor: pointer;
  min-width: 180px;
  transition: border-color 0.3s;
}

.control-select:focus {
  outline: none;
  border-color: #ff6b35;
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
  to {
    transform: rotate(360deg);
  }
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

/* ========== Сетка площадок ========== */
.venues-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.venue-card {
  background: linear-gradient(145deg, #1a1a2e, #16213e);
  border: 1px solid #ff6b3533;
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.venue-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 107, 53, 0.1),
    transparent
  );
  transition: left 0.5s;
  z-index: 1;
  pointer-events: none;
}

.venue-card:hover::before {
  left: 100%;
}

.venue-card:hover {
  transform: translateY(-5px);
  border-color: #ff6b35;
  box-shadow: 0 10px 40px rgba(255, 107, 53, 0.2);
}

.venue-info {
  position: relative;
  z-index: 2;
}

.venue-title {
  font-family: "JetBrains Mono", monospace;
  font-size: 1.4rem;
  color: #ff6b35;
  margin-bottom: 12px;
}

.venue-city {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.city-icon {
  font-size: 1rem;
  opacity: 0.8;
}

.city-name {
  color: #00ccff;
  font-size: 1rem;
}

.venue-address {
  color: #888;
  font-size: 0.9rem;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ff6b3522;
}

.venue-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
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
  font-family: "JetBrains Mono", monospace;
  font-weight: bold;
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
  padding: 32px;
}

.modal-body {
  /* No additional padding needed since modal-content has padding */
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
  margin-bottom: 16px;
}

.modal-header-row h2 {
  flex: 1;
  margin-bottom: 0;
}

.modal-content h2 {
  font-family: "JetBrains Mono", monospace;
  color: #ff6b35;
  font-size: 1.8rem;
  margin-bottom: 24px;
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

.modal-city {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(0, 204, 255, 0.08);
  border-radius: 8px;
  border-left: 3px solid #00ccff;
}

.modal-city .city-icon {
  font-size: 1.2rem;
}

.modal-city .city-name {
  color: #00ccff;
  font-weight: 600;
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

.modal-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
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
  font-family: "JetBrains Mono", monospace;
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

/* ========== Форма добавления/редактирования ========== */
.add-venue-modal {
  max-width: 550px;
}

.add-venue-modal h2 {
  margin-bottom: 20px;
}

.add-venue-form {
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

.form-input.small {
  width: 150px;
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

/* ========== Помещения ========== */
.rooms-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #ff6b3533;
}

.rooms-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.rooms-header h3 {
  margin-bottom: 0;
}

.add-room-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(145deg, #ff6b35, #e55a2b);
  border: none;
  color: #fff;
  font-size: 1.4rem;
  font-weight: bold;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.add-room-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 15px rgba(255, 107, 53, 0.4);
}

.rooms-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.room-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  border: 1px solid #ff6b3522;
}

.room-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.room-name {
  color: #e0e0e0;
  font-size: 1rem;
}

.room-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.room-badge.blackbox {
  background: rgba(138, 43, 226, 0.2);
  color: #b380ff;
  border: 1px solid #8a2be255;
}

.room-actions {
  display: flex;
  gap: 6px;
}

.room-edit-btn,
.room-delete-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  transition: all 0.2s ease;
}

.room-edit-btn {
  background: rgba(255, 107, 53, 0.15);
  color: #ff6b35;
}

.room-edit-btn:hover {
  background: rgba(255, 107, 53, 0.3);
}

.room-delete-btn {
  background: rgba(255, 68, 68, 0.15);
  color: #ff4444;
}

.room-delete-btn:hover {
  background: rgba(255, 68, 68, 0.3);
}

.no-rooms {
  color: #666;
  font-size: 0.95rem;
  text-align: center;
  padding: 16px;
}

/* Форма добавления помещения */
.add-room-modal {
  max-width: 450px;
}

.add-room-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Чекбокс */
.checkbox-group {
  margin-top: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  user-select: none;
}

.checkbox-input {
  display: none;
}

.checkbox-custom {
  width: 24px;
  height: 24px;
  border: 2px solid #ff6b3555;
  border-radius: 6px;
  background: rgba(10, 10, 10, 0.6);
  position: relative;
  transition: all 0.2s ease;
}

.checkbox-input:checked + .checkbox-custom {
  background: linear-gradient(145deg, #ff6b35, #e55a2b);
  border-color: #ff6b35;
}

.checkbox-input:checked + .checkbox-custom::after {
  content: "✓";
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #fff;
  font-size: 14px;
  font-weight: bold;
}

.checkbox-text {
  color: #e0e0e0;
  font-size: 1rem;
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
    flex-direction: column;
  }

  .control-search,
  .control-select {
    width: 100%;
    min-width: 100%;
  }

  .add-btn {
    width: 100%;
    justify-content: center;
  }

  .venues-grid {
    grid-template-columns: 1fr;
  }

  .modal-stats {
    grid-template-columns: 1fr;
    gap: 12px;
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
