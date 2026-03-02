<template>
  <a-select
    v-model:value="selectedDialect"
    style="width: 140px"
    :options="dialectOptions"
    @change="handleChange"
  />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { SqlDialect } from '@/stores/editor'

const props = defineProps<{
  modelValue: SqlDialect
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: SqlDialect): void
  (e: 'change', value: SqlDialect): void
}>()

const selectedDialect = ref<SqlDialect>(props.modelValue)

const dialectOptions = [
  { value: 'ansi', label: 'ANSI SQL' },
  { value: 'sparksql', label: 'SparkSQL' },
  { value: 'hive', label: 'HiveSQL' },
]

watch(
  () => props.modelValue,
  (newValue) => {
    selectedDialect.value = newValue
  }
)

function handleChange(value: SqlDialect) {
  emit('update:modelValue', value)
  emit('change', value)
}
</script>
