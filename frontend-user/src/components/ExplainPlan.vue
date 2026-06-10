<template>
  <div class="explain-plan-container">
    <div class="plan-header">
      <div class="plan-title">
        <LineChartOutlined />
        <span>执行计划</span>
      </div>
      <div class="plan-stats">
        <span class="stat-item">
          <span class="stat-label">总成本:</span>
          <span class="stat-value">{{ plan?.total_cost?.toFixed(2) || 0 }}</span>
        </span>
        <span class="stat-item">
          <span class="stat-label">方言:</span>
          <span class="stat-value">{{ plan?.dialect || '-' }}</span>
        </span>
      </div>
    </div>

    <div class="legend">
      <div class="legend-item">
        <span class="legend-color legend-full-scan"></span>
        <span>全表扫描</span>
      </div>
      <div class="legend-item">
        <span class="legend-color legend-index-scan"></span>
        <span>索引扫描</span>
      </div>
      <div class="legend-item">
        <span class="legend-color legend-temp-table"></span>
        <span>临时表</span>
      </div>
    </div>

    <div v-if="plan?.warnings?.length" class="warnings-panel">
      <div class="warnings-title">
        <WarningOutlined />
        <span>性能警告 ({{ plan.warnings.length }})</span>
      </div>
      <ul class="warnings-list">
        <li v-for="(warning, idx) in plan.warnings" :key="idx">
          {{ warning }}
        </li>
      </ul>
    </div>

    <div ref="svgContainer" class="svg-container">
      <svg ref="svgRef" class="plan-svg"></svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { LineChartOutlined, WarningOutlined } from '@ant-design/icons-vue'
import * as d3 from 'd3'
import type { ExplainResponse, ExplainPlanNode, ExplainAccessType } from '@/api/explain'
import { ExplainAccessType as AccessTypeEnum } from '@/api/explain'

interface Props {
  plan: ExplainResponse | null
}

const props = defineProps<Props>()

const svgContainer = ref<HTMLElement | null>(null)
const svgRef = ref<SVGSVGElement | null>(null)

const NODE_WIDTH = 180
const NODE_HEIGHT = 90
const NODE_HORIZONTAL_SPACING = 60
const NODE_VERTICAL_SPACING = 30

function getNodeColor(accessType: ExplainAccessType | null): string {
  switch (accessType) {
    case AccessTypeEnum.FULL_SCAN:
      return '#ff4d4f'
    case AccessTypeEnum.INDEX_SCAN:
    case AccessTypeEnum.INDEX_SEEK:
      return '#52c41a'
    case AccessTypeEnum.TEMP_TABLE:
      return '#faad14'
    default:
      return '#1890ff'
  }
}

function getNodeBorderColor(accessType: ExplainAccessType | null): string {
  switch (accessType) {
    case AccessTypeEnum.FULL_SCAN:
      return '#cf1322'
    case AccessTypeEnum.INDEX_SCAN:
    case AccessTypeEnum.INDEX_SEEK:
      return '#389e0d'
    case AccessTypeEnum.TEMP_TABLE:
      return '#d48806'
    default:
      return '#096dd9'
  }
}

function countNodes(node: ExplainPlanNode): number {
  let count = 1
  for (const child of node.children) {
    count += countNodes(child)
  }
  return count
}

function countDepth(node: ExplainPlanNode): number {
  if (!node.children || node.children.length === 0) return 1
  let maxDepth = 0
  for (const child of node.children) {
    maxDepth = Math.max(maxDepth, countDepth(child))
  }
  return maxDepth + 1
}

function renderTree() {
  if (!props.plan || !svgRef.value || !svgContainer.value) return

  const svg = d3.select(svgRef.value)
  svg.selectAll('*').remove()

  const containerWidth = svgContainer.value.clientWidth
  const containerHeight = svgContainer.value.clientHeight

  const depth = countDepth(props.plan.plan)
  const nodeCount = countNodes(props.plan.plan)

  const treeWidth = depth * (NODE_WIDTH + NODE_HORIZONTAL_SPACING)
  const treeHeight = Math.max(
    containerHeight - 40,
    nodeCount * (NODE_HEIGHT + NODE_VERTICAL_SPACING) * 0.6
  )

  const width = Math.max(containerWidth - 40, treeWidth)
  const height = Math.max(containerHeight - 40, treeHeight)

  svg.attr('width', width + 40).attr('height', height + 40)

  const g = svg
    .append('g')
    .attr('transform', 'translate(20, 20)')

  const treeLayout = d3.tree<ExplainPlanNode>()
    .size([height, width - NODE_WIDTH])
    .separation(() => 1.2)

  const root = d3.hierarchy(props.plan.plan, (d) => d.children)
  treeLayout(root)

  g.selectAll('.link')
    .data(root.links())
    .enter()
    .append('path')
    .attr('class', 'link')
    .attr('d', (d) => {
      const sourceX = d.source.y! + NODE_WIDTH
      const sourceY = d.source.x!
      const targetX = d.target.y!
      const targetY = d.target.x!
      const midX = (sourceX + targetX) / 2

      return `M${sourceX},${sourceY}
              C${midX},${sourceY}
               ${midX},${targetY}
               ${targetX},${targetY}`
    })
    .attr('fill', 'none')
    .attr('stroke', '#d9d9d9')
    .attr('stroke-width', 2)

  const nodes = g.selectAll('.node')
    .data(root.descendants())
    .enter()
    .append('g')
    .attr('class', 'node')
    .attr('transform', (d) => `translate(${d.y!},${d.x! - NODE_HEIGHT / 2})`)

  const nodeGroups = nodes.append('g')
    .attr('class', 'node-group')
    .style('cursor', 'pointer')

  nodeGroups.append('rect')
    .attr('width', NODE_WIDTH)
    .attr('height', NODE_HEIGHT)
    .attr('rx', 8)
    .attr('ry', 8)
    .attr('fill', (d) => getNodeColor(d.data.access_type))
    .attr('fill-opacity', 0.15)
    .attr('stroke', (d) => getNodeBorderColor(d.data.access_type))
    .attr('stroke-width', 2)

  nodeGroups.append('text')
    .attr('x', NODE_WIDTH / 2)
    .attr('y', 22)
    .attr('text-anchor', 'middle')
    .attr('class', 'node-operation')
    .style('font-size', '13px')
    .style('font-weight', '600')
    .style('fill', '#262626')
    .text((d) => d.data.operation)

  nodeGroups.append('line')
    .attr('x1', 15)
    .attr('y1', 34)
    .attr('x2', NODE_WIDTH - 15)
    .attr('y2', 34)
    .attr('stroke', '#e8e8e8')
    .attr('stroke-width', 1)

  nodeGroups.append('text')
    .attr('x', 12)
    .attr('y', 50)
    .attr('text-anchor', 'start')
    .attr('class', 'node-table')
    .style('font-size', '11px')
    .style('fill', '#595959')
    .text((d) => d.data.table_name ? `表: ${d.data.table_name}` : '')

  nodeGroups.append('text')
    .attr('x', 12)
    .attr('y', 66)
    .attr('text-anchor', 'start')
    .attr('class', 'node-rows')
    .style('font-size', '11px')
    .style('fill', '#595959')
    .text((d) => `行数: ${d.data.estimated_rows.toLocaleString()}`)

  nodeGroups.append('text')
    .attr('x', 12)
    .attr('y', 80)
    .attr('text-anchor', 'start')
    .attr('class', 'node-cost')
    .style('font-size', '10px')
    .style('fill', '#8c8c8c')
    .text((d) => `cost: ${d.data.cost.toFixed(2)}`)

  nodeGroups
    .on('mouseenter', function (event, d) {
      d3.select(this).select('rect')
        .transition()
        .duration(150)
        .attr('fill-opacity', 0.3)
        .attr('stroke-width', 3)

      const tooltip = d3.select('body')
        .append('div')
        .attr('class', 'explain-tooltip')
        .style('position', 'absolute')
        .style('background', 'rgba(0, 0, 0, 0.85)')
        .style('color', '#fff')
        .style('padding', '10px 12px')
        .style('border-radius', '6px')
        .style('font-size', '12px')
        .style('pointer-events', 'none')
        .style('z-index', '1000')
        .style('max-width', '250px')
        .style('box-shadow', '0 4px 12px rgba(0,0,0,0.3)')

      let tooltipHtml = `<div style="font-weight:600;margin-bottom:6px;font-size:13px;">${d.data.operation}</div>`
      if (d.data.table_name) {
        tooltipHtml += `<div>表名: ${d.data.table_name}</div>`
      }
      tooltipHtml += `<div>估计行数: ${d.data.estimated_rows.toLocaleString()}</div>`
      tooltipHtml += `<div>操作成本: ${d.data.cost.toFixed(2)}</div>`
      if (d.data.access_type) {
        tooltipHtml += `<div>访问类型: ${d.data.access_type}</div>`
      }
      if (d.data.description) {
        tooltipHtml += `<div style="margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.2);">${d.data.description}</div>`
      }

      tooltip.html(tooltipHtml)
        .style('left', (event.pageX + 15) + 'px')
        .style('top', (event.pageY + 15) + 'px')
    })
    .on('mousemove', function (event) {
      d3.select('.explain-tooltip')
        .style('left', (event.pageX + 15) + 'px')
        .style('top', (event.pageY + 15) + 'px')
    })
    .on('mouseleave', function () {
      d3.select(this).select('rect')
        .transition()
        .duration(150)
        .attr('fill-opacity', 0.15)
        .attr('stroke-width', 2)

      d3.select('.explain-tooltip').remove()
    })
}

watch(
  () => props.plan,
  () => {
    nextTick(() => {
      renderTree()
    })
  },
  { deep: true }
)

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  nextTick(() => {
    renderTree()
  })

  if (svgContainer.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      renderTree()
    })
    resizeObserver.observe(svgContainer.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  d3.select('.explain-tooltip').remove()
})
</script>

<style lang="scss" scoped>
.explain-plan-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

.plan-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  flex-shrink: 0;
}

.plan-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
}

.plan-stats {
  display: flex;
  gap: 20px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  opacity: 0.85;
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
}

.legend {
  display: flex;
  gap: 20px;
  padding: 10px 16px;
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #595959;
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 2px solid;
}

.legend-full-scan {
  background: rgba(255, 77, 79, 0.15);
  border-color: #cf1322;
}

.legend-index-scan {
  background: rgba(82, 196, 26, 0.15);
  border-color: #389e0d;
}

.legend-temp-table {
  background: rgba(250, 173, 20, 0.15);
  border-color: #d48806;
}

.warnings-panel {
  padding: 10px 16px;
  background: #fffbe6;
  border-bottom: 1px solid #ffe58f;
  flex-shrink: 0;
}

.warnings-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #d48806;
  margin-bottom: 6px;
}

.warnings-list {
  margin: 0;
  padding-left: 20px;
  font-size: 12px;
  color: #874d00;

  li {
    margin-bottom: 4px;

    &:last-child {
      margin-bottom: 0;
    }
  }
}

.svg-container {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 10px;
  background: #fafafa;
}

.plan-svg {
  display: block;
}

:deep(.node-operation) {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

:deep(.node-table),
:deep(.node-rows),
:deep(.node-cost) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}
</style>
