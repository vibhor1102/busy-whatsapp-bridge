import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import Overview from '@/views/Overview.vue'
import WhatsAppManager from '@/views/WhatsAppManager.vue'
import MessageQueue from '@/views/MessageQueue.vue'
import LiveLogs from '@/views/LiveLogs.vue'
import SystemControl from '@/views/SystemControl.vue'
import Settings from '@/views/Settings.vue'
import Reminders from '@/views/Reminders.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Overview',
    component: Overview,
    meta: { title: 'Overview', icon: 'pi pi-home' }
  },
  {
    path: '/whatsapp',
    name: 'WhatsApp',
    component: WhatsAppManager,
    meta: { title: 'WhatsApp', icon: 'pi pi-whatsapp' }
  },
  {
    path: '/queue',
    name: 'Message Queue',
    component: MessageQueue,
    meta: { title: 'Message Queue', icon: 'pi pi-inbox' }
  },
  {
    path: '/reminders',
    name: 'Payment Reminders',
    component: Reminders,
    meta: { title: 'Payment Reminders', icon: 'pi pi-bell' }
  },
  {
    path: '/logs',
    name: 'Logs',
    component: LiveLogs,
    meta: { title: 'Live Logs', icon: 'pi pi-list' }
  },
  {
    path: '/system',
    name: 'System',
    component: SystemControl,
    meta: { title: 'System Control', icon: 'pi pi-cog' }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
    meta: { title: 'Settings', icon: 'pi pi-sliders-h' }
  }
]

export const navRoutes = routes.map((route) => ({
  path: route.path,
  name: route.name,
  meta: route.meta,
}))

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
