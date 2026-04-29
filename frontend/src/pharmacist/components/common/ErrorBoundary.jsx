import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(_error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details for debugging with enhanced information
    console.error('🚨 ErrorBoundary caught an error:', error);
    console.error('📋 Error Info:', errorInfo);
    console.error('🔍 Component Stack:', errorInfo?.componentStack);
    console.error('📊 Error Details:', {
      name: error.name,
      message: error.message,
      stack: error.stack,
      fileName: error.fileName,
      lineNumber: error.lineNumber,
      columnNumber: error.columnNumber
    });
    
    // Log additional context if available
    if (this.props.fallbackRender) {
      console.warn('⚠️ Custom fallback renderer is defined but not used');
    }
    
    this.setState({
      error,
      errorInfo,
    });
  }

  handleRetry = () => {
    // Attempt to recover by reloading the page
    window.location.reload();
  };

  handleGoHome = () => {
    // Navigate to home page
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      // Enhanced error logging for production debugging
      if (process.env.NODE_ENV === 'production') {
        // Send error to monitoring service in production
        console.error('Production Error:', {
          error: this.state.error?.message,
          componentStack: this.state.errorInfo?.componentStack,
          timestamp: new Date().toISOString(),
          url: window.location.href,
          userAgent: navigator.userAgent
        });
      }

      // Custom fallback UI
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="bg-white p-8 rounded-lg shadow-lg max-w-md w-full border-l-4 border-red-500">
            <div className="text-center mb-6">
              <div className="mx-auto h-16 w-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
                <svg
                  className="h-8 w-8 text-red-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Что-то пошло не так
              </h2>
              <p className="text-gray-600 text-sm">
                Произошла ошибка при загрузке компонента
              </p>
            </div>

            {/* Enhanced Error Details (only in development) */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div className="mb-4 p-3 bg-gray-100 rounded text-left">
                <p className="text-xs font-mono text-red-600 break-all mb-2">
                  <strong>Error:</strong> {this.state.error.toString()}
                </p>
                {this.state.error.stack && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-gray-600 hover:text-gray-800">
                      Показать стек вызовов
                    </summary>
                    <pre className="mt-2 text-xs overflow-auto max-h-40 bg-gray-200 p-2 rounded">
                      {this.state.error.stack}
                    </pre>
                  </details>
                )}
                {this.state.errorInfo?.componentStack && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-gray-600 hover:text-gray-800">
                      Показать компонентный стек
                    </summary>
                    <pre className="mt-2 text-xs overflow-auto max-h-40 bg-gray-200 p-2 rounded">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </details>
                )}
              </div>
            )}

            <div className="space-y-3">
              <button
                onClick={this.handleRetry}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center"
              >
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                Повторить попытку
              </button>
              
              <button
                onClick={this.handleGoHome}
                className="w-full bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center"
              >
                <svg
                  className="w-5 h-5 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
                  />
                </svg>
                На главную
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;