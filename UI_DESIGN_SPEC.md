# Busy Whatsapp Bridge - UI/UX Design Specification

## Project Overview
Modern web dashboard for managing WhatsApp gateway with real-time updates, dark mode support, and professional 2026 design aesthetic.

---

## 1. Global Layout Architecture

### Root Component Hierarchy
```
App.vue
├── Toast (global notifications)
├── ConfirmDialog (confirmation dialogs)
├── Sidebar (navigation)
│   ├── Logo/Brand Header
│   ├── Menu (PrimeVue Menu)
│   └── Theme Toggle
├── Main Layout Area
│   ├── Menubar (top header)
│   │   ├── Breadcrumbs
│   │   ├── Real-time Status Indicator
│   │   └── User Actions
│   └── RouterView
│       └── Page Content
└── ConnectionStatusBar (footer - optional)
```

### Component: AppLayout.vue
```vue
<template>
  <div class="app-layout" :class="{ 'dark-mode': isDarkMode }">
    <Toast position="top-right" />
    <ConfirmDialog />
    
    <Sidebar
      v-model:visible="sidebarVisible"
      :showCloseIcon="false"
      class="main-sidebar"
    >
      <template #header>
        <div class="brand-header">
          <i class="pi pi-whatsapp brand-icon"></i>
          <span class="brand-text">Busy Gateway</span>
        </div>
      </template>
      
      <Menu :model="menuItems" class="main-menu" />
      
      <template #footer>
        <ToggleButton
          v-model="isDarkMode"
          onIcon="pi pi-moon"
          offIcon="pi pi-sun"
          onLabel="Dark"
          offLabel="Light"
          class="theme-toggle"
        />
      </template>
    </Sidebar>
    
    <div class="main-content" :class="{ 'sidebar-collapsed': !sidebarVisible }">
      <Menubar class="top-menubar">
        <template #start>
          <Button
            icon="pi pi-bars"
            text
            @click="sidebarVisible = !sidebarVisible"
            class="menu-toggle"
          />
          <Breadcrumb :home="home" :model="breadcrumbs" />
        </template>
        
        <template #end>
          <div class="status-indicators">
            <Tag
              :value="connectionStatus"
              :severity="connectionSeverity"
              icon="pi pi-wifi"
              class="connection-tag"
            />
            <Button icon="pi pi-bell" text badge="3" badgeSeverity="danger" />
            <Avatar icon="pi pi-user" shape="circle" class="user-avatar" />
          </div>
        </template>
      </Menubar>
      
      <main class="page-content">
        <router-view />
      </main>
    </div>
  </div>
</template>
```

---

## 2. Sidebar Navigation Structure

### Menu Configuration
```javascript
const menuItems = ref([
  {
    label: 'Dashboard',
    icon: 'pi pi-home',
    to: '/',
    badge: null
  },
  {
    label: 'WhatsApp',
    icon: 'pi pi-whatsapp',
    to: '/whatsapp',
    badge: 'connected',
    badgeStyle: { background: '#10b981', color: '#fff' }
  },
  {
    label: 'Queue',
    icon: 'pi pi-inbox',
    to: '/queue',
    badge: '12',
    badgeSeverity: 'warning'
  },
  {
    separator: true
  },
  {
    label: 'System',
    items: [
      {
        label: 'Logs',
        icon: 'pi pi-file-edit',
        to: '/logs'
      },
      {
        label: 'Diagnostics',
        icon: 'pi pi-cog',
        to: '/system'
      },
      {
        label: 'Settings',
        icon: 'pi pi-sliders-h',
        to: '/settings'
      }
    ]
  }
])
```

### Sidebar Props
```javascript
{
  visible: Boolean,           // v-model for visibility
  position: 'left',
  modal: false,              // Non-modal for desktop
  showCloseIcon: false,
  class: 'main-sidebar',
  style: {
    width: '260px',
    borderRight: '1px solid var(--surface-border)'
  }
}
```

---

## 3. Color Scheme Specification

### CSS Custom Properties (Dark Mode - Default)
```css
:root {
  /* Primary Brand Colors */
  --primary-50: #ecfdf5;
  --primary-100: #d1fae5;
  --primary-200: #a7f3d0;
  --primary-300: #6ee7b7;
  --primary-400: #34d399;
  --primary-500: #10b981;  /* WhatsApp green accent */
  --primary-600: #059669;
  --primary-700: #047857;
  --primary-800: #065f46;
  --primary-900: #064e3b;
  
  /* Surface Colors (Dark Mode) */
  --surface-0: #ffffff;
  --surface-50: #f8fafc;
  --surface-100: #f1f5f9;
  --surface-200: #e2e8f0;
  --surface-300: #cbd5e1;
  --surface-400: #94a3b8;
  --surface-500: #64748b;
  --surface-600: #475569;
  --surface-700: #334155;
  --surface-800: #1e293b;
  --surface-900: #0f172a;  /* Main background */
  --surface-950: #020617;
  
  /* Semantic Colors */
  --success: #22c55e;
  --warning: #f59e0b;
  --danger: #ef4444;
  --info: #3b82f6;
  
  /* Accent Colors */
  --accent-blue: #0ea5e9;
  --accent-purple: #8b5cf6;
  --accent-pink: #ec4899;
  
  /* Text Colors */
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  
  /* Border & Shadow */
  --border-color: rgba(148, 163, 184, 0.1);
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
  --shadow-glow: 0 0 20px rgba(16, 185, 129, 0.3);
}

/* Light Mode Override */
[data-theme="light"] {
  --surface-900: #f8fafc;
  --surface-800: #f1f5f9;
  --surface-700: #e2e8f0;
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --border-color: rgba(148, 163, 184, 0.2);
}
```

### Theme Preset Configuration
```javascript
const darkTheme = definePreset(Aura, {
  semantic: {
    primary: {
      50: '{emerald.50}',
      100: '{emerald.100}',
      200: '{emerald.200}',
      300: '{emerald.300}',
      400: '{emerald.400}',
      500: '{emerald.500}',
      600: '{emerald.600}',
      700: '{emerald.700}',
      800: '{emerald.800}',
      900: '{emerald.900}',
      950: '{emerald.950}'
    },
    colorScheme: {
      dark: {
        surface: {
          0: '#ffffff',
          50: '{slate.50}',
          100: '{slate.100}',
          200: '{slate.200}',
          300: '{slate.300}',
          400: '{slate.400}',
          500: '{slate.500}',
          600: '{slate.600}',
          700: '{slate.700}',
          800: '{slate.800}',
          900: '#0f172a',
          950: '#020617'
        },
        primary: {
          color: '{primary.500}',
          inverseColor: '#ffffff',
          hoverColor: '{primary.400}',
          activeColor: '{primary.300}'
        },
        content: {
          background: '{surface.900}',
          hoverBackground: '{surface.800}',
          borderColor: '{surface.700}'
        }
      }
    }
  }
})
```

---

## 4. Page Specifications

### Page 1: Overview Dashboard (`/`)

**Layout Structure:**
```
DashboardView.vue
├── PageHeader (title + refresh button)
├── StatsCards Grid (4 columns)
├── Main Content Splitter
│   ├── Left Panel (60%) - Charts & Activity
│   │   ├── ConnectionChart (Line chart)
│   │   └── RecentActivity (Timeline)
│   └── Right Panel (40%) - System Health
│       ├── HealthCards (Server, DB, WhatsApp)
│       └── QuickActions
└── AlertsPanel (collapsible)
```

**Components Used:**

```vue
<template>
  <div class="dashboard-page">
    <!-- Page Header -->
    <div class="page-header">
      <h1>Dashboard Overview</h1>
      <div class="header-actions">
        <Button
          icon="pi pi-refresh"
          text
          :loading="loading"
          @click="refreshDashboard"
          tooltip="Refresh Data"
        />
        <Calendar
          v-model="dateRange"
          selectionMode="range"
          showIcon
          placeholder="Select Date Range"
        />
      </div>
    </div>
    
    <!-- Stats Cards -->
    <div class="stats-grid">
      <Card v-for="stat in stats" :key="stat.id" class="stat-card">
        <template #content>
          <div class="stat-content">
            <div class="stat-icon" :style="{ background: stat.color + '20' }">
              <i :class="stat.icon" :style="{ color: stat.color }"></i>
            </div>
            <div class="stat-info">
              <span class="stat-label">{{ stat.label }}</span>
              <span class="stat-value">{{ stat.value }}</span>
              <Tag
                :value="stat.trend"
                :severity="stat.trend > 0 ? 'success' : 'danger'"
                icon="pi pi-arrow-up"
              />
            </div>
          </div>
        </template>
      </Card>
    </div>
    
    <!-- Main Content Splitter -->
    <Splitter style="height: 500px" class="main-splitter">
      <SplitterPanel :size="60" :minSize="40">
        <TabView>
          <TabPanel header="Activity Timeline" headerIcon="pi pi-clock">
            <Timeline :value="activities" align="alternate">
              <template #content="slotProps">
                <Card class="activity-card">
                  <template #title>
                    <div class="activity-header">
                      <Tag :value="slotProps.item.type" :severity="slotProps.item.severity" />
                      <span class="activity-time">{{ slotProps.item.time }}</span>
                    </div>
                  </template>
                  <template #content>
                    <p>{{ slotProps.item.description }}</p>
                  </template>
                </Card>
              </template>
            </Timeline>
          </TabPanel>
          
          <TabPanel header="Connection History" headerIcon="pi pi-chart-line">
            <Chart type="line" :data="connectionData" :options="chartOptions" />
          </TabPanel>
        </TabView>
      </SplitterPanel>
      
      <SplitterPanel :size="40" :minSize="30">
        <div class="health-panel">
          <h3>System Health</h3>
          <Panel
            v-for="service in services"
            :key="service.name"
            :header="service.name"
            :collapsed="false"
            toggleable
            class="health-panel-item"
          >
            <div class="health-status">
              <Knob
                :value="service.health"
                :size="80"
                :strokeWidth="10"
                :valueColor="service.color"
                :textColor="service.textColor"
                valueTemplate="{value}%"
              />
              <div class="health-details">
                <Tag
                  :value="service.status"
                  :severity="service.severity"
                  class="health-tag"
                />
                <span class="health-uptime">Uptime: {{ service.uptime }}</span>
              </div>
            </div>
          </Panel>
        </div>
      </SplitterPanel>
    </Splitter>
  </div>
</template>
```

**Stats Cards Data:**
```javascript
const stats = ref([
  { 
    id: 1, 
    label: 'Messages Sent Today', 
    value: '1,247', 
    trend: '+12%', 
    icon: 'pi pi-send', 
    color: '#10b981' 
  },
  { 
    id: 2, 
    label: 'Queue Size', 
    value: '23', 
    trend: '-5%', 
    icon: 'pi pi-inbox', 
    color: '#f59e0b' 
  },
  { 
    id: 3, 
    label: 'Success Rate', 
    value: '98.5%', 
    trend: '+0.3%', 
    icon: 'pi pi-check-circle', 
    color: '#22c55e' 
  },
  { 
    id: 4, 
    label: 'Failed Messages', 
    value: '3', 
    trend: '-2', 
    icon: 'pi pi-exclamation-triangle', 
    color: '#ef4444' 
  }
])
```

---

### Page 2: WhatsApp (`/whatsapp`)

**Layout Structure:**
```
WhatsAppView.vue
├── ConnectionStatus Header
├── Main Content Area
│   ├── QR Code Display (center, large)
│   ├── Connection Controls
│   └── Session Info Panel
└── Connection Log (bottom panel)
```

**Components Used:**

```vue
<template>
  <div class="whatsapp-page">
    <!-- Connection Status Header -->
    <div class="connection-header">
      <div class="status-display">
        <Avatar
          :icon="connectionIcon"
          :style="{ background: connectionColor + '20', color: connectionColor }"
          size="xlarge"
          shape="circle"
        />
        <div class="status-text">
          <h2>{{ connectionTitle }}</h2>
          <Tag :value="connectionStatus" :severity="connectionSeverity" />
        </div>
      </div>
      
      <div class="connection-actions">
        <Button
          :label="isConnected ? 'Disconnect' : 'Connect'"
          :icon="isConnected ? 'pi pi-power-off' : 'pi pi-play'"
          :severity="isConnected ? 'danger' : 'success'"
          @click="toggleConnection"
          :loading="connecting"
        />
        <Button
          icon="pi pi-refresh"
          label="Regenerate QR"
          severity="secondary"
          @click="regenerateQR"
          :disabled="!needsQR"
        />
        <Button
          icon="pi pi-ellipsis-v"
          severity="secondary"
          text
          @click="toggleMenu"
        />
        <Menu ref="menu" :model="connectionMenu" popup />
      </div>
    </div>
    
    <!-- Main Content -->
    <div class="qr-container">
      <Card v-if="showQR" class="qr-card">
        <template #title>
          <div class="qr-header">
            <i class="pi pi-qrcode"></i>
            <span>Scan with WhatsApp</span>
          </div>
        </template>
        <template #content>
          <div class="qr-wrapper">
            <!-- QR Code Image from API -->
            <Skeleton v-if="!qrCode" width="300px" height="300px" />
            <img v-else :src="qrCode" alt="WhatsApp QR Code" class="qr-image" />
            
            <!-- QR Refresh Timer -->
            <ProgressBar
              :value="qrProgress"
              :showValue="false"
              class="qr-timer"
              :class="{ 'expiring': qrProgress < 20 }"
            />
            
            <p class="qr-instructions">
              Open WhatsApp on your phone → Settings → Linked Devices → Link a Device
            </p>
          </div>
        </template>
      </Card>
      
      <Card v-else-if="isConnected" class="connected-card">
        <template #content>
          <div class="connected-state">
            <i class="pi pi-check-circle success-icon"></i>
            <h3>Connected Successfully</h3>
            <p>Your WhatsApp is now linked and ready to send messages</p>
            <div class="session-info">
              <div class="info-item">
                <span class="label">Phone Number:</span>
                <span class="value">{{ sessionInfo.phone }}</span>
              </div>
              <div class="info-item">
                <span class="label">Connected Since:</span>
                <span class="value">{{ sessionInfo.connectedAt }}</span>
              </div>
              <div class="info-item">
                <span class="label">Session ID:</span>
                <span class="value">{{ sessionInfo.sessionId }}</span>
              </div>
            </div>
          </div>
        </template>
      </Card>
    </div>
    
    <!-- Connection Log Panel -->
    <Panel header="Connection Log" toggleable :collapsed="true" class="log-panel">
      <Terminal
        welcomeMessage="WhatsApp Connection Log"
        prompt="gateway $"
        :response="terminalResponse"
        class="connection-terminal"
      />
    </Panel>
  </div>
</template>
```

---

### Page 3: Queue (`/queue`)

**Layout Structure:**
```
QueueView.vue
├── PageHeader with Stats
├── Tabbed Interface
│   ├── Tab 1: Pending
│   ├── Tab 2: Retrying
│   ├── Tab 3: Dead Letter
│   └── Tab 4: History
└── DataTable in each tab
```

**Components Used:**

```vue
<template>
  <div class="queue-page">
    <div class="page-header">
      <div class="header-title">
        <h1>Message Queue</h1>
        <Tag :value="`${totalMessages} total`" severity="info" />
      </div>
      <div class="header-actions">
        <Button
          icon="pi pi-filter"
          label="Filters"
          severity="secondary"
          @click="showFilters = true"
        />
        <Button
          icon="pi pi-refresh"
          label="Refresh"
          severity="secondary"
          @click="refreshQueue"
          :loading="loading"
        />
        <Button
          icon="pi pi-play"
          label="Process All"
          severity="success"
          @click="processAll"
          :disabled="pendingCount === 0"
        />
      </div>
    </div>
    
    <!-- Queue Stats Cards -->
    <div class="queue-stats">
      <div v-for="stat in queueStats" :key="stat.status" class="stat-item">
        <span class="stat-count" :style="{ color: stat.color }">{{ stat.count }}</span>
        <span class="stat-label">{{ stat.label }}</span>
        <ProgressBar :value="stat.percentage" :showValue="false" :class="stat.status" />
      </div>
    </div>
    
    <!-- Tabbed Queue View -->
    <TabView v-model:activeIndex="activeTab" class="queue-tabs">
      <!-- Pending Tab -->
      <TabPanel header="Pending">
        <template #header>
          <span class="tab-header">
            <i class="pi pi-clock"></i>
            Pending
            <Badge :value="pendingCount" severity="warning" />
          </span>
        </template>
        
        <DataTable
          :value="pendingMessages"
          :paginator="true"
          :rows="20"
          :rowsPerPageOptions="[10, 20, 50, 100]"
          v-model:selection="selectedMessages"
          dataKey="id"
          :filters="filters"
          filterDisplay="menu"
          :loading="loading"
          stripedRows
          removableSort
          class="queue-table"
        >
          <Column selectionMode="multiple" headerStyle="width: 3rem" />
          <Column field="id" header="ID" sortable style="width: 100px">
            <template #body="{ data }">
              <Tag :value="`#${data.id}`" severity="secondary" />
            </template>
          </Column>
          <Column field="phone" header="Phone" sortable>
            <template #body="{ data }">
              <div class="phone-cell">
                <i class="pi pi-phone"></i>
                <span>{{ data.phone }}</span>
              </div>
            </template>
          </Column>
          <Column field="message" header="Message" style="max-width: 300px">
            <template #body="{ data }">
              <span class="message-preview">{{ truncate(data.message, 50) }}</span>
            </template>
          </Column>
          <Column field="createdAt" header="Created" sortable>
            <template #body="{ data }">
              <span class="timestamp">{{ formatDate(data.createdAt) }}</span>
            </template>
          </Column>
          <Column field="priority" header="Priority" sortable style="width: 120px">
            <template #body="{ data }">
              <Tag
                :value="data.priority"
                :severity="prioritySeverity(data.priority)"
              />
            </template>
          </Column>
          <Column style="width: 150px">
            <template #body="{ data }">
              <Button
                icon="pi pi-play"
                severity="success"
                text
                tooltip="Process Now"
                @click="processMessage(data.id)"
              />
              <Button
                icon="pi pi-pencil"
                severity="secondary"
                text
                tooltip="Edit"
                @click="editMessage(data)"
              />
              <Button
                icon="pi pi-trash"
                severity="danger"
                text
                tooltip="Cancel"
                @click="confirmCancel(data)"
              />
            </template>
          </Column>
        </DataTable>
      </TabPanel>
      
      <!-- Retrying Tab -->
      <TabPanel header="Retrying">
        <template #header>
          <span class="tab-header">
            <i class="pi pi-replay"></i>
            Retrying
            <Badge :value="retryingCount" severity="info" />
          </span>
        </template>
        
        <DataTable :value="retryingMessages" class="queue-table">
          <Column field="id" header="ID" />
          <Column field="phone" header="Phone" />
          <Column field="retryCount" header="Retry Count">
            <template #body="{ data }">
              <Knob
                :value="data.retryCount"
                :max="5"
                :size="50"
                :strokeWidth="10"
                valueColor="#f59e0b"
              />
              <span class="retry-text">{{ data.retryCount }}/5</span>
            </template>
          </Column>
          <Column field="nextRetry" header="Next Retry">
            <template #body="{ data }">
              <CountdownTimer :target="data.nextRetry" />
            </template>
          </Column>
          <Column field="lastError" header="Last Error" style="max-width: 250px">
            <template #body="{ data }">
              <span class="error-text" :title="data.lastError">
                {{ truncate(data.lastError, 40) }}
              </span>
            </template>
          </Column>
          <Column>
            <template #body="{ data }">
              <Button
                icon="pi pi-fast-forward"
                label="Retry Now"
                severity="warning"
                @click="retryNow(data.id)"
              />
            </template>
          </Column>
        </DataTable>
      </TabPanel>
      
      <!-- Dead Letter Tab -->
      <TabPanel header="Dead Letter">
        <template #header>
          <span class="tab-header">
            <i class="pi pi-times-circle"></i>
            Dead Letter
            <Badge :value="deadLetterCount" severity="danger" />
          </span>
        </template>
        
        <DataTable :value="deadLetterMessages" class="queue-table">
          <Column field="id" header="ID" />
          <Column field="phone" header="Phone" />
          <Column field="failedAt" header="Failed At" />
          <Column field="totalRetries" header="Total Retries" />
          <Column field="finalError" header="Final Error" />
          <Column>
            <template #body="{ data }">
              <Button
                icon="pi pi-undo"
                label="Requeue"
                severity="secondary"
                @click="requeueMessage(data.id)"
              />
              <Button
                icon="pi pi-eye"
                severity="info"
                text
                @click="viewDetails(data)"
              />
            </template>
          </Column>
        </DataTable>
      </TabPanel>
      
      <!-- History Tab -->
      <TabPanel header="History">
        <template #header>
          <span class="tab-header">
            <i class="pi pi-history"></i>
            History
          </span>
        </template>
        
        <DataTable
          :value="messageHistory"
          :paginator="true"
          :rows="25"
          :lazy="true"
          @page="onPage"
          :totalRecords="totalHistory"
          class="queue-table"
        >
          <Column field="id" header="ID" />
          <Column field="phone" header="Phone" />
          <Column field="status" header="Status">
            <template #body="{ data }">
              <Tag
                :value="data.status"
                :severity="statusSeverity(data.status)"
                :icon="statusIcon(data.status)"
              />
            </template>
          </Column>
          <Column field="sentAt" header="Sent At" sortable />
          <Column field="deliveredAt" header="Delivered" />
          <Column>
            <template #body="{ data }">
              <Button
                icon="pi pi-search"
                severity="secondary"
                text
                @click="viewMessageDetails(data)"
              />
            </template>
          </Column>
        </DataTable>
      </TabPanel>
    </TabView>
    
    <!-- Message Detail Dialog -->
    <Dialog
      v-model:visible="showMessageDialog"
      :header="`Message #${selectedMessage?.id}`"
      :style="{ width: '600px' }"
      :modal="true"
    >
      <div class="message-detail">
        <div class="detail-row">
          <label>Phone:</label>
          <span>{{ selectedMessage?.phone }}</span>
        </div>
        <div class="detail-row">
          <label>Message:</label>
          <Textarea
            :modelValue="selectedMessage?.message"
            readonly
            rows="5"
            class="w-full"
          />
        </div>
        <div class="detail-row">
          <label>PDF URL:</label>
          <a v-if="selectedMessage?.pdfUrl" :href="selectedMessage.pdfUrl" target="_blank">
            {{ selectedMessage.pdfUrl }}
          </a>
          <span v-else class="text-muted">None</span>
        </div>
        <Timeline :value="selectedMessage?.history" class="message-timeline">
          <template #content="slotProps">
            <span>{{ slotProps.item.event }}</span>
            <small>{{ slotProps.item.timestamp }}</small>
          </template>
        </Timeline>
      </div>
    </Dialog>
  </div>
</template>
```

---

### Page 4: Logs (`/logs`)

**Layout Structure:**
```
LogsView.vue
├── Log Controls Toolbar
├── Terminal/Log Viewer (main area)
└── Log Filter Sidebar (collapsible)
```

**Components Used:**

```vue
<template>
  <div class="logs-page">
    <!-- Toolbar -->
    <Toolbar class="logs-toolbar">
      <template #start>
        <div class="toolbar-group">
          <Dropdown
            v-model="selectedLogLevel"
            :options="logLevels"
            optionLabel="label"
            placeholder="Log Level"
            class="log-level-filter"
          />
          <MultiSelect
            v-model="selectedSources"
            :options="logSources"
            optionLabel="name"
            placeholder="Sources"
            display="chip"
            class="source-filter"
          />
          <InputText
            v-model="searchQuery"
            placeholder="Search logs..."
            class="search-input"
          >
            <template #prefix>
              <i class="pi pi-search"></i>
            </template>
          </InputText>
        </div>
      </template>
      
      <template #center>
        <div class="live-indicator" :class="{ 'live': isLive }">
          <span class="pulse-dot"></span>
          <span>{{ isLive ? 'Live' : 'Paused' }}</span>
        </div>
      </template>
      
      <template #end>
        <div class="toolbar-group">
          <ToggleButton
            v-model="isLive"
            onIcon="pi pi-pause"
            offIcon="pi pi-play"
            onLabel="Pause"
            offLabel="Live"
            class="live-toggle"
          />
          <Button
            icon="pi pi-download"
            label="Export"
            severity="secondary"
            @click="exportLogs"
          />
          <Button
            icon="pi pi-trash"
            label="Clear"
            severity="danger"
            text
            @click="clearLogs"
          />
        </div>
      </template>
    </Toolbar>
    
    <!-- Log Viewer -->
    <Splitter class="logs-splitter">
      <SplitterPanel :size="75">
        <Terminal
          ref="logTerminal"
          class="log-terminal"
          welcomeMessage="Log Stream - Connected"
          prompt=""
          :response="terminalLines"
        />
      </SplitterPanel>
      
      <SplitterPanel :size="25" :minSize="20">
        <div class="log-sidebar">
          <h3>Log Statistics</h3>
          
          <div class="stat-cards">
            <Card v-for="stat in logStats" :key="stat.level" class="log-stat-card">
              <template #content>
                <div class="log-stat">
                  <span class="stat-number">{{ stat.count }}</span>
                  <Tag :value="stat.level" :severity="stat.severity" />
                </div>
              </template>
            </Card>
          </div>
          
          <Divider />
          
          <h3>Active Filters</h3>
          <div class="active-filters">
            <Chip
              v-for="filter in activeFilters"
              :key="filter.id"
              :label="filter.label"
              removable
              @remove="removeFilter(filter)"
            />
          </div>
          
          <Divider />
          
          <h3>Time Range</h3>
          <Calendar
            v-model="timeRange"
            selectionMode="range"
            showTime
            hourFormat="24"
            placeholder="Select time range"
            class="w-full"
          />
        </div>
      </SplitterPanel>
    </Splitter>
  </div>
</template>
```

---

### Page 5: System (`/system`)

**Layout Structure:**
```
SystemView.vue
├── Process Control Cards
├── System Metrics Dashboard
├── Diagnostic Tools Section
└── Action Panel
```

**Components Used:**

```vue
<template>
  <div class="system-page">
    <div class="page-header">
      <h1>System Management</h1>
      <Button
        icon="pi pi-refresh"
        label="Refresh Stats"
        severity="secondary"
        @click="refreshStats"
      />
    </div>
    
    <!-- Process Control Cards -->
    <div class="process-grid">
      <Card v-for="process in processes" :key="process.name" class="process-card">
        <template #title>
          <div class="process-header">
            <i :class="process.icon"></i>
            <span>{{ process.name }}</span>
            <Tag
              :value="process.status"
              :severity="process.severity"
              class="process-status"
            />
          </div>
        </template>
        <template #content>
          <div class="process-metrics">
            <div class="metric">
              <span class="metric-label">PID</span>
              <span class="metric-value">{{ process.pid || 'N/A' }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Uptime</span>
              <span class="metric-value">{{ process.uptime }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">Memory</span>
              <span class="metric-value">{{ process.memory }}</span>
            </div>
          </div>
          <ProgressBar :value="process.cpuUsage" class="cpu-bar">
            <span class="cpu-label">CPU: {{ process.cpuUsage }}%</span>
          </ProgressBar>
        </template>
        <template #footer>
          <div class="process-actions">
            <Button
              :icon="process.running ? 'pi pi-pause' : 'pi pi-play'"
              :label="process.running ? 'Stop' : 'Start'"
              :severity="process.running ? 'danger' : 'success'"
              @click="toggleProcess(process)"
              :loading="process.loading"
            />
            <Button
              icon="pi pi-refresh"
              label="Restart"
              severity="secondary"
              @click="restartProcess(process)"
              :disabled="!process.running"
            />
            <Button
              icon="pi pi-info-circle"
              severity="secondary"
              text
              @click="showProcessDetails(process)"
            />
          </div>
        </template>
      </Card>
    </div>
    
    <!-- System Metrics -->
    <div class="metrics-section">
      <h2>System Resources</h2>
      <div class="metrics-grid">
        <Panel header="CPU Usage" class="metric-panel">
          <Chart type="line" :data="cpuData" :options="chartOptions" />
        </Panel>
        <Panel header="Memory Usage" class="metric-panel">
          <Chart type="bar" :data="memoryData" :options="chartOptions" />
        </Panel>
        <Panel header="Disk Usage" class="metric-panel">
          <div class="disk-stats">
            <div v-for="disk in diskUsage" :key="disk.name" class="disk-item">
              <span class="disk-name">{{ disk.name }}</span>
              <ProgressBar :value="disk.percentage" :class="disk.status" />
              <span class="disk-size">{{ disk.used }} / {{ disk.total }}</span>
            </div>
          </div>
        </Panel>
        <Panel header="Network I/O" class="metric-panel">
          <Chart type="line" :data="networkData" :options="chartOptions" />
        </Panel>
      </div>
    </div>
    
    <!-- Diagnostic Tools -->
    <Panel header="Diagnostic Tools" toggleable class="diagnostics-panel">
      <div class="diagnostics-grid">
        <Card class="diagnostic-card">
          <template #title>Health Check</template>
          <template #content>
            <p>Run comprehensive system health check</p>
            <Button
              icon="pi pi-check-circle"
              label="Run Check"
              @click="runHealthCheck"
              :loading="checking"
            />
          </template>
        </Card>
        
        <Card class="diagnostic-card">
          <template #title>Database Test</template>
          <template #content>
            <p>Test database connectivity</p>
            <Button
              icon="pi pi-database"
              label="Test Connection"
              severity="secondary"
              @click="testDatabase"
            />
          </template>
        </Card>
        
        <Card class="diagnostic-card">
          <template #title>WhatsApp Ping</template>
          <template #content>
            <p>Test WhatsApp service response</p>
            <Button
              icon="pi pi-whatsapp"
              label="Ping Service"
              severity="success"
              @click="pingWhatsApp"
            />
          </template>
        </Card>
        
        <Card class="diagnostic-card">
          <template #title>Network Test</template>
          <template #content>
            <p>Check external connectivity</p>
            <Button
              icon="pi pi-globe"
              label="Test Network"
              severity="info"
              @click="testNetwork"
            />
          </template>
        </Card>
      </div>
    </Panel>
  </div>
</template>
```

---

### Page 6: Settings (`/settings`)

**Layout Structure:**
```
SettingsView.vue
├── Settings Navigation (vertical tabs)
├── Settings Content Panel
│   ├── General Settings
│   ├── WhatsApp Configuration
│   ├── Database Settings
│   ├── Notifications
│   └── Advanced
```

**Components Used:**

```vue
<template>
  <div class="settings-page">
    <h1>Configuration</h1>
    
    <TabView orientation="left" class="settings-tabs">
      <!-- General Settings -->
      <TabPanel header="General" headerIcon="pi pi-cog">
        <div class="settings-section">
          <h2>Application Settings</h2>
          
          <div class="setting-item">
            <label>Application Name</label>
            <InputText v-model="settings.appName" class="w-full" />
          </div>
          
          <div class="setting-item">
            <label>Debug Mode</label>
            <ToggleButton
              v-model="settings.debug"
              onLabel="Enabled"
              offLabel="Disabled"
            />
          </div>
          
          <div class="setting-item">
            <label>Log Level</label>
            <Dropdown
              v-model="settings.logLevel"
              :options="logLevelOptions"
              optionLabel="label"
              optionValue="value"
              class="w-full"
            />
          </div>
          
          <div class="setting-item">
            <label>Timezone</label>
            <Dropdown
              v-model="settings.timezone"
              :options="timezoneOptions"
              filter
              class="w-full"
            />
          </div>
        </div>
      </TabPanel>
      
      <!-- WhatsApp Settings -->
      <TabPanel header="WhatsApp" headerIcon="pi pi-whatsapp">
        <div class="settings-section">
          <h2>WhatsApp Provider</h2>
          
          <div class="setting-item">
            <label>Provider</label>
            <SelectButton
              v-model="settings.provider"
              :options="providerOptions"
              optionLabel="label"
              optionValue="value"
            />
          </div>
          
          <!-- Baileys Settings -->
          <div v-if="settings.provider === 'baileys'" class="provider-settings">
            <Panel header="Baileys Configuration">
              <div class="setting-item">
                <label>Server URL</label>
                <InputText v-model="settings.baileysUrl" class="w-full" />
              </div>
              <div class="setting-item">
                <label>Auto Reconnect</label>
                <ToggleButton v-model="settings.autoReconnect" />
              </div>
              <div class="setting-item">
                <label>QR Timeout (seconds)</label>
                <Slider v-model="settings.qrTimeout" :min="30" :max="300" />
                <span class="slider-value">{{ settings.qrTimeout }}s</span>
              </div>
            </Panel>
          </div>
          
          <!-- Meta Settings -->
          <div v-if="settings.provider === 'meta'" class="provider-settings">
            <Panel header="Meta Business API">
              <div class="setting-item">
                <label>Phone Number ID</label>
                <InputText v-model="settings.metaPhoneId" class="w-full" />
              </div>
              <div class="setting-item">
                <label>Access Token</label>
                <Password
                  v-model="settings.metaToken"
                  toggleMask
                  class="w-full"
                />
              </div>
              <div class="setting-item">
                <label>Business Account ID</label>
                <InputText v-model="settings.metaBusinessId" class="w-full" />
              </div>
            </Panel>
          </div>
        </div>
      </TabPanel>
      
      <!-- Database Settings -->
      <TabPanel header="Database" headerIcon="pi pi-database">
        <div class="settings-section">
          <h2>Busy Database</h2>
          
          <div class="setting-item">
            <label>BDS File Path</label>
            <div class="file-input">
              <InputText v-model="settings.bdsPath" class="w-full" readonly />
              <Button icon="pi pi-folder-open" @click="selectBdsFile" />
            </div>
          </div>
          
          <div class="setting-item">
            <label>Database Password</label>
            <Password
              v-model="settings.bdsPassword"
              toggleMask
              class="w-full"
            />
          </div>
          
          <div class="setting-item">
            <label>Connection Timeout</label>
            <InputNumber v-model="settings.dbTimeout" suffix=" seconds" />
          </div>
          
          <Button
            icon="pi pi-check"
            label="Test Connection"
            severity="secondary"
            @click="testDbConnection"
            :loading="testingDb"
          />
        </div>
        
        <Divider />
        
        <div class="settings-section">
          <h2>Message Queue Database</h2>
          
          <div class="setting-item">
            <label>Database Path</label>
            <InputText v-model="settings.queueDbPath" class="w-full" />
          </div>
          
          <div class="setting-item">
            <label>Max Retries</label>
            <InputNumber v-model="settings.maxRetries" :min="1" :max="10" />
          </div>
          
          <div class="setting-item">
            <label>Retry Delays (seconds)</label>
            <Chips v-model="settings.retryDelays" separator="," />
          </div>
        </div>
      </TabPanel>
      
      <!-- Notifications -->
      <TabPanel header="Notifications" headerIcon="pi pi-bell">
        <div class="settings-section">
          <h2>Notification Settings</h2>
          
          <div class="setting-item">
            <label>Enable Notifications</label>
            <ToggleButton v-model="settings.notifications" />
          </div>
          
          <div class="setting-item">
            <label>On Message Failed</label>
            <div class="notification-options">
              <Checkbox v-model="settings.notifyOnFail" :binary="true" />
              <label>Show toast notification</label>
            </div>
            <div class="notification-options">
              <Checkbox v-model="settings.emailOnFail" :binary="true" />
              <label>Send email</label>
            </div>
          </div>
          
          <div class="setting-item">
            <label>On Queue Full</label>
            <InputNumber
              v-model="settings.queueThreshold"
              suffix=" messages"
              :min="10"
              :max="1000"
            />
          </div>
          
          <div class="setting-item">
            <label>Email Recipients</label>
            <Chips v-model="settings.emailRecipients" separator="," />
          </div>
        </div>
      </TabPanel>
      
      <!-- Advanced -->
      <TabPanel header="Advanced" headerIcon="pi pi-sliders-h">
        <div class="settings-section">
          <h2>Advanced Configuration</h2>
          
          <div class="setting-item">
            <label>Configuration Editor</label>
            <Textarea
              v-model="rawConfig"
              rows="20"
              class="w-full config-editor"
              spellcheck="false"
            />
          </div>
          
          <div class="setting-actions">
            <Button
              icon="pi pi-undo"
              label="Reset to Default"
              severity="secondary"
              @click="resetConfig"
            />
            <Button
              icon="pi pi-check"
              label="Validate JSON"
              severity="info"
              @click="validateConfig"
            />
            <Button
              icon="pi pi-save"
              label="Save Configuration"
              severity="success"
              @click="saveConfig"
              :loading="saving"
            />
          </div>
        </div>
      </TabPanel>
    </TabView>
  </div>
</template>
```

---

## 5. Key Interactions & Components

### Toast Notifications System
```javascript
// Usage examples
const toast = useToast()

// Success notification
toast.add({
  severity: 'success',
  summary: 'Message Sent',
  detail: 'Message #1234 sent successfully to +91XXXXXXXXXX',
  life: 3000,
  group: 'br'  // bottom-right
})

// Error notification
toast.add({
  severity: 'error',
  summary: 'Connection Failed',
  detail: 'Failed to connect to WhatsApp service',
  life: 5000,
  sticky: true  // Requires manual dismissal
})

// Confirmation dialog
const confirm = useConfirm()

const confirmAction = () => {
  confirm.require({
    message: 'Are you sure you want to delete this message?',
    header: 'Confirm Delete',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Delete',
    rejectLabel: 'Cancel',
    acceptClass: 'p-button-danger',
    accept: () => {
      // Perform delete
      toast.add({
        severity: 'success',
        summary: 'Deleted',
        detail: 'Message removed from queue'
      })
    }
  })
}
```

### WebSocket Real-time Updates
```javascript
// WebSocket composable
export function useWebSocket() {
  const ws = ref(null)
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)
  
  const connect = () => {
    ws.value = new WebSocket('ws://localhost:8000/ws')
    
    ws.value.onopen = () => {
      isConnected.value = true
      reconnectAttempts.value = 0
    }
    
    ws.value.onmessage = (event) => {
      const data = JSON.parse(event.data)
      handleMessage(data)
    }
    
    ws.value.onclose = () => {
      isConnected.value = false
      // Reconnect with exponential backoff
      setTimeout(connect, Math.min(1000 * 2 ** reconnectAttempts.value, 30000))
      reconnectAttempts.value++
    }
  }
  
  const handleMessage = (data) => {
    switch (data.type) {
      case 'qr_code':
        // Update QR code display
        break
      case 'connection_status':
        // Update connection status
        break
      case 'queue_update':
        // Refresh queue data
        break
      case 'log_entry':
        // Append to log viewer
        break
    }
  }
  
  return { connect, isConnected }
}
```

---

## 6. Responsive Behavior

### Breakpoints
```css
/* Desktop-first design */
:root {
  --breakpoint-sm: 640px;
  --breakpoint-md: 768px;
  --breakpoint-lg: 1024px;
  --breakpoint-xl: 1280px;
  --breakpoint-2xl: 1536px;
}

/* Sidebar behavior */
.main-sidebar {
  width: 260px;
  transition: transform 0.3s ease;
}

.main-sidebar.collapsed {
  transform: translateX(-100%);
}

/* Grid adaptations */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
}

@media (max-width: 1280px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}

/* Table responsiveness */
.queue-table {
  .p-datatable-tbody > tr > td {
    white-space: nowrap;
  }
}

/* Splitter minimum sizes */
.main-splitter {
  .p-splitter-panel {
    min-width: 300px;
  }
}
```

### Collapsible Sidebar
```vue
<template>
  <Sidebar
    v-model:visible="sidebarVisible"
    :modal="isMobile"
    :showCloseIcon="isMobile"
    :position="isMobile ? 'left' : 'static'"
    class="main-sidebar"
    :style="sidebarStyle"
  >
    <!-- Content -->
  </Sidebar>
</template>

<script setup>
const isMobile = computed(() => window.innerWidth < 768)
const sidebarVisible = ref(!isMobile.value)

const sidebarStyle = computed(() => ({
  width: isMobile.value ? '280px' : '260px',
  position: isMobile.value ? 'fixed' : 'relative'
}))
</script>
```

---

## 7. Component Library Configuration

### PrimeVue Global Configuration
```javascript
// main.js
import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import { definePreset } from '@primevue/themes'
import Aura from '@primevue/themes/aura'
import App from './App.vue'

const app = createApp(App)

const customPreset = definePreset(Aura, {
  // Theme configuration from Section 3
})

app.use(PrimeVue, {
  theme: {
    preset: customPreset,
    options: {
      darkModeSelector: '.dark-mode',
      cssLayer: false
    }
  },
  ripple: true,
  inputStyle: 'filled',
  zIndex: {
    modal: 1100,
    overlay: 1000,
    menu: 1000,
    tooltip: 1100
  }
})
```

### Component Registration
```javascript
// Import all PrimeVue components globally
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Card from 'primevue/card'
import Panel from 'primevue/panel'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import Avatar from 'primevue/avatar'
import ProgressBar from 'primevue/progressbar'
import Timeline from 'primevue/timeline'
import Terminal from 'primevue/terminal'
import Splitter from 'primevue/splitter'
import SplitterPanel from 'primevue/splitterpanel'
import Menu from 'primevue/menu'
import Menubar from 'primevue/menubar'
import Breadcrumb from 'primevue/breadcrumb'
import ToggleButton from 'primevue/togglebutton'
import Dropdown from 'primevue/dropdown'
import Calendar from 'primevue/calendar'
import Knob from 'primevue/knob'
import Chart from 'primevue/chart'
import Toolbar from 'primevue/toolbar'
import SelectButton from 'primevue/selectbutton'
import Slider from 'primevue/slider'
import InputNumber from 'primevue/inputnumber'
import Password from 'primevue/password'
import Chips from 'primevue/chips'
import Checkbox from 'primevue/checkbox'
import Textarea from 'primevue/textarea'
import Chip from 'primevue/chip'
import Skeleton from 'primevue/skeleton'
import MultiSelect from 'primevue/multiselect'
import Divider from 'primevue/divider'
import Sidebar from 'primevue/sidebar'

// Register all components
const components = [
  Toast, ConfirmDialog, Dialog, Button, InputText,
  DataTable, Column, Card, Panel, TabView, TabPanel,
  Tag, Badge, Avatar, ProgressBar, Timeline, Terminal,
  Splitter, SplitterPanel, Menu, Menubar, Breadcrumb,
  ToggleButton, Dropdown, Calendar, Knob, Chart,
  Toolbar, SelectButton, Slider, InputNumber, Password,
  Chips, Checkbox, Textarea, Chip, Skeleton,
  MultiSelect, Divider, Sidebar
]

components.forEach(component => {
  app.component(component.name, component)
})
```

---

## 8. CSS Architecture

### Utility Classes
```css
/* Spacing */
.gap-1 { gap: 0.25rem; }
.gap-2 { gap: 0.5rem; }
.gap-3 { gap: 0.75rem; }
.gap-4 { gap: 1rem; }
.gap-6 { gap: 1.5rem; }

/* Layout */
.flex { display: flex; }
.flex-col { flex-direction: column; }
.items-center { align-items: center; }
.justify-between { justify-content: space-between; }
.w-full { width: 100%; }
.h-full { height: 100%; }

/* Text */
.text-center { text-align: center; }
.text-muted { color: var(--text-muted); }
.text-primary { color: var(--text-primary); }
.text-secondary { color: var(--text-secondary); }

/* Common patterns */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.page-header h1 {
  font-size: 1.875rem;
  font-weight: 600;
  color: var(--text-primary);
}
```

---

## Summary

This design specification provides a complete component hierarchy and layout strategy for the Busy Whatsapp Bridge dashboard using exclusively PrimeVue components. Key features include:

- **Professional dark mode aesthetic** with emerald green accents matching WhatsApp branding
- **Real-time WebSocket integration** for live updates across all pages
- **Desktop-optimized layout** with collapsible sidebar and resizable panels
- **Comprehensive component usage** leveraging PrimeVue's full component library
- **Consistent interaction patterns** with toast notifications, confirmation dialogs, and loading states
- **Modular architecture** allowing easy extension and maintenance

The design prioritizes system visibility, quick access to critical functions, and a professional appearance suitable for enterprise deployment.