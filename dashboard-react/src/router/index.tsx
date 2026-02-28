import { createBrowserRouter } from 'react-router-dom';
import { lazy } from 'react';
import { Layout } from '../components/Layout';
import { LazyPage } from '../components/LazyPage';

// Lazy load all page components for code splitting
// Use .then() to convert named exports to default exports for lazy loading
const Overview = lazy(() => import('../pages/Overview').then(m => ({ default: m.Overview })));
const WhatsAppManager = lazy(() => import('../pages/WhatsAppManager').then(m => ({ default: m.WhatsAppManager })));
const MessageQueue = lazy(() => import('../pages/MessageQueue').then(m => ({ default: m.MessageQueue })));
const Reminders = lazy(() => import('../pages/Reminders').then(m => ({ default: m.Reminders })));
const LiveLogs = lazy(() => import('../pages/LiveLogs').then(m => ({ default: m.LiveLogs })));
const SystemControl = lazy(() => import('../pages/SystemControl').then(m => ({ default: m.SystemControl })));
const Settings = lazy(() => import('../pages/Settings').then(m => ({ default: m.Settings })));

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: (
          <LazyPage>
            <Overview />
          </LazyPage>
        ),
      },
      {
        path: 'whatsapp',
        element: (
          <LazyPage>
            <WhatsAppManager />
          </LazyPage>
        ),
      },
      {
        path: 'queue',
        element: (
          <LazyPage>
            <MessageQueue />
          </LazyPage>
        ),
      },
      {
        path: 'reminders',
        element: (
          <LazyPage>
            <Reminders />
          </LazyPage>
        ),
      },
      {
        path: 'logs',
        element: (
          <LazyPage>
            <LiveLogs />
          </LazyPage>
        ),
      },
      {
        path: 'system',
        element: (
          <LazyPage>
            <SystemControl />
          </LazyPage>
        ),
      },
      {
        path: 'settings',
        element: (
          <LazyPage>
            <Settings />
          </LazyPage>
        ),
      },
    ],
  },
], {
  basename: '/dashboard',
});
