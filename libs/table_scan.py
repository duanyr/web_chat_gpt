#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, absolute_import

import six
import random
from django.db import models


class ITableChunk(object):

    def __iter__(self):
        raise NotImplementedError

    def get_pk_start(self):
        raise NotImplementedError

    def get_pk_stop(self):
        raise NotImplementedError


class TableScannerChunk(ITableChunk):

    def __init__(self, data_list, pk_start, pk_stop):
        self._data_list = data_list
        self._pk_start = pk_start
        self._pk_stop = pk_stop

    def __iter__(self):
        return iter(self._data_list)

    def get_pk_start(self):
        return self._pk_start

    def get_pk_stop(self):
        return self._pk_stop


class TableScannerChunkIterator(object):

    def __init__(self, scanner, last_pk, chunk_size):
        assert isinstance(scanner, TableScanner)
        self._scanner = scanner
        self._last_pk = last_pk
        self._chunk_size = chunk_size

    def __iter__(self):
        while True:
            last_pk = self._last_pk
            data_list, next_last_pk = self._scanner.get_next_data_list(last_pk=last_pk, chunk_size=self._chunk_size)
            self._last_pk = next_last_pk
            yield TableScannerChunk(data_list=data_list, pk_start=last_pk, pk_stop=next_last_pk)


class TableScannerFlattenIterator(object):

    def __init__(self, scanner, last_pk):
        assert isinstance(scanner, TableScanner)
        self._scanner = scanner
        self._last_pk = last_pk

    def __iter__(self):
        while True:
            data_list, next_last_pk = self._scanner.get_next_data_list(last_pk=self._last_pk)
            self._last_pk = next_last_pk
            for data in data_list:
                yield data


class TableScanner(object):

    def __init__(self, queryset):
        assert isinstance(queryset, models.QuerySet)
        self._model = queryset.model
        self._query = queryset.query
        self._db_table = self._model._meta.db_table

    @property
    def queryset(self):
        return models.QuerySet(model=self._model, query=self._query)

    @property
    def model_queryset(self):
        return self._model.objects

    def get_random_pk(self):
        count = self.model_queryset.count()
        if count == 0:
            return None
        index = random.randrange(count)
        try:
            return self.model_queryset.values_list('pk', flat=True)[index]
        except IndexError:
            return None

    def get_next_data_list(self, last_pk=None, chunk_size=1):
        qs = self.queryset.order_by('pk')
        if last_pk is not None:
            qs = qs.filter(pk__gt=last_pk)
        data_list = list(qs[:chunk_size])
        if len(data_list) == 0:
            next_last_pk = None
        else:
            next_last_pk = data_list[-1].pk
        return data_list, next_last_pk

    def __iter__(self):
        pk = self.get_random_pk()
        return iter(TableScannerFlattenIterator(scanner=self, last_pk=pk))

    def chunks(self, chunk_size):
        pk = self.get_random_pk()
        return iter(TableScannerChunkIterator(scanner=self, last_pk=pk, chunk_size=chunk_size))


class TableSlicerChunk(ITableChunk):
    """
    this object can be pickled and transferred to another process.
    """

    def __init__(self, model, query, pk_start, pk_stop):
        self._model = model
        self._query = query
        self._pk_start = pk_start
        self._pk_stop = pk_stop

    def __iter__(self):
        data_list = self.__get_range(self._model, self._query, pk_start=self._pk_start, pk_stop=self._pk_stop)
        return iter(data_list)

    def get_pk_start(self):
        return self._pk_start

    def get_pk_stop(self):
        return self._pk_stop

    @classmethod
    def __get_range(cls, model, query, pk_start, pk_stop):
        qs = models.QuerySet(model=model, query=query)
        if pk_start is not None:
            qs = qs.filter(pk__gte=pk_start)
        if pk_stop is not None:
            qs = qs.filter(pk__lt=pk_stop)
        return list(qs)


class TableSlicer(object):

    def __init__(self, queryset, chunk_size=None, chunk_count=None, sep_list=None):
        assert isinstance(queryset, models.QuerySet)
        assert chunk_size is None or isinstance(chunk_size, six.integer_types)
        assert chunk_count is None or isinstance(chunk_count, six.integer_types)
        assert sep_list is None or isinstance(sep_list, list)

        assert (chunk_size is not None) + (chunk_count is not None) + (sep_list is not None) == 1

        if sep_list is not None:
            sep_list = list(sep_list)
        else:
            count = queryset.count()
            if chunk_size is None:
                chunk_size = count / chunk_count
            index_list = list(range(0, count, chunk_size))
            sep_list = [
                queryset.order_by('pk').values_list('pk', flat=True)[index]
                for index in index_list
            ]

        self._model = queryset.model
        self._query = queryset.query
        self._sep_list = [None] + sep_list + [None]


    def chunks(self):
        reversed_sep_list = list(reversed(self._sep_list))
        for i in range(len(self._sep_list) - 1):
            pk_start = reversed_sep_list[i+1]
            pk_stop = reversed_sep_list[i]
            yield TableSlicerChunk(model=self._model, query=self._query, pk_start=pk_start, pk_stop=pk_stop)


class TableStreamingSlicer(object):

    def __init__(self, queryset, chunk_size=None):
        assert isinstance(queryset, models.QuerySet)
        assert chunk_size is None or isinstance(chunk_size, six.integer_types)

        self._model = queryset.model
        self._query = queryset.query
        self._chunk_size = chunk_size
        self._descend = False

    def chunks(self):
        last_pk = None
        queryset = models.QuerySet(model=self._model, query=self._query).order_by('pk')
        value_list = queryset.values_list('pk', flat=True)
        while True:
            current_value_list = value_list
            if last_pk is not None:
                current_value_list = current_value_list.filter(pk__gt=last_pk)
            try:
                next_last_pk = current_value_list[self._chunk_size-1]
            except IndexError:
                next_last_pk = None
            yield TableSlicerChunk(model=self._model, query=self._query, pk_start=last_pk, pk_stop=next_last_pk)
            last_pk = next_last_pk
            if last_pk is None:
                break
