<template>
  <div class="explain-panel">
    <div class="explain-header">
      <div class="header-left">
        <ApartmentOutlined />
        <span class="panel-title">执行计划</span>
      </div>
      <div class="header-right">
        <div class="legend">
          <span class="legend-item legend-red">全表扫描</span>
          <span class="legend-item legend-green">索引扫描</span>
          <span class="legend-item legend-yellow">临时表</span>
        </div>
        <a-button size="small" type="text" @click="$emit('close')">
          <template #icon><CloseOutlined /></template>
        </a-button>
      </div>
    </div>
    <div v-if="loading" class="explain-loading">
      <a-spin tip="正在生成执行计划..." />
    </div>
    <div v-else-if="error" class="explain-error">
      <ExclamationCircleOutlined />
      <span>{{ error }}</span>
    </div>
    <div v-else ref="treeContainer" class="explain-tree-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as d3 from 'd3'
import { ApartmentOutlined, CloseOutlined, ExclamationCircleOutlined } from '@ant-design/icons-vue'
import type { ExplainNode } from '@/types/explain'
import { getAccessTypeColor, getAccessTypeLabel } from '@/types/explain'

const props = defineProps<{
  plan: ExplainNode | null
  loading: boolean
  error: string | null
}>()

defineEmits<{
  (e: 'close'): void
}>()

const treeContainer = ref<HTMLElement | null>(null)
let resizeObserver: ResizeObserver | null = null

const colorMap: Record<string, string> = {
  red: '#ff4d4f',
  green: '#52c41a',
  yellow: '#faad14',
  blue: '#1677ff',
}

const bgColorMap: Record<string, string> = {
  red: 'rgba(255, 77, 79, 0.1)',
  green: 'rgba(82, 196, 26, 0.1)',
  yellow: 'rgba(250, 173, 20, 0.1)',
  blue: 'rgba(22, 119, 255, 0.1)',
}

const borderColorMap: Record<string, string> = {
  red: 'rgba(255, 77, 79, 0.4)',
  green: 'rgba(82, 196, 26, 0.4)',
  yellow: 'rgba(250, 173, 20, 0.4)',
  blue: 'rgba(22, 119, 255, 0.4)',
}

interface D3HierarchyNode {
  id: string
  operation_type: string
  table_name: string | null
  estimated_rows: number
  access_type: string
  cost: number
  details: string | null
  children: D3HierarchyNode[]
}

function renderTree() {
  if (!treeContainer.value || !props.plan) return

  const container = treeContainer.value
  d3.select(container).selectAll('*').remove()

  const width = container.clientWidth || 800
  const height = container.clientHeight || 300

  const svg = d3
    .select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .append('g')
    .attr('transform', 'translate(40, 30)')

  const root = d3.hierarchy<D3HierarchyNode>(props.plan as unknown as D3HierarchyNode)

  const nodeWidth = 180
  const nodeHeight = 70
  const horizontalSpacing = 30
  const verticalSpacing = 40

  const treeLayout = d3
    .tree<D3HierarchyNode>()
    .nodeSize([nodeWidth + horizontalSpacing, nodeHeight + verticalSpacing])

  treeLayout(root)

  let minX = Infinity
  let maxX = -Infinity
  let maxY = -Infinity
  root.each((d) => {
    minX = Math.min(minX, d.x ?? 0)
    maxX = Math.max(maxX, d.x ?? 0)
    maxY = Math.max(maxY, d.y ?? 0)
  })

  const treeWidth = maxX - minX + nodeWidth + 80
  const treeHeight = maxY + nodeHeight + 60

  const svgEl = d3.select(container).select('svg')
  svgEl.attr('width', Math.max(width, treeWidth)).attr('height', Math.max(height, treeHeight))

  svg.attr('transform', `translate(${40 - minX + nodeWidth / 2}, 30)`)

  svg
    .selectAll('.link')
    .data(root.links())
    .join('path')
    .attr('class', 'link')
    .attr('d', (d) => {
      const sx = d.source.x ?? 0
      const sy = d.source.y ?? 0
      const tx = d.target.x ?? 0
      const ty = d.target.y ?? 0
      return `M${sx},${sy + nodeHeight / 2}
              C${sx},${(sy + ty) / 2}
               ${tx},${(sy + ty) / 2}
               ${tx},${ty - nodeHeight / 2}`
    })
    .attr('fill', 'none')
    .attr('stroke', '#c0c0c0')
    .attr('stroke-width', 1.5)

  const nodeGroup = svg
    .selectAll('.node')
    .data(root.descendants())
    .join('g')
    .attr('class', 'node')
    .attr('transform', (d) => `translate(${(d.x ?? 0) - nodeWidth / 2}, ${(d.y ?? 0) - nodeHeight / 2})`)

  nodeGroup
    .append('rect')
    .attr('width', nodeWidth)
    .attr('height', nodeHeight)
    .attr('rx', 6)
    .attr('ry', 6)
    .attr('fill', (d) => bgColorMap[getAccessTypeColor(d.data.access_type)])
    .attr('stroke', (d) => borderColorMap[getAccessTypeColor(d.data.access_type)])
    .attr('stroke-width', 1.5)

  nodeGroup
    .append('rect')
    .attr('width', 4)
    .attr('height', nodeHeight)
    .attr('rx', 2)
    .attr('fill', (d) => colorMap[getAccessTypeColor(d.data.access_type)])

  nodeGroup
    .append('text')
    .attr('x', 14)
    .attr('y', 18)
    .attr('font-size', '12px')
    .attr('font-weight', '600')
    .attr('fill', '#333')
    .text((d) => d.data.operation_type)

  nodeGroup
    .append('text')
    .attr('x', 14)
    .attr('y', 34)
    .attr('font-size', '11px')
    .attr('fill', '#666')
    .text((d) => {
      const label = getAccessTypeLabel(d.data.access_type)
      const table = d.data.table_name ? ` | ${d.data.table_name}` : ''
      return `${label}${table}`
    })

  nodeGroup
    .append('text')
    .attr('x', 14)
    .attr('y', 50)
    .attr('font-size', '10px')
    .attr('fill', '#999')
    .text((d) => `rows: ${d.data.estimated_rows.toLocaleString()} | cost: ${d.data.cost}`)

  nodeGroup
    .append('text')
    .attr('x', 14)
    .attr('y', 63)
    .attr('font-size', '9px')
    .attr('fill', '#aaa')
    .text((d) => (d.data.details && d.data.details.length > 28 ? d.data.details.substring(0, 28) + '...' : d.data.details || ''))
}

onMounted(() => {
  nextTick(() => {
    renderTree()
  })

  if (treeContainer.value) {
    resizeObserver = new ResizeObserver(() => {
      renderTree()
    })
    resizeObserver.observe(treeContainer.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})

watch(
  () => props.plan,
  () => {
    nextTick(() => {
      renderTree()
    })
  },
  { deep: true }
)
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.explain-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: $bg-card;
  border-radius: $border-radius-md;
  box-shadow: $shadow-sm;
  overflow: hidden;
}

.explain-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-sm $spacing-md;
  border-bottom: 1px solid $border-color-light;
  background-color: #fafafa;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  color: $text-primary;
  font-size: $font-size-base;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.legend {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  font-size: $font-size-sm;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;

  &::before {
    content: '';
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }
}

.legend-red {
  color: #ff4d4f;
  &::before {
    background-color: #ff4d4f;
  }
}

.legend-green {
  color: #52c41a;
  &::before {
    background-color: #52c41a;
  }
}

.legend-yellow {
  color: #faad14;
  &::before {
    background-color: #faad14;
  }
}

.explain-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: $spacing-lg;
}

.explain-error {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-sm;
  flex: 1;
  padding: $spacing-lg;
  color: $error-color;
  font-size: $font-size-base;
}

.explain-tree-container {
  flex: 1;
  overflow: auto;
  min-height: 0;
  padding: $spacing-sm;
}
</style>
