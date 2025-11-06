<template>
    <div class="analysis-container">
      <h2 class="analysis-title">回答结果分析</h2>
  
      <!-- 可视化视图容器 - 新布局 -->
      <div class="visualization-layout">
        <!-- 第一行：桑基图占满宽度 -->
        <div class="sankey-container">
          <SankeyChart :jsonData="jsonData" ref="sankeyChartRef" />
        </div>
  
        <!-- 第二行：三个图表水平排列 -->
        <div class="charts-row">
          <!-- 词云图 -->
          <div class="visualization-card">
            <h3 class="visualization-title">关键词词云</h3>
            <div ref="wordCloudChart" class="chart-container"></div>
          </div>
  
          <!-- 相似度热力图 -->
          <div class="visualization-card">
            <h3 class="visualization-title">回答相似度分析</h3>
            <div ref="similarityChart" class="chart-container"></div>
          </div>
  
          <!-- 可能正确率坐标图 -->
          <div class="visualization-card">
            <h3 class="visualization-title">关键词可信度分析</h3>
            <div ref="confidenceChart" class="chart-container"></div>
          </div>
        </div>
      </div>
  
      <!-- 分析详情 -->
      <div class="analysis-details">
        <h3>综合分析结果</h3>
        <div class="details-card">
          <div class="top-keywords">
            <h4>最可能的关键结果:</h4>
            <div class="keyword-chips">
              <span
                v-for="(item, index) in topKeywords"
                :key="index"
                class="keyword-chip"
                :style="{ background: getColorByConfidence(item.confidence) }"
              >
                {{ item.keyword }}
                <span class="confidence-badge">{{ Math.round(item.confidence * 100) }}%</span>
              </span>
            </div>
          </div>
          <div class="analysis-metrics">
            <div class="metric-item">
              <span class="metric-label">一致性指数:</span>
              <span class="metric-value">{{ Math.round(consistencyIndex * 100) }}%</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">平均相似度:</span>
              <span class="metric-value">{{ Math.round(averageSimilarity * 100) }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  import { onMounted, onUnmounted, ref, computed, watch } from 'vue';
  // 引入本地util中的echarts，作为备选
  import echarts from '../../utils/charts.js';
  // 导入桑基图组件
  import SankeyChart from './SankeyChart.vue';
  
  export default {
    name: 'ResultAnalysis',
    components: {
      SankeyChart
    },
    props: {
      jsonData: Object
    },
    setup(props) {
      // 图表引用
      const wordCloudChart = ref(null);
      const similarityChart = ref(null);
      const confidenceChart = ref(null);
      const sankeyChartRef = ref(null);
      
      // 图表实例
      let wordCloud = null;
      let similarityMap = null;
      let confidenceGraph = null;
      
      // 使用全局echarts对象或导入的备选对象
      const getEchartsInstance = () => {
        return window.echarts || echarts;
      };
  
      // 计算属性 - 所有关键词及其频率
      // 所有结果 最终结果 关键词频率统计 keywordFrequency.value
      const keywordFrequency = computed(() => {
        if (!props.jsonData?.responses || props.jsonData.responses.length === 0) return {};
        
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
        
        return frequency;
      });
      
      // 计算属性 - 每个回答的关键词集合
      const responseKeywords = computed(() => {
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
      });
      
      // 计算属性 - 排名前的关键词
      const topKeywords = computed(() => {
        const keywords = Object.entries(keywordFrequency.value)
          .map(([keyword, count]) => ({
            keyword,
            count,
            confidence: count / props.jsonData.responses.length
          }))
          .sort((a, b) => b.count - a.count)
          .slice(0, 10);
        
        return keywords;
      });
      
      // 计算属性 - 一致性指数
      // 意义：看多个 LLM 回答中用了多少重复的关键词，越多代表它们越一致。
      const consistencyIndex = computed(() => {
        if (!props.jsonData?.responses || props.jsonData.responses.length === 0) return 0;
        
        const totalKeywords = Object.values(keywordFrequency.value).reduce((sum, count) => sum + count, 0);
        const uniqueKeywords = Object.keys(keywordFrequency.value).length;
        
        if (uniqueKeywords === 0) return 0;
        
        // 计算理想情况下如果所有回答都包含相同关键词的总计数
        // 实际所有关键词总数 / 理想总数 -> 越接近1，代表重复率越高，回答越一致
        const idealTotal = props.jsonData.responses.length * uniqueKeywords;
        
        return totalKeywords / idealTotal;
      });
      
      // 计算属性 - 平均相似度
      const averageSimilarity = computed(() => {
        if (responseKeywords.value.length <= 1) return 1;
        
        let totalSimilarity = 0;
        let pairCount = 0;
        
        for (let i = 0; i < responseKeywords.value.length; i++) {
          for (let j = i + 1; j < responseKeywords.value.length; j++) {
            const similarity = calculateJaccardSimilarity(
              responseKeywords.value[i].keywords,
              responseKeywords.value[j].keywords
            );
            totalSimilarity += similarity;
            pairCount++;
          }
        }
        
        return pairCount > 0 ? totalSimilarity / pairCount : 0;
      });
      
      // 计算两个关键词集合的Jaccard相似度
      // Jaccard 相似度测量两个集合的交集大小除以它们的并集大小
      const calculateJaccardSimilarity = (set1, set2) => {
        if (set1.length === 0 && set2.length === 0) return 1;
        if (set1.length === 0 || set2.length === 0) return 0;
        
        const set1Set = new Set(set1);
        const set2Set = new Set(set2);
        
        const intersection = new Set([...set1Set].filter(x => set2Set.has(x)));
        const union = new Set([...set1Set, ...set2Set]);
        
        return intersection.size / union.size;
      };
      
      // 基于可信度返回不同组件的颜色
      const getColorByConfidence = (confidence) => {
        if (confidence >= 0.8) return '#4a5560'; // 深墨灰色
        if (confidence >= 0.6) return '#546d7a'; // 青墨色
        if (confidence >= 0.4) return '#68838b'; // 墨蓝色
        if (confidence >= 0.2) return '#8ca0a9'; // 淡墨色
        return '#b5bec4'; // 浅灰色
      };

      // 为词云返回墨绿色系的颜色
      const getWordCloudColor = (confidence) => {
        if (confidence >= 0.8) return '#3a545c'; // 深墨绿
        if (confidence >= 0.6) return '#4d6b5f'; // 青墨绿
        if (confidence >= 0.4) return '#5f8162'; // 中墨绿
        if (confidence >= 0.2) return '#7a9778'; // 淡墨绿
        return '#a3b59e'; // 浅墨绿
      };

      // 为柱状图返回墨蓝色系的颜色
      const getBarChartColor = (confidence) => {
        if (confidence >= 0.8) return '#374b6d'; // 深墨蓝
        if (confidence >= 0.6) return '#446285'; // 墨蓝
        if (confidence >= 0.4) return '#577a99'; // 中墨蓝
        if (confidence >= 0.2) return '#7a94ad'; // 淡墨蓝
        return '#a9bacb'; // 浅墨蓝
      };
      
      // 初始化词云图
      const initWordCloud = () => {
        if (wordCloudChart.value) {
          try {
            wordCloud = getEchartsInstance().init(wordCloudChart.value);
            console.log('词云图初始化成功');
          } catch (error) {
            console.error('词云图初始化失败:', error);
          }
        }
      };
      
      // 更新词云图
      const updateWordCloud = () => {
        if (!wordCloud) return;
        
        const data = Object.entries(keywordFrequency.value).map(([keyword, count]) => ({
          name: keyword,
          value: count,
          textStyle: {
            color: getWordCloudColor(count / props.jsonData.responses.length)
          }
        }));
        
        // 确保在服务器端渲染时不会出错
        if (data.length === 0) {
          data.push({
            name: '暂无数据',
            value: 0,
            textStyle: { color: '#ccc' }
          });
        }
        
        try {
          console.log('尝试渲染词云图，数据项数:', data.length);
          // 所有结果 最终结果 关键词频率统计
          console.log('词云关键词频率:', keywordFrequency.value);
          console.log('传入的数据:', props.jsonData);
          
          const option = {
            tooltip: {
              show: true,
              trigger: 'item',
              formatter: '{b}: {c} 次',
              textStyle: {
                fontFamily: 'KaiTi, STKaiti, serif'
              }
            },
            series: [{
              type: 'wordCloud',
              shape: 'circle',
              left: 'center',
              top: 'center',
              width: '80%',
              height: '80%',
              sizeRange: [12, 50],
              rotationRange: [-45, 45],
              rotationStep: 15,
              gridSize: 8,
              drawOutOfBound: false,
              layoutAnimation: true,
              textStyle: {
                fontFamily: 'KaiTi, STKaiti, serif',
                fontWeight: 'bold'
              },
              emphasis: {
                focus: 'self',
                textStyle: {
                  shadowBlur: 10,
                  shadowColor: '#333',
                  fontFamily: 'KaiTi, STKaiti, serif'
                }
              },
              data
            }]
          };
  
          wordCloud.setOption(option);
          console.log('词云图渲染完成1111');
        } catch (error) {
          console.error('词云图渲染错误:', error);
        }
      };
      
      // 初始化相似度热力图
      const initSimilarityChart = () => {
        if (similarityChart.value) {
          similarityMap = getEchartsInstance().init(similarityChart.value);
        }
      };
      
      // 更新相似度热力图
      const updateSimilarityChart = () => {
        if (!similarityMap || responseKeywords.value.length === 0) return;
        
        const n = responseKeywords.value.length;
        const data = [];
        const xData = [];
        const yData = [];
        
        for (let i = 0; i < n; i++) {
          xData.push(`回答${i + 1}`);
          yData.push(`回答${i + 1}`);
        }
        
        for (let i = 0; i < n; i++) {
          for (let j = 0; j < n; j++) {
            const similarity = i === j ? 1 : calculateJaccardSimilarity(
              responseKeywords.value[i].keywords,
              responseKeywords.value[j].keywords
            );
            
            data.push([i, j, similarity.toFixed(2)]);
          }
        }
        
        const option = {
          tooltip: {
            position: 'top',
            formatter: function (params) {
              return `${params.name}<br/>${xData[params.value[0]]}与${yData[params.value[1]]}<br/>相似度: ${params.value[2]}`;
            },
            textStyle: {
              fontFamily: 'KaiTi, STKaiti, serif'
            }
          },
          grid: {
            top: '2%',
            right: '10%',
            bottom: '15%',
            left: '15%'
          },
          xAxis: {
            type: 'category',
            data: xData,
            splitArea: {
              show: true
            },
            axisLabel: {
              fontFamily: 'KaiTi, STKaiti, serif'
            }
          },
          yAxis: {
            type: 'category',
            data: yData,
            splitArea: {
              show: true
            },
            axisLabel: {
              fontFamily: 'KaiTi, STKaiti, serif'
            }
          },
          visualMap: {
            min: 0,
            max: 1,
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: '0%',
            color: ['#1e3a5f', '#4f6d92', '#7a94ad', '#a9bacb', '#d6d9db', '#e6d0c6', '#d4a992', '#c1826d', '#a65c4a', '#8c3c29', '#6b1f15'],
            textStyle: {
              fontFamily: 'KaiTi, STKaiti, serif'
            }
          },
          series: [{
            name: '相似度',
            type: 'heatmap',
            data: data,
            label: {
              show: true,
              formatter: function (params) {
                return params.value[2];
              }
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }]
        };
        
        similarityMap.setOption(option);
      };
      
      // 初始化可信度图
      const initConfidenceChart = () => {
        if (confidenceChart.value) {
          confidenceGraph = getEchartsInstance().init(confidenceChart.value);
        }
      };
      
      // 更新可信度图
      const updateConfidenceChart = () => {
        if (!confidenceGraph) return;
        
        const topKeywordsData = topKeywords.value.slice(0, 10);
        
        const option = {
          tooltip: {
            trigger: 'axis',
            axisPointer: {
              type: 'shadow'
            },
            formatter: '{b}: {c}%',
            textStyle: {
              fontFamily: 'KaiTi, STKaiti, serif'
            }
          },
          grid: {
            top: '15%',
            right: '8%',
            bottom: '15%',
            left: '8%'
          },
          xAxis: {
            type: 'category',
            data: topKeywordsData.map(item => item.keyword),
            axisLabel: {
              interval: 0,
              rotate: 30,
              fontFamily: 'KaiTi, STKaiti, serif'
            }
          },
          yAxis: {
            type: 'value',
            min: 0,
            max: 100,
            name: '可信度 (%)',
            nameTextStyle: {
              fontFamily: 'KaiTi, STKaiti, serif'
            },
            axisLabel: {
              fontFamily: 'KaiTi, STKaiti, serif'
            }
          },
          series: [{
            name: '可信度',
            type: 'bar',
            data: topKeywordsData.map(item => Math.round(item.confidence * 100)),
            itemStyle: {
              color: function(params) {
                return getBarChartColor(topKeywordsData[params.dataIndex].confidence);
              }
            },
            label: {
              show: true,
              position: 'top',
              formatter: '{c}%',
              textStyle: {
                fontFamily: 'KaiTi, STKaiti, serif'
              }
            }
          }]
        };
        
        confidenceGraph.setOption(option);
      };
      
      // 初始化所有图表
      const initCharts = () => {
        initWordCloud();
        initSimilarityChart();
        initConfidenceChart();
      };
      
      // 更新所有图表
      const updateCharts = () => {
        updateWordCloud();
        updateSimilarityChart();
        updateConfidenceChart();
      };
      
      // 监听数据变化
      watch(() => props.jsonData, () => {
        if (props.jsonData) {
          updateCharts();
        }
      }, { deep: true });
      
      // 组件挂载时初始化图表
      onMounted(() => {
        // 确保DOM渲染完成后再初始化图表
        setTimeout(() => {
          console.log('初始化所有图表');
          initCharts();
          if (props.jsonData) {
            console.log('更新所有图表');
            updateCharts();
          }
        }, 300); // 增加延迟时间
        
        window.addEventListener('resize', () => {
          wordCloud?.resize();
          similarityMap?.resize();
          confidenceGraph?.resize();
        });
      });
      
      // 组件卸载时清理
      onUnmounted(() => {
        wordCloud?.dispose();
        similarityMap?.dispose();
        confidenceGraph?.dispose();
        
        window.removeEventListener('resize', () => {
          wordCloud?.resize();
          similarityMap?.resize();
          confidenceGraph?.resize();
        });
      });
      
      return {
        wordCloudChart,
        similarityChart,
        confidenceChart,
        sankeyChartRef,
        topKeywords,
        consistencyIndex,
        averageSimilarity,
        getColorByConfidence
      };
    }
  };
  </script>
  
  <style scoped>
  .analysis-container {
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
  
  /* 新的布局结构 */
  .visualization-layout {
    display: flex;
    flex-direction: column;
    gap: 72px; /* 增加间距 */
    margin-bottom: 30px;
  }
  
  /* 桑基图容器 - 占满宽度 */
  .sankey-container {
    width: 100%;
    height: 700px;
  }
  
  /* 三个图表水平排列 */
  .charts-row {
    display: flex;
    gap: 24px;
    width: 100%;
  }
  
  .visualization-card {
    flex: 1;
    background: #f9f6f1; /* 浅米色背景 */
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    padding: 20px;
    display: flex;
    flex-direction: column;
    border: 1px solid #d3c8b4; /* 棕褐色边框 */
  }
  
  .visualization-title {
    margin: 0 0 16px 0;
    color: #5d4037; /* 深棕色文字 */
    font-size: 1.1rem;
    font-weight: 600;
    text-align: center;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .chart-container {
    flex: 1;
    min-height: 250px;
    width: 100%;
  }
  
  .analysis-details {
    background: #f9f6f1; /* 浅米色背景 */
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    padding: 20px;
    border: 1px solid #d3c8b4; /* 棕褐色边框 */
  }
  
  .analysis-details h3 {
    margin: 0 0 16px 0;
    color: #5d4037; /* 深棕色文字 */
    font-size: 1.1rem;
    font-weight: 600;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .details-card {
    background: #f0e9e2; /* 淡褐色背景 */
    border-radius: 8px;
    padding: 16px;
    border: 1px solid #e8e0d8; /* 米黄色边框 */
  }
  
  .top-keywords {
    margin-bottom: 20px;
    font-weight: bold;
  }
  
  .top-keywords h4 {
    margin: 0 0 12px 0;
    color: #5d4037; /* 深棕色文字 */
    font-size: 1rem;
    font-weight: bold;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .keyword-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    font-weight: bold;
  }
  
  .keyword-chip {
    color: #f9f6f1; /* 米色文字 */
    padding: 6px 12px;
    border-radius: 16px;
    font-size: 14px;
    font-weight: bold;
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  }
  
  .confidence-badge {
    background: rgba(255, 255, 255, 0.8);
    color: #5d4037; /* 深棕色文字 */
    padding: 2px 6px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: bold;
  }
  
  .analysis-metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    font-weight: bold;
  }
  
  .metric-item {
    background: #f9f6f1; /* 浅米色背景 */
    padding: 10px 16px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 10px;
    border: 1px solid #d3c8b4; /* 棕褐色边框 */
    font-weight: bold;
  }
  
  .metric-label {
    color: #8c7a5b; /* 棕褐色文字 */
    font-size: 14px;
    font-weight: 500;
    font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
    font-weight: bold;
  }
  
  .metric-value {
    color: #5d4037; /* 深棕色文字 */
    font-size: 16px;
    font-weight: 700;
    font-weight: bold;
  }
  
  /* 移除响应式堆叠 */
  @media (max-width: 768px) {
    .sankey-container {
      height: 500px;
    }
  }
  </style> 