import { create } from 'zustand';
import type { QueueStats, Message } from '../types';

interface QueueState {
  stats: QueueStats | null;
  pending: Message[];
  retrying: Message[];
  deadLetter: Message[];
  history: Message[];
  selectedTab: 'pending' | 'retrying' | 'deadLetter' | 'history';
  isLoading: boolean;
}

interface QueueActions {
  setStats: (stats: QueueStats | null) => void;
  setPending: (messages: Message[]) => void;
  setRetrying: (messages: Message[]) => void;
  setDeadLetter: (messages: Message[]) => void;
  setHistory: (messages: Message[]) => void;
  setSelectedTab: (tab: QueueState['selectedTab']) => void;
  setLoading: (loading: boolean) => void;
  updateMessage: (message: Message) => void;
}

export const useQueueStore = create<QueueState & QueueActions>((set, get) => ({
  // State
  stats: null,
  pending: [],
  retrying: [],
  deadLetter: [],
  history: [],
  selectedTab: 'pending',
  isLoading: false,

  // Actions
  setStats: (stats) => set({ stats }),
  setPending: (pending) => set({ pending }),
  setRetrying: (retrying) => set({ retrying }),
  setDeadLetter: (deadLetter) => set({ deadLetter }),
  setHistory: (history) => set({ history }),
  setSelectedTab: (selectedTab) => set({ selectedTab }),
  setLoading: (isLoading) => set({ isLoading }),
  
  updateMessage: (updatedMessage) => {
    const { pending, retrying, history } = get();
    
    set({
      pending: pending.map(m => m.id === updatedMessage.id ? updatedMessage : m),
      retrying: retrying.map(m => m.id === updatedMessage.id ? updatedMessage : m),
      history: history.map(m => m.id === updatedMessage.id ? updatedMessage : m),
    });
  },
}));

// Computed selectors
export const selectTotalPending = (state: QueueState) => state.pending.length;
export const selectTotalRetrying = (state: QueueState) => state.retrying.length;
export const selectTotalDeadLetter = (state: QueueState) => state.deadLetter.length;
export const selectTotalSent = (state: QueueState) => 
  state.history.filter(m => m.status === 'sent').length;
