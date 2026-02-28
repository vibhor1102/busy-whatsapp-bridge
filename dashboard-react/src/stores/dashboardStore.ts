import { create } from 'zustand';
import type { DashboardStats, LogEntry } from '../types';

interface DashboardState {
  stats: DashboardStats | null;
  logs: LogEntry[];
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
}

interface DashboardActions {
  setStats: (stats: DashboardStats | null) => void;
  addLog: (log: LogEntry) => void;
  setConnectionStatus: (connected: boolean) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearLogs: () => void;
}

export const useDashboardStore = create<DashboardState & DashboardActions>((set, get) => ({
  // State
  stats: null,
  logs: [],
  isConnected: false,
  isLoading: false,
  error: null,

  // Actions
  setStats: (stats) => set({ stats }),
  
  addLog: (log) => {
    const { logs } = get();
    const newLogs = [log, ...logs].slice(0, 1000);
    set({ logs: newLogs });
  },
  
  setConnectionStatus: (isConnected) => set({ isConnected }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearLogs: () => set({ logs: [] }),
}));

// Selectors
export const selectDashboardStats = (state: DashboardState) => state.stats;
export const selectHasError = (state: DashboardState) => !!state.error;
export const selectLatestLogs = (state: DashboardState) => state.logs.slice(0, 100);
