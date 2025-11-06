<template>
  <div class="side-panel">
    <div class="panel-header">
      <h2>查询控制面板</h2>
      <div class="settings-icon" @click="showSettings = true">
        <span class="icon">⚙️</span>
        <span class="tooltip">LLM 参数设置</span>
      </div>
    </div>

    <div class="input-group">
      <label>
        <span class="label-text">问题描述</span>
        <div class="input-with-button">
          <input 
            type="text" 
            v-model="question" 
            placeholder="请输入您的问题..."
            :class="{ 'error': isSubmitted && !question }"
          />
          <button 
            @click="autoAnalyzeQuestion" 
            class="auto-analyze-button" 
            :disabled="!question || analyzeLoading"
            :title="!question ? '请先输入问题' : '自动识别问题类型和实体'"
          >
            <span v-if="!analyzeLoading">✨</span>
            <span v-else class="mini-spinner"></span>
          </button>
        </div>
      </label>
    </div>

    <div class="input-group">
      <label>
        <span class="label-text">问题类型</span>
        <select 
          v-model="q_type"
          :class="{ 'error': isSubmitted && !q_type }"
        >
          <option value="">请选择问题类型</option>
          <option value="时间">时间</option>
          <option value="地点">地点</option>
          <option value="人物">人物</option>
          <option value="事件">事件</option>
        </select>
      </label>
    </div>

    <div class="input-group">
      <label>
        <span class="label-text">实体名称</span>
        <input 
          type="text" 
          v-model="entity" 
          placeholder="请输入实体名称..."
          :class="{ 'error': isSubmitted && !entity }"
        />
      </label>
    </div>

    <div v-if="analyzeResult.confidence" class="confidence-indicator">
      <span class="confidence-label">识别置信度:</span>
      <div class="confidence-bar-container">
        <div class="confidence-bar" :style="{ width: `${analyzeResult.confidence * 100}%`, backgroundColor: confidenceColor }"></div>
      </div>
      <span class="confidence-value">{{ (analyzeResult.confidence * 100).toFixed(0) }}%</span>
    </div>

    <div class="model-display" @click="showSettings = true">
      <span class="label-text">当前模型</span>
      <div class="model-info">
        <span class="model-name">{{ displayModelName }}</span>
        <span class="model-edit">点击修改</span>
      </div>
    </div>

    <button 
      class="submit-button" 
      @click="submitQuery" 
      :disabled="loading"
      :class="{ 'loading': loading }"
    >
      <span class="button-content">
        <span class="button-text">{{ loading ? '查询中...' : '提交查询' }}</span>
        <span v-if="loading" class="loading-spinner"></span>
      </span>
    </button>

    <div 
      class="feedback" 
      :class="{ 
        'success': feedback.includes('成功'), 
        'error': feedback.includes('失败') || feedback.includes('请填写')
      }"
    >
      {{ feedback }}
    </div>

    <LLMSettingsDialog
      v-if="showSettings"
      :model="model"
      :llmParams="llmParams"
      @update="handleSettingsUpdate"
      @close="showSettings = false"
    />
  </div>
</template>

<script>
import LLMSettingsDialog from './LLMSettingsDialog.vue'

export default {
  components: { LLMSettingsDialog },
  data() {
    return {
      question: '',
      q_type: '',
      entity: '',
      model: 'internlm/internlm2_5-7b-chat',
      showSettings: false,
      loading: false,
      analyzeLoading: false,
      feedback: '',
      isSubmitted: false,
      analyzeResult: {
        confidence: 0
      },
      llmParams: {
        temperature: 0.7,
        top_p: 0.7,
        top_k: 50,
        frequency_penalty: 0.5,
        max_tokens: 1024,
        stop: null,
        stream: false,
        n: 8
      }
    };
  },
  computed: {
    displayModelName() {
      return this.model.split('/').pop();
    },
    confidenceColor() {
      const confidence = this.analyzeResult.confidence;
      if (confidence >= 0.8) return '#42b983'; // 高置信度为绿色
      if (confidence >= 0.6) return '#f0ad4e'; // 中等置信度为黄色
      return '#ff6b6b'; // 低置信度为红色
    }
  },
  methods: {
    handleSettingsUpdate({ model, params }) {
      this.model = model;
      this.llmParams = { ...params };
    },
    async autoAnalyzeQuestion() {
      if (!this.question) {
        this.feedback = "请先输入问题！";
        return;
      }
      
      this.analyzeLoading = true;
      this.feedback = "正在分析问题...";
      
      try {
        const response = await fetch("http://localhost:5000/api/analyze-question", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: this.question,
            model: this.model
          })
        });
        
        const data = await response.json();
        
        if (data.q_type && data.entity) {
          this.q_type = data.q_type;
          this.entity = data.entity;
          this.analyzeResult.confidence = data.confidence || 0;
          
          this.feedback = `已自动识别问题类型和实体（置信度: ${Math.round(data.confidence * 100)}%）`;
        } else {
          this.feedback = "问题分析失败，请手动填写";
        }
      } catch (err) {
        console.error(err);
        this.feedback = "问题分析失败，请检查服务器";
      } finally {
        this.analyzeLoading = false;
      }
    },
    async submitQuery() {
      this.isSubmitted = true;
      
      if (!this.question || !this.q_type || !this.entity) {
        this.feedback = "请填写所有必填项！";
        return;
      }

      this.loading = true;
      this.feedback = "";

      try {
        // 通过接口访问Flask后端内容
        const response = await fetch("http://localhost:5000/api/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: this.question,
            q_type: this.q_type,
            entity: this.entity,
            model: this.model,
            ...this.llmParams
          })
        });
        // 从后端拿到数据
        const data = await response.json();
        this.$emit("query-submitted", data);
        this.feedback = "查询成功！";
        this.isSubmitted = false;
      } catch (err) {
        this.feedback = "查询失败，请检查服务器。";
      } finally {
        this.loading = false;
      }
    }
  }
};
</script>

<style scoped>
.side-panel {
  width: 300px;
  background: #f9f6f1; /* 浅米色背景，类似宣纸 */
  padding: 20px;
  border-right: 1px solid #d6cfc2; /* 淡棕色边框 */
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 2px 0 4px rgba(0, 0, 0, 0.05);
  box-sizing: border-box;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  border-bottom: 2px solid #8c7a5b; /* 棕褐色边框，模拟水墨画边框 */
  padding-bottom: 10px;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.5em;
  color: #5d4037; /* 深棕色 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.settings-icon {
  position: relative;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: background-color 0.3s;
}

.settings-icon:hover {
  background-color: #e8e0d8; /* 米黄色 */
}

.settings-icon .tooltip {
  position: absolute;
  top: 100%;
  right: 0;
  background: #68838b; /* 墨蓝色 */
  color: #f9f6f1; /* 米色 */
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  display: none;
  white-space: nowrap;
}

.settings-icon:hover .tooltip {
  display: block;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
}

.input-group label {
  width: 100%;
}

.input-with-button {
  display: flex;
  align-items: center;
  width: 100%;
}

.input-with-button input {
  flex-grow: 1;
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.auto-analyze-button {
  height: 37px;
  width: 37px;
  padding: 0;
  border: 1px solid #d3c8b4; /* 棕褐色边框 */
  border-left: none;
  background: #f0e9e2; /* 淡褐色背景 */
  cursor: pointer;
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all 0.3s;
}

.auto-analyze-button:hover:not(:disabled) {
  background: #e0d5c8; /* 更深的褐色 */
}

.auto-analyze-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mini-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #5d4037; /* 深棕色边框 */
  border-top: 2px solid transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.label-text {
  font-size: 14px;
  font-weight: bold;
  color: #5d4037; /* 深棕色文字 */
  margin-bottom: 4px;
  display: block;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

input, select {
  width: 100%;
  padding: 10px;
  font-size: 14px;
  border: 1px solid #d3c8b4; /* 棕褐色边框 */
  border-radius: 6px;
  transition: all 0.3s;
  background: #f8f5f0; /* 米色背景 */
  box-sizing: border-box;
  margin: 0;
  color: #5d4037; /* 深棕色文字 */
}

/* 特别为select元素添加一致的文本对齐和内部填充 */
select {
  text-indent: 0;
  padding-left: 10px;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%235d4037' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3e%3cpolyline points='6 9 12 15 18 9'%3e%3c/polyline%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 10px center;
  background-size: 16px;
}

input:focus, select:focus {
  outline: none;
  border-color: #8c7a5b; /* 棕褐色边框 */
  box-shadow: 0 0 0 2px rgba(140, 122, 91, 0.1); /* 棕褐色阴影 */
  background: #fff;
}

input::placeholder {
  color: #a8998a; /* 浅棕色 */
}

.error {
  border-color: #a98175 !important; /* 砖红色边框 */
  background-color: #f9f2f0 !important; /* 浅红米色背景 */
}

.submit-button {
  background-color: #68838b; /* 墨蓝色背景 */
  color: #f9f6f1; /* 米色文字 */
  padding: 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.3s;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 8px;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.submit-button:hover:not(:disabled) {
  background-color: #4a6056; /* 墨绿色 */
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.submit-button:disabled {
  background-color: #a6b6bb; /* 浅墨蓝色 */
  cursor: not-allowed;
}

.button-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #f9f6f1; /* 米色边框 */
  border-top: 2px solid transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.feedback {
  font-size: 14px;
  padding: 8px;
  border-radius: 4px;
  text-align: center;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.feedback.success {
  background-color: #e8efe9; /* 浅墨绿色背景 */
  color: #4a6056; /* 墨绿色文字 */
}

.feedback.error {
  background-color: #f8efed; /* 浅砖红色背景 */
  color: #a98175; /* 砖红色文字 */
}

.model-display {
  background: #f0e9e2; /* 淡褐色背景 */
  border: 1px solid #d3c8b4; /* 棕褐色边框 */
  border-radius: 6px;
  padding: 10px;
  cursor: pointer;
  transition: all 0.3s;
}

.model-display:hover {
  background: #e8e0d8; /* 米黄色背景 */
  border-color: #8c7a5b; /* 棕褐色边框 */
}

.model-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}

.model-name {
  font-weight: 500;
  color: #5d4037; /* 深棕色文字 */
}

.model-edit {
  font-size: 12px;
  color: #68838b; /* 墨蓝色 */
}

.confidence-indicator {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 100%;
}

.confidence-label {
  font-size: 12px;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  font-weight: bold;
  color: #5d4037; /* 深棕色文字 */
}

.confidence-bar-container {
  width: 100%;
  height: 6px;
  background-color: #e8e0d8; /* 米黄色背景 */
  border-radius: 3px;
  overflow: hidden;
}

.confidence-bar {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s, background-color 0.5s;
  background-color: #68838b !important; /* 强制使用墨蓝色 */
}

.confidence-value {
  font-size: 12px;
  color: #5d4037; /* 深棕色文字 */
  align-self: flex-end;
}
</style>