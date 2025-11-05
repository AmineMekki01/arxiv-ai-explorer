import axios from 'axios';
import { SearchRequest, EnhancedSearchResponse } from '../types/search';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiEndpoints = {
  health: () => api.get('/health'),
  healthDetailed: () => api.get('/health/detailed'),
  
  queryAssistant: (query: string, chatId: string, conversationType: string = 'research') => 
    api.get(`/assistant?q=${encodeURIComponent(query)}&chat_id=${chatId}&conversation_type=${conversationType}`),
  
  queryAssistantPost: (data: { query: string; chat_id: string; conversation_type?: string }) =>
    api.post('/assistant/query', data),
  
  getSessionInfo: (chatId: string) => 
    api.get(`/assistant/session/${chatId}`),
  
  clearSession: (chatId: string) => 
    api.delete(`/assistant/session/${chatId}`),
  
  switchContextStrategy: (chatId: string, strategy: string) =>
    api.post(`/assistant/session/${chatId}/strategy`, { strategy }),
  
  getStrategyRecommendations: (conversationType: string) =>
    api.get(`/assistant/recommendations/${conversationType}`),
  
  listStrategies: () =>
    api.get('/assistant/strategies'),

  listChats: () => api.get('/chats'),
  createChat: (name?: string) => api.post('/chats', { name: name || null }),
  renameChat: (chatId: string, name: string) => api.post(`/chats/${chatId}/rename`, { name }),
  deleteChat: (chatId: string) => api.delete(`/chats/${chatId}`),
  getMessages: (chatId: string, before?: string, limit?: number) => api.get(`/chats/${chatId}/messages`, { params: { before, limit } }),
  sendMessage: (chatId: string, role: string, content: string, clientMsgId?: string) => api.post(`/chats/${chatId}/messages`, { role, content, client_msg_id: clientMsgId }),
  
  enhancedSearch: (data: SearchRequest) =>
    api.post<EnhancedSearchResponse>('/search/enhanced', data),
  
  enhancedSearchGet: (query: string, limit: number = 10, includeFoundations: boolean = true) =>
    api.get<EnhancedSearchResponse>(`/search/enhanced?query=${encodeURIComponent(query)}&limit=${limit}&include_foundations=${includeFoundations}`),
  
  addFocusedPaper: (chatId: string, data: { arxiv_id: string; title: string }) =>
    api.post(`/assistant/session/${chatId}/focus`, data),
  
  removeFocusedPaper: (chatId: string, arxivId: string) =>
    api.delete(`/assistant/session/${chatId}/focus/${arxivId}`),
  
  clearFocusedPapers: (chatId: string) =>
    api.delete(`/assistant/session/${chatId}/focus`),
  
  getFocusedPapers: (chatId: string) =>
    api.get(`/assistant/session/${chatId}/focus`),
  
  getPaperDetail: (arxivId: string) =>
    api.get(`/assistant/papers/${arxivId}/detail`),
};

export const apiHelpers = {
  checkHealth: async () => {
    try {
      const response = await apiEndpoints.health();
      return response.data.status === 'healthy';
    } catch (error) {
      return false;
    }
  },

  queryAssistant: async (query: string, chatId?: string, conversationType: string = 'research') => {
    const sessionId = chatId || `chat_${Date.now()}`;
    
    try {
      const response = await apiEndpoints.queryAssistant(query, sessionId, conversationType);
      console.log(response);
      return {
        success: true,
        data: response.data,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to query assistant',
      };
    }
  },

  getSessionInfo: async (chatId: string) => {
    try {
      const response = await apiEndpoints.getSessionInfo(chatId);
      return {
        success: true,
        data: response.data,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to get session info',
      };
    }
  },

  clearSession: async (chatId: string) => {
    try {
      const response = await apiEndpoints.clearSession(chatId);
      return {
        success: true,
        data: response.data,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to clear session',
      };
    }
  },

  switchContextStrategy: async (chatId: string, strategy: string) => {
    try {
      const response = await apiEndpoints.switchContextStrategy(chatId, strategy);
      return {
        success: true,
        data: response.data,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to switch strategy',
      };
    }
  },

  getStrategies: async () => {
    try {
      const response = await apiEndpoints.listStrategies();
      return {
        success: true,
        data: response.data,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to get strategies',
      };
    }
  },
  
  getSystemStatus: async () => {
    try {
      const response = await apiEndpoints.healthDetailed();
      return {
        status: response.data.status,
        services: response.data.services,
        version: response.data.version,
      };
    } catch (error) {
      return {
        status: 'error',
        services: {},
        version: 'unknown',
      };
    }
  },

  enhancedSearch: async (request: SearchRequest) => {
    try {
      const response = await apiEndpoints.enhancedSearch(request);
      return {
        success: true,
        data: response.data,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to perform search',
      };
    }
  },

  listChats: async () => {
    try {
      const res = await apiEndpoints.listChats();
      return { success: true, items: res.data.items as any[] };
    } catch (e: any) {
      return { success: false, error: e.response?.data?.detail || 'Failed to list chats' };
    }
  },

  createChat: async (name?: string) => {
    try {
      const res = await apiEndpoints.createChat(name);
      return { success: true, chat: res.data.chat };
    } catch (e: any) {
      return { success: false, error: e.response?.data?.detail || 'Failed to create chat' };
    }
  },

  renameChat: async (chatId: string, name: string) => {
    try {
      await apiEndpoints.renameChat(chatId, name);
      return { success: true };
    } catch (e: any) {
      return { success: false, error: e.response?.data?.detail || 'Failed to rename chat' };
    }
  },

  deleteChat: async (chatId: string) => {
    try {
      await apiEndpoints.deleteChat(chatId);
      return { success: true };
    } catch (e: any) {
      return { success: false, error: e.response?.data?.detail || 'Failed to delete chat' };
    }
  },

  getMessages: async (chatId: string, before?: string, limit?: number) => {
    try {
      const res = await apiEndpoints.getMessages(chatId, before, limit);
      return { success: true, messages: res.data.messages as any[] };
    } catch (e: any) {
      return { success: false, error: e.response?.data?.detail || 'Failed to load messages' };
    }
  },

  sendMessage: async (chatId: string, role: string, content: string, clientMsgId?: string) => {
    try {
      const res = await apiEndpoints.sendMessage(chatId, role, content, clientMsgId);
      return { success: true, message: res.data.message, sources: res.data.sources || [], graph_insights: res.data.graph_insights || {} };
    } catch (e: any) {
      return { success: false, error: e.response?.data?.detail || 'Failed to send message' };
    }
  },
};

export default api;
