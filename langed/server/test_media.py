"""Хранилище media (S3 или файловая система) и отдача файлов по /media/<путь>."""

import tempfile
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage, storages
from django.test import SimpleTestCase, TestCase, override_settings

from langed.media_settings import build_storages
from .media import ACCEL_REDIRECT_LOCATION, S3_URI_HEADER
from .models import Game
from .storage import MediaS3Storage

S3_CONFIG = {
    'endpoint_url': 'http://minio.test:9000',
    'bucket_name': 'langed-test',
    'access_key': 'test-access-key',
    'secret_key': 'test-secret-key',
    'location': '/pvc-test/',
}


class BuildStoragesTests(SimpleTestCase):
    def test_filesystem_without_s3_config(self):
        for media_s3 in (None, {}, {'bucket_name': ''}):
            with self.subTest(media_s3=media_s3):
                storages = build_storages(media_s3)
                self.assertEqual(
                    storages['default'],
                    {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
                )
                self.assertEqual(
                    storages['staticfiles']['BACKEND'],
                    'django.contrib.staticfiles.storage.StaticFilesStorage',
                )

    def test_s3_with_config(self):
        storages = build_storages(S3_CONFIG)
        self.assertEqual(storages['default']['BACKEND'], 'server.storage.MediaS3Storage')
        options = storages['default']['OPTIONS']
        self.assertEqual(options['endpoint_url'], 'http://minio.test:9000')
        self.assertEqual(options['bucket_name'], 'langed-test')
        self.assertEqual(options['access_key'], 'test-access-key')
        self.assertEqual(options['secret_key'], 'test-secret-key')
        self.assertEqual(options['location'], 'pvc-test')
        self.assertEqual(options['region_name'], 'us-east-1')
        self.assertIsNone(options['default_acl'])
        self.assertEqual(options['addressing_style'], 'path')
        self.assertEqual(options['signature_version'], 's3v4')
        self.assertTrue(options['querystring_auth'])
        self.assertFalse(options['file_overwrite'])

    def test_incomplete_s3_config_fails(self):
        with self.assertRaises(ImproperlyConfigured) as error:
            build_storages({'bucket_name': 'langed-test', 'endpoint_url': 'http://minio.test:9000'})
        self.assertIn('access_key', str(error.exception))
        self.assertIn('secret_key', str(error.exception))


class MediaS3StorageTests(SimpleTestCase):
    def setUp(self):
        self.storage = MediaS3Storage(**build_storages(S3_CONFIG)['default']['OPTIONS'])

    def test_url_points_to_site_media(self):
        self.assertEqual(
            self.storage.url('games/posters/all_in.jpg'), '/media/games/posters/all_in.jpg'
        )
        self.assertEqual(
            self.storage.url('games/posters/a b.jpg'), '/media/games/posters/a%20b.jpg'
        )

    def test_presigned_url_points_to_object_in_location(self):
        url = urlsplit(self.storage.presigned_url('games/posters/all_in.jpg', content_type='image/jpeg'))
        self.assertEqual(url.netloc, 'minio.test:9000')
        self.assertEqual(url.path, '/langed-test/pvc-test/games/posters/all_in.jpg')
        query = parse_qs(url.query)
        self.assertEqual(query['response-content-type'], ['image/jpeg'])
        self.assertEqual(query['X-Amz-Algorithm'], ['AWS4-HMAC-SHA256'])
        self.assertIn('X-Amz-Signature', query)


@override_settings(STORAGES=build_storages(S3_CONFIG))
class S3MediaViewTests(TestCase):
    def test_default_storage_is_s3(self):
        self.assertIsInstance(storages['default'], MediaS3Storage)

    def test_existing_object_is_redirected_to_nginx(self):
        with mock.patch.object(MediaS3Storage, 'exists', return_value=True) as exists:
            response = self.client.get('/media/games/posters/all_in.jpg')
        exists.assert_called_once_with('games/posters/all_in.jpg')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertEqual(response['X-Accel-Redirect'], ACCEL_REDIRECT_LOCATION)
        target = urlsplit(response[S3_URI_HEADER])
        self.assertEqual(target.netloc, '')
        self.assertEqual(target.path, '/langed-test/pvc-test/games/posters/all_in.jpg')
        query = parse_qs(target.query)
        self.assertEqual(query['response-content-type'], ['image/jpeg'])
        self.assertIn('X-Amz-Signature', query)

    def test_content_type_by_extension(self):
        cases = {
            'games/posters/p.png': 'image/png',
            'games/posters/p.webp': 'image/webp',
            'games/posters/p': 'application/octet-stream',
        }
        for name, content_type in cases.items():
            with self.subTest(name=name), mock.patch.object(MediaS3Storage, 'exists', return_value=True):
                response = self.client.get(f'/media/{name}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], content_type)
                query = parse_qs(urlsplit(response[S3_URI_HEADER]).query)
                self.assertEqual(query['response-content-type'], [content_type])

    def test_head_is_allowed(self):
        with mock.patch.object(MediaS3Storage, 'exists', return_value=True):
            response = self.client.head('/media/games/posters/all_in.jpg')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Accel-Redirect'], ACCEL_REDIRECT_LOCATION)

    def test_missing_object_is_404(self):
        with mock.patch.object(MediaS3Storage, 'exists', return_value=False):
            response = self.client.get('/media/games/posters/missing.jpg')
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('X-Accel-Redirect', response)

    def test_path_traversal_is_404_without_storage_access(self):
        paths = [
            '/media/../langed/settings.py',
            '/media/games/../../langed/settings.py',
            '/media/games/%2e%2e/%2e%2e/secret',
            '/media/games/..%2f..%2fsecret',
            '/media/./games/posters/all_in.jpg',
            '/media//etc/passwd',
            '/media/games/posters/',
            '/media/games\\..\\secret',
            '/media/games/%00.jpg',
        ]
        with mock.patch.object(MediaS3Storage, 'exists', return_value=True) as exists:
            for path in paths:
                with self.subTest(path=path):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 404)
                    self.assertNotIn('X-Accel-Redirect', response)
        exists.assert_not_called()

    def test_write_methods_are_not_allowed(self):
        with mock.patch.object(MediaS3Storage, 'exists', return_value=True):
            response = self.client.post('/media/games/posters/all_in.jpg')
        self.assertEqual(response.status_code, 405)

    def test_api_poster_url_stays_on_site(self):
        Game.objects.create(name='With poster', poster='games/posters/p.png')
        response = self.client.get('/api/games/?search=With poster')
        self.assertEqual(
            response.json()['results'][0]['poster'], 'http://testserver/media/games/posters/p.png'
        )


class FileSystemMediaViewTests(TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        media_root = Path(self.root.name) / 'media'
        (media_root / 'games' / 'posters').mkdir(parents=True)
        (media_root / 'games' / 'posters' / 'p.jpg').write_bytes(b'jpeg-bytes')
        # Файл рядом с MEDIA_ROOT — до него не должно быть доступа
        (Path(self.root.name) / 'secret.txt').write_bytes(b'secret')
        settings_override = override_settings(MEDIA_ROOT=str(media_root))
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def test_default_storage_is_filesystem(self):
        self.assertIsInstance(storages['default'], FileSystemStorage)

    def test_existing_file_is_served(self):
        response = self.client.get('/media/games/posters/p.jpg')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'jpeg-bytes')
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertEqual(response['Cache-Control'], 'public, max-age=604800')
        self.assertNotIn('X-Accel-Redirect', response)

    def test_missing_file_is_404(self):
        response = self.client.get('/media/games/posters/missing.jpg')
        self.assertEqual(response.status_code, 404)

    def test_path_traversal_is_404(self):
        for path in ('/media/../secret.txt', '/media/games/%2e%2e/%2e%2e/secret.txt'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)
