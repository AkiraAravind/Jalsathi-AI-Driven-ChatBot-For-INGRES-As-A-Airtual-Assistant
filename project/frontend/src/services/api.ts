import axios from 'axios';

const API_BASE_URL = '/api';

const getAuthHeader = () => {
  const token = localStorage.getItem('ingres_token');
  if (!token) {
    throw new Error('Missing auth token. Please login again.');
  }
  return { 'Authorization': `Bearer ${token}` };
};

export interface ChatResponse {
  answer: string;
  citations?: string[];
  chart?: any;
  language?: string;
  query_type?: string;
  [key: string]: any;
}

export interface ChatStreamFinalEvent {
  type: 'final';
  answer: string;
  citations?: string[];
  chart?: any;
  language?: string;
  query_type?: string;
  entities?: any;
}

export interface PortalStateLevel {
  state: string;
  level: number;
  year?: number;
}

export interface PortalDashboardData {
  summary: {
    extraction_avg: number;
    at_risk_blocks: number;
    monitored_states: number;
    latest_year?: number | null;
  };
  state_levels: PortalStateLevel[];
  critical_states: PortalStateLevel[];
  healthy_states: PortalStateLevel[];
  source?: string;
}

export const chatService = {
  async getPortalDashboardData(): Promise<PortalDashboardData> {
    const response = await axios.get(`${API_BASE_URL}/portal/dashboard-data`, {
      headers: getAuthHeader()
    });
    return response.data.data as PortalDashboardData;
  },

  async updateProfile(name: string): Promise<void> {
    await axios.post(`${API_BASE_URL}/auth/profile`, { name }, {
      headers: getAuthHeader()
    });
  },
  async uploadFile(file: File): Promise<string> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await axios.post(`${API_BASE_URL}/chat/upload`, formData, {
      headers: {
        ...getAuthHeader(),
        'Content-Type': 'multipart/form-data'
      }
    });
    return response.data.extracted_context;
  },

  async sendMessage(message: string, sessionId?: string, uploadedContext?: string): Promise<ChatResponse> {
    const response = await axios.post(`${API_BASE_URL}/chat`, {
      message,
      session_id: sessionId,
      uploaded_context: uploadedContext
    }, {
      headers: getAuthHeader()
    });
    return response.data;
  },

  async streamMessage(
    message: string,
    sessionId: string | undefined,
    uploadedContext: string | undefined,
    handlers: {
      onToken: (token: string) => void;
      onFinal: (event: ChatStreamFinalEvent) => void;
      onError: (message: string) => void;
    }
  ): Promise<void> {
    const token = localStorage.getItem('ingres_token');
    if (!token) {
      throw new Error('Missing auth token. Please login again.');
    }

    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        uploaded_context: uploadedContext,
        stream: true,
      }),
    });

    if (!response.ok || !response.body) {
      const fallback = await response.text();
      throw new Error(fallback || `Streaming request failed (${response.status})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const eventChunk of events) {
        const dataLine = eventChunk
          .split('\n')
          .find((line) => line.startsWith('data: '));
        if (!dataLine) {
          continue;
        }

        const payloadText = dataLine.slice(6).trim();
        if (!payloadText) {
          continue;
        }

        try {
          const payload = JSON.parse(payloadText);
          if (payload.type === 'token') {
            handlers.onToken(String(payload.content || ''));
          } else if (payload.type === 'final') {
            handlers.onFinal(payload as ChatStreamFinalEvent);
          } else if (payload.type === 'error') {
            handlers.onError(String(payload.message || 'Streaming failed'));
          }
        } catch {
          // Ignore malformed partial events and continue stream processing.
        }
      }
    }
  },

  async getHistory(): Promise<any[]> {
    const response = await axios.get(`${API_BASE_URL}/chat/history`, {
      headers: getAuthHeader()
    });
    return response.data.sessions;
  },

  async exportChat(sessionId: string): Promise<void> {
    await axios.post(`${API_BASE_URL}/chat/export`, {
      session_id: sessionId
    }, {
      headers: getAuthHeader()
    });
  },

  async downloadChatPdf(sessionId: string, messages?: Array<{ role: string; content: string; citations?: string[] }>): Promise<Blob> {
    const response = await axios.post(`${API_BASE_URL}/chat/export/download`, {
      session_id: sessionId,
      messages: messages || [],
    }, {
      headers: getAuthHeader(),
      responseType: 'blob',
    });
    return response.data as Blob;
  }
};
