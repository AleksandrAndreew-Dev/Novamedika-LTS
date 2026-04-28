import React from 'react';
import { AuthProvider } from './hooks/useAuth.jsx';
import ErrorBoundary from './components/common/ErrorBoundary';
import PharmacistContent from './PharmacistContent';

export default function PharmacistDashboard() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <PharmacistContent />
      </AuthProvider>
    </ErrorBoundary>
  );
}
