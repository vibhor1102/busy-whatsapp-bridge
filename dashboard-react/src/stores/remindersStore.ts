import { create } from 'zustand';
import type {
  ReminderConfig,
  ReminderStats,
  ReminderSnapshotStatus,
  PartyReminderInfo,
  MessageTemplate,
  AntiSpamConfig,
  ReminderSession,
} from '../types';

interface RemindersState {
  config: ReminderConfig | null;
  stats: ReminderStats | null;
  snapshotStatus: ReminderSnapshotStatus | null;
  templates: MessageTemplate[];
  parties: PartyReminderInfo[];
  selectedPartyCodes: Set<string>;
  defaultTemplateId: string;
  partyTemplates: Record<string, string>;
  antiSpamConfig: AntiSpamConfig;
  activeSession: ReminderSession | null;
  isLoading: boolean;
  isSending: boolean;
  persistedSelection: Record<string, boolean>;
}

interface RemindersActions {
  setConfig: (config: ReminderConfig | null) => void;
  setStats: (stats: ReminderStats | null) => void;
  setSnapshotStatus: (status: ReminderSnapshotStatus | null) => void;
  setTemplates: (templates: MessageTemplate[]) => void;
  setParties: (parties: PartyReminderInfo[]) => void;
  setDefaultTemplateId: (id: string) => void;
  setPartyTemplate: (partyCode: string, templateId: string) => void;
  setAntiSpamConfig: (config: AntiSpamConfig) => void;
  setActiveSession: (session: ReminderSession | null) => void;
  togglePartySelection: (partyCode: string) => void;
  selectParties: (partyCodes: string[]) => void;
  deselectParties: (partyCodes: string[]) => void;
  clearSelection: () => void;
  setLoading: (loading: boolean) => void;
  setSending: (sending: boolean) => void;
  setPersistedSelection: (selection: Record<string, boolean>) => void;
  updatePersistedSelection: (partyCode: string, enabled: boolean) => void;
}

export const useRemindersStore = create<RemindersState & RemindersActions>((set, get) => ({
  config: null,
  stats: null,
  snapshotStatus: null,
  templates: [],
  parties: [],
  selectedPartyCodes: new Set(),
  defaultTemplateId: '',
  partyTemplates: {},
  antiSpamConfig: {
    enabled: true,
    message_inflation: true,
    pdf_inflation: true,
    typing_simulation: true,
    startup_delay_enabled: true,
    reminder_cooldown_enabled: true,
    reminder_cooldown_minutes: 60,
  },
  activeSession: null,
  isLoading: false,
  isSending: false,
  persistedSelection: {},

  setConfig: (config) => set({ config }),
  setStats: (stats) => set({ stats }),
  setSnapshotStatus: (snapshotStatus) => set({ snapshotStatus }),
  setTemplates: (templates) => set({ templates }),
  setParties: (parties) => set({ parties }),
  setDefaultTemplateId: (defaultTemplateId) => set({ defaultTemplateId }),

  setPartyTemplate: (partyCode, templateId) => {
    const { partyTemplates } = get();
    set({
      partyTemplates: {
        ...partyTemplates,
        [partyCode]: templateId,
      },
    });
  },

  setAntiSpamConfig: (antiSpamConfig) => set({ antiSpamConfig }),
  setActiveSession: (activeSession) => set({ activeSession }),

  setPersistedSelection: (persistedSelection) => set({ persistedSelection }),

  updatePersistedSelection: (partyCode, enabled) => {
    const { persistedSelection } = get();
    set({
      persistedSelection: {
        ...persistedSelection,
        [partyCode]: enabled,
      },
    });
  },

  togglePartySelection: (partyCode) => {
    const { selectedPartyCodes, persistedSelection } = get();
    const newSet = new Set(selectedPartyCodes);
    const wasSelected = newSet.has(partyCode);
    if (wasSelected) {
      newSet.delete(partyCode);
    } else {
      newSet.add(partyCode);
    }
    set({
      selectedPartyCodes: newSet,
      persistedSelection: {
        ...persistedSelection,
        [partyCode]: !wasSelected,
      },
    });
  },

  selectParties: (partyCodes) => {
    const { selectedPartyCodes, persistedSelection } = get();
    const newSet = new Set(selectedPartyCodes);
    const newPersisted = { ...persistedSelection };
    partyCodes.forEach(code => {
      newSet.add(code);
      newPersisted[code] = true;
    });
    set({ selectedPartyCodes: newSet, persistedSelection: newPersisted });
  },

  deselectParties: (partyCodes) => {
    const { selectedPartyCodes, persistedSelection } = get();
    const newSet = new Set(selectedPartyCodes);
    const newPersisted = { ...persistedSelection };
    partyCodes.forEach(code => {
      newSet.delete(code);
      newPersisted[code] = false;
    });
    set({ selectedPartyCodes: newSet, persistedSelection: newPersisted });
  },

  clearSelection: () => set({ selectedPartyCodes: new Set(), partyTemplates: {} }),
  setLoading: (isLoading) => set({ isLoading }),
  setSending: (isSending) => set({ isSending }),
}));

// Computed selectors
export const selectSelectedParties = (state: RemindersState) =>
  state.parties.filter(p => state.selectedPartyCodes.has(p.code));

export const selectSelectedTotalAmount = (state: RemindersState) =>
  Array.from(state.selectedPartyCodes).reduce((sum, code) => {
    const party = state.parties.find(p => p.code === code);
    return sum + (party?.amount_due || 0);
  }, 0);

export const selectDefaultTemplate = (state: RemindersState) =>
  state.templates.find(t => t.id === state.defaultTemplateId);
