"""
Кастомные middleware для API
"""
import json
import logging
import traceback

from django.http import JsonResponse

logger = logging.getLogger(__name__)


class APIExceptionMiddleware:
    """
    Middleware для гарантии JSON ответов на все ошибки в API запросах.
    
    Если в процессе обработки API запроса происходит необработанное исключение,
    этот middleware вернёт JSON ответ вместо HTML страницы ошибки.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """
        Обрабатывает необработанные исключения для API запросов.
        """
        # Только для API запросов
        if not request.path.startswith('/api/'):
            return None
        
        # Логируем ошибку
        logger.exception(
            "Unhandled exception in API request: %s %s",
            request.method,
            request.path,
            exc_info=exception
        )
        
        # Возвращаем JSON ответ
        return JsonResponse(
            {
                'detail': 'Внутренняя ошибка сервера',
                'status_code': 500,
            },
            status=500
        )
