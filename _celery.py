# !/usr/bin/env python
# encoding=utf-8
from __future__ import absolute_import

import os
# set the default Django settings module for the 'celery' program.
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat.settings')

import raven
from raven.contrib.celery import register_signal, register_logger_signal
from celery import Celery
from django.conf import settings


class Celery(Celery):
    """wrap for celery.Celery."""

    def on_configure(self):
        # check if sentry settings provided
        if not settings.SENTRY_CELERY_ENDPOINT:
            return

        client = raven.Client(settings.SENTRY_CELERY_ENDPOINT)

        # register a custom filter to filter out duplicate logs
        register_logger_signal(client)

        # hook into the Celery error handler
        register_signal(client)


app = Celery('gpt_chat_tasks')


# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

