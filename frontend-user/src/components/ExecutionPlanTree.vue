<template>
  <div class="execution-plan-container">
    <div ref="treeContainer" class="tree-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as d3 from 'd3'
import type { ExplainPlanNode } from '@/api/explain'

interface HierarchyNode extends d3.HierarchyNode<ExplainPlanNode> {
  x: number
  y: number
}

const props = defineProps<{
  plan: ExplainPlanNode | null
}>()

const treeContainer = ref<HTMLElement | null>(null)
let svg: d3.Selection<SVGSVGElement, unknown, null, undefined> | null = null
let g: d3.Selection<SVGGElement, unknown, null, undefined> | null = null
let zoom: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null

const nodeWidth = 220
const nodeHeight = 90
const gapX = 40
const gapY = 60

function getNodeColor(node: ExplainPlanNode): string {
  if (node.is_bottleneck && (node.operation_type === 'TABLE_SCAN' || node.operation_type === 'SUBQUERY')) {
    return '#ff4d4f'
  }
  if (node.operation_type === 'INDEX_SCAN') {
    return '#52c41a'
  }
  if (node.operation_type === 'TEMP_TABLE' || node.operation_type === 'SORT') {
    return '#faad14'
  }
  if (node.operation_type === 'HASH_JOIN' || node.operation_type === 'NESTED_LOOP_JOIN' || node.operation_type === 'MERGE_JOIN') {
    return '#1890ff'
  }
  return '#8c8c8c'
}

function getNodeBorderColor(node: ExplainPlanNode): string {
  return node.is_bottleneck ? '#ff4d4f' : '#d9d9d9'
}

function initSvg(): void {
  if (!treeContainer.value) return

  const containerWidth = treeContainer.value.clientWidth
  const containerHeight = treeContainer.value.clientHeight

  const svgSelection = d3.select(treeContainer.value)
    .append('svg')
    .attr('width', containerWidth)
    .attr('height', containerHeight)
    .style('font-family', '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif')

  svg = svgSelection

  const zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.2, 3])
    .on('zoom', (event) => {
      g?.attr('transform', event.transform)
    })

  zoom = zoomBehavior
  svgSelection.call(zoomBehavior)

  g = svgSelection.append('g')
    .attr('transform', 'translate(40, 20)')
}

function renderTree(rootData: ExplainPlanNode): void {
  if (!g || !svg || !treeContainer.value) return

  g.selectAll('*').remove()

  const root = d3.hierarchy(rootData) as HierarchyNode

  const treeLayout = d3.tree<ExplainPlanNode>()
    .nodeSize([nodeWidth + gapX, nodeHeight + gapY])

  treeLayout(root)

  const nodes = root.descendants() as HierarchyNode[]
  const links = root.links()

  const linkGenerator = d3.linkHorizontal<d3.HierarchyLink<ExplainPlanNode>, HierarchyNode>()
    .x(d => d.x)
    .y(d => d.y)

  g.selectAll<SVGPathElement, d3.HierarchyLink<ExplainPlanNode>>('.link')
    .data(links)
    .enter()
    .append('path')
    .attr('class', 'link')
    .attr('fill', 'none')
    .attr('stroke', '#d9d9d9')
    .attr('stroke-width', 2)
    .attr('d', d => linkGenerator(d))

  const nodeGroups = g.selectAll<SVGGElement, HierarchyNode>('.node')
    .data(nodes)
    .enter()
    .append('g')
    .attr('class', 'node')
    .attr('transform', d => `translate(${d.x - nodeWidth / 2}, ${d.y - nodeHeight / 2})`)

  nodeGroups.append('rect')
    .attr('width', nodeWidth)
    .attr('height', nodeHeight)
    .attr('rx', 8)
    .attr('ry', 8)
    .attr('fill', '#ffffff')
    .attr('stroke', d => getNodeBorderColor(d.data))
    .attr('stroke-width', d => d.data.is_bottleneck ? 3 : 1)
    .attr('filter', 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1))')

  nodeGroups.append('rect')
    .attr('x', 0)
    .attr('y', 0)
    .attr('width', 6)
    .attr('height', nodeHeight)
    .attr('rx', 3)
    .attr('fill', d => getNodeColor(d.data))

  nodeGroups.append('text')
    .attr('x', 20)
    .attr('y', 22)
    .attr('font-size', '14px')
    .attr('font-weight', '600')
    .attr('fill', '#262626')
    .text(d => d.data.operation_type.replace(/_/g, ' '))

  if (nodes.some(d => d.data.table_name)) {
    nodeGroups.append('text')
      .attr('x', 20)
      .attr('y', 42)
      .attr('font-size', '12px')
      .attr('fill', '#595959')
      .text(d => d.data.table_name ? `表: ${d.data.table_name}` : '')
  }

  nodeGroups.append('text')
    .attr('x', 20)
    .attr('y', 60)
    .attr('font-size', '11px')
    .attr('fill', '#8c8c8c')
    .text(d => `行数: ${d.data.estimated_rows.toLocaleString()}`)

  nodeGroups.append('text')
    .attr('x', 20)
    .attr('y', 76)
    .attr('font-size', '11px')
    .attr('fill', '#8c8c8c')
    .text(d => `Cost: ${d.data.cost.toFixed(2)}`)

  if (nodes.some(d => d.data.access_type)) {
    nodeGroups.append('text')
      .attr('x', 120)
      .attr('y', 60)
      .attr('font-size', '11px')
      .attr('fill', '#8c8c8c')
      .text(d => d.data.access_type || '')
  }

  const bounds = g.node()?.getBBox()
  if (bounds && svg && zoom) {
    const containerWidth = treeContainer.value?.clientWidth || 800
    const containerHeight = treeContainer.value?.clientHeight || 400
    
    const scale = Math.min(
      (containerWidth - 80) / bounds.width,
      (containerHeight - 40) / bounds.height,
      1
    )
    
    const translateX = (containerWidth - bounds.width * scale) / 2 - bounds.x * scale
    const translateY = 20 - bounds.y * scale
    
    const transform = d3.zoomIdentity
      .translate(translateX, translateY)
      .scale(scale)
    
    svg.call(zoom.transform, transform)
  }
}

function resize(): void {
  if (!treeContainer.value || !svg) return
  
  const containerWidth = treeContainer.value.clientWidth
  const containerHeight = treeContainer.value.clientHeight
  
  svg.attr('width', containerWidth)
    .attr('height', containerHeight)
}

watch(() => props.plan, (newPlan) => {
  if (newPlan) {
    renderTree(newPlan)
  }
})

onMounted(() => {
  initSvg()
  if (props.plan) {
    renderTree(props.plan)
  }
  window.addEventListener('resize', resize)
})

onUnmounted(() => {
  window.removeEventListener('resize', resize)
})
</script>

<style lang="scss" scoped>
.execution-plan-container {
  width: 100%;
  height: 100%;
  background-color: #fafafa;
  border-radius: 4px;
  overflow: hidden;
}

.tree-container {
  width: 100%;
  height: 100%;
}
</style>
