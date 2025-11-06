<template>
  <div class="kg-container">
    <div class="legend-container">
      <div class="legend-title">图例</div>
      <div class="legend-items">
        <div 
          v-for="(color, type) in nodeColorMap" 
          :key="type"
          class="legend-item"
          :class="{ active: activeTypes.has(type) }"
          @click="toggleNodeType(type)"
        >
          <span class="legend-color" :style="{ backgroundColor: color }"></span>
          <span class="legend-label">{{ getTypeName(type) }}</span>
        </div>
      </div>
    </div>
    <div ref="graphContainer" class="graph-container"></div>
    <div class="graph-controls">
      <button 
        @click="clearSelection" 
        class="clear-button"
        :disabled="activeTypes.size === 0"
        :class="{ 'clear-button-disabled': activeTypes.size === 0 }"
      >
        清空选择
      </button>
      <button @click="refreshGraph" class="refresh-button">
        刷新图谱
      </button>
    </div>
  </div>
</template>

<script>
import * as d3 from 'd3';
import axios from 'axios';

export default {
  name: 'Neo4jGraph',
  props: {
    entity: {
      type: String,
      required: true,
    }
  },
  data() {
    return {
      nodes: [],
      links: [],
      simulation: null,
      svg: null,
      width: 0,
      height: 0,
      apiBaseUrl: 'http://localhost:5000', // 设置API基础URL
      activeTypes: new Set(), // 改为Set存储多个激活的类型
      nodeColorMap: {
        'Person': '#68838b',    // 墨蓝色
        'Dynasty': '#4a6056',   // 墨绿色
        'Year': '#8c7a5b',      // 棕褐色
        'AssocEvent': '#ab6c63', // 红褐色
        'Text': '#6e7783',      // 灰蓝色
        'Association': '#786153', // 深棕色
        'Status': '#8B7355',    // 褐色
        'Gender': '#737CA1',    // 蓝灰色
      },
    };
  },
  watch: {
    entity: {
      handler(newEntity) {
        if (newEntity) {
          this.queryGraph();
        }
      },
      immediate: true
    }
  },
  mounted() {
    this.width = this.$refs.graphContainer.clientWidth;
    this.height = this.$refs.graphContainer.clientHeight;
    this.initGraph();
    
    // 监听窗口大小变化
    window.addEventListener('resize', this.handleResize);
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.handleResize);
    if (this.simulation) {
      this.simulation.stop();
    }
  },
  methods: {
    handleResize() {
      this.width = this.$refs.graphContainer.clientWidth;
      this.height = this.$refs.graphContainer.clientHeight;
      if (this.svg) {
        this.svg.attr('width', this.width).attr('height', this.height);
        if (this.simulation) {
          this.simulation.force('center', d3.forceCenter(this.width / 2, this.height / 2));
          this.simulation.alpha(0.3).restart();
        }
      }
    },
    
    initGraph() {
      // 清除已有的SVG
      if (this.$refs.graphContainer.querySelector('svg')) {
        this.$refs.graphContainer.querySelector('svg').remove();
      }
      
      this.svg = d3.select(this.$refs.graphContainer)
        .append('svg')
        .attr('width', this.width)
        .attr('height', this.height);
        
      // 添加缩放功能
      const zoom = d3.zoom()
        .scaleExtent([0.2, 3])
        .on('zoom', (event) => {
          mainGroup.attr('transform', event.transform);
        });
      
      this.svg.call(zoom);
      
      // 创建主要的组，用于缩放和平移
      const mainGroup = this.svg.append('g');
      this.mainGroup = mainGroup;
      
      // 创建箭头标记
      mainGroup.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('viewBox', '-0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('orient', 'auto')
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('xoverflow', 'visible')
        .append('svg:path')
        .attr('d', 'M 0,-5 L 10 ,0 L 0,5')
        .attr('fill', '#8c7a5b')
        .style('stroke', 'none');
    },
    
    // 向后端传递参数 personName = this.entity
    async queryGraph() {
      try {
        const response = await axios.post(`${this.apiBaseUrl}/api/neo4j/graph`, { 
          personName: this.entity 
        });
        
        this.updateGraph(response.data);
      } catch (error) {
        console.error('查询图数据失败:', error);
      }
    },
    
    refreshGraph() {
      this.activeTypes.clear(); // 清空选中状态
      this.queryGraph();
    },
    
    updateGraph(data) {
      // 清除现有图形
      this.mainGroup.selectAll('*').remove();
      this.initGraph();
      
      if (!data.nodes || data.nodes.length === 0) {
        this.addNoDataMessage();
        return;
      }
      
      this.nodes = data.nodes;
      this.links = data.links;
      
      // 创建模拟
      this.simulation = d3.forceSimulation(this.nodes)
        .force('link', d3.forceLink(this.links).id(d => d.id).distance(80))
        .force('charge', d3.forceManyBody().strength(-400))
        .force('center', d3.forceCenter(this.width / 2, this.height / 2))
        .force('collide', d3.forceCollide().radius(40))
        .on('tick', this.ticked);
      
      // 绘制连接线
      const link = this.mainGroup.append('g')
        .selectAll('line')
        .data(this.links)
        .enter()
        .append('line')
        .attr('stroke', '#d3c8b4')
        .attr('stroke-width', 1.5)
        .attr('marker-end', 'url(#arrowhead)');
      
      // 绘制节点
      const node = this.mainGroup.append('g')
        .selectAll('g')
        .data(this.nodes)
        .enter()
        .append('g')
        .on('click', (event, d) => {
          event.stopPropagation(); // 防止事件冒泡
          this.toggleNodeType(d.type);
        });
        
      // 添加节点圆形
      node.append('circle')
        .attr('r', d => d.type === 'Person' ? 18 : 12)
        .attr('fill', d => this.getNodeColor(d.type))
        .attr('stroke', '#8c7a5b')
        .attr('stroke-width', 1.5)
        .style('cursor', 'pointer');
      
      // 添加节点文本标签
      node.append('text')
        .text(d => d.type === 'AssocEvent' ? d.code : d.name)
        .attr('font-size', 12)
        .attr('text-anchor', 'middle')
        .attr('dy', d => d.type === 'Person' ? 30 : 25)
        .attr('fill', '#5d4037')
        .style('font-family', '"KaiTi", "楷体", "STKaiti", "华文楷体", serif')
        .style('cursor', 'pointer');
      
      // 添加连接标签
      const linkText = this.mainGroup.append('g')
        .selectAll('text')
        .data(this.links)
        .enter()
        .append('text')
        .attr('font-size', 10)
        .attr('fill', '#68838b')
        .text(d => d.type)
        .attr('text-anchor', 'middle');
      
      // 节点拖拽行为
      node.call(d3.drag()
        .on('start', this.dragstarted)
        .on('drag', this.dragged)
        .on('end', this.dragended));
      
      // 更新模拟引用
      this.simulation.nodes(this.nodes);
      this.simulation.force('link').links(this.links);
      
      // 存储引用以便在tick函数中使用
      this.linkElements = link;
      this.nodeElements = node;
      this.linkTextElements = linkText;

      // 添加背景点击事件，用于取消高亮
      this.svg.on('click', () => {
        this.activeTypes.clear();
        this.updateNodesVisibility();
      });
    },
    
    addNoDataMessage() {
      this.mainGroup.append('text')
        .attr('x', this.width / 2)
        .attr('y', this.height / 2)
        .attr('text-anchor', 'middle')
        .attr('font-size', 16)
        .attr('fill', '#8c7a5b')
        .text(`未找到 "${this.entity}" 的相关知识图谱数据`);
    },
    
    ticked() {
      // 更新连接位置
      this.linkElements
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
      
      // 更新节点位置
      this.nodeElements
        .attr('transform', d => `translate(${d.x}, ${d.y})`);
      
      // 更新连接文本位置
      this.linkTextElements
        .attr('x', d => (d.source.x + d.target.x) / 2)
        .attr('y', d => (d.source.y + d.target.y) / 2 - 5);
    },
    
    dragstarted(event, d) {
      if (!event.active) this.simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    },
    
    dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    },
    
    dragended(event, d) {
      if (!event.active) this.simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    },
    
    getNodeColor(type) {
      return this.nodeColorMap[type] || '#d3c8b4';
    },

    // 获取节点类型的中文名称
    getTypeName(type) {
      const typeNames = {
        'Person': '人物',
        'Dynasty': '朝代',
        'Year': '年份',
        'AssocEvent': '事件',
        'Text': '文献',
        'Association': '关联',
        'Status': '身份',
        'Gender': '性别',
      };
      return typeNames[type] || type;
    },

    // 切换节点类型的显示状态（改为多选）
    toggleNodeType(type) {
      if (this.activeTypes.has(type)) {
        this.activeTypes.delete(type);
      } else {
        this.activeTypes.add(type);
      }
      this.updateNodesVisibility();
    },

    // 清空所有选择
    clearSelection() {
      this.activeTypes.clear();
      this.updateNodesVisibility();
    },

    // 更新节点的可见性
    updateNodesVisibility() {
      if (!this.nodeElements) return;

      this.nodeElements.style('opacity', d => {
        return this.activeTypes.size === 0 ? 1 : (this.activeTypes.has(d.type) ? 1 : 0.1);
      });

      this.linkElements.style('opacity', d => {
        if (this.activeTypes.size === 0) return 0.6;
        return (this.activeTypes.has(d.source.type) || this.activeTypes.has(d.target.type)) ? 0.6 : 0.1;
      });

      this.linkTextElements.style('opacity', d => {
        if (this.activeTypes.size === 0) return 1;
        return (this.activeTypes.has(d.source.type) || this.activeTypes.has(d.target.type)) ? 1 : 0.1;
      });
    },
  }
};
</script>

<style scoped>
.kg-container {
  margin-bottom: 20px;
  height: 430px;
  position: relative;
  overflow: hidden;
  border: none;
}

.legend-container {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(249, 246, 241, 0.9);
  padding: 8px;
  border-radius: 6px;
  border: 1px solid #d3c8b4;
  z-index: 10;
}

.legend-title {
  font-family: "KaiTi", "楷体", "STKaiti", "华文楷体", serif;
  font-size: 14px;
  color: #5d4037;
  margin-bottom: 8px;
  text-align: center;
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.3s ease;
}

.legend-item:hover {
  background: rgba(211, 200, 180, 0.2);
}

.legend-item.active {
  background: rgba(211, 200, 180, 0.4);
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid #8c7a5b;
}

.legend-label {
  font-family: "KaiTi", "楷体", "STKaiti", "华文楷体", serif;
  font-size: 12px;
  color: #5d4037;
}

.graph-container {
  width: 100%;
  height: 100%;
}

.graph-controls {
  position: absolute;
  bottom: 10px;
  right: 10px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.clear-button {
  padding: 6px 12px;
  background: #f0e9e2;
  border: 1px solid #d3c8b4;
  border-radius: 4px;
  color: #5d4037;
  cursor: pointer;
  font-family: "STKaiti", "FangSong", serif;
  transition: all 0.3s ease;
}

.refresh-button {
  padding: 6px 12px;
  background: #f0e9e2;
  border: 1px solid #d3c8b4;
  border-radius: 4px;
  color: #5d4037;
  cursor: pointer;
  font-family: "STKaiti", "FangSong", serif;
  transition: all 0.3s ease;
}

.refresh-button:hover {
  background: #e8e0d8;
  border-color: #8c7a5b;
}

.clear-button:hover:not(:disabled) {
  background: #e8e0d8;
  border-color: #8c7a5b;
}

.clear-button-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #f5f3ef;
}
</style> 