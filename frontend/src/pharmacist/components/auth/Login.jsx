import React from 'react';
import LoginForm from './LoginForm';

export default function Login() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-purple-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Pharmacist Dashboard</h1>
          <p className="mt-2 text-gray-600">Войдите для доступа к панели управления</p>
        </div>
        <LoginForm />
      </div>
    </div>
  );
}
