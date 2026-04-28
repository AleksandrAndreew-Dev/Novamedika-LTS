// Service for managing questions/consultations with users
import apiClient from '../../api/client';
import { logger } from '../../utils/logger';

class QuestionsService {
  /**
   * Get list of questions with filtering and pagination
   * @param {Object} params - Query parameters
   * @param {string} params.status - Filter by status (pending, in_progress, answered, completed)
   * @param {number} params.page - Page number
   * @param {number} params.limit - Items per page
   * @returns {Promise<Object>} Questions list with pagination
   */
  async getQuestions(params = {}) {
    try {
      const response = await apiClient.get('/api/pharmacist/questions', { params });
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch questions:', error);
      throw error;
    }
  }

  /**
   * Get single question with full details and message history
   * @param {string} questionId - Question UUID
   * @returns {Promise<Object>} Question details with messages
   */
  async getQuestionById(questionId) {
    try {
      const response = await apiClient.get(`/api/pharmacist/questions/${questionId}`);
      return response.data;
    } catch (error) {
      logger.error(`Failed to fetch question ${questionId}:`, error);
      throw error;
    }
  }

  /**
   * Send answer to user's question
   * @param {string} questionId - Question UUID
   * @param {Object} answerData - Answer data
   * @param {string} answerData.text - Answer text
   * @param {File|null} answerData.photo - Optional photo attachment
   * @returns {Promise<Object>} Created answer
   */
  async sendAnswer(questionId, answerData) {
    try {
      // If there's a photo, use FormData
      if (answerData.photo) {
        const formData = new FormData();
        formData.append('text', answerData.text);
        formData.append('photo', answerData.photo);
        
        const response = await apiClient.post(
          `/api/pharmacist/questions/${questionId}/answer`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          }
        );
        return response.data;
      } else {
        // Text-only answer
        const response = await apiClient.post(
          `/api/pharmacist/questions/${questionId}/answer`,
          { text: answerData.text }
        );
        return response.data;
      }
    } catch (error) {
      logger.error(`Failed to send answer to question ${questionId}:`, error);
      throw error;
    }
  }

  /**
   * Complete/close consultation
   * @param {string} questionId - Question UUID
   * @returns {Promise<void>}
   */
  async completeQuestion(questionId) {
    try {
      await apiClient.put(`/api/pharmacist/questions/${questionId}/complete`);
    } catch (error) {
      logger.error(`Failed to complete question ${questionId}:`, error);
      throw error;
    }
  }

  /**
   * Assign question to current pharmacist
   * @param {string} questionId - Question UUID
   * @returns {Promise<void>}
   */
  async assignQuestion(questionId) {
    try {
      await apiClient.post(`/api/pharmacist/questions/${questionId}/assign`);
    } catch (error) {
      logger.error(`Failed to assign question ${questionId}:`, error);
      throw error;
    }
  }

  /**
   * Get count of unread/new questions
   * @returns {Promise<Object>} Unread count
   */
  async getUnreadCount() {
    try {
      const response = await apiClient.get('/api/pharmacist/questions/unread-count');
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch unread count:', error);
      throw error;
    }
  }

  /**
   * Get quick reply templates
   * @returns {Promise<Array>} List of quick reply templates
   */
  async getQuickReplies() {
    try {
      const response = await apiClient.get('/api/pharmacist/quick-replies');
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch quick replies:', error);
      // Return default templates if API fails
      return [
        { id: 1, text: 'Здравствуйте! Чем могу помочь?' },
        { id: 2, text: 'Уточните, пожалуйста, название препарата' },
        { id: 3, text: 'Препарат есть в наличии. Когда вам удобно забрать?' },
        { id: 4, text: 'К сожалению, препарата нет в наличии' },
        { id: 5, text: 'Нужна ли вам консультация врача?' },
      ];
    }
  }

  /**
   * Search questions by text
   * @param {string} query - Search query
   * @param {Object} params - Additional filters
   * @returns {Promise<Object>} Search results
   */
  async searchQuestions(query, params = {}) {
    try {
      const response = await apiClient.get('/api/pharmacist/questions/search', {
        params: { q: query, ...params },
      });
      return response.data;
    } catch (error) {
      logger.error('Failed to search questions:', error);
      throw error;
    }
  }

  /**
   * Get dashboard statistics (alias for getConsultationStats)
   * @returns {Promise<Object>} Statistics data with newQuestions, inProgress, completedToday, avgResponseTime
   */
  async getDashboardStats() {
    try {
      const response = await apiClient.get('/api/pharmacist/consultations/stats');
      
      // Transform backend response to match frontend expectations
      return {
        newQuestions: response.data.pending_count || 0,
        inProgress: response.data.in_progress_count || 0,
        completedToday: response.data.completed_today || 0,
        avgResponseTime: Math.round(response.data.avg_response_time_minutes || 0)
      };
    } catch (error) {
      logger.error('Failed to fetch dashboard stats:', error);
      // Return default stats if API fails
      return {
        newQuestions: 0,
        inProgress: 0,
        completedToday: 0,
        avgResponseTime: 0
      };
    }
  }

  /**
   * Get consultation statistics
   * @param {Object} params - Date range filters
   * @returns {Promise<Object>} Statistics data
   */
  async getConsultationStats(params = {}) {
    try {
      const response = await apiClient.get('/api/pharmacist/consultations/stats', { params });
      return response.data;
    } catch (error) {
      logger.error('Failed to fetch consultation stats:', error);
      throw error;
    }
  }
}

export const questionsService = new QuestionsService();
export default questionsService;
