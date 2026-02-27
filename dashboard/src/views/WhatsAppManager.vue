<template>
  <div class="bw-page">
    <div class="bw-page-header">
      <div>
        <h1>WhatsApp Connection</h1>
        <p class="subtitle">Manage your WhatsApp Web session via Baileys</p>
      </div>
      <div class="header-actions">
        <Button label="Refresh" icon="pi pi-refresh" class="p-button-outlined p-button-sm" :loading="loading" @click="refresh" />
        <Button label="Restart" icon="pi pi-replay" severity="warning" class="p-button-outlined p-button-sm" :loading="busyRestart" @click="restartConnection" />
        <Button label="Logout" icon="pi pi-sign-out" severity="danger" class="p-button-outlined p-button-sm" :loading="busyLogout" @click="logoutConnection" />
      </div>
    </div>

    <div class="wa-grid">
      <!-- Status Card -->
      <div class="bw-section">
        <div class="bw-section-header">
          <h2><i class="pi pi-info-circle"></i> Connection Status</h2>
          <Tag :value="statusLabel" :severity="statusSeverity" />
        </div>
        <div class="bw-section-body">
          <div class="kv-list">
            <div class="kv-row">
              <span class="kv-label">Provider</span>
              <span class="kv-value">Baileys (WhatsApp Web)</span>
            </div>
            <div class="kv-row">
              <span class="kv-label">State</span>
              <span class="kv-value">
                <span class="bw-status-dot" :class="status?.state === 'connected' ? 'bw-status-dot--online' : 'bw-status-dot--offline'" style="margin-right: 6px"></span>
                {{ status?.state || 'unknown' }}
              </span>
            </div>
            <div class="kv-row">
              <span class="kv-label">Phone</span>
              <span class="kv-value">{{ userPhone }}</span>
            </div>
            <div class="kv-row">
              <span class="kv-label">Name</span>
              <span class="kv-value">{{ userName }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- QR Card -->
      <div class="bw-section qr-section">
        <div class="bw-section-header">
          <h2><i class="pi pi-qrcode"></i> QR Scan</h2>
        </div>
        <div class="bw-section-body qr-body">
          <!-- Connected -->
          <div v-if="status?.state === 'connected'" class="qr-connected">
            <div class="connected-icon">
              <i class="pi pi-check-circle"></i>
            </div>
            <p>WhatsApp is connected</p>
            <small>No QR scan required</small>
          </div>

          <!-- QR Available -->
          <div v-else-if="qrImage" class="qr-available">
            <div class="qr-image-wrap">
              <img :src="qrImage" alt="WhatsApp QR Code" class="qr-img" />
            </div>
            <div class="qr-steps">
              <div class="qr-step"><span class="step-num">1</span> Open WhatsApp on phone</div>
              <div class="qr-step"><span class="step-num">2</span> Settings → Linked Devices</div>
              <div class="qr-step"><span class="step-num">3</span> Tap "Link a Device" and scan</div>
            </div>
          </div>

          <!-- Waiting -->
          <div v-else class="qr-waiting">
            <i class="pi pi-spin pi-spinner" style="font-size: 1.5rem; color: var(--bw-brand-primary)"></i>
            <p>Waiting for QR code...</p>
            <small>Make sure Baileys server is running</small>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { api } from '@/services/api'
import { useSystemStore } from '@/stores/system'
import type { BaileysStatus } from '@/types'

const systemStore = useSystemStore()
const loading = ref(false)
const busyRestart = ref(false)
const busyLogout = ref(false)
const status = ref<BaileysStatus | null>(null)
const qrImage = ref<string>('')
let timer: number | null = null

const statusLabel = computed(() => {
  const state = status.value?.state
  if (state === 'connected') return 'Connected'
  if (state === 'qr_ready' || state === 'logged_out') return 'Scan Required'
  if (state === 'connecting' || state === 'reconnecting') return 'Connecting'
  if (state === 'disconnected') return 'Disconnected'
  return 'Unknown'
})

const statusSeverity = computed(() => {
  const state = status.value?.state
  if (state === 'connected') return 'success'
  if (state === 'qr_ready' || state === 'logged_out' || state === 'connecting' || state === 'reconnecting') return 'warning'
  return 'danger'
})

const userPhone = computed(() => {
  const id = status.value?.user?.id || ''
  return id ? id.split(':')[0] : 'Not connected'
})

const userName = computed(() => status.value?.user?.name || 'Not connected')

const refresh = async () => {
  loading.value = true
  try {
    const latestStatus = await api.getBaileysStatus()
    status.value = latestStatus
    systemStore.setBaileysStatus(latestStatus)
    if (latestStatus.state !== 'connected') {
      const qr = await api.getBaileysQr()
      qrImage.value = qr.qrImage || ''
    } else {
      qrImage.value = ''
    }
  } catch (error) {
    status.value = { state: 'unreachable', error: error instanceof Error ? error.message : String(error) }
    qrImage.value = ''
  } finally {
    loading.value = false
  }
}

const restartConnection = async () => {
  busyRestart.value = true
  try { await api.restartBaileys(); await refresh() } finally { busyRestart.value = false }
}

const logoutConnection = async () => {
  busyLogout.value = true
  try { await api.disconnectWhatsApp(); await refresh() } finally { busyLogout.value = false }
}

onMounted(async () => {
  await refresh()
  timer = window.setInterval(refresh, 5000)
})

onBeforeUnmount(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.header-actions {
  display: flex;
  gap: var(--bw-space-sm);
  flex-wrap: wrap;
}

.wa-grid {
  display: grid;
  grid-template-columns: 1fr 1.3fr;
  gap: var(--bw-space-lg);
}

@media (max-width: 960px) {
  .wa-grid { grid-template-columns: 1fr; }
}

/* KV list */
.kv-list {
  display: flex;
  flex-direction: column;
}

.kv-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.7rem 0;
  border-bottom: 1px solid var(--bw-border-subtle);
}

.kv-row:last-child { border-bottom: none; }

.kv-label {
  font-size: 0.82rem;
  color: var(--bw-text-muted);
}

.kv-value {
  font-weight: 600;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
}

/* QR states */
.qr-body {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 320px;
}

.qr-connected {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--bw-space-sm);
  color: var(--bw-text-secondary);
}

.connected-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(34, 197, 94, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--bw-space-sm);
}

.connected-icon i {
  font-size: 2rem;
  color: #22c55e;
}

.qr-available {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--bw-space-lg);
  width: 100%;
}

.qr-image-wrap {
  padding: 1rem;
  background: white;
  border-radius: var(--bw-radius-lg);
  box-shadow: var(--bw-shadow-md);
}

.qr-img {
  width: 260px;
  max-width: 100%;
  display: block;
}

.qr-steps {
  display: flex;
  flex-direction: column;
  gap: var(--bw-space-sm);
  width: 100%;
  max-width: 300px;
}

.qr-step {
  display: flex;
  align-items: center;
  gap: var(--bw-space-sm);
  font-size: 0.82rem;
  color: var(--bw-text-secondary);
}

.step-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--bw-brand-primary-alpha);
  color: var(--bw-brand-primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  flex-shrink: 0;
}

.qr-waiting {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--bw-space-sm);
  color: var(--bw-text-muted);
}
</style>
