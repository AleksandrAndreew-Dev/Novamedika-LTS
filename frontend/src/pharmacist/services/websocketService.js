// WebSocket service for real-time consultation updates
import { logger } from '../../utils/logger';

class WebSocketService {
  constructor() {
    this.ws = null;
    this.reconnectInterval = 3000;
    this.maxReconnectAttempts = 10;
    this.reconnectAttempts = 0;
    this.eventHandlers = new Map();
    this.isConnected = false;
    this.url = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/pharmacist';
  }

  /**
   * Connect to WebSocket server
   */
  connect() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      logger.info('WebSocket already connected');
      return;
    }

    try {
      logger.info(`Connecting to WebSocket: ${this.url}`);
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        logger.info('WebSocket connected successfully');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        // Subscribe to pharmacist events
        this.send({ type: 'subscribe', channel: 'pharmacist' });
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          logger.debug('WebSocket message received:', data);
          
          // Trigger event handlers
          if (data.type && this.eventHandlers.has(data.type)) {
            const handlers = this.eventHandlers.get(data.type);
            handlers.forEach(handler => handler(data.payload));
          }
        } catch (error) {
          logger.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onerror = (error) => {
        logger.error('WebSocket error:', error);
      };

      this.ws.onclose = (event) => {
        logger.info(`WebSocket closed: ${event.code} ${event.reason}`);
        this.isConnected = false;
        
        // Attempt to reconnect
        if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnect();
        }
      };
    } catch (error) {
      logger.error('Failed to create WebSocket connection:', error);
      this.reconnect();
    }
  }

  /**
   * Reconnect to WebSocket server
   */
  reconnect() {
    this.reconnectAttempts++;
    const delay = this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1);
    
    logger.info(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`);
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Send message to WebSocket server
   * @param {Object} data - Message data
   */
  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      logger.warn('WebSocket not connected, message not sent:', data);
    }
  }

  /**
   * Subscribe to specific event type
   * @param {string} eventType - Event type to subscribe to
   * @param {Function} handler - Event handler function
   * @returns {Function} Unsubscribe function
   */
  on(eventType, handler) {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, []);
    }
    
    this.eventHandlers.get(eventType).push(handler);
    logger.info(`Subscribed to event: ${eventType}`);
    
    // Return unsubscribe function
    return () => {
      const handlers = this.eventHandlers.get(eventType);
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
        logger.info(`Unsubscribed from event: ${eventType}`);
      }
    };
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
      this.eventHandlers.clear();
      logger.info('WebSocket disconnected');
    }
  }

  /**
   * Check if WebSocket is connected
   * @returns {boolean}
   */
  isConnected() {
    return this.isConnected && this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get WebSocket ready state
   * @returns {number}
   */
  getReadyState() {
    return this.ws?.readyState || WebSocket.CLOSED;
  }
}

export const websocketService = new WebSocketService();
export default websocketService;
