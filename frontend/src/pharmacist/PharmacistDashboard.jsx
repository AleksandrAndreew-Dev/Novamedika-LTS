import React from 'react';
import { HashRouter } from 'react-router-dom';
import { AuthProvider } from './components/auth/AuthProvider';
import ErrorBoundary from './components/common/ErrorBoundary';
import PharmacistContent from './PharmacistContent';

export default function PharmacistDashboard() {
  return (
    <ErrorBoundary>
      <HashRouter>
        <AuthProvider>
          <PharmacistContent />
        </AuthProvider>
      </HashRouter>
    </ErrorBoundary>
  );
}