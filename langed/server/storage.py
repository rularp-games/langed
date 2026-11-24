"""Хранилище media в S3 (MinIO) с адресами файлов на самом сайте."""

from urllib.parse import urljoin

from django.conf import settings
from django.utils.encoding import filepath_to_uri
from storages.backends.s3 import S3Storage


class MediaS3Storage(S3Storage):
    """Файлы лежат в приватном бакете, а браузер получает их по MEDIA_URL.

    url() возвращает тот же адрес, что и FileSystemStorage (/media/<путь>), а не адрес
    MinIO: бакет приватный и снаружи кластера недоступен. Подписанную ссылку на объект
    строит presigned_url() — её использует только nginx пода (см. server/media.py).
    """

    def url(self, name, parameters=None, expire=None, http_method=None):
        path = filepath_to_uri(name)
        if path is not None:
            path = path.lstrip('/')
        return urljoin(settings.MEDIA_URL, path)

    def presigned_url(self, name, content_type=None):
        """Подписанная ссылка на GET объекта; content_type MinIO подставит в ответ."""
        parameters = {'ResponseContentType': content_type} if content_type else None
        return super().url(name, parameters=parameters)
