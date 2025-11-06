<template>
    <div class="sankey-chart-container">
      <!-- 修改标题和搜索框布局 -->
      <div class="header-container">
        <!-- 让标题居中显示 -->
        <div class="title-container">
          <h3 class="visualization-title">回答-推理路径-关键词流向图</h3>
        </div>
        
        <!-- 搜索框添加放大镜图标 -->
        <div class="search-container">
          <!-- 添加搜索图标 -->
          <span class="search-icon">&#128269;</span>
          <input 
            type="text" 
            v-model="searchQuery" 
            placeholder="搜索节点内容..." 
            class="search-input"
            @input="handleSearch"
          />
          <button v-if="searchQuery" @click="clearSearch" class="clear-search-btn">×</button>
          <div v-if="searchResults.length > 0" class="search-results-count">
            找到 {{ searchResults.length }} 个匹配结果
          </div>
        </div>
      </div>
      
      <div class="chart-container">
        <!-- 添加时间轴容器，使用条件渲染 -->
        <div v-if="showTimeline && isTimeQuery" class="timeline-container">
          <div class="timeline-header">
            <h4>时间轴</h4>
            <button class="close-timeline-btn" @click="toggleTimeline">&times;</button>
          </div>
          <div ref="timelineChart" class="timeline-chart"></div>
        </div>
        
        <!-- 时间轴展开按钮，放在右侧 -->
        <div v-if="isTimeQuery && !showTimeline" class="timeline-expand-btn" @click="toggleTimeline">
          <span>查看时间轴</span>
        </div>
        
        <!-- 地点层次关系展开按钮，放在右侧 -->
        <div v-if="isLocationQuery && !showLocationHierarchy" class="location-expand-btn" @click="toggleLocationHierarchy">
          <span>显示地点层次关系</span>
        </div>
        
        <!-- 地点层次关系恢复按钮，在开启层次结构后显示 -->
        <div v-if="isLocationQuery && showLocationHierarchy" class="location-collapse-btn" @click="toggleLocationHierarchy">
          <span>恢复默认视图</span>
        </div>
        
        <div ref="sankeyChart" class="sankey-chart" :class="{ 'with-timeline': showTimeline && isTimeQuery }"></div>
        
        <!-- 浮层背景遮罩 -->
        <transition name="fade">
          <div v-if="showDetails" class="panel-overlay" @click="closeDetails"></div>
        </transition>
        
        <!-- 右侧弹出面板 - 添加left/right类控制位置 -->
        <transition name="slide-right" v-if="panelPosition === 'right'">
          <div v-if="showDetails" class="node-details-panel right-panel">
            <div class="panel-header">
              <h4>{{ selectedNodeLabel }}</h4>
              <button class="close-btn" @click="closeDetails">&times;</button>
            </div>
            <div class="panel-content">
              <!-- 1. 聚类节点详情 -->
              <div v-if="panelType === 'cluster'">
                <div class="summary-section">
                  <h5>聚类摘要</h5>
                  <p>{{ selectedNodeSummary }}</p>
                </div>
                
                <div class="responses-section">
                  <h5>聚类包含的回答 ({{ selectedNodeResponses.length }})</h5>
                  <div v-for="(response, index) in selectedNodeResponses" :key="index" class="response-item">
                    <div class="response-header">
                      <span class="response-label">回答 {{ response.responseIndex + 1 }}</span>
                    </div>
                    <p class="response-content">{{ response.content }}</p>
                  </div>
                </div>
              </div>
              
              <!-- 2. 完整LLM回答详情 -->
              <div v-else-if="panelType === 'response' && selectedLlmResponse">
                <div class="response-full">
                  <div v-if="selectedLlmResponse.总结" class="summary-section">
                    <h5>总结</h5>
                    <p>{{ selectedLlmResponse.总结 }}</p>
                  </div>
                  
                  <div v-if="selectedLlmResponse.最终结果" class="summary-section">
                    <h5>最终结果</h5>
                    <p>{{ selectedLlmResponse.最终结果 }}</p>
                  </div>
                  
                  <div v-if="selectedLlmResponse.事件背景概要" class="summary-section">
                    <h5>事件背景概要</h5>
                    <p>{{ selectedLlmResponse.事件背景概要 }}</p>
                  </div>
                  
                  <!-- 展示所有路径，使用计算属性过滤掉非路径数据 -->
                  <div class="paths-container">
                    <div v-for="pathKey in getPathKeys(selectedLlmResponse)" :key="pathKey" class="path-section">
                      <h5>{{ selectedLlmResponse[pathKey].标题 }}</h5>
                      
                      <div v-if="selectedLlmResponse[pathKey].节点" class="nodes-container">
                        <div v-for="(nodeContent, nodeKey) in selectedLlmResponse[pathKey].节点" :key="nodeKey" class="node-item">
                          <div class="node-header">{{ nodeKey }}</div>
                          <p class="node-content">{{ nodeContent }}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 3. 关键词相关回答详情 -->
              <div v-else-if="panelType === 'keyword'">
                <div class="keyword-section">
                  <h3>关键词: {{ selectedKeyword }}</h3>
                  <p class="keyword-desc">包含此关键词的回答总数: {{ keywordResponses.length }}</p>
                </div>
                
                <div class="responses-section">
                  <div v-for="(response, index) in keywordResponses" :key="index" class="response-item">
                    <div class="response-header">
                      <span class="response-label">回答 {{ response.responseIndex + 1 }}</span>
                    </div>
                    <div class="response-content">
                      <h5>推理逻辑与总结</h5>
                      <p>{{ response.summary }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>

        <!-- 左侧弹出面板 - 新增 -->
        <transition name="slide-left">
          <div v-if="showDetails && panelPosition === 'left'" class="node-details-panel left-panel">
            <div class="panel-header">
              <button class="close-btn" @click="closeDetails">&times;</button>
              <h4>{{ selectedNodeLabel }}</h4>
            </div>
            <div class="panel-content">
              <!-- 1. 聚类节点详情 -->
              <div v-if="panelType === 'cluster'">
                <div class="summary-section">
                  <h5>聚类摘要</h5>
                  <p>{{ selectedNodeSummary }}</p>
                </div>
                
                <div class="responses-section">
                  <h5>聚类包含的回答 ({{ selectedNodeResponses.length }})</h5>
                  <div v-for="(response, index) in selectedNodeResponses" :key="index" class="response-item">
                    <div class="response-header">
                      <span class="response-label">回答 {{ response.responseIndex + 1 }}</span>
                    </div>
                    <p class="response-content">{{ response.content }}</p>
                  </div>
                </div>
              </div>
              
              <!-- 2. 完整LLM回答详情 -->
              <div v-else-if="panelType === 'response' && selectedLlmResponse">
                <div class="response-full">
                  <div v-if="selectedLlmResponse.总结" class="summary-section">
                    <h5>总结</h5>
                    <p>{{ selectedLlmResponse.总结 }}</p>
                  </div>
                  
                  <div v-if="selectedLlmResponse.最终结果" class="summary-section">
                    <h5>最终结果</h5>
                    <p>{{ selectedLlmResponse.最终结果 }}</p>
                  </div>
                  
                  <div v-if="selectedLlmResponse.事件背景概要" class="summary-section">
                    <h5>事件背景概要</h5>
                    <p>{{ selectedLlmResponse.事件背景概要 }}</p>
                  </div>
                  
                  <!-- 展示所有路径，使用计算属性过滤掉非路径数据 -->
                  <div class="paths-container">
                    <div v-for="pathKey in getPathKeys(selectedLlmResponse)" :key="pathKey" class="path-section">
                      <h5>{{ selectedLlmResponse[pathKey].标题 }}</h5>
                      
                      <div v-if="selectedLlmResponse[pathKey].节点" class="nodes-container">
                        <div v-for="(nodeContent, nodeKey) in selectedLlmResponse[pathKey].节点" :key="nodeKey" class="node-item">
                          <div class="node-header">{{ nodeKey }}</div>
                          <p class="node-content">{{ nodeContent }}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- 3. 关键词相关回答详情 -->
              <div v-else-if="panelType === 'keyword'">
                <div class="keyword-section">
                  <h3>关键词: {{ selectedKeyword }}</h3>
                  <p class="keyword-desc">包含此关键词的回答总数: {{ keywordResponses.length }}</p>
                </div>
                
                <div class="responses-section">
                  <div v-for="(response, index) in keywordResponses" :key="index" class="response-item">
                    <div class="response-header">
                      <span class="response-label">回答 {{ response.responseIndex + 1 }}</span>
                    </div>
                    <div class="response-content">
                      <h5>推理逻辑与总结</h5>
                      <p>{{ response.summary }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>
      </div>
    </div>
  </template>
  
  <script>
  import { onMounted, onUnmounted, ref, watch } from 'vue';
  // 引入本地util中的echarts，作为备选
  import echarts from '../../utils/charts.js';
  import axios from 'axios';
  // 导入地址链工具
  import { loadAddrChainData, findAddressRecords, buildAddressHierarchy } from '../../utils/addrChainUtil';
  
  export default {
    name: 'SankeyChart',
    props: {
      jsonData: Object
    },
    setup(props) {
      const sankeyChart = ref(null);
      let sankey = null;
      const clusterResults = ref(null);
      const loading = ref(false);
      
      // 弹出面板状态
      const showDetails = ref(false);
      const selectedNodeLabel = ref('');
      const selectedNodeSummary = ref('');
      const selectedNodeResponses = ref([]);
      
      // 新增变量：处理不同类型节点的点击
      const panelType = ref('cluster'); // 'cluster', 'response', 'keyword'
      const selectedLlmResponse = ref(null);
      const selectedKeyword = ref('');
      const keywordResponses = ref([]);
      
      // 新增面板位置控制变量
      const panelPosition = ref('right');
      
      // 存储节点数据的映射
      const nodeDataMap = ref(new Map());
      
      // 在setup函数中添加以下变量和方法
      const searchQuery = ref('');
      const searchResults = ref([]);
      const originalNodeColors = ref(new Map()); // 存储原始节点颜色
      
      // 添加地址链相关状态
      const addrChainData = ref([]); // 存储地址链数据
      const locationHierarchy = ref(null); // 存储LLM分析后的地点层次结构
      
      // 标记是否为地点类型的查询
      const isLocationQuery = ref(false);
      
      // 标记是否为时间类型的查询
      const isTimeQuery = ref(false);
      
      // 时间轴相关状态
      const timelineChart = ref(null);
      let timeline = null;
      const showTimeline = ref(false);
      const timeData = ref([]);
      
      // 地点层次关系相关状态
      const showLocationHierarchy = ref(false);
      
      // 使用全局echarts对象或导入的备选对象
      const getEchartsInstance = () => {
        console.log('获取echarts实例');
        if (window.echarts) {
          console.log('使用全局echarts对象');
          return window.echarts;
        } else {
          console.log('使用导入的echarts对象');
          return echarts;
        }
      };
      
      // 计算每个回答的关键词集合
      const responseKeywords = () => {
        if (!props.jsonData?.responses) return [];
        
        return props.jsonData.responses.map((response, index) => {
          if (response.最终结果) {
            const keywords = response.最终结果.split(',').map(k => k.trim()).filter(k => k);
            return {
              index,
              keywords
            };
          }
          return { index, keywords: [] };
        });
      };
      
      // 获取排名前的关键词
      // 所有结果 最终结果 关键词频率统计
      const topKeywords = () => {
        if (!props.jsonData?.responses || props.jsonData.responses.length === 0) return [];
        
        const frequency = {};
        props.jsonData.responses.forEach(response => {
          if (response.最终结果) {
            const keywords = response.最终结果.split(',').map(k => k.trim());
            keywords.forEach(keyword => {
              if (keyword) {
                // 关键词频率计数
                frequency[keyword] = (frequency[keyword] || 0) + 1;
              }
            });
          }
        });
        
        const keywords = Object.entries(frequency)
          .map(([keyword, count]) => ({
            keyword,
            count,
            confidence: count / props.jsonData.responses.length
          }))
          .sort((a, b) => b.count - a.count)
          .slice(0, 10);
        
        return keywords;
      };
      
      // 获取聚类分析结果
      const getClusterAnalysisResults = async () => {
        if (!props.jsonData || !props.jsonData.responses || props.jsonData.responses.length < 2) {
          console.log("需要至少两个回答才能进行聚类分析");
          return null;
        }
  
        try {
          loading.value = true;
          
          // 调用后端API进行聚类分析
          const response = await axios.post('http://localhost:5000/api/cluster-analysis', {
            responses: props.jsonData.responses
          });
          
          if (response.data.error) {
            console.error(response.data.error);
            return null;
          } else {
            clusterResults.value = response.data;
            return response.data;
          }
        } catch (err) {
          console.error('聚类分析错误:', err);
          return null;
        } finally {
          loading.value = false;
        }
      };
      
      // 基于可信度返回颜色
      const getColorByConfidence = (confidence) => {
        if (confidence >= 0.8) return '#3F2E3E'; // 深紫色
        if (confidence >= 0.6) return '#5D4A5C'; // 中紫色
        if (confidence >= 0.4) return '#7B677A'; // 浅紫色
        if (confidence >= 0.2) return '#9A8699'; // 灰紫色
        return '#B8A6B7'; // 最浅紫色
      };
      
      // 初始化桑基图
      const initSankeyChart = () => {
        if (sankeyChart.value) {
          console.log('初始化桑基图容器');
          try {
            const echartsInstance = getEchartsInstance();
            console.log('使用的echarts版本:', echartsInstance.version || '未知');
            sankey = echartsInstance.init(sankeyChart.value);
            console.log('桑基图初始化成功');
          
          // 添加点击事件
          sankey.on('click', handleNodeClick);
          } catch (error) {
            console.error('初始化桑基图失败:', error);
          }
        }
      };
      
      // 处理节点点击事件 - 修改为处理多种类型的节点
      const handleNodeClick = (params) => {
        // 关闭已打开的面板
        showDetails.value = false;
        
        // 1. 处理中间聚类节点的点击 (P1-节点A-C0 格式)
        if (params.name.includes('-C')) {
          const nodeData = nodeDataMap.value.get(params.name);
          if (!nodeData) {
            console.log('未找到节点数据:', params.name);
            return;
          }
          
          // 更新选中节点的信息
          selectedNodeLabel.value = formatNodeName(params.name);
          selectedNodeSummary.value = nodeData.summary;
          selectedNodeResponses.value = nodeData.responses;
          panelType.value = 'cluster';
          panelPosition.value = 'right'; // 中间节点在右侧显示详情
          
          // 显示详情面板
          showDetails.value = true;
          return;
        }
        
        // 1.5 处理桥接节点的点击
        if (params.name === '孤立回答桥接') {
          const nodeData = nodeDataMap.value.get(params.name);
          if (!nodeData) {
            console.log('未找到桥接节点数据');
            return;
          }
          
          // 更新选中节点的信息
          selectedNodeLabel.value = '未包含在聚类中的回答';
          selectedNodeSummary.value = nodeData.summary;
          selectedNodeResponses.value = nodeData.responses;
          panelType.value = 'cluster'; // 复用聚类面板显示
          panelPosition.value = 'right'; // 桥接节点在右侧显示详情
          
          // 显示详情面板
          showDetails.value = true;
          return;
        }
        
        // 2. 处理左侧回答节点的点击 (回答1, 回答2 格式)
        if (params.name.startsWith('回答')) {
          const responseIndex = parseInt(params.name.replace('回答', '')) - 1;
          if (responseIndex < 0 || responseIndex >= props.jsonData.responses.length) {
            console.log('无效的回答索引:', responseIndex);
            return;
          }
          
          // 获取完整回答
          const fullResponse = props.jsonData.responses[responseIndex];
          
          // 更新选中节点的信息
          selectedNodeLabel.value = `回答 ${responseIndex + 1} 详情`;
          selectedLlmResponse.value = fullResponse;
          panelType.value = 'response';
          panelPosition.value = 'right'; // 左侧回答节点在右侧显示详情
          
          // 显示详情面板
          showDetails.value = true;
          return;
        }
        
        // 3. 处理地点层次结构节点的点击
        if (locationHierarchy.value && locationHierarchy.value.层次关系 && showLocationHierarchy.value) {
          // 检查是否是大地点（省级）
          const provinceMatch = locationHierarchy.value.层次关系.find(
            province => province.大地点 === params.name
          );
          
          if (provinceMatch) {
            // 收集所有属于该省的城市和小地点
            const allCities = [];
            const allSmallPlaces = [];
            
            provinceMatch.中级地点.forEach(city => {
              allCities.push(city.名称);
              if (city.包含 && Array.isArray(city.包含)) {
                allSmallPlaces.push(...city.包含);
              }
            });
            
            // 查找包含这些地点的回答
            const relatedResponses = [];
            
            props.jsonData.responses.forEach((response, index) => {
              if (!response.最终结果) return;
              
              const keywords = response.最终结果.split(',').map(k => k.trim());
              const matchedKeywords = keywords.filter(k => 
                allSmallPlaces.includes(k) || allCities.includes(k) || k === params.name
              );
              
              if (matchedKeywords.length > 0) {
                let summary = '';
                
                // 获取推理逻辑或总结
                if (response.总结) {
                  summary = response.总结;
                } else if (response.推理逻辑) {
                  summary = response.推理逻辑;
                } else {
                  summary = response.最终结果;
                }
                
                relatedResponses.push({
                  responseIndex: index,
                  keyword: matchedKeywords.join('、'),
                  summary: summary
                });
              }
            });
            
            if (relatedResponses.length === 0) {
              console.log('没有包含该省份地点的回答:', params.name);
              return;
            }
            
            // 更新选中节点的信息
            selectedNodeLabel.value = `${params.name}省相关地点`;
            selectedKeyword.value = `${params.name}`;
            keywordResponses.value = relatedResponses;
            panelType.value = 'keyword';
            panelPosition.value = 'left'; // 地点节点在左侧显示详情
            
            // 显示详情面板
            showDetails.value = true;
            return;
          }
          
          // 检查是否是中级地点（市级）
          let cityMatch = null;
          let parentProvince = null;
          
          for (const province of locationHierarchy.value.层次关系) {
            if (province.中级地点) {
              const city = province.中级地点.find(c => c.名称 === params.name);
              if (city) {
                cityMatch = city;
                parentProvince = province;
                break;
              }
            }
          }
          
          if (cityMatch && parentProvince) {
            // 收集该市下的所有小地点
            const smallPlaces = cityMatch.包含 || [];
            
            // 查找包含这些地点的回答
            const relatedResponses = [];
            
            props.jsonData.responses.forEach((response, index) => {
              if (!response.最终结果) return;
              
              const keywords = response.最终结果.split(',').map(k => k.trim());
              const matchedKeywords = keywords.filter(k => 
                smallPlaces.includes(k) || k === params.name
              );
              
              if (matchedKeywords.length > 0) {
                let summary = '';
                
                // 获取推理逻辑或总结
                if (response.总结) {
                  summary = response.总结;
                } else if (response.推理逻辑) {
                  summary = response.推理逻辑;
                } else {
                  summary = response.最终结果;
                }
                
                relatedResponses.push({
                  responseIndex: index,
                  keyword: matchedKeywords.join('、'),
                  summary: summary
                });
              }
            });
            
            if (relatedResponses.length === 0) {
              console.log('没有包含该市地点的回答:', params.name);
              return;
            }
            
            // 更新选中节点的信息
            selectedNodeLabel.value = `${params.name}市 (${parentProvince.大地点}省)`;
            selectedKeyword.value = `${params.name}`;
            keywordResponses.value = relatedResponses;
            panelType.value = 'keyword';
            panelPosition.value = 'left'; // 地点节点在左侧显示详情
            
            // 显示详情面板
            showDetails.value = true;
            return;
          }
        }
        
        // 4. 处理右侧关键词节点的点击
        const keyword = params.name;
        // 查找包含此关键词的所有回答
        const relatedResponses = [];
        
        props.jsonData.responses.forEach((response, index) => {
          if (response.最终结果 && response.最终结果.includes(keyword)) {
            let summary = '';
            
            // 获取推理逻辑或总结
            if (response.总结) {
              summary = response.总结;
            } else if (response.推理逻辑) {
              summary = response.推理逻辑;
            } else {
              // 如果没有找到专门的总结字段，使用最终结果
              summary = response.最终结果;
            }
            
            relatedResponses.push({
              responseIndex: index,
              keyword: keyword,
              summary: summary
            });
          }
        });
        
        if (relatedResponses.length === 0) {
          console.log('没有包含关键词的回答:', keyword);
          return;
        }
        
        // 更新选中节点的信息
        selectedNodeLabel.value = `包含 "${keyword}" 的回答`;
        selectedKeyword.value = keyword;
        keywordResponses.value = relatedResponses;
        panelType.value = 'keyword';
        panelPosition.value = 'left'; // 关键词节点在左侧显示详情
        
        // 显示详情面板
        showDetails.value = true;
      };
      
      // 关闭详情面板
      const closeDetails = () => {
        showDetails.value = false;
      };
      
      // 格式化节点名称
      const formatNodeName = (name) => {
        if (name.includes('-C')) {
          const parts = name.split('-');
          const pathNum = parts[0].substring(1);
          const nodeKey = parts[1];
          const clusterId = parts[2].substring(1);
          
          // 尝试获取路径和节点的实际名称
          let pathTitle = `路径${pathNum}`;
          if (clusterResults.value && clusterResults.value[`路径${pathNum}`]) {
            pathTitle = clusterResults.value[`路径${pathNum}`].title || pathTitle;
          }
          
          return `${pathTitle} - ${nodeKey} (聚类 ${Number(clusterId) + 1})`;
        }
        return name;
      };
      
      // 获取节点聚类的简短总结
      const getClusterSummary = (summary) => {
        if (!summary) return '无内容';
        
        const maxLength = 30;
        if (summary.length <= maxLength) return summary;
        return summary.substring(0, maxLength) + '...';
      };
      
      // 监听数据变化
      watch(() => props.jsonData, async () => {
        if (props.jsonData) {
          console.log('===== 数据更新, 重新绘制桑基图 =====');
          console.log('问题类型:', props.jsonData.q_type);
          console.log('查询实体:', props.jsonData.entity);
          
          // 检查是否为地点类型查询，并清空之前的分析结果
          isLocationQuery.value = false;
          locationHierarchy.value = null;
          showLocationHierarchy.value = false; // 重置地点层次关系显示状态
          
          // 检查是否为时间类型查询
          isTimeQuery.value = checkIfTimeQuery();
          
          // 如果是时间类型查询，提取时间数据
          if (isTimeQuery.value) {
            extractTimeData();
          }
          
          // 先检测是否为地点类型查询
          const isLocation = checkIfLocationQuery();
          console.log('检测到是否为地点类型:', isLocation);
          
          // 针对地点类型，确保加载地址链数据
          if (isLocationQuery.value && showLocationHierarchy.value && addrChainData.value.length === 0) {
            console.log('加载地址链数据');
            await fetchAddrChainData();
          }
          
          clusterResults.value = null; // 重置聚类结果
          showDetails.value = false; // 隐藏详情面板
          
          // 更新桑基图
          updateSankeyChart();
          
          // 如果是时间类型查询且已显示时间轴，则更新时间轴
          if (isTimeQuery.value && showTimeline.value) {
            updateTimelineChart();
          }
        }
      }, { deep: true });
      
      // 更新桑基图 - 使用路径聚类结果作为中间节点
      const updateSankeyChart = async () => {
        if (!sankey) {
          console.log('Sankey图表实例不存在，初始化图表');
          initSankeyChart();
          if (!sankey) {
            console.error('无法初始化Sankey图表');
            return;
          }
        }
        
        console.log('===== 开始更新桑基图, 基于聚类分析结果 =====');
        console.log('是否为地点类型查询:', isLocationQuery.value);
        console.log('是否显示地点层次关系:', showLocationHierarchy.value);
        
        // 清空节点映射
        nodeDataMap.value.clear();
        
        // 确保有聚类分析结果
        if (!clusterResults.value) {
          console.log('获取聚类分析结果');
          const results = await getClusterAnalysisResults();
          if (!results) {
            console.log('无法获取聚类分析结果');
            return;
          }
        }
        
        // 针对地点类型且需要显示层次关系时，确保加载地址链数据
        if (isLocationQuery.value && showLocationHierarchy.value && addrChainData.value.length === 0) {
          console.log('加载地址链数据');
          await fetchAddrChainData();
        }
        
        // 准备桑基图数据
        const nodes = [];
        const links = [];
        // 定义这些变量，防止未定义错误
        let locationNodeMap = new Map(); 
        let locationKeywordMap = new Map();
        
        // 创建节点名称到索引的映射
        const nodeNameToIndex = new Map();
        
        // 1. 添加左侧的回答节点
        const responsesCount = props.jsonData?.responses?.length || 0;
        for (let i = 0; i < responsesCount; i++) {
          const nodeName = `回答${i + 1}`;
          nodes.push({
            name: nodeName,
            itemStyle: {
              // 最左侧是棕色
              color: '#776156'
            }
          });
          nodeNameToIndex.set(nodeName, nodes.length - 1);
        }
        
        // 2. 基于聚类分析结果添加中间节点
        // 存储每个回答与聚类节点的映射关系
        const responseToClusterMap = new Map();
        const clusterNodeMap = new Map(); // 保存节点名称 -> 节点索引映射
        
        // 添加桥接节点 - 记录哪些回答需要桥接
        // 这里是最特殊情况的特殊处理，实际大概率不会出现
        const needsBridgeResponses = new Set();
        for (let i = 0; i < responsesCount; i++) {
          needsBridgeResponses.add(i); // 初始假设所有回答都需要桥接
        }
        
        // 按顺序获取所有路径
        const sortedPaths = Object.keys(clusterResults.value)
          .filter(key => key.startsWith('路径'))
          .sort((a, b) => {
            const aNum = parseInt(a.match(/\d+/)[0]);
            const bNum = parseInt(b.match(/\d+/)[0]);
            return aNum - bNum;
          });
        
        // 为每个路径的每个节点创建聚类节点
        sortedPaths.forEach(pathKey => {
          const pathData = clusterResults.value[pathKey];
          const pathNumber = pathKey.match(/\d+/)[0];
          
          // 按顺序处理节点
          const sortedNodes = Object.keys(pathData.nodes).sort();
          
          sortedNodes.forEach(nodeKey => {
            const nodeData = pathData.nodes[nodeKey];
            const clusters = nodeData.clusters;
            const summaries = nodeData.summaries;
            const sentences = nodeData.sentences;
            
            // 为每个聚类创建一个节点
            for (let clusterId = 0; clusterId < summaries.length; clusterId++) {
              // 创建聚类节点名称
              const clusterNodeName = `P${pathNumber}-${nodeKey}-C${clusterId}`;
              
              // 添加聚类节点
              const summary = summaries[clusterId];
              nodes.push({
                name: clusterNodeName,
                value: getClusterSummary(summary),
                itemStyle: {
                  // 使用青色表示中间节点
                  color: '#68838B'
                }
              });
              
              // 保存节点索引到映射
              nodeNameToIndex.set(clusterNodeName, nodes.length - 1);
              clusterNodeMap.set(clusterNodeName, nodes.length - 1);
              
              // 收集该聚类的所有回答
              const clusterResponses = [];
              
              // 找出属于这个聚类的所有回答索引
              for (let responseIdx = 0; responseIdx < clusters.length; responseIdx++) {
                if (clusters[responseIdx] === clusterId) {
                  if (!responseToClusterMap.has(responseIdx)) {
                    responseToClusterMap.set(responseIdx, new Map());
                  }
                  
                  // 保存路径节点映射
                  if (!responseToClusterMap.get(responseIdx).has(pathKey)) {
                    responseToClusterMap.get(responseIdx).set(pathKey, {});
                  }
                  
                  responseToClusterMap.get(responseIdx).get(pathKey)[nodeKey] = clusterNodeName;
                  
                  // 添加到该聚类的回答列表
                  clusterResponses.push({
                    responseIndex: responseIdx,
                    content: sentences[responseIdx]
                  });
                  
                  // 该回答已经有连接，从需要桥接的集合中移除
                  needsBridgeResponses.delete(responseIdx);
                }
              }
              
              // 保存节点详细信息到映射
              nodeDataMap.value.set(clusterNodeName, {
                pathNumber,
                nodeKey,
                clusterId,
                summary: summary,
                responses: clusterResponses
              });
            }
          });
        });
        
        // 3. 添加右侧的关键词节点
        const topKeywordsData = topKeywords();
        topKeywordsData.forEach(item => {
          const nodeName = item.keyword;
          nodes.push({
            name: nodeName,
            itemStyle: {
              color: getColorByConfidence(item.confidence)
            }
          });
          nodeNameToIndex.set(nodeName, nodes.length - 1);
        });
        
        // 4. 创建连接：回答 -> 第一层中间节点
        for (let i = 0; i < responsesCount; i++) {
          if (!responseToClusterMap.has(i)) continue;
          
          const responseName = `回答${i + 1}`;
          const responseClusterMap = responseToClusterMap.get(i);
          
          // 只连接到每个路径的第一个节点
          if (sortedPaths.length > 0) {
            const firstPath = sortedPaths[0];
            const firstPathNodeMap = responseClusterMap.get(firstPath) || {};
            
            for (const clusterNodeName of Object.values(firstPathNodeMap)) {
              // 确保源节点和目标节点都存在
              if (nodeNameToIndex.has(responseName) && nodeNameToIndex.has(clusterNodeName)) {
              links.push({
                source: responseName,
                target: clusterNodeName,
                value: 2,
                lineStyle: {
                  color: 'gradient',
                  opacity: 0.7
                }
              });
              } else {
                console.warn(`跳过无效连接: ${responseName} -> ${clusterNodeName}，节点不存在`);
              }
            }
          }
        }
        
        // 5. 创建连接：中间节点之间的流转
        for (let i = 0; i < responsesCount; i++) {
          if (!responseToClusterMap.has(i)) continue;
          
          const responseClusterMap = responseToClusterMap.get(i);
          
          // 遍历路径，连接顺序节点
          for (let pathIdx = 0; pathIdx < sortedPaths.length - 1; pathIdx++) {
            const currentPath = sortedPaths[pathIdx];
            const nextPath = sortedPaths[pathIdx + 1];
            
            if (!responseClusterMap.has(currentPath) || !responseClusterMap.has(nextPath)) continue;
            
            const currentPathNodes = responseClusterMap.get(currentPath);
            const nextPathNodes = responseClusterMap.get(nextPath);
            
            // 遍历当前路径的所有节点
            for (const [, currentClusterNodeName] of Object.entries(currentPathNodes)) {
              // 遍历下一个路径的所有节点
              for (const [, nextClusterNodeName] of Object.entries(nextPathNodes)) {
                // 确保源节点和目标节点都存在
                if (nodeNameToIndex.has(currentClusterNodeName) && nodeNameToIndex.has(nextClusterNodeName)) {
                links.push({
                  source: currentClusterNodeName,
                  target: nextClusterNodeName,
                  value: 1,
                  lineStyle: {
                    color: 'gradient',
                    opacity: 0.7
                  }
                });
                } else {
                  console.warn(`跳过无效连接: ${currentClusterNodeName} -> ${nextClusterNodeName}，节点不存在`);
                }
              }
            }
          }
        }
        
        // 6. 连接：最后一层节点 -> 关键词
        if (sortedPaths.length > 0) {
          const lastPath = sortedPaths[sortedPaths.length - 1];
          
          // 处理地点层次关系
          const locationKeywordMap = new Map(); // 小地点 -> 大地点的映射
          const locationNodeMap = new Map(); // 存储已添加的地点节点索引
          
          // 如果是地点查询并且开启了层次结构显示，分析地点层次结构
          if (isLocationQuery.value && showLocationHierarchy.value) {
            console.log('是地点类型查询，开启了层次结构显示，开始处理地点层次关系');
            
            // 对关键词进行地点层次分析
            if (!locationHierarchy.value) {
              // 分析地点层次关系
              const keywords = topKeywordsData.map(item => item.keyword);
              console.log('准备分析关键词的地点层次关系:', keywords);
              await analyzeLocationHierarchy(keywords);
            }
            
            // 如果有层次结构结果，创建地点层次节点
            if (locationHierarchy.value && locationHierarchy.value.层次关系) {
              console.log('已获取层次结构，开始创建层次节点');
              const hierarchy = locationHierarchy.value.层次关系;
              
              // 先添加所有省级节点
              hierarchy.forEach(province => {
                const largePlaceName = province.大地点;
                
                // 忽略朝代（通常在地址链数据中是最后一个大地址）
                if (['宋朝', '元朝', '明朝', '清朝', '唐朝', '汉朝', '隋朝', '晋朝', '魏朝', '周朝'].includes(largePlaceName)) {
                  console.log(`跳过朝代节点: ${largePlaceName}`);
                  return;
                }
                
                // 标准化地名，去除"省"、"市"等后缀
                let normalizedName = normalizeLocationName(largePlaceName);
                console.log(`创建省级节点: ${largePlaceName} -> 标准化为: ${normalizedName}`);
                
                // 添加省级节点（如果不存在）
                if (!locationNodeMap.has(normalizedName) && !nodeNameToIndex.has(normalizedName)) {
                  nodes.push({
                    name: normalizedName,
                    itemStyle: {
                      color: '#3f51b5', // 紫色系
                      borderWidth: 1
                      // borderColor: '#fff'
                    }
                  });
                  nodeNameToIndex.set(normalizedName, nodes.length - 1);
                  locationNodeMap.set(normalizedName, nodes.length - 1);
                  console.log(`  添加省级节点 ${normalizedName}, 索引: ${nodes.length - 1}`);
                } else if (nodeNameToIndex.has(normalizedName)) {
                  // 如果节点已经存在，更新locationNodeMap
                  locationNodeMap.set(normalizedName, nodeNameToIndex.get(normalizedName));
                }
              });
              
              // 再添加所有市级节点并连接到省级
              hierarchy.forEach(province => {
                const largePlaceName = province.大地点;
                
                // 忽略朝代
                if (['宋朝', '元朝', '明朝', '清朝', '唐朝', '汉朝', '隋朝', '晋朝', '魏朝', '周朝'].includes(largePlaceName)) {
                  return;
                }
                
                // 标准化省级地名
                const normalizedLargeName = normalizeLocationName(largePlaceName);
                
                // 确保省级节点存在于nodeNameToIndex中
                if (!nodeNameToIndex.has(normalizedLargeName)) {
                  console.warn(`省级节点不存在于索引中: ${normalizedLargeName}`);
                  return;
                }
                
                // 处理中级地点（市级）
                if (province.中级地点 && Array.isArray(province.中级地点)) {
                  province.中级地点.forEach(city => {
                    const midPlaceName = city.名称;
                    
                    // 标准化市级地名
                    const normalizedMidName = normalizeLocationName(midPlaceName);
                    console.log(`  处理市级节点: ${midPlaceName} -> 标准化为: ${normalizedMidName}`);
                    
                    // 跳过与省级地名相同的市级节点（例如"浙江省"和"浙江市"）
                    if (normalizedMidName === normalizedLargeName) {
                      console.log(`    跳过与省级地名相同的市级节点: ${normalizedMidName}`);
                      return;
                    }
                    
                    // 添加市级节点（如果不存在）
                    if (!locationNodeMap.has(normalizedMidName) && !nodeNameToIndex.has(normalizedMidName)) {
                      nodes.push({
                        name: normalizedMidName,
                        itemStyle: {
                          color: '#7FFFD4', // 蓝色系
                          borderWidth: 1
                          // borderColor: '#fff'
                        }
                      });
                      nodeNameToIndex.set(normalizedMidName, nodes.length - 1);
                      locationNodeMap.set(normalizedMidName, nodes.length - 1);
                      console.log(`    添加市级节点 ${normalizedMidName}, 索引: ${nodes.length - 1}`);
                    } else if (nodeNameToIndex.has(normalizedMidName)) {
                      // 如果节点已经存在，更新locationNodeMap
                      locationNodeMap.set(normalizedMidName, nodeNameToIndex.get(normalizedMidName));
                    }
                    
                    // 连接市级节点到省级节点
                    if (nodeNameToIndex.has(normalizedMidName) && nodeNameToIndex.has(normalizedLargeName)) {
                      links.push({
                        source: normalizedMidName,
                        target: normalizedLargeName,
                        value: 2, // 增加权重，使连接更粗
                        lineStyle: {
                          color: 'gradient',
                          opacity: 0.7
                        }
                      });
                      console.log(`    创建连接: ${normalizedMidName} -> ${normalizedLargeName}`);
                    } else {
                      console.warn(`    跳过无效连接: ${normalizedMidName} -> ${normalizedLargeName}，节点不存在`);
                    }
                    
                    // 处理县级地点（小地点）
                    if (city.包含 && Array.isArray(city.包含)) {
                      city.包含.forEach(smallPlace => {
                        // 标准化小地点名称
                        const normalizedSmallName = normalizeLocationName(smallPlace);
                        
                        // 跳过与市级或省级地名相同的小地点
                        if (normalizedSmallName === normalizedMidName || normalizedSmallName === normalizedLargeName) {
                          console.log(`      跳过与上级地名相同的小地点: ${normalizedSmallName}`);
                          return;
                        }
                        
                        // 记录小地点到大地点的映射关系
                        locationKeywordMap.set(smallPlace, { 
                          mid: normalizedMidName,
                          large: normalizedLargeName 
                        });
                        // 同时为标准化后的名称添加映射
                        if (smallPlace !== normalizedSmallName) {
                          locationKeywordMap.set(normalizedSmallName, { 
                            mid: normalizedMidName,
                            large: normalizedLargeName 
                          });
                        }
                        console.log(`      添加小地点映射: ${smallPlace}/${normalizedSmallName} -> ${normalizedMidName} -> ${normalizedLargeName}`);
                      });
                    }
                  });
                }
              });
              
              console.log('地点层次节点创建完成，创建了 ' + locationNodeMap.size + ' 个节点');
              console.log('小地点映射关系:', JSON.stringify(Array.from(locationKeywordMap.entries()), null, 2));
            }
          }
          
          // 处理关键词连接
          const handleKeywords = () => {
            // 根据是否为地点类型查询显示不同的日志
            if (isLocationQuery.value && showLocationHierarchy.value) {
              console.log('开始创建聚类节点到关键词的连接 (地点分析模式)');
            } else {
              console.log('开始创建聚类节点到关键词的连接');
            }
          
          responseKeywords().forEach(response => {
            if (!responseToClusterMap.has(response.index)) return;
            
            const responseClusterMap = responseToClusterMap.get(response.index);
            if (!responseClusterMap.has(lastPath)) return;
            
            const lastPathNodes = responseClusterMap.get(lastPath);
            
            // 对于该回答的每个关键词，连接到最后一层的节点
            response.keywords.forEach(keyword => {
              // 检查该关键词是否在topKeywords中
              const keywordObj = topKeywordsData.find(k => k.keyword === keyword);
              if (!keywordObj) return;
              
                // 只在调试模式下输出普通关键词处理信息，仅对地点类型
                if (process.env.NODE_ENV === 'development' && isLocationQuery.value) {
                  console.log(`处理关键词: ${keyword}`);
                }
                
                // 检查关键词节点是否存在
                if (!nodeNameToIndex.has(keyword)) {
                  console.warn(`关键词节点不存在: ${keyword}`);
                  return;
                }
                
                // 仅当是地点查询且开启了层次结构显示时，才进行地点关系判断
                if (isLocationQuery.value && showLocationHierarchy.value) {
                  // 检查该关键词是否有从属关系
                  if (locationKeywordMap.has(keyword) || locationKeywordMap.has(normalizeLocationName(keyword))) {
                    console.log(`  关键词 ${keyword} 是地点且有从属关系`);
                    // 获取该关键词的中级地点（使用标准化名称查询）
                    const normalizedKeyword = normalizeLocationName(keyword);
                    const locationInfo = locationKeywordMap.get(keyword) || locationKeywordMap.get(normalizedKeyword);
                    const midPlace = locationInfo.mid;
                    console.log(`  对应的中级地点: ${midPlace}`);
                    
                    // 如果中级地点已添加为节点，连接关键词到中级地点
                    if (locationNodeMap.has(midPlace) && nodeNameToIndex.has(midPlace)) {
                      console.log(`  创建到中级地点 ${midPlace} 的连接`);
                      
                      // 连接最后一层节点到关键词
                      for (const clusterNodeName of Object.values(lastPathNodes)) {
                                if (nodeNameToIndex.has(clusterNodeName)) {
                        links.push({
                          source: clusterNodeName,
                          target: keyword,
                          value: 1,
                          lineStyle: {
                            color: 'gradient',
                            opacity: 0.6
                          }
                        });
                      }
                      }
                      
                      // 连接关键词到中级地点
                      links.push({
                        source: keyword,
                        target: midPlace,
                        value: 2, // 增加权重，使连接更粗
                        lineStyle: {
                          color: 'gradient',
                          opacity: 0.5
                        }
                      });
                    } else {
                      // 如果中级地点未添加为节点，直接连接到最后一层节点
                      for (const clusterNodeName of Object.values(lastPathNodes)) {
                        if (nodeNameToIndex.has(clusterNodeName)) {
                          links.push({
                            source: clusterNodeName,
                            target: keyword,
                            value: 1,
                            lineStyle: {
                              color: 'gradient',
                              opacity: 0.6
                            }
                          });
                        }
                      }
                    }
                  } else {
                    // 该关键词没有从属关系，作为普通关键词处理
                    for (const clusterNodeName of Object.values(lastPathNodes)) {
                      if (nodeNameToIndex.has(clusterNodeName)) {
                        links.push({
                          source: clusterNodeName,
                          target: keyword,
                          value: 1,
                          lineStyle: {
                            color: 'gradient',
                            opacity: 0.6
                          }
                        });
                      }
                    }
                  }
                } else {
                  // 非地点类型查询或未开启层次结构显示，所有关键词都作普通处理
                  for (const clusterNodeName of Object.values(lastPathNodes)) {
                    if (nodeNameToIndex.has(clusterNodeName)) {
                      links.push({
                        source: clusterNodeName,
                        target: keyword,
                        value: 1,
                        lineStyle: {
                          color: 'gradient',
                          opacity: 0.6
                        }
                      });
                    }
                  }
                }
              });
            });
          };
          
          // 处理关键词连接
          handleKeywords();
        }

        // 7. 处理需要桥接的回答（没有任何连线的结果）
        if (needsBridgeResponses.size > 0) {
          // 添加一个桥接节点
          const bridgeNodeName = '孤立回答桥接';
          nodes.push({
            name: bridgeNodeName,
            value: '连接未包含在聚类分析中的回答',
            itemStyle: {
              color: '#ff7f0e' // 使用橙色表示桥接节点
            }
          });
          nodeNameToIndex.set(bridgeNodeName, nodes.length - 1);
          
          // 为每个需要桥接的回答创建连接
          needsBridgeResponses.forEach(responseIndex => {
            const responseName = `回答${responseIndex + 1}`;
            
            // 检查回答节点是否存在
            if (!nodeNameToIndex.has(responseName)) {
              console.warn(`回答节点不存在: ${responseName}`);
              return;
            }
            
            // 从回答连接到桥接节点
            links.push({
              source: responseName,
              target: bridgeNodeName,
              value: 1,
              lineStyle: {
                color: '#ff7f0e',
                opacity: 0.7,
                type: 'dashed'
              }
            });
            
            // 从桥接节点连接到关键词（如果有）
            const responseKeywordsList = responseKeywords().find(r => r.index === responseIndex);
            if (responseKeywordsList && responseKeywordsList.keywords.length > 0) {
              responseKeywordsList.keywords.forEach(keyword => {
                // 检查该关键词是否在topKeywords中
                const keywordObj = topKeywordsData.find(k => k.keyword === keyword);
                if (!keywordObj || !nodeNameToIndex.has(keyword)) return;
                
                // 连接到关键词
                links.push({
                  source: bridgeNodeName,
                  target: keyword,
                  value: 1,
                  lineStyle: {
                    color: '#ff7f0e',
                    opacity: 0.6,
                    type: 'dashed'
                  }
                });
              });
            }
            
            // 如果没有关键词连接，至少确保有一个连接，否则桑基图可能无法正常显示
            if (!responseKeywordsList || responseKeywordsList.keywords.length === 0) {
              // 尝试连接到任意一个关键词
              if (topKeywordsData.length > 0) {
                const firstKeyword = topKeywordsData[0].keyword;
                // 确保关键词节点存在
                if (nodeNameToIndex.has(firstKeyword)) {
                links.push({
                  source: bridgeNodeName,
                    target: firstKeyword,
                  value: 0.5, // 较小的值表示虚拟连接
                  lineStyle: {
                    color: '#ff7f0e',
                    opacity: 0.3,
                    type: 'dotted'
                  }
                });
                }
              }
            }
          });
          
          // 保存桥接节点信息
          nodeDataMap.value.set(bridgeNodeName, {
            isBridge: true,
            summary: '此节点连接了未包含在聚类分析中的回答。',
            responses: Array.from(needsBridgeResponses).map(index => ({
              responseIndex: index,
              content: props.jsonData.responses[index].最终结果 || '无内容'
            }))
          });
        }
        
        // 确保所有links中的source和target都是合法节点
        const validLinks = links.filter(link => {
          const sourceExists = nodeNameToIndex.has(link.source);
          const targetExists = nodeNameToIndex.has(link.target);
          
          if (!sourceExists) {
            console.warn(`无效的source节点: ${link.source}`);
          }
          if (!targetExists) {
            console.warn(`无效的target节点: ${link.target}`);
          }
          
          return sourceExists && targetExists;
        });
        
        // 确保有足够的连接，否则桑基图可能无法正常显示
        if (validLinks.length === 0 && nodes.length >= 2) {
          // 创建一个安全的连接
          const firstNodeName = nodes[0].name;
          const secondNodeName = nodes[1].name;
          validLinks.push({
            source: firstNodeName,
            target: secondNodeName,
            value: 1
          });
        }
        
        const option = {
          tooltip: {
            trigger: 'item',
            triggerOn: 'mousemove',
            formatter: function(params) {
              // 为桥接节点提供更详细的提示
              if (params.name === '孤立回答桥接') {
                return `桥接节点<br/>连接了${needsBridgeResponses.size}个未包含在聚类中的回答<br/><span style="color:#999;font-size:0.8em">(点击查看详情)</span>`;
              }
              // 为中间节点提供更详细的提示
              if (params.data && params.data.value && typeof params.data.value === 'string') {
                return `${params.name}<br/>${params.data.value}<br/><span style="color:#999;font-size:0.8em">(点击查看详情)</span>`;
              }
              // 左侧回答节点提示
              if (params.name.startsWith('回答')) {
                return `${params.name}<br/><span style="color:#999;font-size:0.8em">(点击查看完整回答)</span>`;
              }
              // 右侧关键词节点提示
              return `${params.name}<br/><span style="color:#999;font-size:0.8em">(点击查看包含此关键词的回答)</span>`;
            }
          },
          series: [{
            type: 'sankey',
            emphasis: {
              focus: 'adjacency'
            },
            nodeWidth: 30, // 节点宽度
            nodeGap: 8, // 节点之间的间距
            layoutIterations: 32, // 布局迭代次数
            left: '5%',
            right: '5%',
            nodeAlign: 'justify',
            levels: [
              { depth: 0, itemStyle: { color: '#5470c6' }, lineStyle: { color: 'source', opacity: 0.6 } },
              { depth: 1, itemStyle: { color: '#91cc75' }, lineStyle: { color: 'source', opacity: 0.6 } },
              { depth: 2, lineStyle: { color: 'target', opacity: 0.6 } }
            ],
            label: {
              position: 'right', // 节点标签位置
              fontFamily: '"KaiTi", "楷体", "STKaiti", "华文楷体", serif',
              fontSize: 14,
              color: '#5d4037',
              formatter: function(params) {
                // 对于桥接节点，显示完整名称
                if (params.name === '孤立回答桥接') {
                  return params.name;
                }
                // 对于聚类节点，使用更短的标签
                if (params.name.includes('-C')) {
                  const parts = params.name.split('-');
                  return `P${parts[0].substring(1)}-${parts[1]}-C${parts[2].substring(1)}`;
                }
                
                // 对于较长的名称进行截断
                if (params.name.length > 10) {
                  return params.name.substring(0, 10) + '...';
                }
                return params.name;
              }
            },
            lineStyle: {
              color: 'gradient', // 使用渐变色
              curveness: 0.5 // 曲率
            },
            data: nodes,
            links: validLinks
          }]
        };
        
        sankey.setOption(option);
        
        // 在完成桑基图渲染后打印节点和连接信息
        console.log('===== 桑基图渲染完成 =====');
        console.log('总节点数:', nodes.length);
        console.log('总连接数:', links.length);
        console.log('地点层次节点数:', locationNodeMap ? locationNodeMap.size : 0);
        
        // 导出数据用于调试
        window.debugData = {
          nodes,
          links,
          locationHierarchy: locationHierarchy.value,
          locationNodeMap,
          locationKeywordMap,
          isLocationQuery: isLocationQuery.value
        };
        console.log('调试数据已导出到 window.debugData');
      };
      
      // 切换时间轴显示状态
      const toggleTimeline = () => {
        showTimeline.value = !showTimeline.value;
        
        if (showTimeline.value) {
          // 延迟执行，确保DOM已更新
          setTimeout(() => {
            // 如果timeline已经存在，先销毁它
            if (timeline) {
              timeline.dispose();
              timeline = null;
            }
            
            // 重新初始化和更新时间轴
            initTimelineChart();
            updateTimelineChart();
            
            // 调整桑基图大小
            if (sankey) {
              sankey.resize();
            }
          }, 100);
        } else {
          // 时间轴关闭时，也需要调整桑基图大小
          setTimeout(() => {
            if (sankey) {
              sankey.resize();
            }
          }, 100);
        }
      };
      
      // 切换地点层次关系显示状态
      const toggleLocationHierarchy = () => {
        showLocationHierarchy.value = !showLocationHierarchy.value;
        console.log('切换地点层次关系状态:', showLocationHierarchy.value);
        
        // 如果显示层次关系且地址链数据为空，则需要先加载数据
        if (showLocationHierarchy.value && addrChainData.value.length === 0) {
          console.log('开始加载地址链数据');
          fetchAddrChainData().then(() => {
            // 数据加载完成后更新图表
            console.log('地址链数据加载完成，更新桑基图');
            updateSankeyChart();
          });
        } else {
          // 不管是开启还是关闭层次关系，都重新创建整个图表
          console.log('直接更新桑基图');
          // 清空已有的层次结构分析结果，强制重新分析
          if (!showLocationHierarchy.value) {
            locationHierarchy.value = null;
          }
          
          // 强制销毁并重建桑基图
          if (sankey) {
            sankey.dispose();
            sankey = null;
          }
          
          // 延迟执行，确保DOM已更新
          setTimeout(() => {
            initSankeyChart();
            updateSankeyChart();
            
            // 调整桑基图大小
            if (sankey) {
              sankey.resize();
            }
          }, 100);
        }
      };
      
      // 监听时间轴显示状态变化，并调整图表大小
      watch(() => showTimeline.value, (newVal) => {
        // 在过渡动画完成后重新调整图表大小
        setTimeout(() => {
          if (sankey) {
            sankey.resize();
          }
          if (newVal && timeline) {
            timeline.resize();
          }
        }, 300); // 给过渡动画足够的时间
      });
      
      // 监听地点层次结构显示状态变化
      watch(() => showLocationHierarchy.value, (newVal) => {
        console.log('地点层次结构显示状态变化:', newVal);
        // 等待DOM更新后调整图表
        setTimeout(() => {
          if (sankey) {
            sankey.resize();
          }
        }, 300);
      });
      
      // 对外暴露的更新方法 - 可供父组件调用
      const updateChart = () => {
        // 检查是否有可用的sankey实例，如果没有则初始化
        if (!sankey) {
          console.log('updateChart: 初始化桑基图实例');
          initSankeyChart();
        }
        
        console.log('updateChart: 更新桑基图和时间轴');
        // 更新桑基图
        updateSankeyChart();
        
        // 如果是时间类型查询且已显示时间轴，则更新时间轴
        if (isTimeQuery.value && showTimeline.value) {
          updateTimelineChart();
        }
        
        // 确保图表大小正确
        setTimeout(() => {
          if (sankey) {
            console.log('updateChart: 调整桑基图大小');
            sankey.resize();
          }
          if (timeline && showTimeline.value) {
            console.log('updateChart: 调整时间轴大小');
            timeline.resize();
          }
        }, 100);
      };
      
      // 添加到setup函数中的方法
      const getPathKeys = (response) => {
        if (!response) return [];
        return Object.keys(response)
          .filter(key => key.startsWith('路径') && response[key].标题)
          .sort((a, b) => {
            const aNum = parseInt(a.match(/\d+/)?.[0] || '0');
            const bNum = parseInt(b.match(/\d+/)?.[0] || '0');
            return aNum - bNum;
          });
      };
      
      // 组件挂载时初始化图表
      onMounted(() => {
        // 确保DOM渲染完成后再初始化图表
        setTimeout(async () => {
          console.log('初始化桑基图');
          initSankeyChart();
          if (props.jsonData) {
            // 检查是否为时间类型查询
            const isTime = checkIfTimeQuery();
            if (isTime) {
              console.log('初始化时检测到是时间类型查询');
              extractTimeData();
            }
            
            // 检查是否为地点类型查询，提前加载数据
            const isLocation = checkIfLocationQuery();
            console.log('初始化时检测到是否为地点类型:', isLocation);
            
            // 如果是地点类型且需要显示层次结构，预加载地址链数据
            if (isLocation && showLocationHierarchy.value && addrChainData.value.length === 0) {
              console.log('初始化时加载地址链数据');
              await fetchAddrChainData();
            }
            
            console.log('更新桑基图');
            updateSankeyChart();
          }
        }, 300); // 增加延迟时间
        
        window.addEventListener('resize', () => {
          sankey?.resize();
          timeline?.resize();
        });
      });
      
      // 组件卸载时清理
      onUnmounted(() => {
        sankey?.dispose();
        timeline?.dispose();
        
        window.removeEventListener('resize', () => {
          sankey?.resize();
          timeline?.resize();
        });
      });
      
      // 处理搜索
      const handleSearch = () => {
        // 清除之前的高亮效果
        restoreNodeColors();
        
        // 如果搜索关键词为空，则不执行搜索
        if (!searchQuery.value.trim()) {
          searchResults.value = [];
          return;
        }
        
        // 获取当前的搜索关键词
        const query = searchQuery.value.trim().toLowerCase();
        
        // 如果没有初始化桑基图，则不执行搜索
        if (!sankey) return;
        
        // 获取当前的option
        const option = sankey.getOption();
        const nodes = option.series[0].data;
        
        // 找到包含搜索词的节点
        const matchingNodes = [];
        
        nodes.forEach((node, index) => {
          let nodeText = '';
          
          // 检查节点名称
          if (node.name) {
            nodeText += node.name.toLowerCase();
          }
          
          // 检查节点值（用于中间节点的聚类摘要）
          if (node.value && typeof node.value === 'string') {
            nodeText += ' ' + node.value.toLowerCase();
          }
          
          // 检查节点对应的详细数据
          const nodeData = nodeDataMap.value.get(node.name);
          if (nodeData) {
            // 如果有摘要，添加到搜索文本中
            if (nodeData.summary) {
              nodeText += ' ' + nodeData.summary.toLowerCase();
            }
            
            // 如果有响应内容，添加到搜索文本中
            if (nodeData.responses && nodeData.responses.length > 0) {
              nodeData.responses.forEach(response => {
                if (response.content) {
                  nodeText += ' ' + response.content.toLowerCase();
                }
              });
            }
          }
          
          // 如果节点文本包含搜索关键词，则添加到结果中
          if (nodeText.includes(query)) {
            matchingNodes.push({
              index,
              name: node.name,
              originalColor: node.itemStyle ? node.itemStyle.color : null
            });
          }
        });
        
        // 更新搜索结果
        searchResults.value = matchingNodes;
        
        // 保存原始颜色并高亮匹配节点
        matchingNodes.forEach(node => {
          // 保存原始颜色
          if (node.originalColor) {
            originalNodeColors.value.set(node.index, node.originalColor);
          }
          
          // 设置高亮颜色
          option.series[0].data[node.index].itemStyle = {
            color: '#f50057', // 高亮颜色
            borderWidth: 2,
            borderColor: '#ffeb3b'
          };
        });
        
        // 应用更新的选项
        sankey.setOption(option);
      };
      
      // 恢复节点颜色
      const restoreNodeColors = () => {
        if (!sankey || originalNodeColors.value.size === 0) return;
        
        const option = sankey.getOption();
        
        // 恢复所有节点的原始颜色
        originalNodeColors.value.forEach((color, index) => {
          if (option.series[0].data[index]) {
            option.series[0].data[index].itemStyle = {
              color: color
            };
          }
        });
        
        // 清空颜色映射
        originalNodeColors.value.clear();
        
        // 应用更新的选项
        sankey.setOption(option);
      };
      
      // 清除搜索
      const clearSearch = () => {
        searchQuery.value = '';
        searchResults.value = [];
        restoreNodeColors();
      };
      
      // 新增的导出
      const fetchAddrChainData = async () => {
        try {
          // 使用导入的loadAddrChainData函数
          const data = await loadAddrChainData();
          addrChainData.value = data;
          console.log('已加载地址链数据:', data.length, '条记录');
          
          // 使用导入的buildAddressHierarchy函数构建本地层次结构
          const topKeywordsData = topKeywords();
          if (topKeywordsData.length > 0) {
            const keywords = topKeywordsData.map(item => item.keyword);
            const { hierarchy, smallToLarge } = buildAddressHierarchy(data, keywords);
            console.log('本地构建的地址层次结构:', hierarchy);
            console.log('小地点到大地点的映射:', smallToLarge);
          }
          
          return data;
        } catch (error) {
          console.error('加载地址链数据失败:', error);
          return [];
        }
      };
      
      // 分析地点层次关系
      const analyzeLocationHierarchy = async (keywords) => {
        if (!keywords || keywords.length === 0) return null;
        
        console.log('===== 开始分析地点层次关系 =====');
        console.log('输入关键词:', keywords);
        
        try {
          // 查找匹配的地址记录
          const matchedRecords = findAddressRecords(addrChainData.value, keywords);
          console.log('找到匹配的地址记录:', matchedRecords.length, '条');
          console.log('匹配记录详情:', JSON.stringify(matchedRecords, null, 2));
          
          // 调用后端API分析地点层次关系
          console.log('准备调用后端API...');
          const response = await axios.post('http://localhost:5000/api/analyze-location-hierarchy', {
            keywords: keywords.map(k => k.keyword || k),
            records: matchedRecords
          });
          
          console.log('API响应结果:', JSON.stringify(response.data, null, 2));
          
          // 验证响应数据格式
          let parsedData;
          try {
            // 如果response.data是字符串，尝试解析它
            if (typeof response.data === 'string') {
              parsedData = JSON.parse(response.data);
            } else {
              parsedData = response.data;
            }

            // 验证数据结构
            if (!parsedData || typeof parsedData !== 'object') {
              throw new Error('响应数据格式无效');
            }
          } catch (parseError) {
            console.error('解析响应数据失败:', parseError);
            return null;
          }
          
          if (parsedData.error) {
            console.error('分析地点层次关系失败:', parsedData.error);
            return null;
          }
          
          console.log('地点层次分析成功，结果:', JSON.stringify(parsedData, null, 2));
          locationHierarchy.value = parsedData;
          
          // 检查层次关系结构
          if (parsedData.层次关系 && Array.isArray(parsedData.层次关系)) {
            console.log('找到', parsedData.层次关系.length, '个省级地点');
            
            // 详细打印每个省级地点及其包含的城市
            parsedData.层次关系.forEach((province, i) => {
              console.log(`省级地点${i+1}: ${province.大地点}`);
              
              if (province.中级地点 && Array.isArray(province.中级地点)) {
                console.log(`- 包含${province.中级地点.length}个中级地点`);
                
                province.中级地点.forEach((city, j) => {
                  console.log(`  - 中级地点${j+1}: ${city.名称}`);
                  
                  if (city.包含 && Array.isArray(city.包含)) {
                    console.log(`    - 包含${city.包含.length}个小地点: ${city.包含.join(', ')}`);
                  } else {
                    console.log('    - 没有包含小地点');
                  }
                });
              } else {
                console.log('- 没有包含中级地点');
              }
            });
          } else {
            console.warn('响应中没有找到有效的层次关系结构');
          }
          
          console.log('===== 地点层次分析完成 =====');
          return parsedData;
        } catch (error) {
          console.error('分析地点层次关系发生错误:', error);
          return null;
        }
      };
      
      const checkIfLocationQuery = () => {
        if (!props.jsonData) return false;
        
        // 检查是否包含问题类型信息
        if (props.jsonData.q_type && props.jsonData.q_type === '地点') {
          console.log('检测到问题类型为"地点"');
          isLocationQuery.value = true;
          return true;
        }
        
        // 如果没有明确的问题类型，尝试从回答中推断
        if (props.jsonData.responses && props.jsonData.responses.length > 0) {
          // 检查第一个回答中是否包含地点相关的标志词
          const firstResponse = props.jsonData.responses[0];
          const locationKeywords = ['地点', '位置', '城市', '省份', '地区', '州'];
          
          if (firstResponse.总结) {
            const hasSummaryLocationHint = locationKeywords.some(keyword => 
              firstResponse.总结.includes(keyword)
            );
            if (hasSummaryLocationHint) {
              console.log('从回答总结中推断出问题类型可能是"地点"');
              isLocationQuery.value = true;
              return true;
            }
          }
        }
        
        console.log('未检测到问题类型为"地点"');
        isLocationQuery.value = false;
        return false;
      };
      
      // 检查是否为时间类型的查询
      const checkIfTimeQuery = () => {
        if (!props.jsonData) return false;
        
        // 检查是否包含问题类型信息
        if (props.jsonData.q_type && props.jsonData.q_type === '时间') {
          console.log('检测到问题类型为"时间"');
          isTimeQuery.value = true;
          return true;
        }
        
        // 如果没有明确的问题类型，尝试从回答中推断
        if (props.jsonData.responses && props.jsonData.responses.length > 0) {
          // 检查回答中是否包含时间相关的标志词或年份模式
          const timePatterns = [
            /\d{1,4}[-–—~]\d{1,4}/, // 时间范围匹配，如1079-1084
            /\d{3,4}年/, // 中文年份匹配，如1079年
            /公元前?\s?\d{1,4}/, // 公元前/后年份匹配
            /\d{1,4}世纪/, // 世纪匹配
            /\b\d{3,4}\b/ // 独立的年份数字
          ];
          
          // 检查前几个回答中是否包含时间模式
          const sampleResponses = props.jsonData.responses.slice(0, Math.min(3, props.jsonData.responses.length));
          
          for (const response of sampleResponses) {
            if (response.最终结果) {
              // 检查是否匹配时间模式
              const hasTimePattern = timePatterns.some(pattern => 
                pattern.test(response.最终结果)
              );
              
              if (hasTimePattern) {
                console.log('从回答中推断出问题类型可能是"时间"');
                isTimeQuery.value = true;
                return true;
              }
            }
          }
        }
        
        console.log('未检测到问题类型为"时间"');
        isTimeQuery.value = false;
        return false;
      };
      
      // 提取时间数据
      const extractTimeData = () => {
        if (!props.jsonData || !props.jsonData.responses) return;
        
        console.log('===== 开始提取时间数据 =====');
        timeData.value = [];
        
        const timeRangePattern = /(\d{1,4})[-–—~](\d{1,4})/;
        const singleYearPattern = /\b(\d{3,4})\b/;
        
        // 处理所有回答
        props.jsonData.responses.forEach((response, responseIndex) => {
          if (!response.最终结果) return;
          
          const keywords = response.最终结果.split(',').map(k => k.trim());
          
          // 遍历每个关键词，查找时间数据
          keywords.forEach(keyword => {
            // 尝试匹配时间范围（如1079-1084）
            const rangeMatch = keyword.match(timeRangePattern);
            if (rangeMatch) {
              const startYear = parseInt(rangeMatch[1]);
              const endYear = parseInt(rangeMatch[2]);
              
              // 确保开始年份小于结束年份
              const [smallYear, largeYear] = startYear <= endYear ? 
                [startYear, endYear] : [endYear, startYear];
              
              // 添加到时间数据
              timeData.value.push({
                type: 'range',
                start: smallYear,
                end: largeYear,
                source: {
                  responseIndex,
                  keyword
                },
                frequency: 1
              });
              
              console.log(`发现时间范围: ${smallYear}-${largeYear}, 来自回答${responseIndex + 1}`);
              return;
            }
            
            // 尝试匹配单个年份
            const yearMatch = keyword.match(singleYearPattern);
            if (yearMatch) {
              const year = parseInt(yearMatch[1]);
              
              // 检查这个年份是否已存在
              const existingYearIndex = timeData.value.findIndex(item => 
                item.type === 'single' && item.year === year
              );
              
              if (existingYearIndex >= 0) {
                // 已存在，增加频率
                timeData.value[existingYearIndex].frequency += 1;
                timeData.value[existingYearIndex].sources.push({
                  responseIndex,
                  keyword
                });
                console.log(`增加已有年份频率: ${year}, 现在频率为${timeData.value[existingYearIndex].frequency}`);
              } else {
                // 不存在，添加新的
                timeData.value.push({
                  type: 'single',
                  year,
                  sources: [{
                    responseIndex,
                    keyword
                  }],
                  frequency: 1
                });
                console.log(`添加新的年份: ${year}, 来自回答${responseIndex + 1}`);
              }
              return;
            }
          });
        });
        
        // 处理完毕后对时间数据进行排序
        timeData.value.sort((a, b) => {
          if (a.type === 'single' && b.type === 'single') {
            return a.year - b.year;
          } else if (a.type === 'range' && b.type === 'range') {
            // 先比较开始年份
            if (a.start !== b.start) {
              return a.start - b.start;
            }
            // 如果开始年份相同，比较结束年份
            return a.end - b.end;
          } else if (a.type === 'single') {
            // 单个年份与范围比较，使用单个年份与范围开始年份比较
            return a.year - b.start;
          } else {
            // 范围与单个年份比较
            return a.start - b.year;
          }
        });
        
        console.log('提取的时间数据:', timeData.value);
        console.log('===== 时间数据提取完成 =====');
        
        // 合并相同时间范围的数据
        mergeIdenticalTimeRanges();
      };
      
      // 合并完全相同的时间范围
      const mergeIdenticalTimeRanges = () => {
        if (timeData.value.length <= 1) return;
        
        console.log('===== 开始合并相同时间范围 =====');
        const merged = [];
        
        // 遍历所有时间范围数据
        for (let i = 0; i < timeData.value.length; i++) {
          const current = timeData.value[i];
          
          // 对于范围类型，查找完全相同的范围并合并
          if (current.type === 'range') {
            const existingIndex = merged.findIndex(item => 
              item.type === 'range' && 
              item.start === current.start && 
              item.end === current.end
            );
            
            if (existingIndex >= 0) {
              // 已存在相同范围，增加频率
              merged[existingIndex].frequency += current.frequency;
              if (current.source) {
                if (!merged[existingIndex].sources) {
                  merged[existingIndex].sources = [current.source];
                } else {
                  merged[existingIndex].sources.push(current.source);
                }
              }
              console.log(`合并时间范围: ${current.start}-${current.end}, 频率增加到${merged[existingIndex].frequency}`);
            } else {
              // 转换单个source为sources数组
              if (current.source && !current.sources) {
                current.sources = [current.source];
                delete current.source;
              }
              merged.push(current);
            }
          } else {
            // 单个年份类型保持不变
            merged.push(current);
          }
        }
        
        timeData.value = merged;
        console.log('合并后的时间数据:', timeData.value);
        console.log('===== 合并时间范围完成 =====');
      };
      
      // 初始化时间轴图表
      const initTimelineChart = () => {
        if (!timelineChart.value) return;
        
        console.log('初始化时间轴图表');
        try {
          const echartsInstance = getEchartsInstance();
          // 销毁现有实例
          if (timeline) {
            timeline.dispose();
          }
          
          // 创建新实例时设置溢出可见
          timeline = echartsInstance.init(timelineChart.value, null, {
            renderer: 'canvas',
            useDirtyRect: false,
            devicePixelRatio: window.devicePixelRatio,
            overflow: 'visible' // 允许内容溢出容器
          });
          console.log('时间轴图表初始化成功');
          
          // 添加点击事件
          timeline.on('click', handleTimelineClick);
        } catch (error) {
          console.error('初始化时间轴图表失败:', error);
        }
      };
      
      // 处理时间轴点击事件
      const handleTimelineClick = (params) => {
        console.log('时间轴点击事件:', params);
        // 这里可以添加时间轴点击的处理逻辑
      };
      
      // 更新时间轴图表
      const updateTimelineChart = () => {
        if (!timelineChart.value) {
          console.log('时间轴DOM元素不存在，无法更新时间轴');
          return;
        }
        
        if (!timeline) {
          initTimelineChart();
          if (!timeline) return;
        }
        
        console.log('更新时间轴图表');
        
        if (timeData.value.length === 0) {
          console.log('没有时间数据可显示');
          return;
        }
        
        // 计算时间轴的数据范围
        let minYear = Number.MAX_SAFE_INTEGER;
        let maxYear = Number.MIN_SAFE_INTEGER;
        
        timeData.value.forEach(item => {
          if (item.type === 'single') {
            minYear = Math.min(minYear, item.year);
            maxYear = Math.max(maxYear, item.year);
          } else {
            minYear = Math.min(minYear, item.start);
            maxYear = Math.max(maxYear, item.end);
          }
        });
        
        // 稍微扩大范围，增加显示空间
        minYear = Math.max(1, minYear - 10);
        maxYear = maxYear + 10;
        
        // 创建图表系列数据
        const series = [];

        const rangeData = timeData.value.filter(item => item.type === 'range');
        const singleYearData = timeData.value.filter(item => item.type === 'single');

        // 提取所有年份并排序
        const allYearPoints = new Set();
        rangeData.forEach(item => {
          allYearPoints.add(item.start);
          allYearPoints.add(item.end);
        });
        const sortedYears = [...allYearPoints].sort((a, b) => a - b);

        // 年份占位偏移逻辑
        const yearUsageCount = {};
        sortedYears.forEach(year => {
          yearUsageCount[year] = 0;
        });

        // 处理线段
        rangeData.forEach((range, idx) => {
          const lineWidth = 2 + range.frequency * 2;
          const alpha = 0.5 + Math.min(range.frequency * 0.1, 0.5);
          // const color = `rgba(24, 144, 255, ${alpha})`;
          
          // 水墨风格颜色数组，根据索引选择不同颜色
          const inkColors = [
            { light: 'rgba(76, 54, 38, 0.2)', dark: `rgba(76, 54, 38, ${alpha})` }, // 深墨棕
            { light: 'rgba(68, 88, 75, 0.2)', dark: `rgba(68, 88, 75, ${alpha})` }, // 墨绿
            { light: 'rgba(84, 63, 94, 0.2)', dark: `rgba(84, 63, 94, ${alpha})` }, // 墨紫
            { light: 'rgba(88, 65, 54, 0.2)', dark: `rgba(88, 65, 54, ${alpha})` }, // 赭石色
            { light: 'rgba(62, 73, 88, 0.2)', dark: `rgba(62, 73, 88, ${alpha})` }  // 墨青
          ];
          
          // 根据索引循环选择颜色
          const colorIndex = idx % inkColors.length;
          const selectedColor = inkColors[colorIndex];
          
          // 边框和强调色
          const borderColor = selectedColor.dark.replace(/${alpha}/, '1');
          
          const startIndex = sortedYears.indexOf(range.start);
          const endIndex = sortedYears.indexOf(range.end);

          const startOffset = (yearUsageCount[range.start] + 0.5) * 0.3;
          const endOffset = (yearUsageCount[range.end] - 0.5) * 0.3;

          const startX = startIndex + startOffset;
          const endX = endIndex + endOffset;

          // 可见线段
          series.push({
            type: 'line',
            name: `时间范围${idx + 1}`,
            data: [
              [startX, range.start],
              [endX, range.end]
            ],
            lineStyle: {
              width: lineWidth,
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 1,
                y2: 0,
                colorStops: [
                  { offset: 0, color: selectedColor.light }, // 根据索引选择不同深浅的起点颜色
                  { offset: 1, color: selectedColor.dark }   // 根据索引选择不同深浅的终点颜色
                ]
              },
              shadowBlur: 8,
              shadowColor: selectedColor.dark.replace(/${alpha}/, '0.3'),
              cap: 'round'
            },
            symbol: 'emptyCircle', // 改为空心圆，更有水墨风格感
            symbolSize: 6 + range.frequency * 2,
            itemStyle: {
              color: '#d9cdbf', // 将背景色改为更深的米色，与水墨风格更匹配
              borderColor: borderColor, // 根据线条颜色设置边框
              borderWidth: 1 + Math.min(range.frequency * 0.5, 2) // 根据频率增加边框粗细
            },
            emphasis: {
              lineStyle: {
                width: lineWidth + 2,
                shadowBlur: 15,
                shadowColor: borderColor,
                color: borderColor
              },
              itemStyle: {
                color: '#bcaa94', // 悬停时更深的填充色
                borderColor: borderColor,
                borderWidth: 2 + Math.min(range.frequency * 0.5, 2)
              }
            },
            tooltip: {
              show: true
            },
            silent: false,
            hoverAnimation: true,
            triggerLineEvent: true,
            zlevel: 2
          });

          yearUsageCount[range.start]++;
          yearUsageCount[range.end]++;
        });

        // 处理散点
        if (singleYearData.length > 0) {
          const scatterData = singleYearData.map((item) => {
            const size = 10 + item.frequency * 3;
            const alpha = 0.7 + Math.min(item.frequency * 0.1, 0.3);
            // 更有水墨韵味的颜色
            const baseColor = '#4C3626'; // 深墨棕色
            
            return {
              value: [-0.5, item.year], // 位置调整得更靠左，从-0.15改为-0.5
              itemStyle: {
                color: '#d9cdbf', // 更深的米灰色
                borderColor: baseColor,
                borderWidth: 1 + Math.min(item.frequency * 0.5, 2), // 根据频率调整边框粗细
                shadowBlur: 5,
                shadowColor: `rgba(76, 54, 38, ${alpha})`
              },
              symbolSize: size,
              symbol: 'circle' // 实心圆
            };
          });

          series.push({
            type: 'scatter',
            name: '单一年份',
            data: scatterData,
            emphasis: {
              scale: true,
              itemStyle: {
                color: '#bcaa94', // 悬停时更深的填充色
                borderColor: '#4C3626',
                borderWidth: 3,
                shadowBlur: 15,
                shadowColor: 'rgba(76, 54, 38, 0.8)'
              }
            }
          });
        }

        // 构建完整 option
        const option = {
          grid: {
            left: 50,
            right: 20,
            top: 30,
            bottom: 50,
            containLabel: true
          },
          tooltip: {
            trigger: 'item',
            confine: false,
            position: function (point, params, dom, rect, size) {
              const [x, y] = point;
              const [w, h] = size.viewSize;
              return [
                x + 200 > w ? x - 150 : x + 20,
                y + 100 > h ? y - 80 : y + 10
              ];
            },
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            borderColor: '#ddd',
            borderWidth: 1,
            textStyle: {
              color: '#5d4037', // 深棕色文字，与总体风格一致
              fontSize: 13,
              fontFamily: '"STKaiti", "FangSong", serif' // 使用楷体或仿宋字体
            },
            extraCssText: 'box-shadow: 0 2px 12px rgba(0,0,0,0.1);',
            
            // 全局Formatter 交互文本框格式修改
            formatter: function (params) {
              if (params.componentSubType === 'line') {
                if (params.seriesName?.startsWith('时间范围')) {
                  const idx = parseInt(params.seriesName.replace('时间范围', '')) - 1;
                  const data = rangeData[idx];
                  return `
                    <div style="font-weight:bold;margin-bottom:5px;color:#5d4037;">时间范围: ${data.start}—${data.end}</div>
                    <div>出现次数: ${data.frequency}</div>
                    ${data.sources ? `<div style="margin-top:5px;font-size:12px;color:#8d6e63;">来自 ${data.sources.length} 个回答</div>` : ''}
                  `;
                }
                // 显示线段端点时
                if (params.dataIndex !== undefined) {
                  const year = params.data[1];
                  const relevantRanges = rangeData.filter(range =>
                    range.start === year || range.end === year
                  );
                  const totalFrequency = relevantRanges.reduce((sum, r) => sum + r.frequency, 0);
                  return `
                    <div style="font-weight:bold;margin-bottom:5px;color:#5d4037;">年份: ${year}</div>
                    <div>出现次数: ${totalFrequency}</div>
                    <div style="margin-top:5px;font-size:12px;color:#8d6e63;">
                      包含在 ${relevantRanges.length} 个时间范围中
                    </div>`;
                }
              } else if (params.componentSubType === 'scatter') {
                const data = singleYearData[params.dataIndex];
                return `
                  <div style="font-weight:bold;margin-bottom:5px;color:#5d4037;">年份: ${data.year}</div>
                  <div>出现次数: ${data.frequency}</div>
                  ${data.sources ? `<div style="margin-top:5px;font-size:12px;color:#8d6e63;">来自 ${data.sources.length} 个回答</div>` : ''}
                `;
              }
              return '';
            }

          },
          toolbox: {
            feature: {
              dataZoom: { yAxisIndex: 'none' },
              restore: {},
              saveAsImage: {}
            },
            top: 10,
            right: 10,
            iconStyle: {
              borderColor: '#4C3626' // 深墨棕色
            },
            emphasis: {
              iconStyle: {
                borderColor: '#4C3626',
                color: '#4C3626'
              }
            }
          },
          xAxis: {
            type: 'value',
            show: false
          },
          yAxis: {
            type: 'value',
            name: '年份',
            min: minYear,
            max: maxYear,
            nameTextStyle: {
              color: '#5d4037', // 深棕色文字
              fontSize: 14, // 从12增大到14
              fontWeight: 'bold', // 加粗
              fontFamily: '"STKaiti", "FangSong", serif' // 使用楷体或仿宋字体
            },
            axisLine: {
              lineStyle: {
                color: '#a1887f', // 浅棕色
                width: 2 // 增加轴线宽度
              }
            },
            splitLine: {
              show: true,
              lineStyle: {
                color: '#efebe9', // 极浅棕色
                type: 'dashed'
              }
            },
            axisLabel: {
              color: '#6d4c41', // 中棕色
              fontSize: 14, // 从默认的12增大到14
              fontWeight: 'bold', // 加粗
              fontFamily: '"STKaiti", "FangSong", serif' // 使用楷体或仿宋字体
            }
          },
          series: series
        };

        
        timeline.setOption(option);
      };
      
      // 添加标准化地名的工具函数
      const normalizeLocationName = (name) => {
        // 添加空值和类型检查
        if (!name || typeof name !== 'string') {
          console.warn('normalizeLocationName 收到无效的地名:', name);
          return '';
        }
        
        // 移除省、市、县、区、府等后缀
        let result = name.replace(/省$|市$|县$|区$|府$/, '');
        
        // 特殊情况处理
        if (result === '临安' && name === '临安府') {
          result = '临安';
        }
        
        return result;
      };
      
      return {
        sankeyChart,
        timelineChart,
        updateChart,
        showDetails,
        selectedNodeLabel,
        selectedNodeSummary,
        selectedNodeResponses,
        closeDetails,
        panelType,
        selectedLlmResponse,
        selectedKeyword,
        keywordResponses,
        getPathKeys,
        searchQuery,
        searchResults,
        handleSearch,
        clearSearch,
        panelPosition,
        // 新增的导出
        addrChainData,
        locationHierarchy,
        isLocationQuery,
        isTimeQuery,
        showTimeline,
        toggleTimeline,
        showLocationHierarchy,
        toggleLocationHierarchy,
        fetchAddrChainData,
        analyzeLocationHierarchy,
        checkIfLocationQuery,
        normalizeLocationName
      };
    }
  };
  </script>
  
  <style scoped>
  .sankey-chart-container {
    background: #f5f3ef;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    padding: 20px;
    height: 100%;
    display: flex;
    flex-direction: column;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .header-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    flex-wrap: wrap;
    position: relative;
  }
  
  .title-container {
    flex: 1;
    text-align: center;
  }
  
  .visualization-title {
    margin: 0;
    color: #5d4037; /* 深棕色文字 */
    font-size: 1.1rem;
    font-weight: 600;
    text-align: center;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .chart-container {
    flex: 1;
    display: flex;
    position: relative;
  }
  
  .sankey-chart {
    flex: 1;
    min-height: 500px;
    width: 100%;
    transition: all 0.3s ease;
  }
  
  /* 时间轴相关样式 */
  .timeline-controls {
    position: absolute;
    right: 320px;
    z-index: 5;
  }
  
  .timeline-toggle-btn {
    background-color: #1890ff;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 12px;
    cursor: pointer;
    transition: background-color 0.3s;
  }
  
  .timeline-toggle-btn:hover {
    background-color: #096dd9;
  }
  
  .timeline-container {
    position: absolute;
    top: 0;
    right: 0;
    width: 500px;
    height: 100%;
    z-index: 4;
    box-shadow: -2px 0 8px rgba(0, 0, 0, 0.1);
    border-radius: 8px 0 0 8px;
    display: flex;
    flex-direction: column;
    overflow: visible; /* 允许内容溢出，确保tooltip可见 */
    transition: all 0.3s ease;
    border-left: 1px solid #e4e7ed; /* 添加左边框 */
    background-color: #f5f3ef;
  }
  
  .timeline-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 15px;
    background-color: #f5f3ef;
    border-bottom: 1px solid #e4e7ed;
    z-index: 5; /* 确保标题在tooltip之下 */
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体，与整体风格统一 */
  }
  
  .timeline-header h4 {
    margin: 0;
    font-size: 14px;
    color: #5d4037; /* 改为深棕色文字，与整体风格统一 */
    font-weight: bold;
  }
  
  .close-timeline-btn {
    background: none;
    border: none;
    color: #909399;
    font-size: 18px;
    cursor: pointer;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: all 0.2s;
  }
  
  .close-timeline-btn:hover {
    background-color: rgba(144, 147, 153, 0.1);
    color: #606266;
  }
  
  .timeline-chart {
    flex: 1;
    width: 100%;
    height: 100%;
    position: relative; /* 创建新的层叠上下文 */
    overflow: visible; /* 允许内容溢出，确保tooltip可见 */
  }
  
  /* 右侧展开按钮 */
  .timeline-expand-btn {
    position: absolute;
    right: 0;
    top: 40%;
    transform: translateY(-50%);
    background-color: #3f51b5; /* 修改为与地点层次按钮一致的颜色 */
    color: white;
    border-radius: 4px 0 0 4px;
    padding: 10px 6px;
    font-size: 12px;
    cursor: pointer;
    z-index: 3;
    display: flex;
    align-items: center;
    writing-mode: vertical-lr;
    letter-spacing: 1px;
    box-shadow: -2px 0 5px rgba(0, 0, 0, 0.1);
    transition: all 0.3s;
  }
  
  .timeline-expand-btn:hover {
    background-color: #3f51b5; /* 与地点层次按钮一致的悬停颜色 */
    padding-right: 10px;
  }
  
  /* 地点层次关系展开按钮 */
  .location-expand-btn {
    position: absolute;
    right: 0;
    top: 60%;
    transform: translateY(-50%);
    background-color: #3f51b5;
    color: white;
    border-radius: 4px 0 0 4px;
    padding: 10px 6px;
    font-size: 12px;
    cursor: pointer;
    z-index: 3;
    display: flex;
    align-items: center;
    writing-mode: vertical-lr;
    letter-spacing: 1px;
    box-shadow: -2px 0 5px rgba(0, 0, 0, 0.1);
    transition: all 0.3s;
  }
  
  .location-expand-btn:hover {
    background-color: #303f9f;
    padding-right: 10px;
  }
  
  /* 地点层次关系恢复按钮，在开启层次结构后显示 */
  .location-collapse-btn {
    position: absolute;
    right: 0;
    top: 60%;
    transform: translateY(-50%);
    background-color: #3f51b5;
    color: white;
    border-radius: 4px 0 0 4px;
    padding: 10px 6px;
    font-size: 12px;
    cursor: pointer;
    z-index: 3;
    display: flex;
    align-items: center;
    writing-mode: vertical-lr;
    letter-spacing: 1px;
    box-shadow: -2px 0 5px rgba(0, 0, 0, 0.1);
    transition: all 0.3s;
  }
  
  .location-collapse-btn:hover {
    background-color: #303f9f;
    padding-right: 10px;
  }
  
  /* 背景遮罩 */
  .panel-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.1);
    z-index: 5;
    backdrop-filter: blur(1px);
    cursor: pointer;
  }
  
  /* 节点详情面板样式 */
  .node-details-panel {
    position: absolute;
    top: 0;
    width: 290px;
    height: 100%;
    background: rgba(255, 255, 255, 0.98);
    backdrop-filter: blur(3px);
    box-shadow: 0 0 15px rgba(0, 0, 0, 0.15);
    z-index: 10;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  
  /* 右侧面板样式 */
  .right-panel {
    right: 0;
    box-shadow: -3px 0 15px rgba(0, 0, 0, 0.15);
    border-radius: 8px 0 0 8px;
  }
  
  /* 左侧面板样式 */
  .left-panel {
    left: 0;
    box-shadow: 3px 0 15px rgba(0, 0, 0, 0.15);
    width: 320px; /* 左侧面板可以稍宽一些，因为关键词详情可能较多 */
    border-radius: 0 8px 8px 0;
  }
  
  /* 对左侧面板的头部进行反向布局 */
  .left-panel .panel-header {
    flex-direction: row-reverse;
  }
  
  .left-panel .panel-header .close-btn {
    margin-left: 0;
    margin-right: 10px;
  }
  
  .panel-header {
    background: #f5f7fa;
    padding: 12px 16px;
    border-bottom: 1px solid #e4e7ed;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: relative;
  }
  
  .panel-header h4 {
    margin: 0;
    font-size: 16px;
    color: #303133;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 220px;
  }
  
  .close-btn {
    background: none;
    border: none;
    color: #909399;
    font-size: 20px;
    cursor: pointer;
    padding: 0;
    margin-left: 10px;
    transition: all 0.2s ease;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
  }
  
  .close-btn:hover {
    color: #409eff;
    background-color: rgba(64, 158, 255, 0.1);
  }
  
  .panel-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    transition: all 0.3s ease;
  }
  
  /* 背景遮罩淡入淡出 */
  .fade-enter-active,
  .fade-leave-active {
    transition: opacity 0.3s ease;
  }
  .fade-enter-from,
  .fade-leave-to {
    opacity: 0;
  }
  
  /* 动画效果 */
  .slide-right-enter-active,
  .slide-right-leave-active {
    transition: transform 0.4s cubic-bezier(0.23, 1, 0.32, 1), opacity 0.3s ease;
  }
  .slide-right-enter-from,
  .slide-right-leave-to {
    transform: translateX(100%);
    opacity: 0;
  }
  
  .slide-left-enter-active,
  .slide-left-leave-active {
    transition: transform 0.4s cubic-bezier(0.23, 1, 0.32, 1), opacity 0.3s ease;
  }
  .slide-left-enter-from,
  .slide-left-leave-to {
    transform: translateX(-100%);
    opacity: 0;
  }
  
  /* 保留旧的动画类名以保持兼容性 */
  .slide-enter-active,
  .slide-leave-active {
    transition: transform 0.3s ease;
  }
  .slide-enter-from,
  .slide-leave-to {
    transform: translateX(100%);
  }
  
  /* 新增样式 */
  .path-section {
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #ebeef5;
  }
  
  .nodes-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 8px;
  }
  
  .node-item {
    background: #f8f9fa;
    border-radius: 6px;
    overflow: hidden;
  }
  
  .node-header {
    background: #ebeef5;
    padding: 8px 12px;
    color: #606266;
    font-size: 13px;
    font-weight: 500;
  }
  
  .node-content {
    padding: 12px;
    margin: 0;
    color: #303133;
    font-size: 14px;
    line-height: 1.5;
  }
  
  .response-full {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  
  .keyword-section {
    background: #f0f9eb;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 16px;
  }
  
  .keyword-desc {
    color: #67c23a;
    font-size: 13px;
    margin: 8px 0 0 0;
  }
  
  /* 修改搜索容器和添加搜索图标 */
  .search-container {
    display: flex;
    align-items: center;
    position: absolute;
    right: 0;
    z-index: 5;
    max-width: 300px;
  }
  
  .search-icon {
    font-size: 16px;
    color: #909399;
    margin-right: 8px;
    display: flex;
    align-items: center;
  }
  
  .search-input {
    padding: 8px 12px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    font-size: 14px;
    width: 200px;
    background-color: #f5f3ef;
    transition: all 0.3s;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }
  
  .search-input:focus {
    border-color: #409eff;
    outline: none;
    box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
  }
  
  .clear-search-btn {
    background: none;
    border: none;
    color: #909399;
    font-size: 18px;
    cursor: pointer;
    margin-left: -28px;
    z-index: 6;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .clear-search-btn:hover {
    color: #f56c6c;
  }
  
  .search-results-count {
    margin-left: 10px;
    font-size: 13px;
    color: #606266;
    background-color: #f0f9eb;
    padding: 2px 8px;
    border-radius: 10px;
    border: 1px solid #e1f3d8;
    white-space: nowrap;
  }
  
  /* 在小屏幕上的响应式布局 */
  @media (max-width: 768px) {
    .header-container {
      flex-direction: column;
      align-items: flex-start;
    }
    
    .visualization-title {
      margin-bottom: 10px;
    }
    
    .search-container {
      width: 100%;
      max-width: 100%;
    }
    
    .search-input {
      width: 100%;
    }
  }
  
  .summary-section {
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #ebeef5;
  }
  
  .summary-section h5, .responses-section h5 {
    margin: 0 0 10px 0;
    font-size: 14px;
    color: #606266;
    font-weight: 600;
  }
  
  .summary-section p {
    margin: 0;
    color: #303133;
    line-height: 1.5;
  }
  
  .responses-section {
    margin-bottom: 16px;
  }
  
  .response-item {
    background: #f8f9fa;
    border-radius: 6px;
    margin-bottom: 12px;
    overflow: hidden;
    transition: all 0.3s ease;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  }
  
  .response-item:hover {
    box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
  }
  
  .response-header {
    background: #ebeef5;
    padding: 8px 12px;
    color: #606266;
    font-size: 12px;
    font-weight: 500;
  }
  
  .response-content {
    padding: 12px;
    margin: 0;
    color: #303133;
    font-size: 14px;
    line-height: 1.5;
  }
  
  /* 添加调试按钮样式 */
  .debug-container {
    display: flex;
    align-items: center;
    position: absolute;
    right: 320px;
    z-index: 5;
  }
  
  .debug-btn {
    background-color: #e91e63;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 5px 10px;
    font-size: 12px;
    cursor: pointer;
    margin-right: 10px;
  }
  
  .debug-btn:hover {
    background-color: #c2185b;
  }
  
  .location-indicator {
    background-color: #4caf50;
    color: white;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 12px;
  }
  </style> 