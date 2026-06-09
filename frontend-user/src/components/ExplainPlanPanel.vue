<template>
  <div class="explain-plan-panel">
    <div class="panel-header">
      <div class="header-left">
        <NodeIndexOutlined class="panel-icon" />
        <span class="panel-title">SQL 执行计划</span>
        <a-tag v-if="result" :color="result.sql_valid ? 'blue' : 'red'">
          总成本: {{ result.total_cost.toFixed(2) }}
        </a-tag>
      </div>
      <div class="header-right">
        <div class="legend">
          <span class="legend-item">
            <span class="legend-dot critical"></span> 全表扫描
          </span>
          <span class="legend-item">
            <span class="legend-dot warning"></span> 警告/临时表
          </span>
          <span class="legend-item">
            <span class="legend-dot normal"></span> 索引扫描
          </span>
        </div>
        <a-button type="text" size="small" @click="$emit('close')">
          <template #icon><CloseOutlined /></template>
        </a-button>
      </div>
    </div>

    <div v-if="!result && !loading" class="panel-empty">
      <SearchOutlined class="empty-icon" />
      <p>点击 "Explain" 按钮分析 SQL 执行计划</p>
    </div>

    <div v-if="loading" class="panel-loading">
      <a-spin size="large" />
      <p>正在分析 SQL 执行计划...</p>
    </div>

    <div v-if="result && !loading" class="panel-content">
      <div v-if="result.warnings.length > 0" class="warnings-section">
        <a-alert type="warning" show-icon>
          <template #message>
            <span>性能提示 ({{ result.warnings.length }})</span>
          </template>
          <template #description>
            <ul class="warning-list">
              <li v-for="(w, i) in result.warnings" :key="i">{{ w }}</li>
            </ul>
          </template>
        </a-alert>
      </div>

      <div v-if="!result.sql_valid" class="errors-section">
        <a-alert type="error" show-icon>
          <template #message>SQL 语法错误</template>
          <template #description>
            <ul class="error-list">
              <li v-for="(e, i) in result.validation_errors" :key="i">{{ e }}</li>
            </ul>
          </template>
        </a-alert>
      </div>

      <div ref="treeContainer" class="tree-container"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick, onUnmounted } from 'vue'
import * as d3 from 'd3'
import {
  CloseOutlined,
  NodeIndexOutlined,
  SearchOutlined,
} from '@ant-design/icons-vue'
import type { ExplainResponse, ExecutionPlanNode, TreeNode } from '@/types/executionPlan'
import { BottleneckLevel, AccessType } from '@/types/executionPlan'

const props = defineProps<{
  result: ExplainResponse | null
  loading: boolean
}>()

defineEmits<{
  (e: 'close'): void
}>()

const treeContainer = ref<HTMLElement | null>(null)
let svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null

function getNodeColor(bottleneck: BottleneckLevel, accessType: AccessType | null): string {
  if (bottleneck === BottleneckLevel.CRITICAL || accessType === AccessType.FULL_SCAN) {
    return '#ff4d4f'
  }
  if (bottleneck === BottleneckLevel.WARNING) {
    return '#faad14'
  }
  return '#52c41a'
}

function getNodeBgColor(bottleneck: BottleneckLevel, accessType: AccessType | null): string {
  if (bottleneck === BottleneckLevel.CRITICAL || accessType === AccessType.FULL_SCAN) {
    return '#fff1f0'
  }
  if (bottleneck === BottleneckLevel.WARNING) {
    return '#fffbe6'
  }
  return '#f6ffed'
}

function convertToTree(node: ExecutionPlanNode): TreeNode {
  return {
    name: node.operation_type,
    nodeData: node,
    children: node.children.length > 0 ? node.children.map(convertToTree) : undefined
  }
}

function formatNodeLabel(node: ExecutionPlanNode): string[] {
  const lines: string[] = []
  lines.push(node.operation_type)

  if (node.table_name) {
    lines.push(`表: ${node.table_name}`)
  }
  if (node.access_type) {
    lines.push(`访问: ${node.access_type}`)
  }
  lines.push(`行数: ${node.estimated_rows.toLocaleString()}`)
  lines.push(`代价: ${node.estimated_cost.toFixed(2)}`)
  return lines
}

function renderTree(data: TreeNode) {
  if (!treeContainer.value) return

  d3.select(treeContainer.value).selectAll('*').remove()

  const containerRect = treeContainer.value.getBoundingClientRect()
  const width = containerRect.width || 800
  const marginTop = 40
  const marginBottom = 40
  const marginLeft = 30

  const hierarchy = d3.hierarchy(data)
  const dx = 110
  const dy = Math.min(width / (hierarchy.height + 1), 280)

  const treeLayout = d3.tree<TreeNode>().nodeSize([dx, dy])
  const root = treeLayout(hierarchy)

  let x0 = Infinity
  let x1 = -Infinity
  root.each(d => {
    if (d.x < x0) x0 = d.x
    if (d.x > x1) x1 = d.x
  })

  const height = x1 - x0 + marginTop + marginBottom
  const svgWidth = width
  const gx = marginLeft
  const gy = marginTop - x0

  svg = d3.select(treeContainer.value)
    .append('svg')
    .attr('width', svgWidth)
    .attr('height', height)
    .attr('viewBox', [0, 0, svgWidth, height])
    .attr('style', 'max-width: 100%; height: auto; font: 12px sans-serif; user-select: none;')

  const g = svg.append('g')
    .attr('transform', `translate(${gx},${gy})`)

  g.append('g')
    .attr('fill', 'none')
    .attr('stroke', '#d9d9d9')
    .attr('stroke-opacity', 0.8)
    .attr('stroke-width', 1.8)
    .selectAll('path')
    .data(root.links())
    .join('path')
    .attr('d', d3.linkHorizontal<d3.HierarchyPointLink<TreeNode>, d3.HierarchyPointNode<TreeNode>>()
      .x(d => d.y)
      .y(d => d.x)
    )

  const node = g.append('g')
    .attr('stroke-linejoin', 'round')
    .attr('stroke-width', 3)
    .selectAll('g')
    .data(root.descendants())
    .join('g')
    .attr('transform', d => `translate(${d.y},${d.x})`)

  node.append('rect')
    .attr('x', -6)
    .attr('y', -38)
    .attr('width', 12)
    .attr('height', 12)
    .attr('rx', 2)
    .attr('fill', d => getNodeColor(d.data.nodeData.bottleneck, d.data.nodeData.access_type))
    .attr('stroke', '#fff')
    .attr('stroke-width', 2)

  const cardGroups = node.append('g')
    .attr('transform', 'translate(12, -48)')

  cardGroups.append('rect')
    .attr('width', 180)
    .attr('height', 90)
    .attr('rx', 8)
    .attr('ry', 8)
    .attr('fill', d => getNodeBgColor(d.data.nodeData.bottleneck, d.data.nodeData.access_type))
    .attr('stroke', d => getNodeColor(d.data.nodeData.bottleneck, d.data.nodeData.access_type))
    .attr('stroke-width', 1.5)

  cardGroups.each(function(d) {
    const card = d3.select(this)
    const lines = formatNodeLabel(d.data.nodeData)
    const lineHeight = 17

    lines.forEach((line, i) => {
      const textEl = card.append('text')
        .attr('x', 12)
        .attr('y', 20 + i * lineHeight)
        .text(line)

      if (i === 0) {
        textEl.attr('font-weight', 'bold')
          .attr('font-size', '13px')
          .attr('fill', getNodeColor(d.data.nodeData.bottleneck, d.data.nodeData.access_type))
      } else {
        textEl.attr('font-size', '11px')
          .attr('fill', '#595959')
      }
    })
  })

  node.append('title')
    .text(d => d.data.nodeData.description)
}

function clearTree() {
  if (treeContainer.value) {
    d3.select(treeContainer.value).selectAll('*').remove()
  }
}

watch(() => props.result, async (newResult) => {
  if (newResult && newResult.plan_tree) {
    await nextTick()
    const treeData = convertToTree(newResult.plan_tree)
    renderTree(treeData)
  } else {
    clearTree()
  }
}, { immediate: true })

watch(() => props.loading, (loading) => {
  if (loading) clearTree()
})

onMounted(() => {
  if (props.result && props.result.plan_tree) {
    nextTick(() => {
      const treeData = convertToTree(props.result!.plan_tree)
      renderTree(treeData)
    })
  }
})

onUnmounted(() => {
  clearTree()
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.explain-plan-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: $bg-card;
  border-radius: $border-radius-md;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-sm $spacing-md;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  background-color: #fafafa;
}

.header-left {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.panel-icon {
  font-size: 16px;
  color: $primary-color;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: $text-primary;
}

.header-right {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.legend {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  font-size: 12px;
  color: $text-secondary;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;

  &.critical {
    background-color: #ff4d4f;
  }
  &.warning {
    background-color: #faad14;
  }
  &.normal {
    background-color: #52c41a;
  }
}

.panel-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-md;
  color: $text-secondary;

  .empty-icon {
    font-size: 48px;
    opacity: 0.4;
  }

  p {
    margin: 0;
    font-size: 14px;
  }
}

.panel-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-md;
  color: $text-secondary;

  p {
    margin: 0;
    font-size: 14px;
  }
}

.panel-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.warnings-section,
.errors-section {
  padding: $spacing-md;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.warning-list,
.error-list {
  margin: $spacing-xs 0 0 0;
  padding-left: $spacing-lg;
  font-size: 12px;

  li {
    margin-bottom: 2px;
  }
}

.tree-container {
  flex: 1;
  overflow: auto;
  padding: $spacing-md;
}
</style>
