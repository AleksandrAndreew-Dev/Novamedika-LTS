// Authentication hook for pharmacist dashboard
import { useContext } from 'react';
import { AuthContext } from '../components/auth/AuthProvider';

// useAuth hook - must be used within AuthProvider
export function useAuth() {
  const context = useContext(AuthContext);
  
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  
  return context;
}
