import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './pharmacist/hooks/useAuth';
import Dashboard from './pharmacist/pages/Dashboard';
import Login from './pharmacist/components/auth/Login';
import ProtectedRoute from './pharmacist/components/auth/ProtectedRoute';

export default function PharmacistApp() {
  return (
    <AuthProvider>
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
