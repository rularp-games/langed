<template>
  <div class="modal-overlay" @click.self="$emit('cancel')">
    <div class="modal-content game-editor-modal">
      <button class="modal-close" @click="$emit('cancel')">×</button>

      <div class="modal-body">
        <h2>{{ mode === "add" ? "Добавить игру" : "Редактировать игру" }}</h2>

        <form @submit.prevent="submitForm" class="game-form">
          <div class="form-group">
            <label for="game-name">Название *</label>
            <input
              id="game-name"
              v-model="formData.name"
              type="text"
              required
              class="form-input"
              placeholder="Введите название игры"
            />
          </div>

          <div class="form-group">
            <label>Постер</label>
            <div class="poster-upload">
              <div
                v-if="
                  posterPreview || (game && game.poster_url && !posterRemoved)
                "
                class="poster-preview"
              >
                <img
                  :src="posterPreview || game.poster_url"
                  alt="Превью постера"
                />
                <button
                  type="button"
                  @click="removePoster"
                  class="poster-remove"
                >
                  ×
                </button>
              </div>
              <label v-else class="poster-dropzone" for="game-poster-input">
                <span class="poster-icon">🖼</span>
                <span class="poster-text">Нажмите для выбора изображения</span>
                <span class="poster-hint">JPG, PNG до 5 МБ</span>
              </label>
              <input
                id="game-poster-input"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                @change="onPosterChange"
                class="poster-input"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="game-announcement">Анонс</label>
            <textarea
              id="game-announcement"
              v-model="formData.announcement"
              class="form-input form-textarea"
              placeholder="Описание игры"
              rows="3"
            ></textarea>
          </div>

          <div class="form-group">
            <label for="game-red-flags">Красные флаги</label>
            <textarea
              id="game-red-flags"
              v-model="formData.red_flags"
              class="form-input form-textarea"
              placeholder="Предупреждения о контенте"
              rows="2"
            ></textarea>
          </div>

          <div class="form-row">
            <div class="form-group half">
              <label>Игроки</label>
              <div class="range-inputs">
                <input
                  v-model.number="formData.players_min"
                  type="number"
                  min="1"
                  class="form-input small"
                  placeholder="Мин"
                />
                <span class="range-separator">–</span>
                <input
                  v-model.number="formData.players_max"
                  type="number"
                  min="1"
                  class="form-input small"
                  placeholder="Макс"
                />
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group half">
              <label>Женские роли</label>
              <div class="range-inputs">
                <input
                  v-model.number="formData.female_roles_min"
                  type="number"
                  min="0"
                  class="form-input small"
                  placeholder="Мин"
                />
                <span class="range-separator">–</span>
                <input
                  v-model.number="formData.female_roles_max"
                  type="number"
                  min="0"
                  class="form-input small"
                  placeholder="Макс"
                />
              </div>
            </div>

            <div class="form-group half">
              <label>Мужские роли</label>
              <div class="range-inputs">
                <input
                  v-model.number="formData.male_roles_min"
                  type="number"
                  min="0"
                  class="form-input small"
                  placeholder="Мин"
                />
                <span class="range-separator">–</span>
                <input
                  v-model.number="formData.male_roles_max"
                  type="number"
                  min="0"
                  class="form-input small"
                  placeholder="Макс"
                />
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group half">
              <label>Игротехники</label>
              <input
                v-model.number="formData.technicians"
                type="number"
                min="0"
                class="form-input small"
                placeholder="0"
              />
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
  name: "GameEditor",
  props: {
    game: {
      type: Object,
      default: null,
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
      formData: this.getEmptyGame(),
      posterFile: null,
      posterPreview: null,
      posterRemoved: false,
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
  computed: {
    csrfToken() {
      const match = document.cookie.match(/csrftoken=([^;]+)/);
      return match ? match[1] : "";
    },
  },
  watch: {
    game: {
      handler(newGame) {
        if (newGame && this.mode === "edit") {
          this.formData = {
            id: newGame.id,
            name: newGame.name || "",
            announcement: newGame.announcement || "",
            red_flags: newGame.red_flags || "",
            players_min: newGame.players_min || 1,
            players_max: newGame.players_max || 10,
            female_roles_min: newGame.female_roles_min || 0,
            female_roles_max: newGame.female_roles_max || 0,
            male_roles_min: newGame.male_roles_min || 0,
            male_roles_max: newGame.male_roles_max || 0,
            technicians: newGame.technicians || 0,
          };
        }
      },
      immediate: true,
    },
  },
  methods: {
    getEmptyGame() {
      return {
        name: "",
        announcement: "",
        red_flags: "",
        players_min: 1,
        players_max: 10,
        female_roles_min: 0,
        female_roles_max: 0,
        male_roles_min: 0,
        male_roles_max: 0,
        technicians: 0,
      };
    },
    onPosterChange(event) {
      const file = event.target.files[0];
      if (!file) return;

      // Проверка размера (5 МБ)
      if (file.size > 5 * 1024 * 1024) {
        this.error = "Файл слишком большой. Максимум 5 МБ";
        event.target.value = "";
        return;
      }

      this.posterFile = file;
      this.posterPreview = URL.createObjectURL(file);
      this.posterRemoved = false;
    },
    removePoster() {
      if (this.posterPreview) {
        URL.revokeObjectURL(this.posterPreview);
      }
      this.posterFile = null;
      this.posterPreview = null;
      this.posterRemoved = true;
      // Сбросить input
      const input = document.getElementById("game-poster-input");
      if (input) input.value = "";
    },
    async submitForm() {
      this.loading = true;
      this.error = null;

      try {
        const formData = new FormData();
        formData.append("name", this.formData.name);
        formData.append("announcement", this.formData.announcement || "");
        formData.append("red_flags", this.formData.red_flags || "");
        formData.append("players_min", this.formData.players_min);
        formData.append("players_max", this.formData.players_max);
        formData.append("female_roles_min", this.formData.female_roles_min);
        formData.append("female_roles_max", this.formData.female_roles_max);
        formData.append("male_roles_min", this.formData.male_roles_min);
        formData.append("male_roles_max", this.formData.male_roles_max);
        formData.append("technicians", this.formData.technicians);

        if (this.posterFile) {
          formData.append("poster", this.posterFile);
        } else if (this.posterRemoved) {
          formData.append("poster", "");
        }

        let url = "/api/games/";
        let method = "POST";

        if (this.mode === "edit" && this.formData.id) {
          url = `/api/games/${this.formData.id}/`;
          method = "PATCH";
        }

        const response = await fetch(url, {
          method,
          headers: {
            "X-CSRFToken": this.csrfToken,
          },
          body: formData,
        });

        if (!response.ok) {
          if (response.status === 401 || response.status === 403) {
            throw new Error(
              this.mode === "add"
                ? "Необходима авторизация для добавления игры"
                : "Нет прав для редактирования этой игры"
            );
          }
          const data = await response.json();
          throw new Error(
            data.detail || data.name?.[0] || "Ошибка при сохранении"
          );
        }

        const savedGame = await response.json();
        this.$emit("saved", savedGame);
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },
  },
  beforeUnmount() {
    // Восстанавливаем прокрутку body
    document.body.classList.remove("modal-open");
    document.body.style.top = "";
    window.scrollTo(0, this.savedScrollY);

    if (this.posterPreview) {
      URL.revokeObjectURL(this.posterPreview);
    }
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

.game-editor-modal {
  padding: 32px;
  max-width: 700px;
}

.game-editor-modal h2 {
  font-family: "JetBrains Mono", monospace;
  color: #ff6b35;
  font-size: 1.8rem;
  margin-bottom: 20px;
  padding-right: 40px;
}

.modal-body {
  /* padding handled by game-editor-modal */
}

.game-form {
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

.form-row {
  display: flex;
  gap: 20px;
}

.form-group.half {
  flex: 1;
}

.range-inputs {
  display: flex;
  align-items: center;
  gap: 12px;
}

.range-separator {
  color: #888;
  font-size: 1.2rem;
}

.form-input.small {
  width: 80px;
  text-align: center;
}

/* Загрузка постера */
.poster-upload {
  position: relative;
}

.poster-input {
  display: none;
}

.poster-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px 24px;
  background: rgba(10, 10, 10, 0.4);
  border: 2px dashed #ff6b3555;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.poster-dropzone:hover {
  border-color: #ff6b35;
  background: rgba(255, 107, 53, 0.05);
}

.poster-icon {
  font-size: 2.5rem;
  opacity: 0.7;
}

.poster-text {
  color: #aaa;
  font-size: 0.95rem;
}

.poster-hint {
  color: #666;
  font-size: 0.8rem;
}

.poster-preview {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  max-height: 200px;
}

.poster-preview img {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
  border-radius: 12px;
}

.poster-remove {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 32px;
  height: 32px;
  background: rgba(255, 68, 68, 0.9);
  border: none;
  border-radius: 50%;
  color: #fff;
  font-size: 1.4rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: transform 0.2s, background 0.2s;
}

.poster-remove:hover {
  transform: scale(1.1);
  background: #ff4444;
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
