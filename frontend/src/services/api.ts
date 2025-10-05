import axios from 'axios';

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
};

export default api;
