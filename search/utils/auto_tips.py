#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import, print_function
import logging
import traceback
import json
import base64, hashlib
from libs.es import ESPerform
from libs.cache import redis_client
from libs.tools import g_hospital_pos_dict
from libs.tools import point_distance
from gm_rpcd.all import bind
from trans2es.commons.words_utils import QueryWordAttr, get_tips_word_type
from pypinyin import pinyin, lazy_pinyin
from helios.rpc import create_default_invoker


rpc_invoker = create_default_invoker(debug=False)

def device_is_gray(device_id):
    try:
        grey_codes = ["search_sug"]
        rpc_client = rpc_invoker['platform/grey_control/info_by_names'](grey_codes=grey_codes, device_id=device_id)
        ret = rpc_client.unwrap()
        return ret["codes"]["search_sug"]
    except:
        logging.error("catch exception,err_msg:%s" % traceback.format_exc())
        return False

def get_suggest_tips(query, lat, lng, offset=0, size=50, device_id=None):
    try:
        gray_number = 1
        ###在原来的逻辑上加两层灰度
        sub_index_name = "suggest"
        have_read_tips_set, ret_list, result_dict = get_query_by_es(query=str(query).lower(), lat=lat, lng=lng,
                                                                    offset=offset,
                                                                    size=size, highlight_query=query,
                                                                    have_read_tips_set=set(),
                                                                    sub_index_name=sub_index_name)

        if gray_number == 3:
            # 在去掉强加权的逻辑上根据词频和tag转化率排序后再前段强加权
            front_data = []
            end_data = []
            equal_data = []
            need_change_sort = ret_list[:size]
            for item in need_change_sort:
                ori_name = item.get("ori_name", None)
                if query == ori_name:
                    equal_data.append(item)
                elif query == ori_name[:len(query)]:
                    front_data.append(item)
                else:
                    end_data.append(item)
            equal_data.extend(front_data)
            equal_data.extend(end_data)
            # equal_data.extend(ret_list[30:])
            ret_list = equal_data

        if len(ret_list) >= size:
            logging.info("user_search_query:%s,get_sug_num:%s" % (query, len(ret_list)))
            return ret_list[:size]

        else:
            query_ret_list = []
            wordresemble_ret_list = []
            value_data = []
            QUERY_KEY = "query:search_tip"
            query_base64 = base64.b64encode(query.encode('utf8')).decode('utf8')
            if redis_client.hget(QUERY_KEY, query_base64) is not None:
                value_data = json.loads(str(redis_client.hget(QUERY_KEY, query_base64), encoding='utf-8'))

            if len(value_data) > 0:
                for i in value_data:
                    key = list(i.keys())[0]
                    ori_name = str(base64.b64decode(key), "utf-8")
                    if ori_name not in have_read_tips_set:
                        have_read_tips_set.add(ori_name)
                        result_num = i.get(key, 0)
                        describe = "约" + str(result_num) + "个结果" if result_num else ""
                        logging.info("get result_num:%s" % result_num)
                        highlight_marks = u'<ems>%s</ems>' % query
                        # highlight_name = ori_name.replace(query, highlight_marks)
                        highlight_name = set_highlihgt(query, ori_name)
                        if ori_name == query:
                            query_ret_list.append(
                                {"results_num": result_num, "ori_name": ori_name, "id": None, "is_online": True,
                                 "offline_score": 0,
                                 "type_flag": get_tips_word_type(ori_name), "highlight_name": highlight_name,
                                 "describe": describe})
                        else:

                            wordresemble_ret_list.append(
                                {"results_num": result_num, "ori_name": ori_name, "id": None, "is_online": True,
                                 "offline_score": 0,
                                 "type_flag": get_tips_word_type(ori_name), "highlight_name": highlight_name,
                                 "describe": describe})

                ret_list.extend(query_ret_list)
                ret_list.extend(wordresemble_ret_list)
            ###繁体字删掉，把搜索结果加到简体字上边
            fanti_query = [{'痩脸针': "瘦脸针"}]

            for item in ret_list:
                result_num = [[item['results_num'], list(ret.values())[0], list(ret.keys())[0]] for ret in fanti_query
                              if list(ret.keys())[0] == item['ori_name']]

                if len(result_num) > 0:
                    ret_list.remove(item)
                    for item in ret_list:
                        if item['ori_name'] == result_num[0][1]:
                            item['results_num'] += result_num[0][0]

            ####
            if len(ret_list) >= size:

                logging.info("user_search_query:%s,get_sug_num:%s" % (query, len(ret_list)))
                return ret_list[0:size]

            elif len(ret_list) < size and len(ret_list) > 3:
                logging.info("user_search_query:%s,get_sug_num:%s" % (query, len(ret_list)))
                return ret_list

            else:
                ##无结果的时候把汉字转成拼音再搜一次
                ss = lazy_pinyin(query)
                str_query = ''
                for item in ss:
                    str_query += str(item)

                have_read_tips_set, pinyin_ret_list, result_dict = get_query_by_es(query=str_query, lat=lat, lng=lng,
                                                                                   offset=offset,
                                                                                   size=size - len(ret_list),
                                                                                   highlight_query=query,
                                                                                   have_read_tips_set=have_read_tips_set,
                                                                                   sub_index_name=sub_index_name)
                ret_list.extend(pinyin_ret_list)
                logging.info("user_search_query:%s,get_sug_num:%s" % (query, len(ret_list)))

                if gray_number in (2, 3):
                    return ret_list[:size]

                return ret_list


    except:
        logging.error("catch exception,err_msg:%s" % traceback.format_exc())
        logging.info("error_user_search_query:%s,get_sug_num:%s" % (query, 0))
        return list()


def set_highlihgt(query=None, ori_name=None):
    ###高亮调整
    all_word = set()
    query2 = ori_name
    for item in range(0, len(query)):
        all_word.add(query[item])
    for item in all_word:
        is_find = query2.find(item)
        if is_find >= 0:
            highlight_marks = u'<>%s</>' % item
            high_query = query2.replace(item, highlight_marks)
            query2 = high_query

        highlight_name = query2.replace('<>', '<ems>').replace('</>', '</ems>')

    return highlight_name


def get_query_by_es(query='', lat=0, lng=0, size=0, offset=0, highlight_query=None,
                    have_read_tips_set=None, sub_index_name="suggest"):
    try:

        query = query.replace("\u2006", '')
        q = {
            "suggest": {
                "tips-suggest": {
                    "prefix": query,
                    "completion": {
                        "field": "suggest",
                        "size": size,
                        "contexts": {
                            "is_online": [True]
                        },
                        "fuzzy": {
                            "fuzziness": 0
                        }
                    }
                }
            },
            "_source": {
                "includes": ["id", "ori_name", "offline_score", "is_online", "type_flag", "results_num"]
            }
        }
        get_doctor_hospital_data = list()
        get_tag_wiki_data = list()
        ret_list = list()
        doctor_hospital_equal_query = list()
        get_hospital_data_gt_50 = list()
        tag_equal_query = list()
        result_dict = ESPerform.get_search_results(ESPerform.get_cli(), sub_index_name=sub_index_name, query_body=q,
                                                   offset=offset, size=size, is_suggest_request=True)
        for tips_item in result_dict["suggest"]["tips-suggest"]:
            for hit_item in tips_item["options"]:
                hit_item["_source"]["ori_name"] = hit_item["_source"]["ori_name"].replace("超声刀", "超声提升")
                hit_item["_source"]["ori_name"] = hit_item["_source"]["ori_name"].replace("私密超声刀", "私密超声紧致")
                if hit_item["_source"]["ori_name"] not in have_read_tips_set and "郑爽" not in hit_item["_source"][
                    "ori_name"]:
                    have_read_tips_set.add(hit_item["_source"]["ori_name"])
                    highlight_marks = u'<ems>%s</ems>' % query
                    # hit_item["_source"]["highlight_name"] = hit_item["_source"]["ori_name"].replace(query,
                    #                                                                                 highlight_marks)
                    hit_item["_source"]["highlight_name"] = set_highlihgt(highlight_query,
                                                                          hit_item["_source"]["ori_name"])
                    if hit_item["_source"]["type_flag"] == "hospital":
                        if lat is not None and lng is not None and lat != 0.0 and lng != 0.0:
                            if hit_item["_source"]["ori_name"] in g_hospital_pos_dict:
                                distance = point_distance(lng, lat,
                                                          g_hospital_pos_dict[hit_item["_source"]["ori_name"]][0],
                                                          g_hospital_pos_dict[hit_item["_source"]["ori_name"]][1])
                                if distance < 1000 * 50:
                                    if distance < 1000:
                                        if distance < 100:
                                            hit_item["_source"]["describe"] = "<100" + "米"
                                        else:
                                            hit_item["_source"]["describe"] = "约" + str(int(distance)) + "米"
                                    else:
                                        hit_item["_source"]["describe"] = "约" + str(
                                            round(1.0 * distance / 1000, 1)) + "km"
                                else:
                                    hit_item["_source"]["describe"] = ">50km"
                            else:
                                hit_item["_source"]["describe"] = ""
                        else:
                            hit_item["_source"]["describe"] = ""
                        if hit_item["_source"]["ori_name"] == query:
                            doctor_hospital_equal_query.append(hit_item["_source"])
                        elif hit_item["_source"]["describe"] == ">50km":
                            get_hospital_data_gt_50.append(hit_item["_source"])
                        else:
                            get_doctor_hospital_data.append(hit_item["_source"])

                    else:
                        if hit_item["_source"]["type_flag"] == "doctor":
                            hit_item["_source"]["describe"] = ""

                            if hit_item["_source"]["ori_name"] == query:
                                doctor_hospital_equal_query.append(hit_item["_source"])
                            else:
                                get_doctor_hospital_data.append(hit_item["_source"])
                        else:
                            if hit_item["_source"]["results_num"] > 0:
                                hit_item["_source"]["describe"] = "约" + str(
                                    hit_item["_source"]["results_num"]) + "个结果" if \
                                    hit_item["_source"]["results_num"] else ""
                                if hit_item["_source"]["ori_name"] == query:
                                    tag_equal_query.append(hit_item["_source"])
                                else:
                                    get_tag_wiki_data.append(hit_item["_source"])

            ret_list.extend(tag_equal_query)
            ret_list.extend(doctor_hospital_equal_query)
            ret_list.extend(get_tag_wiki_data)
            ret_list.extend(get_doctor_hospital_data)
            ret_list.extend(get_hospital_data_gt_50)

        return have_read_tips_set, ret_list, result_dict
    except:
        return set(), list(), list()


def recommed_service_category_device_id(device_id):
    try:
        '''
        设备品类显示, 是否命中灰度 
        '''
        categroy_select_cary1 = ["0", "1", "2", "3", "c", "d", "e", "f"]
        categroy_select_cary2 = ["4", "5", "6", "a"]
        categroy_select_cary3 = ["9", "8", "7", "b"]

        if not device_id:
            return 1

        hd_id = hashlib.md5(str(device_id).encode()).hexdigest()
        is_gray = hd_id[-1]

        if is_gray in categroy_select_cary2:
            return 2
        elif is_gray in categroy_select_cary3:
            return 3
        else:
            return 1
    except:
        return 1
