<template>
  <div class="reminders-page">
    <div class="page-header">
      <div class="header-content">
        <h1>Payment Reminders</h1>
        <p class="subtitle">Send automated payment reminders with attached ledgers</p>
        <div class="snapshot-meta" v-if="snapshotStatus">
          <span v-if="snapshotStatus.has_snapshot">
            Last refreshed: {{ formatDateTime(snapshotStatus.last_refreshed_at) }}
          </span>
          <span v-else>
            Snapshot not generated yet
          </span>
          <span>
            Rows: {{ snapshotStatus.row_count }} | Due &gt; 0: {{ snapshotStatus.nonzero_count }}
          </span>
        </div>
      </div>
      <div class="header-actions">
        <Button
          label="Refresh Snapshot"
          icon="pi pi-sync"
          class="p-button-outlined"
          @click="refreshSnapshot"
          :loading="snapshotRefreshing"
        />
        <Button
          icon="pi pi-cog"
          class="p-button-outlined ml-2"
          @click="showConfigPanel = true"
        />
      </div>
    </div>

    <Message v-if="loadError" severity="warn" :closable="false" class="mb-3">
      {{ loadError }}
    </Message>
    <Message v-if="metaHealth?.stale_callbacks" severity="warn" :closable="false" class="mb-3">
      Webhook configured but no recent Meta callback in the last
      {{ metaHealth.callback_staleness_minutes ?? 'many' }} minutes.
      Check tunnel stability and Meta webhook subscription.
    </Message>

    <Card class="meta-health mb-4">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <span>Meta Delivery Health</span>
          <Button
            icon="pi pi-refresh"
            class="p-button-text p-button-sm"
            @click="loadMetaHealth"
          />
        </div>
      </template>
      <template #content>
        <div class="health-grid">
          <div class="health-item">
            <label>Webhook Configured</label>
            <span :class="metaHealth?.verified_config ? 'text-green-500' : 'text-orange-500'">
              {{ metaHealth?.verified_config ? 'Yes' : 'No' }}
            </span>
          </div>
          <div class="health-item">
            <label>Last Verify</label>
            <span>{{ formatDateTime(metaHealth?.last_verify_at) }}</span>
          </div>
          <div class="health-item">
            <label>Last Callback</label>
            <span>{{ formatDateTime(metaHealth?.last_webhook_post_at) }}</span>
          </div>
          <div class="health-item">
            <label>Last Status Seen</label>
            <span>{{ metaHealth?.last_webhook_delivery_status_seen || 'N/A' }}</span>
          </div>
          <div class="health-item">
            <label>Reminder Provider</label>
            <span>{{ settingsInfo?.REMINDER_PROVIDER_CONFIGURED || 'N/A' }}</span>
          </div>
          <div class="health-item">
            <label>Token State</label>
            <span>{{ settingsInfo?.META_WEBHOOK_CONFIGURED ? 'Configured' : 'Missing' }}</span>
          </div>
        </div>

        <div class="runbook mt-3">
          <h4>Quick Setup (5 steps)</h4>
          <ol>
            <li>Start tunnel to <code>http://localhost:8000</code> (prefer ngrok/cloudflared).</li>
            <li>Set callback URL in Meta: <code>{{ webhookCallbackUrl }}</code>.</li>
            <li>Set verify token to configured value in app settings.</li>
            <li>Subscribe only <code>messages</code> webhook field.</li>
            <li>Send one test reminder and confirm transition beyond <code>accepted</code>.</li>
          </ol>
          <p class="text-muted">
            Note: <code>loca.lt</code> is not recommended for webhook callbacks due to interstitial/password behavior.
          </p>
          <div class="runbook-actions">
            <Button
              label="Copy Callback URL"
              icon="pi pi-copy"
              class="p-button-outlined p-button-sm"
              @click="copyToClipboard(webhookCallbackUrl, 'Callback URL copied')"
            />
            <Button
              label="Copy Status Command"
              icon="pi pi-copy"
              class="p-button-outlined p-button-sm ml-2"
              @click="copyToClipboard(historyCommand, 'Command copied')"
            />
          </div>
        </div>

        <div class="recent-transitions mt-3">
          <h4>Recent Delivery Transitions</h4>
          <ul v-if="recentTransitions.length > 0">
            <li v-for="item in recentTransitions" :key="item.id">
              <code>{{ item.phone }}</code> ->
              <strong>{{ item.delivery_status || 'unknown' }}</strong>
              at {{ formatDateTime(item.delivery_updated_at || item.completed_at) }}
            </li>
          </ul>
          <p v-else class="text-muted">No recent reminder delivery transitions yet.</p>
        </div>
      </template>
    </Card>

    <div class="stats-grid">
      <Card class="stat-card">
        <template #content>
          <div class="stat-value">{{ stats?.eligible_parties || 0 }}</div>
          <div class="stat-label">Eligible Parties</div>
        </template>
      </Card>
      <Card class="stat-card">
        <template #content>
          <div class="stat-value">{{ stats?.enabled_parties || 0 }}</div>
          <div class="stat-label">Reminders Enabled</div>
        </template>
      </Card>
      <Card class="stat-card">
        <template #content>
          <div class="stat-value">{{ formatCurrency(stats?.total_amount_due || 0) }}</div>
          <div class="stat-label">Total Amount Due</div>
        </template>
      </Card>
      <Card class="stat-card">
        <template #content>
          <div class="stat-value" :class="schedulerStatusClass">{{ schedulerStatusText }}</div>
          <div class="stat-label">Scheduler Status</div>
        </template>
      </Card>
    </div>

    <Card v-if="showConfigPanel" class="config-panel mb-4">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <span>Configuration</span>
          <Button icon="pi pi-times" class="p-button-text" @click="showConfigPanel = false" />
        </div>
      </template>
      <template #content>
        <div class="config-grid">
          <div class="config-section">
            <h4>Schedule Settings</h4>
            <div class="field">
              <label>Enable Scheduler</label>
              <InputSwitch v-model="config.schedule.enabled" @change="saveSchedule" />
            </div>
            <div class="field">
              <label>Frequency</label>
              <Dropdown
                v-model="config.schedule.frequency"
                :options="frequencyOptions"
                optionLabel="label"
                optionValue="value"
                @change="saveSchedule"
              />
            </div>
            <div class="field">
              <label>Day of Week</label>
              <Dropdown
                v-model="config.schedule.day_of_week"
                :options="dayOptions"
                optionLabel="label"
                optionValue="value"
                @change="saveSchedule"
              />
            </div>
            <div class="field">
              <label>Time</label>
              <InputMask v-model="config.schedule.time" mask="99:99" placeholder="HH:MM" @blur="saveSchedule" />
            </div>
          </div>
          <div class="config-section">
            <h4>Scheduler Control</h4>
            <div class="button-group">
              <Button
                label="Start"
                icon="pi pi-play"
                class="p-button-success"
                @click="startScheduler"
                :disabled="schedulerStatus?.is_running"
              />
              <Button
                label="Stop"
                icon="pi pi-stop"
                class="p-button-danger"
                @click="stopScheduler"
                :disabled="!schedulerStatus?.is_running"
              />
              <Button label="Trigger Now" icon="pi pi-send" class="p-button-primary" @click="triggerManualRun" />
            </div>
          </div>
        </div>
      </template>
    </Card>

    <Card class="template-panel mb-4">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <span>Message Template</span>
          <Button
            icon="pi pi-pencil"
            label="Edit Templates"
            class="p-button-outlined p-button-sm"
            @click="showTemplateEditor = true"
          />
        </div>
      </template>
      <template #content>
        <Dropdown
          v-model="selectedTemplateId"
          :options="templates"
          optionLabel="name"
          optionValue="id"
          placeholder="Select Template"
          class="w-full md:w-30rem"
          @change="onTemplateChange"
        />
        <div v-if="selectedTemplate" class="template-preview mt-3">
          <label>Preview:</label>
          <div class="preview-box">
            <pre>{{ selectedTemplate.content }}</pre>
          </div>
        </div>
      </template>
    </Card>

    <Card class="party-selection">
      <template #title>
        <div class="table-toolbar">
          <span>Party Selection ({{ totalRecords }} total)</span>
          <div class="table-toolbar-right">
            <span class="p-input-icon-left">
              <i class="pi pi-search" />
              <InputText v-model="searchQuery" placeholder="Search parties..." class="p-inputtext-sm" />
            </span>
            <Dropdown
              v-model="filterBy"
              :options="filterOptions"
              optionLabel="label"
              optionValue="value"
              class="p-dropdown-sm"
            />
            <div class="zero-toggle">
              <label>Show zero/unavailable</label>
              <InputSwitch v-model="includeZero" />
            </div>
          </div>
        </div>
      </template>
      <template #content>
        <div class="selection-actions mb-3">
          <Button label="Select Page" icon="pi pi-check-square" class="p-button-outlined p-button-sm" @click="selectPage" />
          <Button
            label="Deselect Page"
            icon="pi pi-minus-square"
            class="p-button-outlined p-button-sm ml-2"
            @click="deselectPage"
          />
          <Button label="Clear All" icon="pi pi-times" class="p-button-text p-button-sm ml-2" @click="clearAllSelections" />
          <span class="ml-3 text-muted">
            Selected: {{ selectedTempCount }} parties ({{ formatCurrency(selectedTotalAmount) }})
          </span>
        </div>

        <DataTable
          :value="parties"
          :loading="loadingParties"
          :lazy="true"
          :paginator="true"
          :rows="rows"
          :totalRecords="totalRecords"
          :first="first"
          :sortField="sortBy"
          :sortOrder="sortOrder === 'asc' ? 1 : -1"
          @page="onPage"
          @sort="onSort"
          class="p-datatable-sm"
          stripedRows
          responsiveLayout="scroll"
        >
          <Column style="width: 3rem">
            <template #body="{ data }">
              <Checkbox
                :modelValue="isSelected(data.code)"
                :binary="true"
                @update:modelValue="(checked) => toggleSelection(data, !!checked)"
              />
            </template>
          </Column>
          <Column field="name" header="Party Name" sortable>
            <template #body="{ data }">
              <div class="party-name">
                <span class="font-medium">{{ data.name }}</span>
                <span class="text-xs text-secondary">Code: {{ data.code }}</span>
              </div>
            </template>
          </Column>
          <Column field="amount_due" header="Amount Due" sortable style="width: 170px">
            <template #body="{ data }">
              <span class="amount-due">{{ data.amount_due_formatted }}</span>
            </template>
          </Column>
          <Column field="sales_credit_days" header="Credit" sortable style="width: 110px">
            <template #body="{ data }">
              <span class="credit-days">{{ data.sales_credit_days }}d</span>
            </template>
          </Column>
          <Column header="Permanent" style="width: 130px">
            <template #body="{ data }">
              <ToggleButton
                :modelValue="data.permanent_enabled"
                onIcon="pi pi-check"
                offIcon="pi pi-times"
                onLabel="On"
                offLabel="Off"
                class="p-button-sm"
                @update:modelValue="(val) => updatePermanentSelection(data.code, !!val)"
              />
            </template>
          </Column>
          <Column header="Actions" style="width: 110px">
            <template #body="{ data }">
              <Button icon="pi pi-file-pdf" class="p-button-text p-button-sm" @click="generateLedger(data.code)" />
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <div class="action-bar">
      <Button
        label="Send Now"
        icon="pi pi-send"
        class="p-button-primary p-button-lg"
        :disabled="selectedTempCount === 0 || !selectedTemplateId"
        @click="confirmSend"
      />
      <Button
        label="Schedule for Later"
        icon="pi pi-calendar"
        class="p-button-outlined p-button-lg ml-3"
        :disabled="selectedTempCount === 0 || !selectedTemplateId"
        @click="showScheduleDialog = true"
      />
      <Button label="Export CSV" icon="pi pi-download" class="p-button-outlined p-button-lg ml-3" @click="exportCsv" />
    </div>

    <Dialog v-model:visible="showScheduleDialog" header="Schedule Reminders" modal :style="{ width: '450px' }">
      <div class="schedule-form">
        <div class="field">
          <label>Schedule Date</label>
          <Calendar v-model="scheduleDate" :minDate="new Date()" dateFormat="yy-mm-dd" />
        </div>
        <div class="field">
          <label>Schedule Time</label>
          <InputMask v-model="scheduleTime" mask="99:99" placeholder="HH:MM" />
        </div>
        <div class="summary">
          <p><strong>Selected:</strong> {{ selectedTempCount }} parties</p>
          <p><strong>Template:</strong> {{ selectedTemplate?.name }}</p>
          <p><strong>Total Amount:</strong> {{ formatCurrency(selectedTotalAmount) }}</p>
        </div>
      </div>
      <template #footer>
        <Button label="Cancel" icon="pi pi-times" class="p-button-text" @click="showScheduleDialog = false" />
        <Button label="Schedule" icon="pi pi-check" @click="scheduleReminders" />
      </template>
    </Dialog>

    <Dialog v-model:visible="showTemplateEditor" header="Message Templates" modal maximizable :style="{ width: '800px', height: '600px' }">
      <TemplateEditor @close="showTemplateEditor = false" @saved="loadTemplates" />
    </Dialog>

    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Calendar from 'primevue/calendar'
import Card from 'primevue/card'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import ConfirmDialog from 'primevue/confirmdialog'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import InputMask from 'primevue/inputmask'
import InputSwitch from 'primevue/inputswitch'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import ToggleButton from 'primevue/togglebutton'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import type { DataTablePageEvent, DataTableSortEvent } from 'primevue/datatable'
import TemplateEditor from '@/components/TemplateEditor.vue'
import { api } from '@/services/api'
import type {
  Message as QueueMessage,
  MetaWebhookStatus,
  MessageTemplate,
  PartyReminderInfo,
  ReminderConfig,
  ReminderSnapshotStatus,
  ReminderStats,
  SchedulerStatus,
} from '@/types'

const confirm = useConfirm()
const toast = useToast()

const loading = ref(false)
const loadingParties = ref(false)
const snapshotRefreshing = ref(false)
const loadError = ref('')

const config = ref<ReminderConfig | null>(null)
const templates = ref<MessageTemplate[]>([])
const selectedTemplateId = ref('')
const stats = ref<ReminderStats | null>(null)
const schedulerStatus = ref<SchedulerStatus | null>(null)
const snapshotStatus = ref<ReminderSnapshotStatus | null>(null)
const metaHealth = ref<MetaWebhookStatus | null>(null)
const settingsInfo = ref<Record<string, any> | null>(null)
const recentTransitions = ref<QueueMessage[]>([])

const parties = ref<PartyReminderInfo[]>([])
const totalRecords = ref(0)
const first = ref(0)
const rows = ref(100)
const sortBy = ref('amount_due')
const sortOrder = ref<'asc' | 'desc'>('desc')
const filterBy = ref('all')
const includeZero = ref(false)
const searchQuery = ref('')

const showConfigPanel = ref(false)
const showTemplateEditor = ref(false)
const showScheduleDialog = ref(false)
const scheduleDate = ref(new Date())
const scheduleTime = ref('10:00')

const tempSelections = ref<Set<string>>(new Set())
const selectedAmounts = ref<Map<string, number>>(new Map())

const frequencyOptions = [
  { label: 'Weekly', value: 'weekly' },
  { label: 'Bi-weekly', value: 'biweekly' },
]

const dayOptions = [
  { label: 'Sunday', value: 0 },
  { label: 'Monday', value: 1 },
  { label: 'Tuesday', value: 2 },
  { label: 'Wednesday', value: 3 },
  { label: 'Thursday', value: 4 },
  { label: 'Friday', value: 5 },
  { label: 'Saturday', value: 6 },
]

const filterOptions = [
  { label: 'All', value: 'all' },
  { label: 'Enabled', value: 'enabled' },
  { label: 'Disabled', value: 'disabled' },
]

const selectedTemplate = computed(() => templates.value.find((t) => t.id === selectedTemplateId.value))
const selectedTempCount = computed(() => tempSelections.value.size)
const selectedTotalAmount = computed(() => {
  let total = 0
  selectedAmounts.value.forEach((v) => {
    total += v
  })
  return total
})

const schedulerStatusText = computed(() => {
  if (!schedulerStatus.value) return 'Unknown'
  return schedulerStatus.value.is_running ? 'Running' : 'Stopped'
})

const schedulerStatusClass = computed(() => {
  if (!schedulerStatus.value) return ''
  return schedulerStatus.value.is_running ? 'text-green-500' : 'text-red-500'
})

const webhookCallbackUrl = computed(() => `${window.location.origin}/api/v1/whatsapp/meta/webhook`)
const historyCommand = `Invoke-RestMethod "http://localhost:8000/api/v1/queue/history?source=payment_reminder&limit=20"`

function isSelected(code: string): boolean {
  return tempSelections.value.has(code)
}

function toggleSelection(party: PartyReminderInfo, checked: boolean): void {
  if (checked) {
    tempSelections.value.add(party.code)
    selectedAmounts.value.set(party.code, Number(party.amount_due || 0))
  } else {
    tempSelections.value.delete(party.code)
    selectedAmounts.value.delete(party.code)
  }
}

function selectPage(): void {
  parties.value.forEach((p) => {
    tempSelections.value.add(p.code)
    selectedAmounts.value.set(p.code, Number(p.amount_due || 0))
  })
}

function deselectPage(): void {
  parties.value.forEach((p) => {
    tempSelections.value.delete(p.code)
    selectedAmounts.value.delete(p.code)
  })
}

function clearAllSelections(): void {
  tempSelections.value.clear()
  selectedAmounts.value.clear()
}

function formatCurrency(amount: number): string {
  const symbol = config.value?.currency_symbol || '₹'
  return `${symbol}${new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)}`
}

function formatDateTime(value?: string): string {
  if (!value) return 'N/A'
  const dt = new Date(value)
  if (Number.isNaN(dt.getTime())) return value
  return dt.toLocaleString()
}

async function loadPartiesPage(newFirst = first.value): Promise<void> {
  loadingParties.value = true
  loadError.value = ''
  try {
    const page = await api.getEligibleParties(
      searchQuery.value || undefined,
      sortBy.value,
      sortOrder.value,
      filterBy.value,
      newFirst,
      rows.value,
      includeZero.value
    )
    parties.value = page.items
    totalRecords.value = page.total
    first.value = page.offset

    // Keep amount cache up-to-date for selections already made.
    for (const p of page.items) {
      if (tempSelections.value.has(p.code)) {
        selectedAmounts.value.set(p.code, Number(p.amount_due || 0))
      }
    }
  } catch {
    parties.value = []
    totalRecords.value = 0
    loadError.value = 'Failed to load parties from snapshot. Refresh snapshot and retry.'
  } finally {
    loadingParties.value = false
  }
}

async function loadMetaData(): Promise<void> {
  const [configResult, templatesResult, schedulerResult, statsResult, snapResult, settingsResult] = await Promise.allSettled([
    api.getReminderConfig(),
    api.getTemplates(),
    api.getSchedulerStatus(),
    api.getReminderStats(),
    api.getReminderSnapshotStatus(),
    api.getSettings(),
  ])

  if (configResult.status === 'fulfilled') {
    config.value = configResult.value
    if (!selectedTemplateId.value) {
      selectedTemplateId.value = configResult.value.active_template_id
    }
  }
  if (templatesResult.status === 'fulfilled') {
    templates.value = templatesResult.value
    if (!selectedTemplateId.value && templates.value.length > 0) {
      selectedTemplateId.value = templates.value[0].id
    }
  }
  if (schedulerResult.status === 'fulfilled') {
    schedulerStatus.value = schedulerResult.value
  }
  if (statsResult.status === 'fulfilled') {
    stats.value = statsResult.value
  }
  if (snapResult.status === 'fulfilled') {
    snapshotStatus.value = snapResult.value
  }
  if (settingsResult.status === 'fulfilled') {
    settingsInfo.value = settingsResult.value
  }
}

async function loadMetaHealth(): Promise<void> {
  const [healthResult, transitionsResult] = await Promise.allSettled([
    api.getMetaWebhookStatus(),
    api.getReminderHistory(undefined, 3),
  ])

  if (healthResult.status === 'fulfilled') {
    metaHealth.value = healthResult.value
  }

  if (transitionsResult.status === 'fulfilled') {
    recentTransitions.value = transitionsResult.value
  }
}

async function loadData(): Promise<void> {
  loading.value = true
  try {
    await Promise.all([loadMetaData(), loadMetaHealth()])
    await loadPartiesPage(0)
  } finally {
    loading.value = false
  }
}

async function refreshSnapshot(): Promise<void> {
  snapshotRefreshing.value = true
  try {
    snapshotStatus.value = await api.refreshReminderSnapshot()
    await Promise.all([loadMetaData(), loadMetaHealth(), loadPartiesPage(0)])
    toast.add({
      severity: 'success',
      summary: 'Snapshot Refreshed',
      detail: `Computed ${snapshotStatus.value.row_count} parties in ${snapshotStatus.value.duration_ms} ms`,
      life: 3000,
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Refresh Failed',
      detail: 'Could not refresh reminder snapshot',
      life: 3000,
    })
  } finally {
    snapshotRefreshing.value = false
  }
}

function onPage(event: DataTablePageEvent): void {
  rows.value = event.rows
  loadPartiesPage(event.first)
}

function onSort(event: DataTableSortEvent): void {
  sortBy.value = (event.sortField as string) || 'amount_due'
  sortOrder.value = event.sortOrder === 1 ? 'asc' : 'desc'
  loadPartiesPage(0)
}

watch([filterBy, includeZero], () => {
  loadPartiesPage(0)
})

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadPartiesPage(0), 300)
})

async function loadTemplates(): Promise<void> {
  try {
    templates.value = await api.getTemplates()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load templates',
      life: 3000,
    })
  }
}

async function onTemplateChange(): Promise<void> {
  try {
    await api.setActiveTemplate(selectedTemplateId.value)
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Active template updated',
      life: 2000,
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to update active template',
      life: 3000,
    })
  }
}

async function updatePermanentSelection(partyCode: string, enabled: boolean): Promise<void> {
  try {
    await api.updatePartyConfig(partyCode, { permanent_enabled: enabled })
    const idx = parties.value.findIndex((p) => p.code === partyCode)
    if (idx >= 0) {
      parties.value[idx].permanent_enabled = enabled
    }
    if (stats.value) {
      stats.value.enabled_parties += enabled ? 1 : -1
      if (stats.value.enabled_parties < 0) stats.value.enabled_parties = 0
    }
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to update party configuration',
      life: 3000,
    })
  }
}

async function generateLedger(partyCode: string): Promise<void> {
  try {
    const blob = await api.generateLedgerPdf(partyCode)
    const url = window.URL.createObjectURL(blob)
    window.open(url, '_blank')
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to generate ledger',
      life: 3000,
    })
  }
}

function confirmSend(): void {
  confirm.require({
    message: `Are you sure you want to send reminders to ${selectedTempCount.value} parties?`,
    header: 'Send Reminders',
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
      await sendReminders()
    },
  })
}

async function sendReminders(): Promise<void> {
  try {
    const partyCodes = Array.from(tempSelections.value)
    const result = await api.sendReminders(partyCodes, selectedTemplateId.value)
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: result.message,
      life: 3000,
    })
    clearAllSelections()
    await loadMetaData()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to send reminders',
      life: 3000,
    })
  }
}

async function scheduleReminders(): Promise<void> {
  try {
    if (!scheduleTime.value || !/^\d{2}:\d{2}$/.test(scheduleTime.value)) {
      throw new Error('Enter schedule time in HH:MM format')
    }
    const partyCodes = Array.from(tempSelections.value)
    const scheduleDateTime = new Date(scheduleDate.value)
    const [hours, minutes] = scheduleTime.value.split(':').map(Number)
    if (hours > 23 || minutes > 59) {
      throw new Error('Invalid schedule time')
    }
    scheduleDateTime.setHours(hours, minutes)

    if (scheduleDateTime <= new Date()) {
      throw new Error('Schedule time must be in the future')
    }

    const result = await api.scheduleReminders(partyCodes, selectedTemplateId.value, scheduleDateTime)
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: result.message,
      life: 3000,
    })
    showScheduleDialog.value = false
    clearAllSelections()
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Failed to schedule reminders'
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: message,
      life: 3000,
    })
  }
}

function exportCsv(): void {
  toast.add({
    severity: 'info',
    summary: 'Info',
    detail: 'CSV export not yet implemented',
    life: 3000,
  })
}

async function saveSchedule(): Promise<void> {
  if (!config.value) return
  try {
    await api.updateScheduleConfig(config.value.schedule)
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to save schedule configuration',
      life: 3000,
    })
  }
}

async function startScheduler(): Promise<void> {
  try {
    await api.startScheduler()
    schedulerStatus.value = await api.getSchedulerStatus()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to start scheduler',
      life: 3000,
    })
  }
}

async function stopScheduler(): Promise<void> {
  try {
    await api.stopScheduler()
    schedulerStatus.value = await api.getSchedulerStatus()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to stop scheduler',
      life: 3000,
    })
  }
}

async function triggerManualRun(): Promise<void> {
  try {
    const result = await api.triggerManualRun()
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: result.message,
      life: 3000,
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to trigger manual run',
      life: 3000,
    })
  }
}

async function copyToClipboard(text: string, successMessage: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    toast.add({
      severity: 'success',
      summary: 'Copied',
      detail: successMessage,
      life: 2000,
    })
  } catch {
    toast.add({
      severity: 'warn',
      summary: 'Clipboard',
      detail: 'Could not copy to clipboard',
      life: 2500,
    })
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.reminders-page {
  padding: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.header-content h1 {
  margin: 0 0 0.4rem 0;
}

.subtitle {
  color: var(--text-color-secondary);
  margin: 0;
}

.snapshot-meta {
  margin-top: 0.5rem;
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.meta-health .health-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
}

.meta-health .health-item {
  display: flex;
  justify-content: space-between;
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 0.6rem 0.75rem;
  font-size: 0.9rem;
}

.meta-health .health-item label {
  color: var(--text-color-secondary);
}

.runbook {
  border: 1px dashed var(--surface-border);
  border-radius: 8px;
  padding: 0.75rem;
}

.runbook h4,
.recent-transitions h4 {
  margin: 0 0 0.5rem 0;
}

.runbook ol {
  margin: 0.4rem 0 0.6rem 1rem;
  padding: 0;
}

.runbook-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.recent-transitions ul {
  margin: 0;
  padding-left: 1rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--primary-color);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  margin-top: 0.25rem;
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.config-section h4 {
  margin-top: 0;
  margin-bottom: 1rem;
}

.config-section .field {
  margin-bottom: 1rem;
}

.config-section label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.button-group {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.template-preview label {
  font-weight: 500;
  margin-bottom: 0.5rem;
  display: block;
}

.preview-box {
  background: var(--surface-ground);
  padding: 1rem;
  border-radius: 6px;
  font-family: monospace;
  font-size: 0.875rem;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

.preview-box pre {
  margin: 0;
}

.table-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.table-toolbar-right {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.zero-toggle {
  display: inline-flex;
  gap: 0.5rem;
  align-items: center;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.selection-actions {
  display: flex;
  align-items: center;
  padding: 0.5rem 0;
}

.party-name {
  display: flex;
  flex-direction: column;
}

.amount-due {
  font-weight: 600;
  color: var(--primary-color);
}

.credit-days {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  padding: 1rem 0;
  gap: 0.5rem;
}

.schedule-form .field {
  margin-bottom: 1rem;
}

.schedule-form label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.summary {
  background: var(--surface-ground);
  padding: 1rem;
  border-radius: 6px;
  margin-top: 1rem;
}

.summary p {
  margin: 0.25rem 0;
}

.text-muted {
  color: var(--text-color-secondary);
}

@media (max-width: 768px) {
  .config-grid {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }

  .action-bar {
    flex-direction: column;
  }

  .action-bar button {
    width: 100%;
    margin-left: 0 !important;
    margin-bottom: 0.5rem;
  }
}
</style>
