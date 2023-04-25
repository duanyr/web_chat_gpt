#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gm_rpcd.all import RPCDFaultException
from gm_types.doris.error import ERROR
from raven.contrib.django.raven_compat.models import client as _sentry_client


def raise_error(error_code, message=None):
    assert error_code != 0
    if message is None:
        message = ERROR.getDesc(error_code)
    raise RPCDFaultException(code=error_code, message=message)


def logging_exception(send_to_sentry=True):
    try:
        # send exception info to sentry, fail silently
        _sentry_client.captureException()
    except:
        pass
