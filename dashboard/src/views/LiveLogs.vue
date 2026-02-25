<template>
  <div class="page-container">
    <div class="page-head">
      <h1>Live Logs</h1>
      <div class="nav-links">
        <router-link to="/" class="nav-link">Overview</router-link>
        <router-link to="/system" class="nav-link">System Control</router-link>
        <router-link to="/settings" class="nav-link">Settings</router-link>
      </div>
    </div>

    <Card class="toolbar-card">
      <template #content>
        <div class="toolbar">
          <label>
            Source
            <select v-model="source">
              <option value="all">All</option>
              <option value="gateway">Gateway</option>
              <option value="service">Service</option>
              <option value="fastapi">FastAPI</option>
              <option value="baileys">Baileys</option>
            </select>
          </label>

          <label>
            Level
            <select v-model="level">
              <option value="">All</option>
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </label>

          <label>
            Limit
            <input v-model.number="limit" type="number" min="20" max="1000" step="20" />
          </label>

          <label class="switch">
            <input v-model="autoRefresh" type="checkbox" />
            Auto refresh
          </label>

          <Button icon="pi pi-refresh" label="Refresh" :loading="loading" @click="loadLogs" />
        </div>
      </template>
    </Card>

    <Card>
      <template #content>
        <div class="meta-row">
          <span>Showing {{ logs.length }} entries</span>
          <span v-if="lastUpdated">Last updated: {{ lastUpdated }}</span>
        </div>
        <div class="log-console">
          <div v-if="logs.length === 0" class="empty">No logs found for the selected filters.</div>
          <div v-for="log in logs" :key="log.id" class="log-line" :class="`level-${(log.level || 'INFO').toLowerCase()}`">
            <span class="ts">[{{ formatTime(log.timestamp) }}]</span>
            <span class="src">[{{ log.source || log.logger || 'app' }}]</span>
            <span class="lvl">[{{ log.level }}]</span>
            <span class="msg">{{ log.message }}</span>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { api } from '@/services/api'
import type { LogEntry } from '@/types'
import Card from 'primevue/card'
import Button from 'primevue/button'

const logs = ref<LogEntry[]>([])
const loading = ref(false)
const source = ref('all')
const level = ref('')
const limit = ref(200)
const autoRefresh = ref(true)
const lastUpdated = ref('')
let timer: number | null = null

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

watch(autoRefresh, () => startAutoRefresh())
watch([source, level, limit], () => loadLogs())

onMounted(async () => {
  await loadLogs()
  startAutoRefresh()
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<style scoped>
.page-container {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  gap: 1rem;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.nav-links {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.nav-link {
  padding: 0.25rem 0.6rem;
  border: 1px solid var(--surface-border);
  border-radius: 999px;
  text-decoration: none;
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

.toolbar {
  display: flex;
  align-items: end;
  gap: 0.75rem;
  flex-wrap: wrap;
}

label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

select,
input[type="number"] {
  min-width: 130px;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: var(--surface-card);
  color: var(--text-color);
  padding: 0.4rem 0.5rem;
}

.switch {
  flex-direction: row;
  align-items: center;
  margin-bottom: 0.35rem;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  margin-bottom: 0.75rem;
}

.log-console {
  background: #091222;
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  padding: 0.8rem;
  max-height: 65vh;
  overflow: auto;
  font-family: Consolas, "Courier New", monospace;
  font-size: 0.8rem;
}

.log-line {
  padding: 0.16rem 0.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: #d8e2f1;
  word-break: break-word;
}

.log-line:last-child {
  border-bottom: none;
}

.ts {
  color: #8aa4c8;
}

.src {
  color: #7cdcc0;
}

.lvl {
  color: #b9d2ff;
}

.level-error .lvl,
.level-critical .lvl {
  color: #ff8e8e;
}

.level-warning .lvl {
  color: #ffd487;
}

.empty {
  color: #9db3ce;
  padding: 0.4rem 0;
}
</style>
