<template>
  <div class="result-evaluation-container">
    <h2 class="evaluation-title">关键词结果评估</h2>
    
    <!-- 评估指标展示 -->
    <div class="evaluation-metrics">
      <div class="metric-card">
        <h3>总体准确率</h3>
        <div class="metric-value">{{ overallAccuracy }}%</div>
      </div>
      <div class="metric-card">
        <h3>直接匹配数</h3>
        <div class="metric-value">{{ directMatchedKeywords.length }}</div>
      </div>
      <div class="metric-card">
        <h3>推断匹配数</h3>
        <div class="metric-value">{{ inferredMatchedKeywords.length }}</div>
      </div>
      <div class="metric-card">
        <h3>未匹配数</h3>
        <div class="metric-value">{{ unmatchedKeywords.length }}</div>
      </div>
    </div>

    <!-- 匹配详情表格 -->
    <div class="evaluation-details">
      <div class="details-header">
        <h3>关键词匹配详情</h3>
        <button 
          @click="refreshLLMMatching" 
          class="refresh-btn" 
          :disabled="isProcessing"
        >
          {{ isProcessing ? '处理中...' : '重新评估未匹配关键词' }}
        </button>
      </div>

      <div class="legend">
        <div class="legend-item"><span class="legend-color direct-match"></span> 直接匹配</div>
        <div class="legend-item"><span class="legend-color inferred-match"></span> 推断匹配</div>
        <div class="legend-item"><span class="legend-color unmatched"></span> 未匹配</div>
      </div>
      <table class="match-table">
        <thead>
          <tr>
            <th>回答结果汇总</th>
            <th>出现频率</th>
            <th>匹配状态</th>
            <th>参考数据</th>
            <th v-if="showInferenceReasons">推断理由</th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="(keyword, index) in sortedKeywords" 
            :key="index" 
            :class="{
              'direct-matched': isDirectMatched(keyword),
              'inferred-matched': isInferredMatched(keyword),
              'not-matched': !isMatched(keyword)
            }"
          >
            <td>{{ keyword }}</td>
            <td>{{ keywordFrequency[keyword] }}</td>
            <td>
              <span :class="getMatchStatusClass(keyword)">
                {{ getMatchStatusText(keyword) }}
              </span>
            </td>
            <td>{{ getMatchedReference(keyword) }}</td>
            <td v-if="showInferenceReasons">{{ inferenceReasons[keyword] || '' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { computed, ref, onMounted, watch } from 'vue';
import axios from 'axios';

export default {
  props: {
    jsonData: Object
  },
  setup(props) {
    const sushiEventMap = ref({});
    const addrChains = ref([]);
    const allAddrs = ref([]);
    const inferredMatches = ref({});
    const inferenceReasons = ref({});
    const isProcessing = ref(false);
    const showInferenceReasons = ref(true);

    const isLocationQuery = ref(false);
    const isTimeQuery = ref(false);

    // 加载 Sushi_structured.csv
    const loadSushiData = async () => {
      try {
        const text = await (await fetch('/SongData/Sushi_structured.csv')).text();
        const lines = text.trim().split('\n');
        const headers = lines[0].split(',');
        for (let i = 1; i < lines.length; i++) {
          const cols = lines[i].split(',');
          const row = {};
          headers.forEach((h, j) => row[h.trim()] = cols[j]?.trim());
          const event = row['Event'];
          if (event) {
            sushiEventMap.value[event] = {
              location: row['Location'],
              description: row['Description'] || '',
              time: row['Time'] || ''
            };
          }
        }
        // 打印从 CSV 中提取的数据，方便调试
        console.log("从 Sushi_structured.csv 加载的数据：");
        Object.entries(sushiEventMap.value).forEach(([event, { location, description, time }]) => {
          console.log(`事件: ${event}, 地点: ${location}, 时间: ${time}, 描述: ${description}`);
        });
      } catch (err) {
        console.error('加载 Sushi_structured.csv 失败', err);
      }
    };


    const loadAddrChains = async () => {
      try {
        const text = await (await fetch('/SongData/SongAddrChain.csv')).text();
        addrChains.value = text.trim().split('\n').slice(1).map(line => line.split(','));
      } catch (err) {
        console.error('加载 SongAddrChain.csv 失败', err);
      }
    };

    const loadAllAddr = async () => {
      try {
        const text = await (await fetch('/SongData/AllAddr.csv')).text();
        allAddrs.value = text.trim().split('\n').slice(1).map(line => line.split(',')[0].trim());
      } catch (err) {
        console.error('加载 AllAddr.csv 失败', err);
      }
    };

    onMounted(() => {
      loadSushiData();
      loadAddrChains();
      loadAllAddr();
    });

    const keywordFrequency = computed(() => {
      const freq = {};
      props.jsonData?.responses?.forEach(res => {
        const words = res.最终结果?.split(',').map(w => w.trim()) || [];
        words.forEach(k => {
          if (k) freq[k] = (freq[k] || 0) + 1;
        });
      });
      return freq;
    });

    const sortedKeywords = computed(() =>
      Object.keys(keywordFrequency.value).sort((a, b) =>
        keywordFrequency.value[b] - keywordFrequency.value[a]
      )
    );

    const isDirectMatched = (keyword) => {
      if (isTimeQuery.value) {
        console.log("目前正在判断 时间 直接匹配过程");
        return isTimeMatched(keyword);
      }
      else{
        console.log("目前正在判断 地点 直接匹配过程");
        return Object.values(sushiEventMap.value).some(item =>
        item.location?.includes(keyword) || keyword.includes(item.location)
        );
      }
    }

    const isInferredFromAddrChain = (keyword) => {
      const addrSet = new Set(allAddrs.value);
      if (!addrSet.has(keyword)) return false;
      for (const { location } of Object.values(sushiEventMap.value)) {
        if (!location) continue;
        const relatedRows = addrChains.value.filter(row => row.includes(keyword) && row.includes(location));
        if (relatedRows.length > 0) return true;
      }
      return false;
    };

    const isInferredMatched = (keyword) => {
      if (isTimeQuery.value) return false; // 时间不推断
      return !isDirectMatched(keyword) && (inferredMatches.value[keyword] === true || isInferredFromAddrChain(keyword));
    };

    const isMatched = (keyword) => {
      return isDirectMatched(keyword) || isInferredMatched(keyword);
    };

    const getMatchStatusClass = (keyword) => {
      if (isDirectMatched(keyword)) return 'status-direct-matched';
      if (isInferredMatched(keyword)) return 'status-inferred-matched';
      return 'status-unmatched';
    };

    const getMatchStatusText = (keyword) => {
      if (isDirectMatched(keyword)) return '直接匹配';
      if (isInferredMatched(keyword)) return '推断匹配';
      return '未匹配';
    };

    const getMatchedReference = (keyword) => {
      if (isTimeQuery.value) {
        const matched = [];
        for (const [event, { time, description }] of Object.entries(sushiEventMap.value)) {
          if (checkTimeOverlap(keyword, time)) {
            matched.push(`${event}: ${description}（时间：${time}）`);
          }
        }
        return matched.join('；');
      } else {
        const matched = [];
        for (const [event, { location, description }] of Object.entries(sushiEventMap.value)) {
          if (location?.includes(keyword) || keyword.includes(location)) {
            matched.push(`${event}: ${description}`);
          }
        }
        return matched.join('；');
      }
    };

    const directMatchedKeywords = computed(() =>
      sortedKeywords.value.filter(isDirectMatched)
    );

    const inferredMatchedKeywords = computed(() =>
      sortedKeywords.value.filter(k => isInferredMatched(k) && !isDirectMatched(k))
    );

    const unmatchedKeywords = computed(() =>
      sortedKeywords.value.filter(k => !isMatched(k))
    );

    const overallAccuracy = computed(() => {
      const total = sortedKeywords.value.length;
      const matched = directMatchedKeywords.value.length + inferredMatchedKeywords.value.length;
      return total > 0 ? Math.round((matched / total) * 100) : 0;
    });

    // ========== 时间处理逻辑 ==========
    // 判断时间是否匹配，支持时间段与时间点的匹配
    const isTimeMatched = (keyword) => {
      console.log(`正在检查时间匹配：关键词 "${keyword}"`);

      // 如果关键词是单一的时间点
      if (/^\d{4}$/.test(keyword)) { // 时间点，格式例如 1079
        console.log(`关键词是时间点：${keyword}`);
        const match = Object.values(sushiEventMap.value).some(({ time }) => time === keyword);
        if (match) {
          console.log(`时间点 ${keyword} 匹配成功`);
        } else {
          console.log(`时间点 ${keyword} 匹配失败`);
        }
        return match;
      }

      // 如果关键词是时间段
      if (/^\d{4}-\d{4}$/.test(keyword)) { // 时间段，格式例如 1079-1085
        const [startTime, endTime] = keyword.split('-').map(Number);
        console.log(`关键词是时间段：${keyword}, 开始时间：${startTime}, 结束时间：${endTime}`);
        
        const match = Object.values(sushiEventMap.value).some(({ time }) => {
          if (!time) return false; // 如果没有时间数据，则跳过
          const [eventStart, eventEnd] = time.split('-').map(Number);
          
          // 打印每个活动的时间区间
          console.log(`事件时间：${time}, 开始时间：${eventStart}, 结束时间：${eventEnd}`);

          const isMatched = (startTime <= eventEnd && endTime >= eventStart); // 判断时间段是否有交集
          if (isMatched) {
            console.log(`时间段 ${keyword} 与事件的时间区间 ${time} 匹配`);
          }
          return isMatched;
        });

        if (!match) {
          console.log(`时间段 ${keyword} 没有匹配的事件`);
        }

        return match;
      }

      console.log(`无法匹配关键词 "${keyword}"`);
      return false; // 其他情况不匹配
    };


    const checkTimeOverlap = (keyword, timeStr) => {
      if (!timeStr) return false;
      const k = parseInt(keyword);
      if (isNaN(k)) return false;

      if (timeStr.includes('-')) {
        const [start, end] = timeStr.split('-').map(s => parseInt(s.trim()));
        if (!isNaN(start) && !isNaN(end)) {
          return k >= start && k <= end;
        }
      } else {
        const t = parseInt(timeStr.trim());
        return k === t;
      }
      return false;
    };

    // ========== LLM 判断推断匹配 ==========
    const checkWithLLM = async (keyword) => {
      try {
        // 构建活动记录
        const facts = Object.entries(sushiEventMap.value).map(
          ([event, { location, description, time }]) => {
            if (time) {
              return `${event}（时间：${time}） - ${description}`;
            }
            if (location) {
              return `${event}（地点：${location}） - ${description}`;
            }
            return `${event} - ${description}`;
          }
        ).join('\n');

        // 判断问题类型并构建不同的 Prompt
        let promptContent = '';

        if (props.jsonData.q_type === 'time') {
          // 时间类型问题的 Prompt
          promptContent = `以下是苏轼活动记录：\n${facts}\n\n关键词：${keyword}\n\n请判断这个时间是否与上述活动相关，若相关，请以“是”开头并说明理由，否则以“否”开头。`;
        } else if (props.jsonData.q_type === 'location') {
          // 地址类型问题的 Prompt（旧有逻辑）
          promptContent = `以下是苏轼活动记录：\n${facts}\n\n关键词：${keyword}\n\n请判断这个地名是否可能与上述地点有关系（如临近、从属等），如可能，请以“是”开头并说明理由，否则以“否”开头。`;
        } else {
          // 默认行为，处理其他问题类型
          promptContent = `以下是苏轼活动记录：\n${facts}\n\n关键词：${keyword}\n\n请判断这个关键词是否与上述活动相关，如可能，请以“是”开头并说明理由，否则以“否”开头。`;
        }

        // 发送请求到 LLM
        const messages = [
          {
            role: "system",
            content: "你是苏轼历史专家，判断某地名或时间是否可能与苏轼历史有关。"
          },
          {
            role: "user",
            content: promptContent
          }
        ];

        const { data } = await axios.post('http://localhost:5000/api/llm/chat', {
          messages,
          temperature: 0.3,
          max_tokens: 200
        });

        // 获取 LLM 返回的结果
        const responseText = data.response;
        const isReasonable = responseText.startsWith('是');
        const reason = responseText.replace(/^是|^否/, '').trim();

        return { isReasonable, reason };
      } catch (err) {
        console.error('LLM 请求失败', err);
        return { isReasonable: false, reason: 'LLM 请求失败' };
      }
    };


    const refreshLLMMatching = async () => {
      if (isProcessing.value) return;
      isProcessing.value = true;

      const candidates = unmatchedKeywords.value.filter(k => inferredMatches.value[k] === undefined);

      const batchSize = 3;
      for (let i = 0; i < candidates.length; i += batchSize) {
        const batch = candidates.slice(i, i + batchSize);
        const results = await Promise.all(batch.map(async k => {
          const r = await checkWithLLM(k);
          return { k, r };
        }));
        results.forEach(({ k, r }) => {
          inferredMatches.value[k] = r.isReasonable;
          inferenceReasons.value[k] = r.reason;
        });
      }

      isProcessing.value = false;
    };

    // 监听 jsonData 变化，判断是否为时间或地点类型问题
    watch(
      () => props.jsonData,
      async () => {
        console.log('watch 被触发');
        console.log('问题类型:', props.jsonData.meta.q_type);
        console.log('查询实体:', props.jsonData.meta.entity);

        isLocationQuery.value = false;
        isTimeQuery.value = false;

        if (props.jsonData.meta.q_type?.includes('地点')) {
          isLocationQuery.value = true;
        } else if (props.jsonData.meta.q_type?.includes('时间')) {
          isTimeQuery.value = true;
        }

        inferredMatches.value = {};
        inferenceReasons.value = {};
      },
      { deep: true, immediate: true } 
    );

    return {
      keywordFrequency,
      sortedKeywords,
      isDirectMatched,
      isInferredMatched,
      isMatched,
      getMatchStatusClass,
      getMatchStatusText,
      getMatchedReference,
      directMatchedKeywords,
      inferredMatchedKeywords,
      unmatchedKeywords,
      overallAccuracy,
      refreshLLMMatching,
      isProcessing,
      showInferenceReasons,
      inferenceReasons
    };
  }
};
</script>

<style scoped>
.result-evaluation-container {
  padding: 24px;
  background-color: #f9f6f1;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  font-Family: "KaiTi", "楷体", "STKaiti", "华文楷体", serif;
}

.evaluation-title {
  color: #5d4037;
  font-size: 1.5rem;
  margin-bottom: 24px;
  padding-bottom: 12px;
  border-bottom: 2px solid #8c7a5b;
}

.evaluation-metrics {
  display: flex;
  gap: 24px;
  margin-bottom: 32px;
}

.metric-card {
  flex: 1;
  background-color: #fff;
  padding: 16px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  text-align: center;
  border-left: 4px solid #8c7a5b;
}

.metric-card h3 {
  font-size: 0.9rem;
  color: #795548;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 2rem;
  font-weight: bold;
  color: #5d4037;
}

.evaluation-details {
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 24px;
}

.evaluation-details h3 {
  color: #5d4037;
  margin-bottom: 16px;
  font-size: 1.2rem;
}

.legend {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  font-size: 0.85rem;
  color: #5d4037;
}

.legend-color {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  margin-right: 8px;
}

.legend-color.direct-match {
  background-color: #e8f5e9;
}

.legend-color.inferred-match {
  background-color: #fff3e0;
}

.legend-color.unmatched {
  background-color: #ffebee;
}

.match-table {
  width: 100%;
  border-collapse: collapse;
}

.match-table th, .match-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.match-table th {
  background-color: #f5f3ef;
  color: #5d4037;
  font-weight: bold;
}

.match-table tr:hover {
  background-color: #f8f5f2;
}

.direct-matched {
  background-color: #f1f8e9;
}

.inferred-matched {
  background-color: #fff8e1;
}

.not-matched {
  background-color: #fef6f6;
}

.status-direct-matched, .status-inferred-matched, .status-unmatched {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.85rem;
}

.status-direct-matched {
  background-color: #e8f5e9;
  color: #2e7d32;
}

.status-inferred-matched {
  background-color: #fff3e0;
  color: #e65100;
}

.status-unmatched {
  background-color: #ffebee;
  color: #c62828;
}

.settings-panel {
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.settings-panel h3 {
  color: #5d4037;
  margin-bottom: 16px;
  font-size: 1.2rem;
}

.settings-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.setting-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.setting-item label {
  font-size: 0.9rem;
  color: #5d4037;
}

.refresh-btn {
  background-color: #8c7a5b;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-Family: "KaiTi", "楷体", "STKaiti", "华文楷体", serif;
  transition: background-color 0.3s;
}

.refresh-btn:hover:not(:disabled) {
  background-color: #736555;
}

.refresh-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
</style>