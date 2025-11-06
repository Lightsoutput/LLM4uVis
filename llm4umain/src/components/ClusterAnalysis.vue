<template>
    <div class="cluster-analysis-container">
      <h2 class="analysis-title">回答聚类分析</h2>
  
      <div v-if="loading" class="loading">
        <div class="spinner"></div>
        <p>正在进行聚类分析，请稍候...</p>
      </div>
  
      <div v-else-if="error" class="error-message">
        <p>{{ error }}</p>
      </div>
  
      <div v-else-if="!clusterResults || Object.keys(clusterResults).length === 0" class="no-data">
        <p>暂无聚类分析数据</p>
      </div>
  
      <div v-else class="analysis-content">
        <!-- 聚类结果概述 -->
        <div class="summary-card">
          <h3>聚类分析概述</h3>
          <div class="stats">
            <div class="stat-item">
              <span class="stat-label">分析路径数:</span>
              <span class="stat-value">{{ Object.keys(clusterResults).length }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">总节点数:</span>
              <span class="stat-value">{{ getTotalNodesCount() }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">聚类总数:</span>
              <span class="stat-value">{{ getTotalClustersCount() }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">平均每节点聚类:</span>
              <span class="stat-value">{{ getAverageClusterCount() }}</span>
            </div>
          </div>
        </div>
  
        <!-- 路径和节点的聚类结果 -->
        <div v-for="(pathData, pathKey) in clusterResults" :key="pathKey" class="path-card">
          <div class="path-header">
            <h3>{{ pathData.title }}</h3>
            <span class="path-key">{{ pathKey }}</span>
          </div>
  
          <div class="nodes-container">
            <div v-for="(nodeData, nodeKey) in pathData.nodes" :key="`${pathKey}-${nodeKey}`" class="node-card">
              <div class="node-header">
                <h4>{{ nodeKey }}</h4>
                <div class="node-stats">
                  <span>{{ nodeData.sentences.length }} 个回答</span>
                  <span class="stats-divider">|</span>
                  <span class="cluster-count">
                    <span class="cluster-dot" :style="getClusterColorStyle(nodeData.cluster_count || nodeData.summaries.length)"></span>
                    {{ nodeData.cluster_count || nodeData.summaries.length }} 个聚类
                  </span>
                </div>
              </div>
  
              <!-- 聚类结果可视化 -->
              <div class="cluster-visualization">
                <div class="cluster-groups">
                  <div 
                    v-for="(summary, clusterIndex) in nodeData.summaries" 
                    :key="`${pathKey}-${nodeKey}-cluster-${clusterIndex}`"
                    class="cluster-group"
                  >
                    <div class="cluster-summary">
                      <div class="cluster-title">聚类 {{ clusterIndex + 1 }}</div>
                      <p>{{ summary }}</p>
                    </div>
  
                    <div class="cluster-items">
                      <div 
                        v-for="(sentence, sentenceIndex) in nodeData.sentences" 
                        :key="`${pathKey}-${nodeKey}-sentence-${sentenceIndex}`"
                        v-show="nodeData.clusters[sentenceIndex] === clusterIndex"
                        class="cluster-item"
                      >
                        <div class="sentence-header">
                          <span class="sentence-label">回答 {{ sentenceIndex + 1 }}</span>
                        </div>
                        <p class="sentence-content">{{ sentence }}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  import { ref, onMounted, watch, computed } from 'vue';
  import axios from 'axios';
  
  export default {
    name: 'ClusterAnalysis',
    props: {
      jsonData: Object
    },
    setup(props) {
      const clusterResults = ref(null);
      const loading = ref(false);
      const error = ref(null);
  
      // 计算最大聚类数量
      const maxClusterCount = computed(() => {
        if (!clusterResults.value) return 0;
        
        let max = 0;
        for (const pathKey in clusterResults.value) {
          for (const nodeKey in clusterResults.value[pathKey].nodes) {
            const nodeData = clusterResults.value[pathKey].nodes[nodeKey];
            const count = nodeData.cluster_count || nodeData.summaries.length;
            if (count > max) max = count;
          }
        }
        return max;
      });
  
      // 计算总节点数
      const getTotalNodesCount = () => {
        if (!clusterResults.value) return 0;
        
        let count = 0;
        for (const pathKey in clusterResults.value) {
          count += Object.keys(clusterResults.value[pathKey].nodes).length;
        }
        return count;
      };
  
      // 计算总聚类数
      const getTotalClustersCount = () => {
        if (!clusterResults.value) return 0;
        
        let count = 0;
        for (const pathKey in clusterResults.value) {
          for (const nodeKey in clusterResults.value[pathKey].nodes) {
            count += clusterResults.value[pathKey].nodes[nodeKey].summaries.length;
          }
        }
        return count;
      };
      
      // 计算平均每节点聚类数量
      const getAverageClusterCount = () => {
        const nodeCount = getTotalNodesCount();
        if (nodeCount === 0) return "0";
        
        const clusterCount = getTotalClustersCount();
        const avg = clusterCount / nodeCount;
        return avg.toFixed(1);
      };
      
      // 根据聚类数量获取颜色
      const getClusterColorStyle = (count) => {
        // 如果只有1个聚类，显示灰色
        if (count <= 1) {
          return { backgroundColor: '#a8998a' }; // 浅棕色
        }
        
        // 计算颜色比例 - 使用墨色系
        const max = Math.max(maxClusterCount.value, 5);
        const ratio = Math.min(count / max, 1);
        
        // 墨色系渐变 - 从浅墨色(少)到深墨色(多)
        if (ratio <= 0.5) {
          // 墨蓝到墨绿
          const b = Math.floor(139 - (ratio * 2) * (139 - 86));
          return { backgroundColor: `rgb(104, ${b}, 139)` }; // 从墨蓝到墨绿
        } else {
          // 墨绿到深墨色
          const g = Math.floor(86 - ((ratio - 0.5) * 2) * 40);
          const b = Math.floor(86 - ((ratio - 0.5) * 2) * 24);
          return { backgroundColor: `rgb(74, ${g}, ${b})` }; // 从墨绿到深墨色
        }
      };
  
      // 进行聚类分析
      const performClusterAnalysis = async () => {
        if (!props.jsonData || !props.jsonData.responses || props.jsonData.responses.length < 2) {
          error.value = "需要至少两个回答才能进行聚类分析";
          loading.value = false;
          return;
        }
  
        try {
          loading.value = true;
          error.value = null;
          
          // 调用后端API进行聚类分析
          const response = await axios.post('http://localhost:5000/api/cluster-analysis', {
            responses: props.jsonData.responses
          });
          
          if (response.data.error) {
            error.value = response.data.error;
          } else {
            clusterResults.value = response.data;
          }
        } catch (err) {
          console.error('聚类分析错误:', err);
          error.value = `聚类分析失败: ${err.message || '未知错误'}`;
        } finally {
          loading.value = false;
        }
      };
  
      // 监听jsonData变化
      watch(() => props.jsonData, (newVal) => {
        if (newVal) {
          performClusterAnalysis();
        }
      }, { immediate: true });
  
      // 组件挂载时执行
      onMounted(() => {
        if (props.jsonData) {
          performClusterAnalysis();
        }
      });
  
      return {
        clusterResults,
        loading,
        error,
        getTotalNodesCount,
        getTotalClustersCount,
        getAverageClusterCount,
        getClusterColorStyle,
        maxClusterCount
      };
    }
  };
  </script>
  
  <style scoped>
  .cluster-analysis-container {
    padding: 24px;
    background-color: #f5f3ef; /* 米黄色背景，类似宣纸 */
    border-radius: 8px;
  }
  
  .analysis-title {
    margin: 0 0 24px 0;
    color: #5d4037; /* 深棕色文字 */
    font-size: 1.5rem;
    font-weight: 600;
    text-align: center;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
    border-bottom: 2px solid #8c7a5b; /* 棕褐色边框 */
    padding-bottom: 8px;
  }
  
  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px;
  }
  
  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(104, 131, 139, 0.2); /* 墨蓝色透明 */
    border-radius: 50%;
    border-top-color: #68838b; /* 墨蓝色 */
    animation: spin 1s ease-in-out infinite;
    margin-bottom: 16px;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  .error-message {
    background-color: #f8efed; /* 浅砖红色背景 */
    color: #a98175; /* 砖红色文字 */
    padding: 16px;
    border-radius: 8px;
    border-left: 4px solid #a98175; /* 砖红色边框 */
    margin-bottom: 24px;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .no-data {
    background-color: #f0e9e2; /* 淡褐色背景 */
    padding: 24px;
    border-radius: 8px;
    text-align: center;
    color: #8c7a5b; /* 棕褐色文字 */
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
    border: 1px dashed #d3c8b4; /* 棕褐色虚线边框 */
  }
  
  .analysis-content {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }
  
  .summary-card {
    background: #f9f6f1; /* 浅米色背景 */
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    padding: 20px;
    border: 1px solid #d3c8b4; /* 棕褐色边框 */
  }
  
  .summary-card h3 {
    margin: 0 0 16px 0;
    color: #5d4037; /* 深棕色文字 */
    font-weight: 600;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .stats {
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
  }
  
  .stat-item {
    flex: 1;
    min-width: 150px;
    background: #f0e9e2; /* 淡褐色背景 */
    padding: 16px;
    border-radius: 8px;
    border: 1px solid #e8e0d8; /* 米黄色边框 */
  }
  
  .stat-label {
    color: #8c7a5b; /* 棕褐色文字 */
    font-size: 14px;
    display: block;
    margin-bottom: 8px;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .stat-value {
    color: #5d4037; /* 深棕色文字 */
    font-size: 24px;
    font-weight: 700;
  }
  
  .path-card {
    background: #f9f6f1; /* 浅米色背景 */
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    border: 1px solid #d3c8b4; /* 棕褐色边框 */
  }
  
  .path-header {
    background: #f0e9e2; /* 淡褐色背景 */
    padding: 16px 20px;
    border-bottom: 1px solid #e8e0d8; /* 米黄色边框 */
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .path-header h3 {
    margin: 0;
    color: #5d4037; /* 深棕色文字 */
    font-weight: 600;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .path-key {
    background: #e8e0d8; /* 米黄色背景 */
    color: #8c7a5b; /* 棕褐色文字 */
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .nodes-container {
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  
  .node-card {
    background: #f9f6f1; /* 浅米色背景 */
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #d3c8b4; /* 棕褐色边框 */
  }
  
  .node-header {
    background: #e8e0d8; /* 米黄色背景 */
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .node-header h4 {
    margin: 0;
    color: #5d4037; /* 深棕色文字 */
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .node-stats {
    font-size: 13px;
    color: #8c7a5b; /* 棕褐色文字 */
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .stats-divider {
    color: #d3c8b4; /* 棕褐色 */
  }
  
  .cluster-count {
    display: flex;
    align-items: center;
    gap: 5px;
    font-weight: 500;
  }
  
  .cluster-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
  }
  
  .cluster-visualization {
    padding: 16px;
  }
  
  .cluster-groups {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  
  .cluster-group {
    border: 1px solid #d3c8b4; /* 棕褐色边框 */
    border-radius: 8px;
    overflow: hidden;
  }
  
  .cluster-summary {
    background: #e8efe9; /* 浅墨绿色背景 */
    padding: 16px;
    border-bottom: 1px solid #d3c8b4; /* 棕褐色边框 */
  }
  
  .cluster-title {
    font-weight: 600;
    color: #4a6056; /* 墨绿色文字 */
    margin-bottom: 8px;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .cluster-summary p {
    color: #5d4037; /* 深棕色文字 */
    margin: 0;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .cluster-items {
    padding: 0 16px 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 16px;
  }
  
  .cluster-item {
    background: #f9f6f1; /* 浅米色背景 */
    border: 1px solid #e8e0d8; /* 米黄色边框 */
    border-radius: 6px;
    overflow: hidden;
  }
  
  .sentence-header {
    background: #f0e9e2; /* 淡褐色背景 */
    padding: 8px 12px;
    border-bottom: 1px solid #e8e0d8; /* 米黄色边框 */
  }
  
  .sentence-label {
    font-size: 13px;
    color: #8c7a5b; /* 棕褐色文字 */
    font-weight: 500;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .sentence-content {
    padding: 12px;
    margin: 0;
    color: #5d4037; /* 深棕色文字 */
    font-size: 14px;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  @media (max-width: 768px) {
    .stats {
      flex-direction: column;
      gap: 12px;
    }
    
    .stat-item {
      min-width: unset;
    }
  }
  </style>