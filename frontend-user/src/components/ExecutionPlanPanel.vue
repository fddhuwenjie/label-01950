<template>
  <div class="execution-plan-panel">
    <div class="panel-header">
      <div class="header-left">
        <ApartmentOutlined class="panel-icon" />
        <span class="panel-title">执行计划</span>
      </div>
      <div class="header-right">
        <div v-if="planData" class="stats">
          <span class="stat-item">
            <DollarOutlined class="stat-icon" />
            总代价: {{ planData.total_cost.toFixed(2) }}
          </span>
          <span class="stat-item">
            <TableOutlined class="stat-icon" />
            估计行数: {{ planData.total_estimated_rows.toLocaleString() }}
          </span>
          <span v-if="planData.has_bottlenecks" class="stat-item bottleneck">
            <WarningOutlined class="stat-icon" />
            瓶颈: {{ planData.bottleneck_count }}
          </span>
        </div>
        <button class="close-btn" @click="handleClose">
          <CloseOutlined />
        </button>
      </div>
    </div>

    <div class="panel-body">
      <div v-if="loading" class="loading-container">
        <a-spin size="large" tip="正在生成执行计划..." />
      </div>
      
      <div v-else-if="error" class="error-container">
        <AlertOutlined class="error-icon" />
        <span class="error-message">{{ error }}</span>
      </div>
      
      <div v-else-if="planData" class="plan-container">
        <ExecutionPlanTree :plan="planData.plan" />
      </div>
      
      <div v-else class="empty-container">
        <DatabaseOutlined class="empty-icon" />
        <span class="empty-text">点击 "Explain" 按钮生成执行计划</span>
      </div>
    </div>

    <div v-if="planData" class="panel-footer">
      <div class="legend">
        <span class="legend-item">
          <span class="legend-color index-scan"></span>
          索引扫描
        </span>
        <span class="legend-item">
          <span class="legend-color full-scan"></span>
          全表扫描
        </span>
        <span class="legend-item">
          <span class="legend-color temp-table"></span>
          临时表/排序
        </span>
        <span class="legend-item">
          <span class="legend-color join"></span>
          连接操作
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  ApartmentOutlined,
  DollarOutlined,
  TableOutlined,
  WarningOutlined,
  CloseOutlined,
  DatabaseOutlined,
  AlertOutlined
} from '@ant-design/icons-vue'
import ExecutionPlanTree from './ExecutionPlanTree.vue'
import type { ExplainResponse } from '@/api/explain'
import { explainSql } from '@/api/explain'
import type { SqlDialect } from '@/stores/editor'

const props = defineProps<{
  sql: string
  dialect: SqlDialect
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const planData = ref<ExplainResponse | null>(null)

function handleClose(): void {
  emit('close')
}

async function generatePlan(): Promise<void> {
  if (!props.sql.trim()) {
    error.value = '请先输入 SQL 语句'
    return
  }

  loading.value = true
  error.value = null
  planData.value = null

  try {
    planData.value = await explainSql({
      sql: props.sql,
      dialect: props.dialect
    })
  } catch (err: any) {
    error.value = err.message || '生成执行计划失败'
  } finally {
    loading.value = false
  }
}

watch(() => props.visible, (newVisible) => {
  if (newVisible && !planData.value && !loading.value) {
    generatePlan()
  }
})

watch([() => props.sql, () => props.dialect], () => {
  if (props.visible) {
    planData.value = null
    generatePlan()
  }
})
</script>

<style lang="scss" scoped>
.execution-plan-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background-color: #ffffff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #ffffff;

  .header-left {
    display: flex;
    align-items: center;
    gap: 8px;

    .panel-icon {
      font-size: 18px;
    }

    .panel-title {
      font-size: 15px;
      font-weight: 600;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;

    .stats {
      display: flex;
      gap: 16px;
      font-size: 13px;

      .stat-item {
        display: flex;
        align-items: center;
        gap: 4px;
        opacity: 0.9;

        .stat-icon {
          font-size: 14px;
        }

        &.bottleneck {
          color: #ffd666;
          font-weight: 500;
        }
      }
    }

    .close-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      background: rgba(255, 255, 255, 0.15);
      border: none;
      border-radius: 4px;
      color: #ffffff;
      cursor: pointer;
      transition: background-color 0.2s;

      &:hover {
        background: rgba(255, 255, 255, 0.25);
      }
    }
  }
}

.panel-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.loading-container,
.error-container,
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  padding: 40px;
}

.error-container {
  .error-icon {
    font-size: 48px;
    color: #ff4d4f;
    margin-bottom: 16px;
  }

  .error-message {
    font-size: 14px;
    color: #595959;
    text-align: center;
  }
}

.empty-container {
  .empty-icon {
    font-size: 64px;
    color: #d9d9d9;
    margin-bottom: 16px;
  }

  .empty-text {
    font-size: 14px;
    color: #8c8c8c;
  }
}

.plan-container {
  width: 100%;
  height: 100%;
}

.panel-footer {
  padding: 10px 16px;
  background-color: #fafafa;
  border-top: 1px solid #f0f0f0;

  .legend {
    display: flex;
    gap: 24px;
    font-size: 12px;
    color: #595959;

    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;

      .legend-color {
        display: inline-block;
        width: 14px;
        height: 14px;
        border-radius: 3px;

        &.index-scan {
          background-color: #52c41a;
        }

        &.full-scan {
          background-color: #ff4d4f;
        }

        &.temp-table {
          background-color: #faad14;
        }

        &.join {
          background-color: #1890ff;
        }
      }
    }
  }
}
</style>
