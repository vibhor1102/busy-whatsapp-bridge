import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { api } from '../services/api';

export function DispatchIncidentWatcher() {
  const lastIncidentKey = useRef<string | null>(null);

  const { data } = useQuery({
    queryKey: ['dispatch-ops-watcher'],
    queryFn: () => api.getDispatchOpsStatus(),
    refetchInterval: 30000,
    staleTime: 15000,
  });

  useEffect(() => {
    const incident = data?.incident?.incident;
    const attentionRequired = data?.incident?.attention_required;
    if (!incident || !attentionRequired) {
      lastIncidentKey.current = null;
      return;
    }

    const incidentKey = `${incident.kind}:${incident.created_at}`;
    if (lastIncidentKey.current === incidentKey) {
      return;
    }
    lastIncidentKey.current = incidentKey;

    toast.error(incident.title, {
      description: incident.message,
      duration: 12000,
    });

    if ('Notification' in window) {
      const showNotification = () => {
        try {
          new Notification(`Busy Bridge: ${incident.title}`, {
            body: incident.message,
          });
        } catch {
          // Ignore notification failures; toast remains primary.
        }
      };

      if (Notification.permission === 'granted') {
        showNotification();
      } else if (Notification.permission === 'default') {
        Notification.requestPermission().then((permission) => {
          if (permission === 'granted') {
            showNotification();
          }
        }).catch(() => undefined);
      }
    }
  }, [data]);

  return null;
}
