#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import logging

LOG_DIR = '/data/log/chat/app/'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(module)s.%(funcName)s Line:%(lineno)d  %(message)s',
    filename=os.path.join(LOG_DIR, 'filelog.log'),
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },

    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(module)s.%(funcName)s Line:%(lineno)d  %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'profile': {
            'format': '%(asctime)s %(message)s'
        },
        'raw': {
            'format': '%(message)s'
        }
    },

    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },

        # 默认的服务器Log(保存到log/filelog.log中, 通过linux的logrotate来处理日志的分割
        'default': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'filelog.log'),
            'formatter': 'verbose',
        },

        # 默认的服务器ERROR log
        'default_err': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'error_logger.log'),
            'formatter': 'verbose',
        },
        'exception_logger': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'exception_logger.log'),
            'formatter': 'verbose',
        },

        'tracer_handler': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'tracer.log'),
            'formatter': 'raw'
        },
    },

    'loggers': {
        'django': {
            'handlers': ['default'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['default_err'],
            'level': 'ERROR',
            'propagate': False,
        },
        'exception_logger': {
            'handlers': ['exception_logger'],
            'level': 'INFO',
            'propagate': False,
        }

    },
}


