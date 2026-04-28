// Hook for managing consultations/questions with real-time updates
import { useState, useEffect, useCallback } from 'react';
import { questionsService } from '../services/questionsService';
import { websocketService } from '../services/websocketService';
import { logger } from '../../utils/logger';

export function useQuestions(initialParams = {}) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    pages: 0,
  });
  const [filters, setFilters] = useState(initialParams);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const [quickReplies, setQuickReplies] = useState([]);

  // Fetch questions list
  const fetchQuestions = useCallback(async (params = {}) => {
    try {
      setLoading(true);
      setError(null);
      
      const queryParams = { ...filters, ...params };
      const data = await questionsService.getQuestions(queryParams);
      
      setQuestions(data.questions || []);
      setPagination({
        page: data.page || 1,
        limit: data.limit || 20,
        total: data.total || 0,
        pages: data.pages || 0,
      });
    } catch (err) {
      logger.error('Failed to fetch questions:', err);
      setError(err.response?.data?.detail || 'Ошибка загрузки вопросов');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Update filters and refetch
  const updateFilters = useCallback((newFilters) => {
    setFilters((prev) => ({ ...prev, ...newFilters, page: 1 }));
  }, []);

  // Change page
  const changePage = useCallback((page) => {
    setFilters((prev) => ({ ...prev, page }));
  }, []);

  // Get single question with full details
  const getQuestionById = useCallback(async (questionId) => {
    try {
      setLoading(true);
      const question = await questionsService.getQuestionById(questionId);
      setCurrentQuestion(question);
      return question;
    } catch (err) {
      logger.error('Failed to fetch question:', err);
      setError(err.response?.data?.detail || 'Ошибка загрузки вопроса');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Send answer
  const sendAnswer = useCallback(async (questionId, text, photo = null) => {
    try {
      const result = await questionsService.sendAnswer(questionId, { 
        text,
        photo 
      });
      
      // Update current question if it's the active one
      if (currentQuestion?.uuid === questionId) {
        setCurrentQuestion((prev) => ({
          ...prev,
          messages: [...(prev.messages || []), result],
          status: 'in_progress',
        }));
      }
      
      logger.info('Answer sent successfully');
      return result;
    } catch (err) {
      logger.error('Failed to send answer:', err);
      throw err;
    }
  }, [currentQuestion]);

  // Complete/close consultation
  const completeQuestion = useCallback(async (questionId) => {
    try {
      await questionsService.completeQuestion(questionId);
      
      // Update local state
      setQuestions((prev) =>
        prev.map((q) =>
          q.uuid === questionId ? { ...q, status: 'completed' } : q
        )
      );
      
      if (currentQuestion?.uuid === questionId) {
        setCurrentQuestion((prev) => ({ ...prev, status: 'completed' }));
      }
      
      logger.info('Question completed');
    } catch (err) {
      logger.error('Failed to complete question:', err);
      throw err;
    }
  }, [currentQuestion]);

  // Assign question to self
  const assignQuestion = useCallback(async (questionId) => {
    try {
      await questionsService.assignQuestion(questionId);
      
      // Update local state
      setQuestions((prev) =>
        prev.map((q) =>
          q.uuid === questionId
            ? { ...q, status: 'in_progress', assigned_to: 'current_pharmacist' }
            : q
        )
      );
      
      logger.info('Question assigned');
    } catch (err) {
      logger.error('Failed to assign question:', err);
      throw err;
    }
  }, []);

  // Fetch unread count
  const fetchUnreadCount = useCallback(async () => {
    try {
      const data = await questionsService.getUnreadCount();
      setUnreadCount(data.count || 0);
    } catch (err) {
      logger.error('Failed to fetch unread count:', err);
    }
  }, []);

  // Load quick reply templates
  const loadQuickReplies = useCallback(async () => {
    try {
      const templates = await questionsService.getQuickReplies();
      setQuickReplies(templates);
    } catch (err) {
      logger.error('Failed to load quick replies:', err);
    }
  }, []);

  // Setup WebSocket listeners for real-time updates
  useEffect(() => {
    const handleNewQuestion = (data) => {
      logger.info('New question received via WebSocket:', data);
      
      // Add new question to the beginning if on first page and filter matches
      if (pagination.page === 1 && (!filters.status || filters.status === 'pending')) {
        setQuestions((prev) => [data, ...prev.slice(0, pagination.limit - 1)]);
        setPagination((prev) => ({ ...prev, total: prev.total + 1 }));
      }
      
      // Increment unread count
      setUnreadCount((prev) => prev + 1);
      
      // Show notification (optional)
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification('Новый вопрос от пользователя', {
          body: data.text?.substring(0, 100) || 'Пользователь задал вопрос',
        });
      }
    };

    const handleQuestionAnswered = (data) => {
      logger.info('Question answered via WebSocket:', data);
      
      // Update question in local state
      setQuestions((prev) =>
        prev.map((q) =>
          q.uuid === data.question_id
            ? { ...q, status: 'answered', updated_at: data.updated_at }
            : q
        )
      );
      
      if (currentQuestion?.uuid === data.question_id) {
        setCurrentQuestion((prev) => ({
          ...prev,
          status: 'answered',
          updated_at: data.updated_at,
        }));
      }
    };

    const handleQuestionCompleted = (data) => {
      logger.info('Question completed via WebSocket:', data);
      
      setQuestions((prev) =>
        prev.map((q) =>
          q.uuid === data.question_id
            ? { ...q, status: 'completed', completed_at: data.completed_at }
            : q
        )
      );
      
      if (currentQuestion?.uuid === data.question_id) {
        setCurrentQuestion((prev) => ({
          ...prev,
          status: 'completed',
          completed_at: data.completed_at,
        }));
      }
    };

    // Subscribe to events
    const unsubscribeNewQuestion = websocketService.on('new_question', handleNewQuestion);
    const unsubscribeQuestionAnswered = websocketService.on(
      'question_answered',
      handleQuestionAnswered
    );
    const unsubscribeQuestionCompleted = websocketService.on(
      'question_completed',
      handleQuestionCompleted
    );

    return () => {
      unsubscribeNewQuestion();
      unsubscribeQuestionAnswered();
      unsubscribeQuestionCompleted();
    };
  }, [pagination.page, pagination.limit, filters.status, currentQuestion]);

  // Initial fetch
  useEffect(() => {
    fetchQuestions();
    fetchUnreadCount();
    loadQuickReplies();
    
    // Poll unread count every 30 seconds
    const interval = setInterval(fetchUnreadCount, 30000);
    
    return () => clearInterval(interval);
  }, [fetchQuestions, fetchUnreadCount, loadQuickReplies]);

  return {
    questions,
    loading,
    error,
    pagination,
    filters,
    currentQuestion,
    unreadCount,
    quickReplies,
    fetchQuestions,
    updateFilters,
    changePage,
    getQuestionById,
    sendAnswer,
    completeQuestion,
    assignQuestion,
    fetchUnreadCount,
    loadQuickReplies,
    setCurrentQuestion,
  };
}
