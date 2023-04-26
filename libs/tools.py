#!/usr/bin/env python
# -*- coding: utf-8 -*-

import django.db.models
from django.conf import settings
from pytz import timezone
from datetime import datetime
from django.http import HttpResponse
import json
import hashlib
import logging
import traceback
from math import radians, cos, sin, asin, sqrt
from libs.cache import redis_client




def json_http_response(result, status=200, extra_headers=None):
    if extra_headers is None:
        extra_headers = dict()
    if 'extra' not in result:
        result['extra'] = {}
    response = HttpResponse(
        json.dumps(result),
        content_type="application/json; charset=UTF-8",
        status=status,
    )
    for header_key, header_value in extra_headers.items():
        response[header_key] = header_value
    return response
