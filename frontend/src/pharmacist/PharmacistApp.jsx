import React, { useEffect } from 'react';
import { Routes, Route, Navigate, useSearchParams } from 'react-router-dom';
import { AuthProvider, useAuth } from './pharmacist/hooks/useAuth';
import Dashboard from './pharmacist/pages/Dashboard';
import Login from './pharmacist/components/auth/Login';
import ProtectedRoute from './pharmacist/components/auth/ProtectedRoute';
import { logger } from './utils/logger';

// Component to handle URL token authentication
function TokenAuthHandler() {
  const [searchParams] = useSearchParams();
  const { loginWithToken } = useAuth();

  useEffect(() => {
    const token = searchParams.get('token');
    
    if (token) {
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
          // Token is invalid or expired, redirect to login
          window.location.href = '/login';
        });
    }
  }, [searchParams, loginWithToken]);

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