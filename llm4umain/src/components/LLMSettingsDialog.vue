<template>
  <div class="modal-overlay">
    <div class="modal">
      <h2>LLM 参数设置</h2>

      <!-- 模型选择 -->
      <div class="model-section">
        <h3>模型选择</h3>
        <div v-for="(models, group) in groupedModels" :key="group" class="model-group">
          <h4>{{ group }} <span class="vendor">（{{ modelVendors[group] }}）</span></h4>
          <div class="model-options">
            <label
              v-for="m in visibleModels(models, group)"
              :key="m"
              class="model-option"
              :class="{ selected: m === localModel }"
            >
              <input type="radio" :value="m" v-model="localModel" />
              {{ m.split('/').slice(-1)[0] }}
            </label>
            <span v-if="models.length > 2" class="toggle-btn" @click="toggleExpand(group)">
              {{ expandedGroups[group] ? '收起' : '展开更多' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 参数控制 -->
      <div class="params-section">
        <h3 class="text-lg font-semibold mb-2">生成控制参数</h3>
        <div class="param-grid">
          <div
            v-for="(val, key) in paramLabels"
            :key="key"
            class="param-row"
          >
            <!-- 左侧说明 -->
            <div class="param-label">
              <div class="param-title">
                {{ val.label }}: {{ localParams[key] }}
              </div>
              <div class="param-desc">
                {{ val.desc }}
              </div>
            </div>

            <!-- 右侧滑块 -->
            <div class="param-slider">
              <input
                type="range"
                :min="val.min"
                :max="val.max"
                :step="val.step"
                v-model.number="localParams[key]"
                class="slider"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- 底部按钮 -->
      <div class="dialog-footer">
        <button class="btn primary" @click="submit">保存设置</button>
        <button class="btn" @click="$emit('close')">取消</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    model: {
      type: String,
      default: 'internlm/internlm2_5-7b-chat'
    },
    llmParams: Object
  },
  data() {
    return {
      localModel: this.model || 'internlm/internlm2_5-7b-chat',
      localParams: { ...this.llmParams },
      expandedGroups: {},
      modelVendors: {
        'Pro': '华为云昇腾云服务',
        'DeepSeek': '深度求索',
        'Qwen': '通义千问',
        'InternLM': '书生·浦语',
        'THUDM': '清华大学',
        'TeleAI': '中国电信',
      },
      groupedModels: {
        'Pro': [
          'Pro/deepseek-ai/DeepSeek-R1',
          'Pro/deepseek-ai/DeepSeek-V3',
          'Pro/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B',
          'Pro/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B',
          'Pro/Qwen/Qwen2.5-7B-Instruct',
          'Pro/Qwen/Qwen2-7B-Instruct',
          'Pro/Qwen/Qwen2-1.5B-Instruct',
        ],
        'DeepSeek': [
          'deepseek-ai/DeepSeek-R1',
          'deepseek-ai/DeepSeek-V3',
          'deepseek-ai/DeepSeek-R1-Distill-Qwen-32B',
          'deepseek-ai/DeepSeek-R1-Distill-Qwen-14B',
          'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B',
          'deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B',
          'deepseek-ai/DeepSeek-V2.5'
        ],
        'Qwen': [
          'Qwen/QwQ-32B',
          'Qwen/Qwen2.5-72B-Instruct-128K',
          'Qwen/Qwen2.5-72B-Instruct',
          'Qwen/Qwen2.5-32B-Instruct',
          'Qwen/Qwen2.5-14B-Instruct',
          'Qwen/Qwen2.5-7B-Instruct',
          'Qwen/Qwen2.5-Coder-32B-Instruct',
          'Qwen/Qwen2.5-Coder-7B-Instruct',
          'Qwen/Qwen2-7B-Instruct',
          'Qwen/Qwen2-1.5B-Instruct',
          'Qwen/QwQ-32B-Preview',
          'Vendor-A/Qwen/Qwen2.5-72B-Instruct'
        ],
        'InternLM': [
          'internlm/internlm2_5-7b-chat',
          'internlm/internlm2_5-20b-chat'
        ],
        'THUDM': [
          'THUDM/GLM-Z1-32B-0414',
          'THUDM/GLM-4-32B-0414',
          'THUDM/GLM-Z1-Rumination-32B-0414',
          'THUDM/GLM-4-9B-0414',
          'THUDM/glm-4-9b-chat',
          'Pro/THUDM/chatglm3-6b',
          'Pro/THUDM/glm-4-9b-chat'
        ],
        'TeleAI': [
          'TeleAI/TeleChat2'
        ]
      },
      paramLabels: {
        temperature: {
          label: "Temperature",
          min: 0,
          max: 2,
          step: 0.1,
          desc: "控制生成的随机程度"
        },
        top_p: {
          label: "Top P",
          min: 0,
          max: 1,
          step: 0.05,
          desc: "采样时考虑的概率总和"
        },
        top_k: {
          label: "Top K",
          min: 0,
          max: 200,
          step: 1,
          desc: "采样最多考虑候选词数"
        },
        frequency_penalty: {
          label: "Frequency Penalty",
          min: 0,
          max: 2,
          step: 0.1,
          desc: "惩罚重复出现的词"
        },
        max_tokens: {
          label: "Max Tokens",
          min: 100,
          max: 4096,
          step: 100,
          desc: "限制最大输出长度"
        },
        n: {
          label: "N",
          min: 1,
          max: 15,
          step: 1,
          desc: "返回几个回答结果"
        }
      }
    };

  },
  methods: {
    submit() {
      this.$emit('update', {
        model: this.localModel,
        params: this.localParams
      });
      this.$emit('close');
    },
    toggleExpand(group) {
      this.expandedGroups[group] = !this.expandedGroups[group];
    },
    visibleModels(models, group) {
      return this.expandedGroups[group] ? models : models.slice(0, 2);
    },
    displayValue(key) {
      return this.localParams[key] ?? '';
    }
  }
};
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0;
  width: 100vw; height: 100vh;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background: #f9f6f1; /* 浅米色背景，类似宣纸 */
  padding: 24px;
  width: 750px;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.2);
  max-height: 90vh;
  overflow-y: auto;
  border: 1px solid #d3c8b4; /* 棕褐色边框 */
}

h2 {
  color: #5d4037; /* 深棕色文字 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  margin-top: 0;
  border-bottom: 4px solid #8c7a5b; /* 棕褐色边框 */
  padding-bottom: 8px;
}

h3 {
  color: #5d4037; /* 深棕色文字 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  margin-top: 0;
  border-bottom: 2px solid #8c7a5b; /* 棕褐色边框 */
  padding-bottom: 8px;
}

h4 {
  color: #5d4037; /* 深棕色文字 */
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  margin-top: 0;
  margin-bottom: 10px; /* 减少与下方元素的距离 */
}

.model-group {
  margin-bottom: 1em;
}

.model-options {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.model-option {
  padding: 6px 12px;
  background: #f0e9e2; /* 淡褐色背景 */
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #d3c8b4; /* 棕褐色边框 */
  color: #5d4037; /* 深棕色文字 */
}

.model-option.selected {
  background: #68838b; /* 墨蓝色背景 */
  color: #f9f6f1; /* 米色文字 */
  font-weight: bold;
  border-color: #68838b; /* 墨蓝色边框 */
}

.model-option input {
  display: none;
}

.toggle-btn {
  cursor: pointer;
  color: #68838b; /* 墨蓝色文字 */
  font-size: 0.9em;
  padding: 6px 10px;
}

.params-section {
  margin-top: 20px;
}

.param-grid {
  display: grid;
  grid-template-columns: 3fr;
  gap: 10px 20px;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.param-row {
  display: contents;
}

.param-row label {
  text-align: left;
  font-weight: bold;
}

.slider {
  width: 100%;
  appearance: none;
  height: 4px;
  background: #e8e0d8; /* 米黄色背景 */
  outline: none;
  border-radius: 2px;
}

.slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  background: #68838b; /* 墨蓝色滑块 */
  border-radius: 50%;
  cursor: pointer;
}

.dialog-footer {
  margin-top: 24px;
  text-align: right;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn {
  padding: 8px 18px;
  border-radius: 6px;
  border: none;
  background-color: #e8e0d8; /* 米黄色背景 */
  color: #5d4037; /* 深棕色文字 */
  font-weight: bold;
  cursor: pointer;
  transition: 0.2s;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
}

.btn.primary {
  background-color: #68838b; /* 墨蓝色背景 */
  color: #f9f6f1; /* 米色文字 */
}

.btn.primary:hover {
  background-color: #4a6056; /* 墨绿色背景 */
}

.btn:hover {
  opacity: 0.9;
}

.vendor {
  font-weight: normal;
  color: #8c7a5b; /* 棕褐色文字 */
  font-size: 0.9em;
  margin-left: 4px;
}

.param-grid {
  display: grid;
  row-gap: 20px;
}

.param-row {
  display: grid;
  grid-template-columns: 200px 1fr;
  align-items: center;
}

.param-label {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  text-align: left;
}

.param-title {
  font-weight: bold;
  color: #5d4037; /* 深棕色文字 */
}

.param-desc {
  font-size: 0.875rem;
  color: #8c7a5b; /* 棕褐色文字 */
  margin-top: 2px;
}

.param-slider {
  width: 100%;
}
</style>
