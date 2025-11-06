<template>
  <div class="main-view">
    <Visualizer :jsonData="jsonData" v-if="jsonData" />
    <div v-else class="placeholder">请先进行查询以显示可视化内容</div>
  </div>
</template>

<script>
import Visualizer from './VisualizerVue.vue';

export default {
  props: {
    jsonData: Object,
  },
  components: {
    Visualizer,
  }
};
</script>

<style scoped>
.main-view {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  background-color: #f5f3ef; /* 米黄色背景，类似宣纸 */
}

.placeholder {
  color: #8c7a5b; /* 棕褐色文字 */
  font-size: 18px;
  text-align: center;
  margin-top: 100px;
  font-family: "STKaiti", "FangSong", serif; /* 使用楷体或仿宋字体 */
  border: 1px dashed #d3c8b4; /* 棕褐色虚线边框 */
  padding: 40px 20px;
  border-radius: 8px;

}
</style>
