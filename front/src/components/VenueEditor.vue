<template>
  <div class="modal-overlay" @click.self="$emit('cancel')">
    <div class="modal-content venue-editor-modal">
      <button class="modal-close" @click="$emit('cancel')">×</button>

      <div class="modal-body">
        <h2>
          {{ mode === "add" ? "Добавить площадку" : "Редактировать площадку" }}
        </h2>

        <form @submit.prevent="submitForm" class="venue-form">
          <div class="form-group">
            <label for="venue-name">Название *</label>
            <input
              id="venue-name"
              v-model="formData.name"
              type="text"
              required
              class="form-input"
              placeholder="Введите название площадки"
            />
          </div>

          <div class="form-group">
            <label for="venue-city">Город *</label>
            <select
              id="venue-city"
              v-model="formData.city_id"
              required
              class="form-input"
            >
              <option value="">Выберите город</option>
              <option v-for="city in cities" :key="city.id" :value="city.id">
                {{ city.name }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label for="venue-address">Адрес</label>
            <input
              id="venue-address"
              v-model="formData.address"
              type="text"
              class="form-input"
              placeholder="Улица, дом, помещение"
            />
          </div>

          <div class="form-group">
            <label for="venue-description">Описание</label>
            <textarea
              id="venue-description"
              v-model="formData.description"
              class="form-input form-textarea"
              placeholder="Дополнительная информация о площадке"
              rows="3"
            ></textarea>
          </div>

          <div class="form-group">
            <label for="venue-capacity">Вместимость</label>
            <input
              id="venue-capacity"
              v-model.number="formData.capacity"
              type="number"
              min="1"
              class="form-input small"
              placeholder="Количество человек"
            />
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
              <span v-if="loading">Сохранение...</span>
              <span v-else>{{
                mode === "add" ? "Добавить" : "Сохранить"
              }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "VenueEditor",
  props: {
    venue: {
      type: Object,
      default: null,
    },
    cities: {
      type: Array,
      required: true,
    },
    mode: {
      type: String,
      default: "add",
      validator: (value) => ["add", "edit"].includes(value),
    },
  },
  emits: ["saved", "cancel"],
  data() {
    return {
      savedScrollY: 0,
      formData: this.getEmptyVenue(),
      loading: false,
      error: null,
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
    document.body.classList.remove("modal-open");
    document.body.style.top = "";
    window.scrollTo(0, this.savedScrollY);
  },
  computed: {
    csrfToken() {
      const match = document.cookie.match(/csrftoken=([^;]+)/);
      return match ? match[1] : "";
    },
  },
  watch: {
    venue: {
      handler(newVenue) {
        if (newVenue && this.mode === "edit") {
          this.formData = {
            id: newVenue.id,
            name: newVenue.name || "",
            city_id: newVenue.city?.id || "",
            address: newVenue.address || "",
            description: newVenue.description || "",
            capacity: newVenue.capacity || null,
          };
        }
      },
      immediate: true,
    },
  },
  methods: {
    getEmptyVenue() {
      return {
        name: "",
        city_id: "",
        address: "",
        description: "",
        capacity: null,
      };
    },
    async submitForm() {
      this.loading = true;
      this.error = null;

      try {
        const payload = {
          name: this.formData.name,
          city_id: this.formData.city_id,
          address: this.formData.address || "",
          description: this.formData.description || "",
          capacity: this.formData.capacity || null,
        };

        let url = "/api/venues/";
        let method = "POST";

        if (this.mode === "edit" && this.formData.id) {
          url = `/api/venues/${this.formData.id}/`;
          method = "PATCH";
        }

        const response = await fetch(url, {
          method,
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this.csrfToken,
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error(
              this.mode === "add"
                ? "Необходима авторизация для добавления площадки"
                : "Нет прав для редактирования этой площадки"
            );
          }
          const data = await response.json();
          throw new Error(
            data.detail || data.name?.[0] || "Ошибка при сохранении"
          );
        }

        const savedVenue = await response.json();
        this.$emit("saved", savedVenue);
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
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

.venue-editor-modal {
  padding: 32px;
  max-width: 700px;
}

.venue-editor-modal h2 {
  font-family: "JetBrains Mono", monospace;
  color: #ff6b35;
  font-size: 1.8rem;
  margin-bottom: 20px;
  padding-right: 40px;
}

.modal-body {
  /* padding handled by venue-editor-modal */
}

.venue-form {
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
  width: 120px;
  text-align: center;
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

@media (max-width: 768px) {
  .form-actions {
    flex-direction: column-reverse;
  }

  .btn {
    width: 100%;
    text-align: center;
  }
}
</style>
