import React from "react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleReset);
      }

      return (
        <div className="min-h-screen bg-telegram-bg flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-6 max-w-md w-full text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-red-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Что-то пошло не так
            </h2>
            <p className="text-gray-600 text-sm mb-6">
              Произошла ошибка при загрузке компонента. Попробуйте обновить
              страницу.
            </p>
            <div className="flex flex-col gap-3">
              <button
                onClick={this.handleReset}
                className="bg-telegram-primary text-gray-900 font-medium py-3 px-6 rounded-lg transition-colors hover:bg-blue-600 min-h-[44px]"
              >
                Попробовать снова
              </button>
              <button
                onClick={() => window.location.reload()}
                className="bg-gray-100 text-gray-800 font-medium py-3 px-6 rounded-lg transition-colors hover:bg-gray-200 min-h-[44px]"
              >
                Обновить страницу
              </button>
            </div>
            {import.meta.env.DEV && this.state.error && (
              <details className="mt-4 text-left">
                <summary className="text-xs text-gray-500 cursor-pointer">
                  Технические детали (DEV)
                </summary>
                <pre className="text-xs text-red-600 bg-red-50 p-3 rounded mt-2 overflow-auto max-h-40">
                  {this.state.error.toString()}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
