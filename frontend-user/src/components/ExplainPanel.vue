<template>
  <div class="explain-panel">
    <div class="panel-header">
      <span class="panel-title">
        <PartitionOutlined />
        执行计划
      </span>
      <span v-if="plan" class="panel-meta">
        总成本: <strong>{{ plan.total_cost }}</strong>
      </span>
      <span v-if="plan && plan.warnings.length > 0" class="panel-warnings">
        <WarningOutlined /> {{ plan.warnings.length }} 项性能提示
      </span>
      <a-button type="text" size="small" class="close-btn" @click="$emit('close')">
        <CloseOutlined />
      </a-button>
    </div>

    <div class="panel-body">
      <div v-if="loading" class="placeholder">
        <a-spin tip="正在生成执行计划..." />
      </div>

      <div v-else-if="error" class="placeholder error">
        <ExclamationCircleOutlined />
        <span>{{ error }}</span>
      </div>

      <a-empty
        v-else-if="!plan"
        description="点击 Explain 按钮生成执行计划"
      />

      <template v-else>
        <div ref="treeContainer" class="tree-container"></div>

        <div v-if="plan.warnings.length > 0" class="warnings">
          <div class="warnings-title">
            <WarningOutlined /> 性能瓶颈警告
          </div>
          <ul>
            <li v-for="(w, i) in plan.warnings" :key="i">{{ w }}</li>
          </ul>
        </div>

        <div class="legend">
          <span class="legend-item"><i class="dot full" /> 全表扫描</span>
          <span class="legend-item"><i class="dot index" /> 索引扫描</span>
          <span class="legend-item"><i class="dot temp" /> 临时表</span>
          <span class="legend-item"><i class="dot ref" /> 引用 / 其他</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onUnmounted } from 'vue'
import * as d3 from 'd3'
import {
  CloseOutlined,
  PartitionOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons-vue'
import type { ExplainNode, ExplainResponse, AccessType } from '@/api/explain'

const props = defineProps<{
  plan: ExplainResponse | null
  loading: boolean
  error: string
}>()

defineEmits<{
  (e: 'close'): void
}>()

const treeContainer = ref<HTMLDivElement | null>(null)
let resizeObserver: ResizeObserver | null = null

interface NodeDatum extends ExplainNode {
  children: NodeDatum[]
}

function colorForAccess(access: AccessType): string {
  switch (access) {
    case 'full_scan':
      return '#f5222d' // red - bottleneck
    case 'index_scan':
      return '#52c41a' // green - good
    case 'temp_table':
      return '#faad14' // yellow - temp
    case 'const':
      return '#1677ff'
    case 'ref':
      return '#13c2c2'
    default:
      return '#8c8c8c'
  }
}

function formatRows(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return String(n)
}

function renderTree(root: ExplainNode) {
  const container = treeContainer.value
  if (!container) return

  // Clear previous render
  d3.select(container).selectAll('*').remove()

  const width = container.clientWidth || 800
  const height = container.clientHeight || 360

  const svg = d3
    .select(container)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', [0, 0, width, height])
    .attr('class', 'explain-svg')

  const g = svg.append('g')

  // Zoom/pan support
  const zoom = d3
    .zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.4, 2.5])
    .on('zoom', (event) => {
      g.attr('transform', event.transform.toString())
    })
  svg.call(zoom as never)

  const hierarchy = d3.hierarchy<ExplainNode>(root, (d) => d.children || [])

  const nodeWidth = 180
  const nodeHeight = 70
  const horizontalGap = 60
  const verticalGap = 40

  const treeLayout = d3
    .tree<ExplainNode>()
    .nodeSize([nodeHeight + verticalGap, nodeWidth + horizontalGap])

  treeLayout(hierarchy)

  // d3.tree (with nodeSize) gives us [y, x] in tree-coords; we'll render
  // top-down: x = node.x, y = node.depth * (nodeHeight + verticalGap)
  const nodes = hierarchy.descendants()
  const links = hierarchy.links()

  // Compute bounds to translate so the tree is centered horizontally
  const xs = nodes.map((n) => n.x ?? 0)
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const treeWidth = maxX - minX + nodeWidth
  const offsetX = (width - treeWidth) / 2 - minX
  const offsetY = 30

  // Links as orthogonal paths
  const linkGen = d3
    .linkVertical<d3.HierarchyLink<ExplainNode>, d3.HierarchyNode<ExplainNode>>()
    .x((d) => (d.x ?? 0) + offsetX + nodeWidth / 2)
    .y((d) => d.depth * (nodeHeight + verticalGap) + offsetY + nodeHeight / 2)

  g.append('g')
    .attr('class', 'links')
    .attr('fill', 'none')
    .attr('stroke', '#bfbfbf')
    .attr('stroke-width', 1.5)
    .selectAll('path')
    .data(links)
    .join('path')
    .attr('d', linkGen as never)

  // Nodes
  const nodeG = g
    .append('g')
    .attr('class', 'nodes')
    .selectAll('g.node')
    .data(nodes)
    .join('g')
    .attr('class', 'node')
    .attr(
      'transform',
      (d) =>
        `translate(${(d.x ?? 0) + offsetX},${
          d.depth * (nodeHeight + verticalGap) + offsetY
        })`,
    )

  nodeG
    .append('rect')
    .attr('width', nodeWidth)
    .attr('height', nodeHeight)
    .attr('rx', 6)
    .attr('ry', 6)
    .attr('fill', (d) => colorForAccess(d.data.access_type as AccessType))
    .attr('fill-opacity', 0.15)
    .attr('stroke', (d) => colorForAccess(d.data.access_type as AccessType))
    .attr('stroke-width', (d) => (d.data.bottleneck ? 2.5 : 1.5))

  // Operation
  nodeG
    .append('text')
    .attr('x', 10)
    .attr('y', 18)
    .attr('font-size', 12)
    .attr('font-weight', 600)
    .attr('fill', '#262626')
    .text((d) => d.data.operation)

  // Table name
  nodeG
    .append('text')
    .attr('x', 10)
    .attr('y', 36)
    .attr('font-size', 11)
    .attr('fill', '#595959')
    .text((d) => (d.data.table ? `表: ${d.data.table}` : ''))

  // Rows + cost
  nodeG
    .append('text')
    .attr('x', 10)
    .attr('y', 52)
    .attr('font-size', 10)
    .attr('fill', '#8c8c8c')
    .text((d) => `行数 ~${formatRows(d.data.estimated_rows)}  cost=${d.data.cost.toFixed(0)}`)

  // Access type badge
  nodeG
    .append('text')
    .attr('x', nodeWidth - 10)
    .attr('y', 18)
    .attr('text-anchor', 'end')
    .attr('font-size', 10)
    .attr('font-weight', 600)
    .attr('fill', (d) => colorForAccess(d.data.access_type as AccessType))
    .text((d) => d.data.access_type)

  // Tooltip via <title>
  nodeG.append('title').text((d) => {
    const lines = [
      `Operation: ${d.data.operation}`,
      d.data.table ? `Table: ${d.data.table}` : null,
      `Access: ${d.data.access_type}`,
      `Estimated rows: ${d.data.estimated_rows}`,
      `Cost: ${d.data.cost}`,
      d.data.bottleneck ? '⚠ 性能瓶颈' : null,
    ].filter(Boolean)
    if (d.data.details) {
      for (const [k, v] of Object.entries(d.data.details)) {
        lines.push(`${k}: ${String(v)}`)
      }
    }
    return lines.join('\n')
  })
}

async function rerender() {
  if (!props.plan) return
  await nextTick()
  renderTree(props.plan.root as NodeDatum)
}

watch(
  () => props.plan,
  () => {
    rerender()
  },
)

watch(
  () => treeContainer.value,
  (el) => {
    if (resizeObserver) {
      resizeObserver.disconnect()
      resizeObserver = null
    }
    if (el) {
      resizeObserver = new ResizeObserver(() => {
        rerender()
      })
      resizeObserver.observe(el)
    }
  },
)

onUnmounted(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
})
</script>

<style lang="scss" scoped>
@import '@/styles/variables.scss';

.explain-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background-color: $bg-card;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-sm $spacing-md;
  border-bottom: 1px solid #e8e8e8;
  background-color: #fafafa;

  .panel-title {
    display: flex;
    align-items: center;
    gap: $spacing-xs;
    font-weight: 600;
    color: $text-primary;
  }

  .panel-meta {
    font-size: $font-size-sm;
    color: $text-secondary;
  }

  .panel-warnings {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: $font-size-sm;
    color: #faad14;
  }

  .close-btn {
    margin-left: auto;
  }
}

.panel-body {
  flex: 1;
  position: relative;
  overflow: hidden;
  padding: $spacing-sm;
  display: flex;
  flex-direction: column;
}

.tree-container {
  flex: 1;
  min-height: 240px;
  width: 100%;
  background: #fff;
  border-radius: $border-radius-md;
  border: 1px solid #f0f0f0;
  overflow: hidden;

  :deep(svg.explain-svg) {
    width: 100%;
    height: 100%;
    display: block;
  }
}

.placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: $spacing-sm;
  color: $text-secondary;

  &.error {
    color: #f5222d;
  }
}

.warnings {
  margin-top: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  background-color: #fffbe6;
  border: 1px solid #ffe58f;
  border-radius: $border-radius-md;
  font-size: $font-size-sm;
  color: #874d00;

  .warnings-title {
    font-weight: 600;
    margin-bottom: 4px;
  }

  ul {
    margin: 0;
    padding-left: 18px;
  }
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-md;
  padding: $spacing-xs $spacing-md;
  font-size: $font-size-sm;
  color: $text-secondary;

  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;

    &.full {
      background: #f5222d;
    }
    &.index {
      background: #52c41a;
    }
    &.temp {
      background: #faad14;
    }
    &.ref {
      background: #13c2c2;
    }
  }
}
</style>
