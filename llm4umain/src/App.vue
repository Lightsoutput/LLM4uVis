<template>
  <div class="app-container">
    <HeaderBar />

    <div class="main-body">
      <SidePanel @query-submitted="handleQueryResult" />
      <MainView :jsonData="jsonData" />
    </div>
  </div>
</template>

<script>
import HeaderBar from './components/HeaderBar.vue'
import SidePanel from './components/SidePanel.vue'
import MainView from './components/MainView.vue'

export default {
  name: 'App',
  components: {
    HeaderBar,
    SidePanel,
    MainView
  },
  data() {
    return {
      jsonData: null
    }
  },
  methods: {
    handleQueryResult(data) {
      this.jsonData = data;
    }
  }
}
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.main-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}
</style>
