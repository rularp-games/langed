#!/bin/bash

/langed/.pyenv/versions/langed/bin/python3 manage.py makemigrations
/langed/.pyenv/versions/langed/bin/python3 manage.py migrate
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@langed.langed', 'qwerty')" | /langed/.pyenv/versions/langed/bin/python3 manage.py shell
/langed/.pyenv/versions/langed/bin/uwsgi --ini /langed/uwsgi/langed.main
