<template>
  <div class="container" v-if="jsonData">
    <!-- 元信息区域 -->
    <div class="meta-info">
      <div class="meta-item">
        <span class="meta-label">问题</span>
        <span class="meta-value">{{ jsonData.meta.question }}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Prompt类型</span>
        <span class="meta-value">{{ jsonData.meta.q_type }}</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">RAG实体</span>
        <span class="meta-value">{{ jsonData.meta.entity }}</span>
      </div>
    </div>

    <!-- 知识图谱可视化区域 -->
    <div class="kg-visualization">
      <h3 class="section-title">知识图谱可视化</h3>
      <Neo4jGraph :entity="jsonData.meta.entity" />
    </div>

    <!-- 两列布局容器 -->
    <div class="content-layout">
      <!-- 左侧：知识图谱信息 -->
      <div class="knowledge-graph-section">
        <h3 class="section-title">知识图谱补充信息</h3>
        <div v-if="firstResponse?.['知识图谱补充信息']" class="graph-info">
          <div class="graph-content">
            <div
              v-for="([key, value], index) in sortedGraphInfo"
              :key="index"
              class="graph-section"
            >
              <details open>
                <summary class="graph-section-title">{{ key }}</summary>
                <div class="graph-section-content">
                  <pre>{{ value }}</pre>
                  <!-- 如果是事件路径部分，添加年份的提示说明 -->
                  <div v-if="key === '事件路径'" class="path-year-info">
                    <span class="info-icon">&#8505;</span>
                    <span class="info-text">年份信息已添加到事件路径中</span>
                  </div>
                </div>
              </details>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：LLM回答区域 -->
      <div class="llm-responses-section">
        <h3 class="section-title">LLM回答结果</h3>
        
        <!-- 回答选择器 -->
        <div class="response-tabs">
          <button
            v-for="(response, index) in jsonData.responses"
            :key="index"
            class="tab-button"
            :class="{ active: selectedResponseIndex === index }"
            @click="selectedResponseIndex = index"
          >
            回答 {{ index + 1 }}
          </button>
        </div>

        <!-- 当前选中的回答内容 -->
        <div v-if="currentResponse" class="response-content">
          
          <!-- 最终结果部分 -->
          <div v-if="currentResponse.最终结果" class="final-result-section">
            <h4>最终结果</h4>
            <div class="keyword-chips">
              <span 
                v-for="(keyword, index) in currentResponse.最终结果.split(',')" 
                :key="index"
                class="keyword-chip"
              >
                {{ keyword.trim() }}
              </span>
            </div>
          </div>

          <!-- 总结部分 -->
          <div v-if="currentResponse.总结" class="result-section">
            <h4>推理逻辑与总结</h4>
            <p class="result-text">{{ currentResponse.总结 }}</p>
          </div>
          
          <!-- 结果部分 -->
          <div v-else-if="currentResponse.结果" class="result-section">
            <h4>总结</h4>
            <p class="result-text">{{ currentResponse.结果 }}</p>
          </div>

          <!-- 推理路径可视化 -->
          <div class="reasoning-paths">
            <h4>推理路径</h4>
            <div class="paths-container">
              <div v-for="(path, key) in paths" :key="key" class="path-block">
                <div class="path-header">
                  <span class="path-number">{{ key.replace('路径', 'Path ') }}</span>
                  <span class="path-title">{{ path["标题"] }}</span>
                </div>
                <div class="path-nodes">
                  <div
                    v-for="(nodeContent, nodeKey) in path['节点']"
                    :key="nodeKey"
                    class="node-card"
                  >
                    <div class="node-header">
                      <span class="node-number">{{ nodeKey }}</span>
                    </div>
                    <div class="node-content">{{ nodeContent }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="loading">加载中，请稍候...</div>
</template>

<script>
import Neo4jGraph from './charts/Neo4jGraph.vue';

export default {
  name: "HelloWorld",
  components: {
    Neo4jGraph
  },
  props: {
    jsonData: Object,
  },
  data() {
    return {
      selectedResponseIndex: 0,
    };
  },
  computed: {
    currentResponse() {
      return this.jsonData?.responses?.[this.selectedResponseIndex];
    },
    firstResponse() {
      return this.jsonData?.responses?.[0];
    },
    paths() {
      if (!this.currentResponse) return {};
      return Object.fromEntries(
        Object.entries(this.currentResponse).filter(([key]) => key.startsWith("路径"))
      );
    },
    sortedGraphInfo() {
      const info = this.firstResponse?.["知识图谱补充信息"];
      if (!info) return [];

      const order = ["基础信息", "事件路径"];
      const ordered = [];

      for (const key of order) {
        if (info[key]) {
          ordered.push([key, info[key]]);
        }
      }

      for (const key in info) {
        if (!order.includes(key)) {
          ordered.push([key, info[key]]);
        }
      }

      return ordered;
    },
  },
};
</script>

<style scoped>
.container {
  width: 100%;
  max-width: 100%;
  margin: 20px auto;
  font-family: "STKaiti", "FangSong", serif;
  line-height: 1.6;
  padding: 0 20px;
  box-sizing: border-box;
}

.meta-info {
  background: #e8efe9;
  padding: 24px;
  border-radius: 8px;
  border-left: 5px solid #4a6056;
  margin-bottom: 20px;
}

/* 知识图谱可视化区域 */
.kg-visualization {
  width: 100%;
  height: 500px;
  margin-bottom: 40px;
  background: #f9f6f1;
  border-radius: 8px;
  border: 1px solid #d3c8b4;
  position: relative;
  z-index: 1;
  padding-top: 10px;
}

.section-title {
  margin: 0 0 20px 0;
  color: #5d4037;
  font-size: 1.25rem;
  font-weight: 600;
  padding: 0 0 12px 0;
  font-family: "STKaiti", "FangSong", serif;
  position: relative;
}

.section-title::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: #8c7a5b;
  opacity: 0.8;
}

.kg-visualization .section-title {
  margin: 0 20px 15px 20px;
}

.content-layout {
  position: relative;
  z-index: 0;
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 20px;
  margin-top: 20px;
}

/* 知识图谱部分样式 */
.knowledge-graph-section {
  background: #f9f6f1;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  border: 1px solid #d3c8b4;
  max-height: 600px;
  overflow-y: auto;
}

.graph-section {
  margin-bottom: 16px;
  border: 1px solid #e8e0d8; /* 米黄色边框 */
  border-radius: 6px;
  overflow: hidden;
}

.graph-section-title {
  padding: 12px 16px;
  background: #f0e9e2; /* 淡褐色背景 */
  font-weight: 700;
  cursor: pointer;
  user-select: none;
  font-size: 14px;
  color: #5d4037; /* 深棕色文字 */
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.graph-section-content {
  padding: 16px;
  background: #f9f6f1; /* 浅米色背景 */
  max-height: 800px;
  overflow-y: auto;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.graph-section-content pre {
  margin: 0;
  white-space: pre-wrap;
  font-size: 14px;
  line-height: 1.6;
  color: #5d4037; /* 深棕色文字 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

/* 自定义滚动条样式 */
.knowledge-graph-section::-webkit-scrollbar {
  width: 8px;
}

.knowledge-graph-section::-webkit-scrollbar-track {
  background: #f0e9e2;
  border-radius: 4px;
}

.knowledge-graph-section::-webkit-scrollbar-thumb {
  background: #d3c8b4;
  border-radius: 4px;
}

.knowledge-graph-section::-webkit-scrollbar-thumb:hover {
  background: #8c7a5b;
}

/* LLM回答部分样式 */
.llm-responses-section {
  background: #f9f6f1;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  border: 1px solid #d3c8b4;
  max-height: 600px;
  overflow-y: auto;
}

.response-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  background: #f9f6f1;
  padding: 10px;
  border-radius: 8px;
  top: 0;
  z-index: 2;
}

.tab-button {
  padding: 8px 16px;
  border: none;
  background: #f0e9e2; /* 淡褐色背景 */
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 14px;
  font-weight: bold;
  color: #8c7a5b; /* 棕褐色文字 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.tab-button.active {
  background: #8c7a5b; /* 棕褐色背景 */
  color: #f9f6f1; /* 米色文字 */
  font-weight: 500;
}

.result-section {
  background: #f0e9e2; /* 淡褐色背景 */
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid #e8e0d8; /* 米黄色边框 */
}

.result-section h4 {
  margin: 0 0 8px 0;
  color: #5d4037; /* 深棕色文字 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.result-text {
  margin: 0;
  color: #5d4037; /* 深棕色文字 */
  font-size: 15px;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

/* 最终结果样式 */
.final-result-section {
  background: #e8efe9; /* 浅墨绿色背景 */
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  border-left: 4px solid #4a6056; /* 墨绿色边框 */
  font-weight: bold;
}

.final-result-section h4 {
  margin: 0 0 12px 0;
  color: #5d4037; /* 深棕色文字 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  font-weight: bold;
}

.keyword-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-weight: bold;
}

.keyword-chip {
  background: #68838b; /* 墨蓝色背景 */
  color: #f9f6f1; /* 米色文字 */
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 14px;
  font-weight: bold;
  display: inline-block;
  border: 1px solid #4a6056; /* 墨绿色边框 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.reasoning-paths {
  margin-top: 24px;
}

.reasoning-paths h4 {
  margin: 0 0 16px 0;
  color: #5d4037; /* 深棕色文字 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.path-block {
  margin-bottom: 24px;
  background: #f9f6f1; /* 浅米色背景 */
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #d3c8b4; /* 棕褐色边框 */
}

.path-header {
  background: #f0e9e2; /* 淡褐色背景 */
  padding: 12px 16px;
  border-bottom: 1px solid #e8e0d8; /* 米黄色边框 */
  display: flex;
  align-items: center;
  gap: 12px;
}

.path-number {
  font-weight: 600;
  color: #68838b; /* 墨蓝色文字 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.path-title {
  color: #5d4037; /* 深棕色文字 */
  font-weight: bold;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.path-nodes {
  padding: 16px;
}

.node-card {
  background: #f9f6f1; /* 浅米色背景 */
  border: 1px solid #e8e0d8; /* 米黄色边框 */
  border-radius: 6px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
}

.node-card:hover {
  border-color: #68838b; /* 墨蓝色边框 */
  box-shadow: 0 2px 8px rgba(104, 131, 139, 0.1); /* 墨蓝色阴影 */
}

.node-header {
  padding: 8px 12px;
  background: #f0e9e2; /* 淡褐色背景 */
  border-bottom: 1px solid #e8e0d8; /* 米黄色边框 */
}

.node-number {
  font-weight: 500;
  color: #68838b; /* 墨蓝色文字 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.node-content {
  padding: 12px;
  color: #5d4037; /* 深棕色文字 */
  font-size: 14px;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.meta-item {
  margin-bottom: 12px;
}

.meta-item:last-child {
  margin-bottom: 0;
}

.meta-label {
  font-size: 1.1rem;
  font-weight: 600;
  color: #5d4037; /* 深棕色文字 */
  margin-right: 12px;
  min-width: 120px;
  display: inline-block;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.meta-value {
  font-size: 1.1rem;
  color: #5d4037; /* 深棕色文字 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.loading {
  text-align: center;
  font-size: 20px;
  color: #8c7a5b; /* 棕褐色文字 */
  margin-top: 100px;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

/* 添加年份信息提示的样式 */
.path-year-info {
  margin-top: 8px;
  padding: 6px 10px;
  background-color: #e8efe9; /* 浅墨绿色背景 */
  border-left: 3px solid #4a6056; /* 墨绿色边框 */
  border-radius: 4px;
  font-size: 13px;
  color: #5d4037; /* 深棕色文字 */
  display: flex;
  align-items: center;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.info-icon {
  font-size: 16px;
  color: #68838b; /* 墨蓝色文字 */
  margin-right: 8px;
}

.info-text {
  font-weight: 500;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

/* 响应式布局调整 */
@media (max-width: 1024px) {
  .container {
    padding: 0 16px;
  }

  .kg-visualization {
    height: 400px;
    margin-bottom: 30px;
  }
  
  .content-layout {
    grid-template-columns: 1fr;
  }

  .knowledge-graph-section,
  .llm-responses-section {
    max-height: 500px;
  }
}
</style>