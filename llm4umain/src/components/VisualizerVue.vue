<template>
  <div class="visualizer-container">
    <!-- 导航标签 -->
    <div class="nav-tabs">
      <button 
        class="nav-tab" 
        :class="{ active: activeTab === 'detail' }"
        @click="activeTab = 'detail'"
      >
        详细推理过程
      </button>
      <button 
        class="nav-tab" 
        :class="{ active: activeTab === 'analysis' }" 
        @click="activeTab = 'analysis'"
      >
        结果分析
      </button>
      <button
        class="nav-tab"
        :class="{ active: activeTab === 'cluster' }"
        @click="activeTab = 'cluster'"
      >
        聚类分析
      </button>
      <button
        class="nav-tab"
        :class="{ active: activeTab === 'evaluation' }"
        @click="activeTab = 'evaluation'"
      >
        结果评估
      </button>
    </div>

    <!-- 内容区域 -->
    <div class="content-area">
      <!-- 详细推理过程 -->
      <HelloWorld
        v-if="activeTab === 'detail'"
        :jsonData="processedJsonData"
        @update-final-result="updateFinalResult"
      />

      <!-- 结果分析 -->
      <ResultAnalysis v-if="activeTab === 'analysis'" :jsonData="processedJsonData" />

      <!-- 聚类分析 -->
      <ClusterAnalysis v-if="activeTab === 'cluster'" :jsonData="processedJsonData" />

      <!-- 结果评估 -->
      <ResultEvaluation v-if="activeTab === 'evaluation'" :jsonData="processedJsonData" />
    </div>
  </div>
</template>

<script>
import HelloWorld from './HelloWorld.vue';
import ResultAnalysis from './charts/ResultAnalysis.vue';
import ClusterAnalysis from './ClusterAnalysis.vue';
import ResultEvaluation from './ResultEvaluation.vue';

export default {
  props: {
    jsonData: Object
  },
  data() {
    return {
      activeTab: 'detail',
      // 用于深拷贝存储jsonData，避免直接修改prop
      localJsonData: null
    };
  },
  components: {
    HelloWorld,
    ResultAnalysis,
    ClusterAnalysis,
    ResultEvaluation
  },
  computed: {
    // 优先使用本地数据，如果本地没有，则使用prop
    processedJsonData() {
      return this.localJsonData || this.jsonData;
    }
  },
  methods: {
    // 处理更新最终结果的事件
    updateFinalResult({ index, result }) {
      // 如果本地还没有存储数据，则进行深拷贝
      if (!this.localJsonData && this.jsonData) {
        this.localJsonData = JSON.parse(JSON.stringify(this.jsonData));
      }

      // 更新本地数据的最终结果
      if (this.localJsonData && this.localJsonData.responses && this.localJsonData.responses[index]) {
        this.localJsonData.responses[index].最终结果 = result;
      }
    }
  },
  watch: {
    // 当jsonData从父组件更新时，重置本地数据
    jsonData: {
      handler(newVal) {
        if (newVal) {
          this.localJsonData = JSON.parse(JSON.stringify(newVal));
        } else {
          this.localJsonData = null;
        }
      },
      immediate: true
    }
  }
};
</script>

<style scoped>
.visualizer-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f5f3ef; /* 米黄色背景，类似宣纸 */
}

.nav-tabs {
  display: flex;
  background-color: #f9f6f1; /* 浅米色背景 */
  padding: 16px 24px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.05);
  margin-bottom: 20px;
  border-radius: 8px;
  border-left: 4px solid #8c7a5b; /* 棕褐色边框，类似水墨画中的边框 */
}

.nav-tab {
  background: none;
  border: none;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 700;
  color: #5d4037; /* 深棕色字体 */
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.3s ease;
  margin-right: 10px;
  font-family: "FangSong", "STKaiti", serif; /* 使用仿宋或楷体字体 */
}

.nav-tab:hover {
  background-color: #f0e9e2; /* 淡褐色悬停效果 */
  color: #795548; /* 棕色文字 */
}

.nav-tab.active {
  background-color: #8c7a5b; /* 棕褐色背景 */
  color: #f9f6f1; /* 米色文字 */
}

.content-area {
  flex: 1;
  padding: 0 16px;
}
</style>