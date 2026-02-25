<template>
  <div class="whatsapp-page">
    <div class="top-row">
      <h1>WhatsApp Connection</h1>
      <div class="actions">
        <Button label="Refresh" icon="pi pi-refresh" outlined :loading="loading" @click="refresh" />
        <Button label="Restart" icon="pi pi-replay" severity="warning" outlined :loading="busyRestart" @click="restartConnection" />
        <Button label="Logout" icon="pi pi-sign-out" severity="danger" outlined :loading="busyLogout" @click="logoutConnection" />
      </div>
    </div>

    <div class="content-grid">
      <Card class="status-card">
        <template #title>
          <div class="title-line">
            <span>Status</span>
            <Tag :value="statusLabel" :severity="statusSeverity" />
          </div>
        </template>
        <template #content>
          <div class="kv"><span>Provider</span><strong>Baileys (WhatsApp Web)</strong></div>
          <div class="kv"><span>State</span><strong>{{ status?.state || 'unknown' }}</strong></div>
          <div class="kv"><span>Phone</span><strong>{{ userPhone }}</strong></div>
          <div class="kv"><span>Name</span><strong>{{ userName }}</strong></div>
          <small class="hint">This page is fully served via port 8000 APIs.</small>
        </template>
      </Card>

      <Card class="qr-card">
        <template #title>QR Scan</template>
        <template #content>
          <div v-if="status?.state === 'connected'" class="connected-block">
            <i class="pi pi-check-circle"></i>
            <p>WhatsApp is connected. No QR scan required.</p>
          </div>

          <div v-else-if="qrImage" class="qr-block">
            <img :src="qrImage" alt="WhatsApp QR Code" class="qr-image" />
            <ol>
              <li>Open WhatsApp on phone</li>
              <li>Settings > Linked Devices</li>
              <li>Tap Link a Device and scan this QR</li>
            </ol>
          </div>

          <div v-else class="empty-qr">
            <i class="pi pi-qrcode"></i>
            <p>Waiting for QR from Baileys...</p>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import Card from 'primevue/card'
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
    status.value = {
      state: 'unreachable',
      error: error instanceof Error ? error.message : String(error),
    }
    qrImage.value = ''
  } finally {
    loading.value = false
  }
}

const restartConnection = async () => {
  busyRestart.value = true
  try {
    await api.restartBaileys()
    await refresh()
  } finally {
    busyRestart.value = false
  }
}

const logoutConnection = async () => {
  busyLogout.value = true
  try {
    await api.disconnectWhatsApp()
    await refresh()
  } finally {
    busyLogout.value = false
  }
}

onMounted(async () => {
  await refresh()
  timer = window.setInterval(refresh, 5000)
})

onBeforeUnmount(() => {
  if (timer) {
    clearInterval(timer)
  }
})
</script>

<style scoped>
.whatsapp-page {
  max-width: 1200px;
  margin: 0 auto;
}

.top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.top-row h1 {
  margin: 0;
}

.actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1.4fr;
  gap: 1rem;
}

.title-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kv {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--surface-border);
}

.hint {
  display: block;
  margin-top: 0.75rem;
  color: var(--text-color-secondary);
}

.connected-block,
.empty-qr {
  min-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  color: var(--text-color-secondary);
}

.connected-block i {
  font-size: 2rem;
  color: var(--green-500);
}

.qr-block {
  display: grid;
  gap: 1rem;
}

.qr-image {
  width: min(320px, 100%);
  border: 1px solid var(--surface-border);
  border-radius: 12px;
  justify-self: center;
}

.qr-block ol {
  margin: 0;
  padding-left: 1.25rem;
}

@media (max-width: 960px) {
  .top-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
