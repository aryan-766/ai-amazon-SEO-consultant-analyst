import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  /**
   * Upload Amazon Excel / CSV Keyword Export file
   */
  uploadDataset: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Run Data cleaning + Feature Engineering + Score generation
   */
  analyzeDataset: async (sessionId: string, userBrand: string, competitors: string[]) => {
    const response = await apiClient.post('/analyze', {
      session_id: sessionId,
      user_brand: userBrand,
      competitors: competitors,
    });
    return response.data;
  },

  /**
   * Fetch Dashboard summary KPI metrics and charts data
   */
  getDashboard: async (sessionId: string) => {
    const response = await apiClient.get('/dashboard', {
      params: { session_id: sessionId },
    });
    return response.data;
  },

  /**
   * Fetch paginated keywords with sorting & filters
   */
  getKeywords: async (
    sessionId: string,
    params: {
      search?: string;
      intent?: string;
      category?: string;
      cluster?: string;
      sort_by?: string;
      sort_desc?: boolean;
      limit?: number;
      offset?: number;
    } = {}
  ) => {
    const response = await apiClient.get('/keywords', {
      params: {
        session_id: sessionId,
        ...params,
      },
    });
    return response.data;
  },

  /**
   * Fetch competitor analysis summaries
   */
  getCompetitors: async (sessionId: string) => {
    const response = await apiClient.get('/competitors', {
      params: { session_id: sessionId },
    });
    return response.data;
  },

  /**
   * Fetch product types / categories
   */
  getCategories: async (sessionId: string) => {
    const response = await apiClient.get('/categories', {
      params: { session_id: sessionId },
    });
    return response.data;
  },

  /**
   * Send chat query to local RAG Copilot
   */
  chatCopilot: async (sessionId: string, message: string) => {
    const response = await apiClient.post('/chat', {
      session_id: sessionId,
      message,
    });
    return response.data;
  },

  /**
   * Generate an optimized Listing draft via AI (Ollama or local fallback template)
   */
  generateListing: async (sessionId: string, targetKeywords: string[]) => {
    const response = await apiClient.post('/listing/generate', {
      session_id: sessionId,
      target_keywords: targetKeywords,
    });
    return response.data;
  },

  /**
   * Fetch real-time listing optimization score and recommendations
   */
  analyzeListing: async (
    sessionId: string,
    title: string,
    bulletPoints: string[],
    description: string,
    searchTerms: string
  ) => {
    const response = await apiClient.post('/listing/analyze', {
      session_id: sessionId,
      title,
      bullet_points: bulletPoints,
      description,
      search_terms: searchTerms,
    });
    return response.data;
  },

  /**
   * Export reports as excel or PDF binary response
   */
  exportData: async (sessionId: string, format: 'xlsx' | 'pdf') => {
    const response = await apiClient.post(
      '/export',
      { session_id: sessionId, format },
      { responseType: 'blob' }
    );
    return response.data;
  },
};
export default api;
