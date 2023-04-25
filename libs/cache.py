#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redis
from django.conf import settings

redis_client = redis.StrictRedis.from_url(settings.REDIS_URL)