<template>
  <div class="bw-page reminders-page">
    <!-- Header -->
    <div class="bw-page-header">
      <div>
        <h1>Payment Reminders</h1>
        <p class="subtitle">
          <template v-if="snapshotStatus?.has_snapshot">
            {{ snapshotStatus.nonzero_count }} parties with dues &middot;
            Last refreshed {{ formatRelativeTime(snapshotStatus.last_refreshed_at) }}
          </template>
          <template v-else>Data not loaded yet</template>
        </p>
      </div>
      <div class="header-actions">
        <Button
          label="Refresh Data"
          icon="pi pi-sync"
          class="p-button-outlined p-button-sm"
          @click="refreshSnapshot"
          :loading="snapshotRefreshing"
        />
      </div>
    </div>

    <!-- Error -->
    <Message v-if="loadError" severity="warn" :closable="false" class="mb-3">
      {{ loadError }}
    </Message>

    <!-- Stats -->
    <div class="bw-stats-grid">
      <div class="bw-stat-card">
        <div class="bw-stat-icon"><i class="pi pi-users"></i></div>
        <div class="bw-stat-value">{{ stats?.eligible_parties || 0 }}</div>
        <div class="bw-stat-label">Eligible</div>
      </div>
      <div class="bw-stat-card">
        <div class="bw-stat-icon" style="background: rgba(34,197,94,0.12); color: #22c55e"><i class="pi pi-check-circle"></i></div>
        <div class="bw-stat-value">{{ stats?.enabled_parties || 0 }}</div>
        <div class="bw-stat-label">Enabled</div>
      </div>
      <div class="bw-stat-card">
        <div class="bw-stat-icon" style="background: rgba(245,158,11,0.12); color: #f59e0b"><i class="pi pi-indian-rupee"></i></div>
        <div class="bw-stat-value">{{ formatCurrency(stats?.total_amount_due || 0) }}</div>
        <div class="bw-stat-label">Total Due</div>
      </div>
      <div class="bw-stat-card" :class="{ 'stat-active-session': activeSession }">
        <div class="bw-stat-icon" :style="activeSession ? 'background: rgba(14,165,233,0.12); color: #0ea5e9' : ''"><i class="pi pi-bolt"></i></div>
        <div class="bw-stat-value" :class="{ 'text-accent': activeSession }">
          {{ activeSession ? activeSession.progress.percentage + '%' : 'Ready' }}
        </div>
        <div class="bw-stat-label">{{ activeSession ? 'Sending...' : 'Session' }}</div>
      </div>
    </div>

    <!-- Active Session Panel (overlay-style) -->
    <transition name="slide-down">
      <div v-if="activeSession" class="session-panel">
        <div class="session-panel-header">
          <div class="session-info">
            <i class="pi pi-send"></i>
            <span class="session-id">{{ activeSession.session_id.slice(0, 8) }}</span>
            <Tag
              :value="activeSession.state"
              :severity="getSessionStateSeverity(activeSession.state)"
              class="session-state-tag"
            />
          </div>
          <div class="session-controls">
            <Button
              v-if="['online', 'sending', 'typing', 'reading'].includes(activeSession.state)"
              icon="pi pi-pause" class="p-button-text p-button-sm p-button-warning"
              @click="pauseSession" title="Pause"
            />
            <Button
              v-if="activeSession.state === 'paused'"
              icon="pi pi-play" class="p-button-text p-button-sm p-button-success"
              @click="resumeSession" title="Resume"
            />
            <Button
              icon="pi pi-stop" class="p-button-text p-button-sm p-button-danger"
              @click="stopSession" title="Stop"
            />
          </div>
        </div>
        <ProgressBar :value="activeSession.progress.percentage" class="session-progress" />
        <div class="session-metrics">
          <span>{{ activeSession.progress.current }} / {{ activeSession.progress.total }}</span>
          <span v-if="activeSession.metrics">{{ formatDuration(activeSession.metrics.duration_seconds) }}</span>
          <span class="pct">{{ activeSession.progress.percentage }}%</span>
        </div>
      </div>
    </transition>

    <!-- MAIN: Party Selection Table (promoted to primary position) -->
    <div class="bw-section party-section">
      <div class="bw-section-header">
        <h2><i class="pi pi-users"></i> Select Parties</h2>
        <div class="party-toolbar">
          <span class="p-input-icon-left search-wrap">
            <i class="pi pi-search" />
            <InputText
              v-model="searchQuery"
              placeholder="Search parties..."
              class="p-inputtext-sm party-search"
              @input="onSearchInput"
            />
          </span>
          <Dropdown
            v-model="filterBy"
            :options="filterOptions"
            optionLabel="label"
            optionValue="value"
            class="p-dropdown-sm filter-dropdown"
          />
        </div>
      </div>
      <div class="bw-section-body party-table-body">
        <DataTable
          :value="displayedParties"
          class="p-datatable-sm party-table"
          scrollable
          scrollHeight="480px"
          sortField="amount_due"
          :sortOrder="-1"
          :rowClass="rowClass"
          dataKey="code"
          :loading="loading"
        >
          <Column style="width: 48px">
            <template #body="{ data }">
              <Checkbox
                :modelValue="isSelected(data.code)"
                @change="(e: any) => toggleSelection(data, e.checked)"
                :binary="true"
              />
            </template>
          </Column>

          <Column field="name" header="Party" sortable style="min-width: 200px">
            <template #body="{ data }">
              <div class="party-cell">
                <span class="party-cell-name">{{ data.name }}</span>
                <span class="party-cell-code">{{ data.code }}</span>
              </div>
            </template>
          </Column>

          <Column field="amount_due" header="Amount Due" sortable style="width: 140px">
            <template #body="{ data }">
              <span class="amount-cell">{{ formatCurrency(data.amount_due) }}</span>
            </template>
          </Column>

          <Column field="phone" header="Phone" style="width: 140px">
            <template #body="{ data }">
              <span class="phone-cell">{{ data.phone || '—' }}</span>
            </template>
          </Column>

          <Column field="last_reminder_sent" header="Last Sent" sortable style="width: 140px">
            <template #body="{ data }">
              <span class="date-cell">
                {{ data.last_reminder_sent ? formatRelativeTime(data.last_reminder_sent) : 'Never' }}
              </span>
            </template>
          </Column>

          <template #empty>
            <div class="bw-empty-state" style="padding: 2rem">
              <i class="pi pi-search"></i>
              <p>No parties found</p>
              <small>Try adjusting your search or filter</small>
            </div>
          </template>
        </DataTable>

        <!-- Pagination -->
        <div class="table-footer">
          <div class="table-footer-left">
            <Button
              label="Select All Visible"
              icon="pi pi-check-square"
              class="p-button-text p-button-sm"
              @click="selectPage"
            />
            <span class="showing-text">
              Showing {{ displayedParties.length }} of {{ totalRecords }}
            </span>
          </div>
          <div class="table-footer-right">
            <Button icon="pi pi-angle-left" class="p-button-text p-button-sm"
              :disabled="first === 0" @click="prevPage" />
            <span class="page-info">Page {{ currentPage }}</span>
            <Button icon="pi pi-angle-right" class="p-button-text p-button-sm"
              :disabled="!hasMore" @click="nextPage" />
          </div>
        </div>
      </div>
    </div>

    <!-- Configuration: Accordion panels (collapsed by default) -->
    <Accordion :multiple="true" class="config-accordion">
      <AccordionTab>
        <template #header>
          <div class="accordion-header-content">
            <i class="pi pi-envelope"></i>
            <span>Message Template</span>
            <Tag v-if="selectedTemplate" :value="selectedTemplate.name" severity="info" class="ml-2" />
          </div>
        </template>
        <div class="template-config">
          <div class="template-selector-row">
            <Dropdown
              v-model="defaultTemplateId"
              :options="templates"
              optionLabel="name"
              optionValue="id"
              placeholder="Select Default Template"
              class="template-dropdown"
            />
            <Button
              icon="pi pi-cog"
              label="Manage"
              class="p-button-outlined p-button-sm"
              @click="showTemplateManager = true"
            />
          </div>
          <div v-if="selectedTemplate" class="template-preview">
            <pre>{{ selectedTemplate.content }}</pre>
          </div>
        </div>
      </AccordionTab>
      <AccordionTab>
        <template #header>
          <div class="accordion-header-content">
            <i class="pi pi-shield"></i>
            <span>Anti-Spam Protection</span>
            <Tag :severity="antiSpamConfig.enabled ? 'success' : 'secondary'" :value="antiSpamConfig.enabled ? 'On' : 'Off'" class="ml-2" />
          </div>
        </template>
        <div class="antispam-config">
          <div class="antispam-master">
            <InputSwitch v-model="antiSpamConfig.enabled" @change="saveAntiSpamConfig" />
            <div>
              <span class="toggle-text">Enable Anti-Spam</span>
              <small>Protects against WhatsApp bulk detection</small>
            </div>
          </div>
          <transition name="slide-down">
            <div v-if="antiSpamConfig.enabled" class="antispam-options">
              <label class="antispam-option">
                <InputSwitch v-model="antiSpamConfig.message_inflation" @change="saveAntiSpamConfig" />
                <div>
                  <span>Message Inflation</span>
                  <small>Adds invisible chars (3-5x size)</small>
                </div>
              </label>
              <label class="antispam-option">
                <InputSwitch v-model="antiSpamConfig.pdf_inflation" @change="saveAntiSpamConfig" />
                <div>
                  <span>PDF Inflation</span>
                  <small>Adds invisible metadata (1-3x)</small>
                </div>
              </label>
              <label class="antispam-option">
                <InputSwitch v-model="antiSpamConfig.typing_simulation" @change="saveAntiSpamConfig" />
                <div>
                  <span>Typing Simulation</span>
                  <small>Shows typing indicator first</small>
                </div>
              </label>
              <label class="antispam-option">
                <InputSwitch v-model="antiSpamConfig.startup_delay_enabled" @change="saveAntiSpamConfig" />
                <div>
                  <span>Startup Delay</span>
                  <small>3-5 min warm-up before sending</small>
                </div>
              </label>
            </div>
          </transition>
        </div>
      </AccordionTab>
    </Accordion>

    <!-- Sticky Action Bar -->
    <div class="action-bar" :class="{ 'has-selection': selectedParties.length > 0 }">
      <div class="action-bar-left">
        <span class="selection-summary" v-if="selectedParties.length > 0">
          <strong>{{ selectedParties.length }}</strong> selected &middot;
          <strong>{{ formatCurrency(selectedTotalAmount) }}</strong>
        </span>
        <span v-else class="selection-summary muted">No parties selected</span>
      </div>
      <div class="action-bar-right">
        <Button
          v-if="selectedParties.length > 0"
          label="Clear"
          icon="pi pi-times"
          class="p-button-text p-button-sm"
          @click="clearAllSelections"
        />
        <Button
          label="Send Reminders"
          icon="pi pi-send"
          class="p-button-primary send-btn"
          :disabled="selectedParties.length === 0 || !defaultTemplateId || !!activeSession"
          :loading="sending"
          @click="confirmSend"
        />
      </div>
    </div>

    <!-- Send Confirmation Dialog -->
    <Dialog
      v-model:visible="showConfirmDialog"
      header="Confirm Send"
      modal
      :style="{ width: '420px' }"
      :pt="{ root: { class: 'confirm-dialog' } }"
    >
      <div class="confirm-body">
        <div class="confirm-icon-wrap">
          <i class="pi pi-send"></i>
        </div>
        <div class="confirm-details">
          <p class="confirm-heading">Send payment reminders to:</p>
          <div class="confirm-stats">
            <div class="confirm-stat">
              <span class="confirm-stat-value">{{ selectedParties.length }}</span>
              <span class="confirm-stat-label">Parties</span>
            </div>
            <div class="confirm-stat">
              <span class="confirm-stat-value">{{ formatCurrency(selectedTotalAmount) }}</span>
              <span class="confirm-stat-label">Total Due</span>
            </div>
          </div>
          <div class="confirm-template">
            Template: <strong>{{ selectedTemplate?.name || 'Default' }}</strong>
          </div>
          <div class="confirm-eta" v-if="antiSpamConfig.enabled">
            <Tag severity="success" value="Anti-Spam" />
            <small>Est. {{ estimatedDuration }}</small>
          </div>
        </div>
      </div>
      <template #footer>
        <Button label="Cancel" icon="pi pi-times" class="p-button-text" @click="showConfirmDialog = false" />
        <Button label="Send Now" icon="pi pi-send" class="p-button-primary" @click="sendReminders" :loading="sending" />
      </template>
    </Dialog>

    <!-- Template Manager Dialog -->
    <Dialog
      v-model:visible="showTemplateManager"
      header="Template Manager"
      modal
      maximizable
      :style="{ width: '900px', height: '600px' }"
    >
      <TemplateManager
        @close="showTemplateManager = false"
        @template-saved="onTemplateSaved"
      />
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Accordion from 'primevue/accordion'
import AccordionTab from 'primevue/accordiontab'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import InputSwitch from 'primevue/inputswitch'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import Tag from 'primevue/tag'
import TemplateManager from '@/components/TemplateManager.vue'
import { useToast } from 'primevue/usetoast'
import { api } from '@/services/api'
import type {
  MessageTemplate,
  PartyReminderInfo,
  ReminderConfig,
  ReminderSnapshotStatus,
  ReminderStats,
} from '@/types'

const toast = useToast()

// State
const loading = ref(false)
const sending = ref(false)
const snapshotRefreshing = ref(false)
const loadError = ref('')

const config = ref<ReminderConfig | null>(null)
const templates = ref<MessageTemplate[]>([])
const defaultTemplateId = ref('')
const stats = ref<ReminderStats | null>(null)
const snapshotStatus = ref<ReminderSnapshotStatus | null>(null)

// Anti-spam
const antiSpamConfig = ref({
  enabled: true,
  message_inflation: true,
  pdf_inflation: true,
  typing_simulation: true,
  startup_delay_enabled: true
})

// Session
const activeSession = ref<{
  session_id: string
  state: string
  progress: { current: number; total: number; percentage: number }
  metrics?: { duration_seconds: number; avg_delay_seconds?: number; typing_time_total?: number }
} | null>(null)

// Parties
const allParties = ref<PartyReminderInfo[]>([])
const selectedPartyCodes = ref<Set<string>>(new Set())
const totalRecords = ref(0)
const first = ref(0)
const rows = ref(25)
const hasMore = ref(false)
const filterBy = ref('all')
const searchQuery = ref('')
let searchTimeout: number | null = null

// UI
const showConfirmDialog = ref(false)
const showTemplateManager = ref(false)

// Computed
const currentPage = computed(() => Math.floor(first.value / rows.value) + 1)

const displayedParties = computed(() => allParties.value)

const selectedParties = computed(() =>
  allParties.value.filter(p => selectedPartyCodes.value.has(p.code))
)

const selectedTotalAmount = computed(() =>
  selectedParties.value.reduce((sum, p) => sum + Number(p.amount_due || 0), 0)
)

const selectedTemplate = computed(() =>
  templates.value.find(t => t.id === defaultTemplateId.value)
)

const estimatedDuration = computed(() => {
  const count = selectedParties.value.length
  if (count === 0) return '0 min'
  const baseSeconds = count * 15
  const startupDelay = antiSpamConfig.value.startup_delay_enabled ? 240 : 0
  const typingDelay = antiSpamConfig.value.typing_simulation ? count * 8 : 0
  const totalSeconds = baseSeconds + startupDelay + typingDelay
  const minutes = Math.ceil(totalSeconds / 60)
  if (minutes < 60) return `${minutes} min`
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
})

const filterOptions = [
  { label: 'All Parties', value: 'all' },
  { label: 'Reminders Enabled', value: 'enabled' },
  { label: 'Not Recent', value: 'recent' }
]

// Methods
function isSelected(code: string): boolean {
  return selectedPartyCodes.value.has(code)
}

function toggleSelection(party: PartyReminderInfo, checked: boolean): void {
  if (checked) {
    selectedPartyCodes.value.add(party.code)
  } else {
    selectedPartyCodes.value.delete(party.code)
  }
}

function rowClass(data: PartyReminderInfo) {
  return isSelected(data.code) ? 'row-selected' : ''
}

function selectPage(): void {
  allParties.value.forEach(p => selectedPartyCodes.value.add(p.code))
}

function clearAllSelections(): void {
  selectedPartyCodes.value.clear()
}

function prevPage(): void {
  first.value = Math.max(0, first.value - rows.value)
  loadParties()
}

function nextPage(): void {
  first.value += rows.value
  loadParties()
}

function onSearchInput(): void {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = window.setTimeout(() => {
    first.value = 0
    loadParties()
  }, 300) as unknown as number
}

function formatCurrency(amount: number): string {
  const symbol = config.value?.currency_symbol || '₹'
  return `${symbol}${new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)}`
}

function formatRelativeTime(dt: string | null): string {
  if (!dt) return 'N/A'
  const now = new Date()
  const then = new Date(dt)
  const diffMs = now.getTime() - then.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 30) return `${diffDays}d ago`
  return then.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins < 60) return `${mins}m ${secs}s`
  return `${Math.floor(mins / 60)}h ${mins % 60}m`
}

function getSessionStateSeverity(state: string): string {
  switch (state) {
    case 'online': case 'sending': return 'success'
    case 'typing': case 'reading': return 'info'
    case 'paused': return 'warning'
    case 'stopped': case 'error': return 'danger'
    default: return 'secondary'
  }
}

// API
async function loadData(): Promise<void> {
  loading.value = true
  try {
    await Promise.all([loadConfig(), loadTemplates(), loadStats(), loadParties()])
  } finally {
    loading.value = false
  }
}

async function loadConfig(): Promise<void> {
  try { config.value = await api.getReminderConfig() } catch (e) { console.error('Config load error', e) }
}

async function loadTemplates(): Promise<void> {
  try {
    templates.value = await api.getTemplates()
    const def = templates.value.find(t => t.is_default)
    if (def && !defaultTemplateId.value) defaultTemplateId.value = def.id
  } catch (e) { console.error('Templates load error', e) }
}

async function loadStats(): Promise<void> {
  try { stats.value = await api.getReminderStats() } catch (e) { console.error('Stats load error', e) }
}

async function loadParties(): Promise<void> {
  try {
    const response = await api.getEligibleParties(
      searchQuery.value || undefined,
      'amount_due', 'desc',
      filterBy.value,
      first.value,
      rows.value
    )
    allParties.value = response.items
    totalRecords.value = response.total
    hasMore.value = response.has_more
  } catch (e) { console.error('Parties load error', e) }
}

async function refreshSnapshot(): Promise<void> {
  snapshotRefreshing.value = true
  try {
    snapshotStatus.value = await api.refreshReminderSnapshot()
    toast.add({ severity: 'success', summary: 'Refreshed', detail: `${snapshotStatus.value.row_count} parties found`, life: 3000 })
    await loadParties()
    await loadStats()
  } catch {
    toast.add({ severity: 'error', summary: 'Refresh Failed', life: 3000 })
  } finally {
    snapshotRefreshing.value = false
  }
}

async function saveAntiSpamConfig(): Promise<void> {
  try {
    await api.updateAntiSpamConfig(antiSpamConfig.value)
    toast.add({ severity: 'success', summary: 'Saved', detail: 'Anti-spam updated', life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to save', life: 3000 })
  }
}

function confirmSend(): void {
  if (selectedParties.value.length === 0) return
  showConfirmDialog.value = true
}

async function sendReminders(): Promise<void> {
  sending.value = true
  showConfirmDialog.value = false
  try {
    const partyCodes = Array.from(selectedPartyCodes.value)
    const result = await api.sendReminders(partyCodes, defaultTemplateId.value)
    if (result.session_id) {
      activeSession.value = {
        session_id: result.session_id,
        state: 'starting',
        progress: { current: 0, total: partyCodes.length, percentage: 0 }
      }
      startSessionPolling(result.session_id)
    }
    toast.add({
      severity: 'success', summary: 'Session Started',
      detail: `Sending to ${partyCodes.length} parties`, life: 5000
    })
    selectedPartyCodes.value.clear()
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to start session', life: 3000 })
  } finally {
    sending.value = false
  }
}

function startSessionPolling(sessionId: string): void {
  const interval = setInterval(async () => {
    try {
      const status = await api.getSessionStatus(sessionId)
      if (status) {
        activeSession.value = {
          session_id: sessionId,
          state: status.state,
          progress: status.progress,
        }
        if (['completed', 'stopped', 'error'].includes(status.state)) {
          clearInterval(interval)
          setTimeout(() => { activeSession.value = null }, 8000)
        }
      }
    } catch {
      clearInterval(interval)
      activeSession.value = null
    }
  }, 2000)
}

async function pauseSession(): Promise<void> {
  if (!activeSession.value) return
  try { await api.pauseSession(activeSession.value.session_id) } catch {}
}

async function resumeSession(): Promise<void> {
  if (!activeSession.value) return
  try { await api.resumeSession(activeSession.value.session_id) } catch {}
}

async function stopSession(): Promise<void> {
  if (!activeSession.value) return
  try {
    await api.stopSession(activeSession.value.session_id)
    activeSession.value = null
  } catch {}
}

function onTemplateSaved(): void { loadTemplates() }

// Watchers
watch(filterBy, () => { first.value = 0; loadParties() })

// Lifecycle
onMounted(() => { loadData() })
</script>

<style scoped>
.reminders-page {
  padding-bottom: 5rem; /* space for sticky bar */
}

/* Text accent */
.text-accent {
  color: var(--bw-brand-primary-light) !important;
}

.stat-active-session {
  border-color: var(--bw-brand-primary) !important;
  box-shadow: var(--bw-shadow-glow);
}

/* Session panel */
.session-panel {
  background: var(--bw-bg-card);
  border: 1px solid var(--bw-border-default);
  border-left: 3px solid var(--bw-brand-primary);
  border-radius: var(--bw-radius-lg);
  padding: var(--bw-space-md) var(--bw-space-lg);
  margin-bottom: var(--bw-space-lg);
}

.session-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--bw-space-sm);
}

.session-info {
  display: flex;
  align-items: center;
  gap: var(--bw-space-sm);
  font-size: 0.875rem;
  font-weight: 600;
}

.session-info i { color: var(--bw-brand-primary); }
.session-id { color: var(--bw-text-secondary); font-weight: 400; }
.session-state-tag { text-transform: capitalize; }

.session-controls {
  display: flex;
  gap: 0.25rem;
}

.session-progress {
  height: 6px;
  margin-bottom: var(--bw-space-xs);
}

.session-metrics {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--bw-text-muted);
}

.session-metrics .pct {
  font-weight: 600;
  color: var(--bw-brand-primary-light);
}

/* Party section */
.party-section {
  margin-bottom: var(--bw-space-lg);
}

.party-toolbar {
  display: flex;
  gap: var(--bw-space-sm);
  align-items: center;
}

.search-wrap { position: relative; }
.search-wrap i {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--bw-text-muted);
  font-size: 0.8rem;
  z-index: 1;
}
.party-search { padding-left: 2rem !important; width: 200px; }
.filter-dropdown { min-width: 155px; }

.party-table-body { padding: 0; }

.party-table :deep(.p-datatable-wrapper) {
  border-radius: 0;
}

.party-table :deep(.row-selected) {
  background: var(--bw-brand-primary-alpha) !important;
}

.party-cell {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.party-cell-name {
  font-weight: 500;
  font-size: 0.875rem;
  color: var(--bw-text-primary);
}

.party-cell-code {
  font-size: 0.72rem;
  color: var(--bw-text-muted);
}

.amount-cell {
  font-weight: 600;
  color: var(--bw-brand-primary-light);
  font-variant-numeric: tabular-nums;
}

.phone-cell {
  font-size: 0.82rem;
  color: var(--bw-text-secondary);
}

.date-cell {
  font-size: 0.78rem;
  color: var(--bw-text-muted);
}

/* Table footer */
.table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--bw-space-sm) var(--bw-space-lg);
  border-top: 1px solid var(--bw-border-subtle);
}

.table-footer-left,
.table-footer-right {
  display: flex;
  align-items: center;
  gap: var(--bw-space-sm);
}

.showing-text {
  font-size: 0.75rem;
  color: var(--bw-text-muted);
}

.page-info {
  font-size: 0.75rem;
  color: var(--bw-text-secondary);
  font-weight: 500;
}

/* Config accordion */
.config-accordion {
  margin-bottom: var(--bw-space-lg);
}

.accordion-header-content {
  display: flex;
  align-items: center;
  gap: var(--bw-space-sm);
  font-weight: 500;
}

.accordion-header-content i {
  color: var(--bw-brand-primary);
}

/* Template config */
.template-config {
  display: flex;
  flex-direction: column;
  gap: var(--bw-space-md);
}

.template-selector-row {
  display: flex;
  gap: var(--bw-space-sm);
  align-items: center;
}

.template-dropdown { flex: 1; max-width: 400px; }

.template-preview {
  background: rgba(15, 23, 42, 0.4);
  border: 1px solid var(--bw-border-subtle);
  border-radius: var(--bw-radius-md);
  padding: var(--bw-space-md);
}

.template-preview pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 0.82rem;
  font-family: var(--bw-font-mono);
  color: var(--bw-text-secondary);
  line-height: 1.6;
}

/* Anti-spam */
.antispam-config {
  display: flex;
  flex-direction: column;
  gap: var(--bw-space-md);
}

.antispam-master {
  display: flex;
  align-items: center;
  gap: var(--bw-space-md);
}

.antispam-master .toggle-text {
  font-weight: 500;
  display: block;
}

.antispam-master small {
  color: var(--bw-text-muted);
  font-size: 0.75rem;
}

.antispam-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--bw-space-md);
  padding-left: var(--bw-space-xl);
}

.antispam-option {
  display: flex;
  align-items: flex-start;
  gap: var(--bw-space-sm);
  cursor: pointer;
}

.antispam-option span {
  font-size: 0.875rem;
  font-weight: 500;
}

.antispam-option small {
  color: var(--bw-text-muted);
  font-size: 0.72rem;
  display: block;
}

/* Sticky action bar */
.action-bar {
  position: fixed;
  bottom: 0;
  left: 260px;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.5rem;
  background: var(--bw-bg-glass);
  backdrop-filter: blur(16px);
  border-top: 1px solid var(--bw-border-subtle);
  z-index: 50;
  transition: all var(--bw-transition-normal);
}

.action-bar.has-selection {
  border-top-color: var(--bw-brand-primary);
  box-shadow: 0 -4px 20px rgba(20, 184, 166, 0.1);
}

.action-bar-left,
.action-bar-right {
  display: flex;
  align-items: center;
  gap: var(--bw-space-sm);
}

.selection-summary {
  font-size: 0.875rem;
  color: var(--bw-text-secondary);
}

.selection-summary strong {
  color: var(--bw-text-primary);
  font-size: 1rem;
}

.selection-summary.muted {
  color: var(--bw-text-muted);
}

.send-btn {
  padding: 0.6rem 1.5rem !important;
  font-size: 0.9rem !important;
}

/* Confirm dialog */
.confirm-body {
  display: flex;
  gap: var(--bw-space-lg);
  align-items: flex-start;
}

.confirm-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: var(--bw-radius-md);
  background: var(--bw-gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  color: white;
  flex-shrink: 0;
}

.confirm-heading {
  font-weight: 600;
  margin-bottom: var(--bw-space-sm);
}

.confirm-stats {
  display: flex;
  gap: var(--bw-space-lg);
  margin-bottom: var(--bw-space-md);
}

.confirm-stat {
  display: flex;
  flex-direction: column;
}

.confirm-stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--bw-brand-primary-light);
}

.confirm-stat-label {
  font-size: 0.72rem;
  color: var(--bw-text-muted);
  text-transform: uppercase;
}

.confirm-template {
  font-size: 0.85rem;
  color: var(--bw-text-secondary);
  margin-bottom: var(--bw-space-sm);
}

.confirm-eta {
  display: flex;
  align-items: center;
  gap: var(--bw-space-sm);
  padding-top: var(--bw-space-sm);
  border-top: 1px solid var(--bw-border-subtle);
}

.confirm-eta small {
  color: var(--bw-text-muted);
}

/* Transitions */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Responsive */
@media (max-width: 1024px) {
  .action-bar {
    left: 0;
  }
}

@media (max-width: 768px) {
  .party-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .party-search {
    width: 100% !important;
  }

  .action-bar {
    flex-direction: column;
    gap: var(--bw-space-sm);
    align-items: stretch;
  }

  .action-bar-right {
    justify-content: flex-end;
  }
}
</style>
