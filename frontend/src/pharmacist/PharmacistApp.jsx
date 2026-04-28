import React, { useEffect } from 'react';
import { Routes, Route, Navigate, useSearchParams } from 'react-router-dom';
import { AuthProvider } from './components/auth/AuthProvider';
import { useAuth } from './hooks/useAuth';
import Dashboard from './pharmacist/pages/Dashboard';
import Login from './pharmacist/components/auth/Login';
import ProtectedRoute from './pharmacist/components/auth/ProtectedRoute';
import { logger } from './utils/logger';

// Component to handle URL token authentication
function TokenAuthHandler() {
  const [searchParams] = useSearchParams();
  const { loginWithToken, isAuthenticated } = useAuth();

  useEffect(() => {
    const token = searchParams.get('token');
    
    console.log('[TokenAuthHandler] Checking for token in URL...');
    console.log('[TokenAuthHandler] Token found:', !!token);
    console.log('[TokenAuthHandler] Already authenticated:', isAuthenticated);
    
    if (token && !isAuthenticated) {
      logger.info('Found token in URL, attempting auto-login');
      
      // Attempt to login with the token from URL
      loginWithToken(token)
        .then(() => {
          logger.info('Auto-login successful');
          // Clear the token from URL by navigating to root
          window.history.replaceState({}, document.title, window.location.pathname);
        })
        .catch((err) => {
          logger.error('Auto-login failed:', err);
          console.error('[TokenAuthHandler] Error details:', {
            status: err.response?.status,
            data: err.response?.data,
            message: err.message
          });
          // Token is invalid or expired, redirect to login
          window.location.href = '/login';
        });
    } else if (!token) {
      console.log('[TokenAuthHandler] No token in URL, checking localStorage...');
    }
  }, [searchParams, loginWithToken, isAuthenticated]);

  return null; // This component doesn't render anything
}

export default function PharmacistApp() {
  return (
    <AuthProvider>
      <TokenAuthHandler />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}