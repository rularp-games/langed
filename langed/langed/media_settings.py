"""Выбор хранилища загружаемых файлов (media) по MEDIA_S3 из private_settings.

Если S3 не настроен, файлы лежат в локальной файловой системе (MEDIA_ROOT):
так работают локальная разработка и тесты.
"""

from django.core.exceptions import ImproperlyConfigured

FILESYSTEM_BACKEND = 'django.core.files.storage.FileSystemStorage'
S3_BACKEND = 'server.storage.MediaS3Storage'
STATICFILES_BACKEND = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Ключи MEDIA_S3, без которых S3 не включить
S3_REQUIRED = ('endpoint_url', 'bucket_name', 'access_key', 'secret_key')

# Ключи MEDIA_S3, которые можно переопределить
S3_OPTIONAL = ('region_name', 'location')

S3_DEFAULTS = {
    'region_name': 'us-east-1',
    # Префикс ключей в бакете (у тома csi-s3 это pvc-<uid>)
    'location': '',
    # Бакет приватный: без ACL, ссылки на объекты подписываются
    'default_acl': None,
    'querystring_auth': True,
    # Подписанная ссылка нужна только nginx пода на время одного запроса
    'querystring_expire': 300,
    'signature_version': 's3v4',
    'addressing_style': 'path',
    # Как у FileSystemStorage: одноимённый файл получает суффикс, а не затирает чужой
    'file_overwrite': False,
}


def build_storages(media_s3):
    """Значение STORAGES: S3 при заданном MEDIA_S3['bucket_name'], иначе файловая система."""
    staticfiles = {'BACKEND': STATICFILES_BACKEND}
    media_s3 = media_s3 or {}
    if not media_s3.get('bucket_name'):
        return {
            'default': {'BACKEND': FILESYSTEM_BACKEND},
            'staticfiles': staticfiles,
        }
    missing = [key for key in S3_REQUIRED if not media_s3.get(key)]
    if missing:
        raise ImproperlyConfigured(
            'MEDIA_S3: не заданы ' + ', '.join(missing)
        )
    options = dict(S3_DEFAULTS)
    for key in S3_REQUIRED + S3_OPTIONAL:
        if media_s3.get(key) is not None:
            options[key] = media_s3[key]
    options['location'] = options['location'].strip('/')
    return {
        'default': {'BACKEND': S3_BACKEND, 'OPTIONS': options},
        'staticfiles': staticfiles,
    }
