<template>
  <div class="bw-page">
    <div class="bw-page-header">
      <div>
        <h1>Live Logs</h1>
        <p class="subtitle">Real-time application logs</p>
      </div>
      <Button icon="pi pi-refresh" label="Refresh" class="p-button-outlined p-button-sm" :loading="loading" @click="loadLogs" />
    </div>

    <!-- Toolbar -->
    <div class="bw-section toolbar-section">
      <div class="bw-section-body">
        <div class="toolbar-row">
          <div class="toolbar-field">
            <label>Source</label>
            <Dropdown v-model="source" :options="sourceOptions" optionLabel="label" optionValue="value" class="p-dropdown-sm" />
          </div>
          <div class="toolbar-field">
            <label>Level</label>
            <Dropdown v-model="level" :options="levelOptions" optionLabel="label" optionValue="value" class="p-dropdown-sm" />
          </div>
          <div class="toolbar-field">
            <label>Limit</label>
            <InputNumber v-model="limit" :min="20" :max="1000" :step="20" class="p-inputtext-sm limit-input" />
          </div>
          <div class="toolbar-field switch-field">
            <InputSwitch v-model="autoRefresh" />
            <label>Auto-refresh</label>
          </div>
        </div>
      </div>
    </div>

    <!-- Logs -->
    <div class="bw-section">
      <div class="bw-section-header">
        <span class="log-meta">{{ logs.length }} entries</span>
        <span v-if="lastUpdated" class="log-meta">Updated {{ lastUpdated }}</span>
      </div>
      <div class="log-console">
        <div v-if="logs.length === 0" class="log-empty">No logs found for selected filters.</div>
        <div v-for="log in logs" :key="log.id" class="log-line" :class="`level-${(log.level || 'INFO').toLowerCase()}`">
          <span class="log-ts">[{{ formatTime(log.timestamp) }}]</span>
          <span class="log-src">[{{ log.source || log.logger || 'app' }}]</span>
          <span class="log-lvl">[{{ log.level }}]</span>
          <span class="log-msg">{{ log.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '@/services/api'
import type { LogEntry } from '@/types'
import Button from 'primevue/button'
import Dropdown from 'primevue/dropdown'
import InputNumber from 'primevue/inputnumber'
import InputSwitch from 'primevue/inputswitch'

const logs = ref<LogEntry[]>([])
const loading = ref(false)
const source = ref('all')
const level = ref('')
const limit = ref(200)
const autoRefresh = ref(true)
const lastUpdated = ref('')
let timer: number | null = null

const sourceOptions = [
  { label: 'All', value: 'all' },
  { label: 'Gateway', value: 'gateway' },
  { label: 'Service', value: 'service' },
  { label: 'FastAPI', value: 'fastapi' },
  { label: 'Baileys', value: 'baileys' },
]

const levelOptions = [
  { label: 'All', value: '' },
  { label: 'DEBUG', value: 'DEBUG' },
  { label: 'INFO', value: 'INFO' },
  { label: 'WARNING', value: 'WARNING' },
  { label: 'ERROR', value: 'ERROR' },
  { label: 'CRITICAL', value: 'CRITICAL' },
]

const formatTime = (iso: string) => {
  if (!iso) return '-'
  const dt = new Date(iso)
  return Number.isNaN(dt.getTime()) ? iso : dt.toLocaleString()
}

const loadLogs = async () => {
  loading.value = true
  try {
    logs.value = await api.getLogs(level.value || undefined, limit.value, source.value)
    lastUpdated.value = new Date().toLocaleTimeString()
  } catch (error) {
    console.error('Failed to load logs', error)
  } finally {
    loading.value = false
  }
}

const startAutoRefresh = () => {
  if (timer) window.clearInterval(timer)
  if (!autoRefresh.value) return
  timer = window.setInterval(loadLogs, 5000)
}

watch(autoRefresh, startAutoRefresh)
watch([source, level, limit], loadLogs)

onMounted(async () => { await loadLogs(); startAutoRefresh() })
onBeforeUnmount(() => { if (timer) window.clearInterval(timer) })
</script>

<style scoped>
.toolbar-section { margin-bottom: var(--bw-space-lg); }

.toolbar-row {
  display: flex;
  align-items: flex-end;
  gap: var(--bw-space-md);
  flex-wrap: wrap;
}

.toolbar-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.toolbar-field label {
  font-size: 0.72rem;
  color: var(--bw-text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.switch-field {
  flex-direction: row;
  align-items: center;
  gap: var(--bw-space-sm);
  margin-bottom: 0.2rem;
}

.switch-field label {
  text-transform: none;
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--bw-text-secondary);
}

.limit-input { width: 100px; }

.log-meta {
  font-size: 0.75rem;
  color: var(--bw-text-muted);
}

/* Log console */
.log-console {
  background: #070e1a;
  border-top: 1px solid var(--bw-border-subtle);
  padding: 0.6rem 1rem;
  max-height: 65vh;
  overflow: auto;
  font-family: var(--bw-font-mono);
  font-size: 0.78rem;
  line-height: 1.7;
}

.log-line {
  padding: 0.1rem 0.25rem;
  border-radius: 2px;
  color: #d1ddf0;
  transition: background var(--bw-transition-fast);
}

.log-line:hover {
  background: rgba(148, 163, 184, 0.06);
}

.log-empty {
  color: var(--bw-text-muted);
  padding: 0.5rem 0;
}

.log-ts { color: #7191b5; }
.log-src { color: #6cc9b3; }
.log-lvl { color: #a3c4f5; }

.level-error .log-lvl,
.level-critical .log-lvl { color: #ff8e8e; }
.level-error .log-msg,
.level-critical .log-msg { color: #ffc4c4; }

.level-warning .log-lvl { color: #ffd487; }
</style>
