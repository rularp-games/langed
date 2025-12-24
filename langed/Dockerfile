FROM ubuntu:24.04

ENV TZ="Asia/Yekaterinburg"
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN mkdir /langed

RUN apt update && apt -y upgrade && apt -yq install nginx git supervisor make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev\
    libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3-openssl \
    net-tools vim uwsgi uwsgi-plugin-python3
RUN git clone 'https://github.com/pyenv/pyenv.git' /langed/.pyenv
RUN git clone 'https://github.com/pyenv/pyenv-virtualenv.git' /langed/.pyenv/plugins/pyenv-virtualenv

ENV PYENV_ROOT="/langed/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"

RUN /langed/.pyenv/bin/pyenv install 3.14.0
RUN /langed/.pyenv/bin/pyenv virtualenv 3.14.0 langed

ENV LC_ALL="en-US.UTF-8"
ENV LANG="en-US.UTF-8"
ENV LANGUAGE="en-US.UTF-8"

COPY . /langed

WORKDIR /langed

RUN chmod 755 /langed/init.sh

RUN /langed/.pyenv/versions/3.14.0/envs/langed/bin/python -m pip install --upgrade pip

RUN /langed/.pyenv/versions/langed/bin/pip3 install -r requirements.txt

RUN /langed/.pyenv/versions/langed/bin/python3 manage.py collectstatic --noinput

RUN ln -s /langed/langed.conf /etc/nginx/conf.d/langed.conf
