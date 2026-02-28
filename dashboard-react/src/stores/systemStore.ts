import { create } from 'zustand';
import type { BaileysStatus, ProcessStatus, SystemResources } from '../types';

interface SystemState {
  baileysStatus: BaileysStatus | null;
  processes: ProcessStatus[];
  resources: SystemResources | null;
  isLoading: boolean;
}

interface SystemActions {
  setBaileysStatus: (status: BaileysStatus | null) => void;
  setProcesses: (processes: ProcessStatus[]) => void;
  setResources: (resources: SystemResources | null) => void;
  setLoading: (loading: boolean) => void;
}

export const useSystemStore = create<SystemState & SystemActions>((set) => ({
  // State
  baileysStatus: null,
  processes: [],
  resources: null,
  isLoading: false,

  // Actions
  setBaileysStatus: (baileysStatus) => set({ baileysStatus }),
  setProcesses: (processes) => set({ processes }),
  setResources: (resources) => set({ resources }),
  setLoading: (isLoading) => set({ isLoading }),
}));

// Computed selectors
export const selectIsBaileysConnected = (state: SystemState) => 
  state.baileysStatus?.state === 'connected';

export const selectIsBaileysRunning = (state: SystemState) => 
  ['connected', 'qr_ready', 'connecting', 'reconnecting'].includes(state.baileysStatus?.state || '');
