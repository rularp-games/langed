"""
URL configuration for langed project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
import os


@never_cache
def vue_app(request):
    """Отдаёт Vue.js SPA index.html"""
    index_path = os.path.join(settings.BASE_DIR, 'static', 'vue', 'index.html')
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            return HttpResponse(f.read(), content_type='text/html')
    except FileNotFoundError:
        return HttpResponse(
            '<h1>Vue.js не собран</h1>'
            '<p>Выполните: <code>cd front && npm run build</code></p>',
            content_type='text/html',
            status=503
        )


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('server.urls')),
    # Catch-all для Vue Router — должен быть последним
    re_path(r'^(?!admin/|api/|static/|media/).*$', vue_app, name='vue_app'),
]

# Для dev-режима: отдача статики и медиа Django
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

