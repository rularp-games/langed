<template>
  <div class="cyberwordly">
    <div class="ticker-left">
      <div class="ticker-content" v-for="(item, index) in leftTickerTexts" :key="'left-' + index" :style="{ animationDelay: item.delay + 's', animationDuration: item.duration + 's' }">
        {{ item.text }}
      </div>
    </div>
    <div class="ticker-left ticker-left-2">
      <div class="ticker-content" v-for="(item, index) in leftTickerTexts2" :key="'left2-' + index" :style="{ animationDelay: item.delay + 's', animationDuration: item.duration + 's' }">
        {{ item.text }}
      </div>
    </div>
    <div class="ticker-left ticker-left-3">
      <div class="ticker-content" v-for="(item, index) in leftTickerTexts3" :key="'left3-' + index" :style="{ animationDelay: item.delay + 's', animationDuration: item.duration + 's' }">
        {{ item.text }}
      </div>
    </div>
    <div class="ticker-left ticker-left-4">
      <div class="ticker-content" v-for="(item, index) in leftTickerTexts4" :key="'left4-' + index" :style="{ animationDelay: item.delay + 's', animationDuration: item.duration + 's' }">
        {{ item.text }}
      </div>
    </div>
    <div class="content-wrapper">
      <table class="data-table">
        <tr v-for="(row, rowIndex) in tableData" :key="rowIndex">
          <td v-for="(cell, colIndex) in row" :key="colIndex">
            {{ cell }}
          </td>
        </tr>
      </table>
      <table class="input-table">
        <tr v-for="(row, rowIndex) in inputTableData" :key="rowIndex">
          <td v-for="(cell, colIndex) in row" :key="colIndex" @click="fillDataTable(cell)">
            {{ cell }}
          </td>
        </tr>
      </table>
    </div>
    <div class="ticker-right">
      <div class="ticker-content" v-for="(item, index) in rightTickerTexts" :key="'right-' + index" :style="{ animationDelay: item.delay + 's', animationDuration: item.duration + 's' }">
        {{ item.text }}
      </div>
    </div>
    <div class="ticker-right ticker-right-2">
      <div class="ticker-content" v-for="(item, index) in rightTickerTexts2" :key="'right2-' + index" :style="{ animationDelay: item.delay + 's', animationDuration: item.duration + 's' }">
        {{ item.text }}
      </div>
    </div>
    <div class="ticker-right ticker-right-3">
      <div class="ticker-content" v-for="(item, index) in rightTickerTexts3" :key="'right3-' + index" :style="{ animationDelay: item.delay + 's', animationDuration: item.duration + 's' }">
        {{ item.text }}
      </div>
    </div>
    <div class="ticker-right ticker-right-4">
      <div class="ticker-content" v-for="(item, index) in rightTickerTexts4" :key="'right4-' + index" :style="{ animationDelay: item.delay + 's', animationDuration: item.duration + 's' }">
        {{ item.text }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CyberwordlyPage',
  data() {
    return {
      tableData: [
        ['', '', '', '', ''],
        ['', '', '', '', ''],
        ['', '', '', '', ''],
        ['', '', '', '', ''],
        ['', '', '', '', '']
      ],
      inputTableData: [
        ['0', '1', '2', '3', '4', '5', '6', '7'],
        ['8', '9', 'A', 'B', 'C', 'D', 'E', 'F'],
      ],
      leftTickerTexts: [],
      leftTickerTexts2: [],
      leftTickerTexts3: [],
      leftTickerTexts4: [],
      rightTickerTexts: [],
      rightTickerTexts2: [],
      rightTickerTexts3: [],
      rightTickerTexts4: [],
      currentDataTableIndex: 0,
      randomValuesArray: []
    }
  },
  mounted() {
    this.generateTickerTexts()
    this.generateRandomValuesArray()
  },
  methods: {
    generateTickerTexts() {
      const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?'
      const generateRandomText = () => {
        let text = ''
        for (let i = 0; i < 20; i++) {
          text += chars[Math.floor(Math.random() * chars.length)] + ' '
        }
        return text
      }
      
      const generateTickerItem = () => {
        return {
          text: generateRandomText(),
          delay: Math.random() * 5, // случайная задержка от 0 до 5 секунд
          duration: 10 + Math.random() * 10 // случайная длительность от 10 до 20 секунд
        }
      }
      
      this.leftTickerTexts = Array(10).fill(0).map(() => generateTickerItem())
      this.leftTickerTexts2 = Array(10).fill(0).map(() => generateTickerItem())
      this.leftTickerTexts3 = Array(10).fill(0).map(() => generateTickerItem())
      this.leftTickerTexts4 = Array(10).fill(0).map(() => generateTickerItem())
      this.rightTickerTexts = Array(10).fill(0).map(() => generateTickerItem())
      this.rightTickerTexts2 = Array(10).fill(0).map(() => generateTickerItem())
      this.rightTickerTexts3 = Array(10).fill(0).map(() => generateTickerItem())
      this.rightTickerTexts4 = Array(10).fill(0).map(() => generateTickerItem())
    },
    fillDataTable(value) {
      const totalCells = this.tableData.length * this.tableData[0].length
      if (this.currentDataTableIndex < totalCells) {
        const rowIndex = Math.floor(this.currentDataTableIndex / this.tableData[0].length)
        const colIndex = this.currentDataTableIndex % this.tableData[0].length
        this.tableData[rowIndex][colIndex] = value
        this.currentDataTableIndex++
      } else {
        // Если таблица заполнена, начинаем заново
        this.currentDataTableIndex = 0
        const rowIndex = Math.floor(this.currentDataTableIndex / this.tableData[0].length)
        const colIndex = this.currentDataTableIndex % this.tableData[0].length
        this.tableData[rowIndex][colIndex] = value
        this.currentDataTableIndex++
      }
    },
    generateRandomValuesArray() {
      // Получаем все значения из input-table
      const allValues = this.inputTableData.flat()
      // Генерируем массив из 5 случайных значений
      this.randomValuesArray = []
      for (let i = 0; i < 5; i++) {
        const randomIndex = Math.floor(Math.random() * allValues.length)
        this.randomValuesArray.push(allValues[randomIndex])
      }
    }
  }
}
</script>

<style scoped>
.cyberwordly {
  min-height: 100vh;
  background-color: #000000;
  display: flex;
  position: relative;
  overflow: hidden;
}

.content-wrapper {
  flex: 1;
  text-align: center;
  padding: 20px;
  margin-left: 200px;
  margin-right: 200px;
  z-index: 1;
}

h1 {
  color: #42b983;
  margin-bottom: 20px;
}

p {
  color: #00ff00;
  font-size: 18px;
}

.data-table {
  margin: 20px auto;
  border-collapse: collapse;
  background-color: #000000;
}

.data-table td {
  border: 1px solid #00ff00;
  padding: 15px;
  color: #00ff00;
  background-color: #000000;
  width: 100px;
  height: 100px;
  text-align: center;
  font-size: 24px;
  font-weight: bold;
}

.input-table {
  margin: 20px auto;
  border-collapse: collapse;
  background-color: #000000;
}

.input-table td {
  border: 1px solid #00ff00;
  padding: 15px;
  color: #00ff00;
  background-color: #000000;
  width: 80px;
  height: 80px;
  text-align: center;
  font-size: 24px;
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.2s;
}

.input-table td:hover {
  background-color: #003300;
}

.ticker-left,
.ticker-right {
  position: fixed;
  top: 0;
  width: 50px;
  height: 100vh;
  overflow: hidden;
  z-index: 0;
}

.ticker-left {
  left: 0;
}

.ticker-left-2 {
  left: 50px;
}

.ticker-left-3 {
  left: 100px;
}

.ticker-left-4 {
  left: 150px;
}

.ticker-right {
  right: 0;
}

.ticker-right-2 {
  right: 50px;
}

.ticker-right-3 {
  right: 100px;
}

.ticker-right-4 {
  right: 150px;
}

.ticker-content {
  writing-mode: vertical-rl;
  text-orientation: mixed;
  color: #00ff00;
  font-size: 14px;
  font-family: 'Courier New', monospace;
  white-space: nowrap;
  animation: ticker-scroll 15s linear infinite;
  margin-bottom: 30px;
  opacity: 0.7;
}

@keyframes ticker-scroll {
  0% {
    transform: translateY(100vh);
  }
  100% {
    transform: translateY(-100%);
  }
}
</style>

