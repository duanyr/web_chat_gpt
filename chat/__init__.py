from __future__ import unicode_literals, absolute_import, print_function

import pymysql
from _celery import app as celery_app

pymysql.install_as_MySQLdb()