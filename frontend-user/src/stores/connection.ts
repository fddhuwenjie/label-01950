/**
 * Connection state management using Pinia.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ConnectionStatus } from '@/api/websocket'

export const useConnectionStore = defineStore('connection', () => {
  // State
  const status = ref<ConnectionStatus>('disconnected')
  const reconnectAttempt = ref(0)
  const maxReconnectAttempts = ref(10)
  const lastConnectedAt = ref<Date | null>(null)
  const lastDisconnectedAt = ref<Date | null>(null)

  // Getters
  const isConnected = computed(() => status.value === 'connected')
  const isConnecting = computed(() => status.value === 'connecting')
  const isDisconnected = computed(() => status.value === 'disconnected')

  const statusText = computed(() => {
    switch (status.value) {
      case 'connected':
        return '已连接'
      case 'connecting':
        return `连接中... (${reconnectAttempt.value}/${maxReconnectAttempts.value})`
      case 'disconnected':
        return '未连接'
      default:
        return '未知'
    }
  })

  const statusColor = computed(() => {
    switch (status.value) {
      case 'connected':
        return 'success'
      case 'connecting':
        return 'warning'
      case 'disconnected':
        return 'error'
      default:
        return 'default'
    }
  })

  // Actions
  function setStatus(newStatus: ConnectionStatus) {
    status.value = newStatus

    if (newStatus === 'connected') {
      lastConnectedAt.value = new Date()
      reconnectAttempt.value = 0
    } else if (newStatus === 'disconnected') {
      lastDisconnectedAt.value = new Date()
    }
  }

  function setReconnectAttempt(attempt: number) {
    reconnectAttempt.value = attempt
  }

  function reset() {
    status.value = 'disconnected'
    reconnectAttempt.value = 0
    lastConnectedAt.value = null
    lastDisconnectedAt.value = null
  }

  return {
    // State
    status,
    reconnectAttempt,
    maxReconnectAttempts,
    lastConnectedAt,
    lastDisconnectedAt,

    // Getters
    isConnected,
    isConnecting,
    isDisconnected,
    statusText,
    statusColor,

    // Actions
    setStatus,
    setReconnectAttempt,
    reset,
  }
})
