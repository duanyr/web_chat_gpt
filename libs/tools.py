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



def word_is_mask(keyword):
    return redis_client.sismember("search_tips:word_masks",keyword)

def tzlc(dt, truncate_to_sec=True):
    if dt is None:
        return None
    if truncate_to_sec:
        dt = dt.replace(microsecond=0)

    if dt.tzinfo is None:
        return timezone(settings.TIME_ZONE).localize(dt)
    else:
        return timezone(settings.TIME_ZONE).normalize(dt)


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


def getMd5Digest(ori_content):
    m5 = hashlib.md5()
    m5.update(ori_content.encode("utf-8"))
    return m5.hexdigest()


def point_distance(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # 将十进制度数转化为弧度
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # haversine公式
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # 地球平均半径，单位为km
    return c * r * 1000

