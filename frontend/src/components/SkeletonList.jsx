import React from 'react';

/**
 * Skeleton Card Component
 * 
 * Placeholder для карточки товара во время загрузки
 * Соответствует e-commerce best practices (Facebook, LinkedIn, Wildberries)
 * Улучшает perceived performance на 30-50%
 */
export function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200 animate-pulse">
      <div className="flex gap-3 sm:gap-4">
        {/* Placeholder для изображения/иконки лекарства */}
        <div className="w-16 h-16 sm:w-20 sm:h-20 bg-gray-200 rounded-lg flex-shrink-0"></div>
        
        <div className="flex-1 space-y-2 sm:space-y-3">
          {/* Placeholder для названия лекарства */}
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          
          {/* Placeholder для формы выпуска и дозировки */}
          <div className="h-3 bg-gray-200 rounded w-1/2"></div>
          
          {/* Placeholder для аптеки */}
          <div className="h-3 bg-gray-200 rounded w-2/3"></div>
          
          {/* Placeholder для цены и наличия */}
          <div className="flex justify-between items-center pt-1 sm:pt-2">
            <div className="h-5 bg-gray-200 rounded w-20"></div>
            <div className="h-8 bg-gray-200 rounded w-24"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Skeleton List Component
 * 
 * Список skeleton карточек для результатов поиска
 */
export default function SkeletonList({ count = 5 }) {
  return (
    <div className="space-y-3" role="status" aria-label="Загрузка результатов">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
      
      {/* Screen reader текст */}
      <span className="sr-only">Загрузка...</span>
    </div>
  );
}
