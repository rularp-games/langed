<template>
  <div class="roadmap-container">
    <h1>Roadmap</h1>
    <p class="roadmap-description">План развития проекта</p>
    
    <div class="roadmap-timeline">
      <div class="roadmap-item completed">
        <div class="roadmap-marker"></div>
        <div class="roadmap-content">
          <h3>MVP</h3>
          <p>Базовый функционал: игры, конвенты, площадки, афиша</p>
        </div>
      </div>
      
      <div class="roadmap-item in-progress">
        <div class="roadmap-marker"></div>
        <div class="roadmap-content">
          <h3>Расписание мероприятий</h3>
          <p>Редактор расписания для конвентов с drag-and-drop</p>
        </div>
      </div>
      
      <div class="roadmap-item planned">
        <div class="roadmap-marker"></div>
        <div class="roadmap-content">
          <h3>Поселение</h3>
          <p>Управление размещением участников на конвентах</p>
        </div>
      </div>
      
      <div class="roadmap-item planned">
        <div class="roadmap-marker"></div>
        <div class="roadmap-content">
          <h3>Оповещения</h3>
          <p>Уведомления о предстоящих играх и изменениях</p>
          <ul class="roadmap-subitems">
            <li>Оповещение в канал Telegram</li>
            <li>Оповещение в личку Telegram</li>
            <li>Оповещение в личку VK</li>
          </ul>
        </div>
      </div>
      
      <div class="roadmap-item planned">
        <div class="roadmap-marker"></div>
        <div class="roadmap-content">
          <h3>Отметка о сдаче взноса на конвент</h3>
          <p>Учёт оплаты участия в мероприятиях</p>
        </div>
      </div>
      
    </div>
  </div>
</template>

<script>
export default {
  name: 'ProjectRoadmap'
}
</script>

<style scoped>
.roadmap-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 24px;
}

h1 {
  color: #ff6b35;
  font-size: 2.5rem;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.roadmap-description {
  color: #888;
  font-size: 1.1rem;
  margin-bottom: 40px;
}

.roadmap-timeline {
  position: relative;
  padding-left: 40px;
}

.roadmap-timeline::before {
  content: '';
  position: absolute;
  left: 12px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: linear-gradient(180deg, #ff6b35 0%, #ff6b3533 100%);
}

.roadmap-item {
  position: relative;
  margin-bottom: 32px;
  padding: 20px 24px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid #333;
  border-radius: 12px;
  transition: all 0.3s ease;
}

.roadmap-item:hover {
  border-color: #ff6b35;
  background: rgba(255, 107, 53, 0.05);
}

.roadmap-marker {
  position: absolute;
  left: -34px;
  top: 24px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 3px solid #0a0a0a;
}

.roadmap-item.completed .roadmap-marker {
  background: #4caf50;
  box-shadow: 0 0 12px rgba(76, 175, 80, 0.5);
}

.roadmap-item.in-progress .roadmap-marker {
  background: #ff6b35;
  box-shadow: 0 0 12px rgba(255, 107, 53, 0.5);
  animation: pulse 2s infinite;
}

.roadmap-item.planned .roadmap-marker {
  background: #666;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 12px rgba(255, 107, 53, 0.5);
  }
  50% {
    box-shadow: 0 0 20px rgba(255, 107, 53, 0.8);
  }
}

.roadmap-content h3 {
  color: #e0e0e0;
  font-size: 1.2rem;
  margin-bottom: 8px;
  font-weight: 600;
}

.roadmap-content p {
  color: #888;
  font-size: 0.95rem;
  line-height: 1.5;
}

.roadmap-subitems {
  margin-top: 12px;
  padding-left: 20px;
  list-style: none;
}

.roadmap-subitems li {
  color: #777;
  font-size: 0.9rem;
  padding: 4px 0;
  position: relative;
}

.roadmap-subitems li::before {
  content: '›';
  position: absolute;
  left: -16px;
  color: #ff6b35;
  font-weight: bold;
}

.roadmap-item.completed .roadmap-content h3 {
  color: #4caf50;
}

.roadmap-item.in-progress .roadmap-content h3 {
  color: #ff6b35;
}

@media (max-width: 768px) {
  .roadmap-container {
    padding: 24px 16px;
  }
  
  h1 {
    font-size: 1.8rem;
  }
  
  .roadmap-timeline {
    padding-left: 30px;
  }
  
  .roadmap-marker {
    left: -24px;
    width: 12px;
    height: 12px;
  }
  
  .roadmap-timeline::before {
    left: 8px;
  }
}
</style>
