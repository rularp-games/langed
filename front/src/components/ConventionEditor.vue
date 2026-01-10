<template>
  <div class="modal-overlay" @click.self="$emit('cancel')">
    <div class="modal-content convention-editor-modal">
      <button class="modal-close" @click="$emit('cancel')">×</button>
      
      <h2>{{ mode === 'add' ? 'Добавить конвент' : 'Редактировать конвент' }}</h2>
      
      <form @submit.prevent="submitForm" class="convention-form">
        <!-- Название -->
        <div class="form-group">
          <label for="conv-name">Название *</label>
          <input 
            id="conv-name"
            v-model="formData.name" 
            type="text" 
            required
            class="form-input"
            placeholder="Введите название конвента"
          />
        </div>
        
        <!-- Описание -->
        <div class="form-group">
          <label for="conv-description">Описание</label>
          <textarea 
            id="conv-description"
            v-model="formData.description"
            class="form-input form-textarea"
            placeholder="Описание конвента"
            rows="3"
          ></textarea>
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
  name: 'ConventionEditor',
  props: {
    // Режим: 'add' или 'edit'
    mode: {
      type: String,
      default: 'add',
      validator: v => ['add', 'edit'].includes(v)
    },
    // Данные существующего конвента для редактирования
    convention: {
      type: Object,
      default: null
    },
    // CSRF токен
    csrfToken: {
      type: String,
      default: ''
    }
  },
  emits: ['save', 'cancel', 'error'],
  data() {
    return {
      formData: {
        id: null,
        name: '',
        description: ''
      },
      loading: false,
      error: null
    }
  },
  watch: {
    convention: {
      immediate: true,
      handler(newVal) {
        if (newVal && this.mode === 'edit') {
          this.initFromConvention(newVal)
        }
      }
    },
    mode: {
      immediate: true,
      handler(newVal) {
        if (newVal === 'add') {
          this.resetForm()
        } else if (newVal === 'edit' && this.convention) {
          this.initFromConvention(this.convention)
        }
      }
    }
  },
  methods: {
    initFromConvention(convention) {
      this.formData = {
        id: convention.id,
        name: convention.name || '',
        description: convention.description || ''
      }
      this.error = null
    },
    
    resetForm() {
      this.formData = {
        id: null,
        name: '',
        description: ''
      }
      this.error = null
    },
    
    async submitForm() {
      this.loading = true
      this.error = null
      
      try {
        // Валидация
        if (!this.formData.name.trim()) {
          throw new Error('Введите название конвента')
        }
        
        // Формируем данные для API
        const conventionData = {
          name: this.formData.name.trim(),
          description: this.formData.description.trim()
        }
        
        // Добавляем ID для редактирования
        if (this.mode === 'edit' && this.formData.id) {
          conventionData.id = this.formData.id
        }
        
        // Эмитим событие с данными
        this.$emit('save', conventionData)
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
  font-family: 'JetBrains Mono', monospace;
  color: #e0e0e0;
  font-size: 1.5rem;
  margin-bottom: 24px;
  padding-right: 40px;
}

.convention-form {
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
  min-height: 80px;
  font-family: inherit;
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

/* Scrollbar */
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

/* Responsive */
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
