import React from "react";

export default function LoadingSkeleton() {
  return (
    <div className="space-y-4 mb-6" aria-live="polite">
      {[1, 2, 3].map((item) => (
        <div key={item} className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="animate-pulse space-y-4">
            <div className="flex space-x-4">
              <div className="rounded-full bg-gray-300 h-12 w-12"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-300 rounded w-3/4"></div>
                <div className="h-3 bg-gray-300 rounded w-1/2"></div>
              </div>
            </div>
            <div className="space-y-2">
              <div className="h-4 bg-gray-300 rounded"></div>
              <div className="h-4 bg-gray-300 rounded w-5/6"></div>
            </div>
          </div>
        </div>
      ))}
      <div className="text-center text-gray-800 text-sm">
        Загрузка результатов...
      </div>
    </div>
  );
}
