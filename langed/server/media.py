"""Отдача загружаемых файлов (media) по адресу /media/<путь>.

Если media лежат в S3, view не читает объект сам: он проверяет путь и наличие объекта
и отвечает X-Accel-Redirect на internal location nginx пода, а в заголовке
X-Media-S3-Uri передаёт путь и query подписанной ссылки на MinIO. Байты идут из MinIO
через nginx, минуя воркеры uwsgi, а nginx кэширует ответ по пути запроса
(конфигурация — site.conf в langed-k8s). Браузер видит только /media/<путь>.

Без S3 (локальная разработка, тесты) файл отдаётся из MEDIA_ROOT самим Django.
"""

import mimetypes
from urllib.parse import urlsplit

from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponse
from django.views.decorators.http import require_safe

# internal location nginx, который проксирует запрос в MinIO по X-Media-S3-Uri
ACCEL_REDIRECT_LOCATION = '/_media_s3/'
S3_URI_HEADER = 'X-Media-S3-Uri'

CACHE_CONTROL = 'public, max-age=604800'
DEFAULT_CONTENT_TYPE = 'application/octet-stream'


def clean_media_path(path):
    """Относительный путь внутри хранилища; всё, что выходит за его пределы, — 404."""
    if not path or '\x00' in path or '\\' in path:
        raise Http404
    if path.startswith('/') or path.endswith('/'):
        raise Http404
    if any(part in ('', '.', '..') for part in path.split('/')):
        raise Http404
    return path


def media_content_type(name):
    content_type, _ = mimetypes.guess_type(name)
    return content_type or DEFAULT_CONTENT_TYPE


@require_safe
def serve_media(request, path):
    name = clean_media_path(path)
    storage = default_storage
    if not storage.exists(name):
        raise Http404
    content_type = media_content_type(name)

    presigned_url = getattr(storage, 'presigned_url', None)
    if presigned_url is not None:
        target = urlsplit(presigned_url(name, content_type=content_type))
        response = HttpResponse(content_type=content_type)
        response['X-Accel-Redirect'] = ACCEL_REDIRECT_LOCATION
        response[S3_URI_HEADER] = f'{target.path}?{target.query}'
        return response

    response = FileResponse(storage.open(name, 'rb'), content_type=content_type)
    response['Cache-Control'] = CACHE_CONTROL
    return response
