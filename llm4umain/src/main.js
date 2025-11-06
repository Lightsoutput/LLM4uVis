import { createApp } from 'vue'
import App from './App.vue'

// 导入echarts和词云图插件
import * as echarts from 'echarts';
import 'echarts-wordcloud';

// 将echarts添加到全局
window.echarts = echarts;

createApp(App).mount('#app')
