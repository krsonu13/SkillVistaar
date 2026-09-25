import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from './AuthContext';

export interface RealtimeMessage {
  type: string;
  data: any;
}

type EventHandler = (data: any) => void;

interface RealtimeContextType {
  isConnected: boolean;
  send: (type: string, data?: any) => void;
  subscribe: (eventType: string, handler: EventHandler) => () => void;
}

const RealtimeContext = createContext<RealtimeContextType | undefined>(undefined);

export const RealtimeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token, isAuthenticated } = useAuth();
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Map<string, Set<EventHandler>>>(new Map());
  const reconnectTimeoutRef = useRef<any>(null);

  const subscribe = useCallback((eventType: string, handler: EventHandler) => {
    if (!handlersRef.current.has(eventType)) {
      handlersRef.current.set(eventType, new Set());
    }
    handlersRef.current.get(eventType)!.add(handler);

    return () => {
      handlersRef.current.get(eventType)?.delete(handler);
    };
  }, []);

  const send = useCallback((type: string, data: any = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...data }));
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setIsConnected(false);
      return;
    }

    let isCancelled = false;

    const connect = () => {
      if (isCancelled) return;

      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

      // Derive WebSocket host from the configured API base URL.
      // In production: VITE_API_BASE_URL = "https://your-backend.onrender.com/api/v1"
      // In dev: Falls back to localhost:8000 for direct backend connection.
      let host: string;
      const apiBase = import.meta.env.VITE_API_BASE_URL as string | undefined;
      if (apiBase && (apiBase.startsWith('http://') || apiBase.startsWith('https://'))) {
        try {
          const parsed = new URL(apiBase);
          host = parsed.host;
        } catch {
          host = window.location.host;
        }
      } else if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        // Local development: backend is on port 8000
        host = `${window.location.hostname}:8000`;
      } else {
        // Same-origin deployment
        host = window.location.host;
      }

      const url = `${wsProtocol}//${host}/api/v1/ws?token=${encodeURIComponent(token)}`;

      try {
        const socket = new WebSocket(url);
        wsRef.current = socket;

        socket.onopen = () => {
          if (!isCancelled) {
            setIsConnected(true);
          }
        };

        socket.onmessage = (event) => {
          try {
            const parsed: RealtimeMessage = JSON.parse(event.data);
            if (parsed.type && handlersRef.current.has(parsed.type)) {
              handlersRef.current.get(parsed.type)!.forEach((h) => {
                try {
                  h(parsed.data);
                } catch (err) {
                  console.error(`[Realtime] Handler error for ${parsed.type}:`, err);
                }
              });
            }
          } catch {
            // Heartbeat response or plain text
          }
        };

        socket.onclose = () => {
          if (!isCancelled) {
            setIsConnected(false);
            // Reconnect after 3 seconds
            reconnectTimeoutRef.current = setTimeout(connect, 3000);
          }
        };

        socket.onerror = () => {
          try {
            socket.close();
          } catch {}
        };
      } catch (err) {
        console.warn('[Realtime] WebSocket connection could not be established:', err);
        if (!isCancelled) {
          reconnectTimeoutRef.current = setTimeout(connect, 5000);
        }
      }
    };

    connect();

    // Heartbeat ping interval
    const pingInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping');
      }
    }, 25000);

    return () => {
      isCancelled = true;
      clearInterval(pingInterval);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      setIsConnected(false);
    };
  }, [token, isAuthenticated]);

  return (
    <RealtimeContext.Provider value={{ isConnected, send, subscribe }}>
      {children}
    </RealtimeContext.Provider>
  );
};

export const useRealtime = (): RealtimeContextType => {
  const context = useContext(RealtimeContext);
  if (!context) {
    throw new Error('useRealtime must be used within a RealtimeProvider');
  }
  return context;
};

export default RealtimeContext;
