#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, absolute_import, print_function
import traceback
import json
from libs.tools import json_http_response
from libs.cache import redis_client
import threading
import time
import openai
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)


user_id_chat_msg_dict = dict()

openai.api_key="" #配置添加：需要填写自己的openAI api_key

g_user_read = {}

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def completion_with_backoff(openai_messages):
    return openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=openai_messages,
            #prompt=content,
            #max_tokens=193,
            temperature=0,
            stream=True
    )


def stream_generate_response(user_id,query,openai_messages):
    redis_key="zn_chat:"+str(user_id)+":"+str(query)
    try:
        start_time=time.time()

        completion = completion_with_backoff(openai_messages)

   
        start_time=time.time() 
        completion_text = ""
        for event in  completion:
            if "content" in event['choices'][0]['delta']:
                completion_text += event['choices'][0]['delta']["content"]
                cur_time=time.time()
                if "\n" in event['choices'][0]['delta']["content"] or cur_time-start_time>=3:
                    if len(completion_text)>len("\n\n"):
                        redis_client.lpush(redis_key,completion_text)           
                        completion_text=""
                        start_time=time.time()
            if completion_text and not event['choices'][0]['delta']:
                redis_client.lpush(redis_key,completion_text)
                completion_text="" 
                start_time=time.time()
        redis_client.lpush(redis_key,"#znzb_q_end#")
    except:
        redis_client.lpush(redis_key,"当前请求人数过多，请稍后重试~~")
        redis_client.lpush(redis_key,"#znzb_q_end#")
    

def chat_complete(request):
    try:
        q = request.POST.get('q', '').strip()
        user_id = request.POST.get('user_id', None).strip()

        if not q:
            return json_http_response({'res': "查询内容不能为空!", 'ending': 1})

        role_key_str="角色扮演"
        if q.startswith(role_key_str):
            system_msg = q[len(role_key_str):]
            system_msg=system_msg.strip(" ")
            system_msg=system_msg.strip(":")
            system_msg=system_msg.strip("\n")
            system_msg=system_msg.strip("：")
            if system_msg:
                user_id_chat_msg_dict[user_id]=[{"role": "system", "content":system_msg}]
            return json_http_response({"res":"好的,已开始角色扮演","ending":1,'msg': 'success'})
        elif q=="结束":
            user_id_chat_msg_dict[user_id]=[] 
            return json_http_response({"res":"好的,已结束角色扮演","ending":1,'msg': 'success'})
 
        redis_key="zn_chat:"+str(user_id)+":"+str(q)
        lock_redis_key="lock_zn_chat:"+str(user_id)+":"+str(q)
        if not redis_client.exists(lock_redis_key):
            if user_id in user_id_chat_msg_dict and len(user_id_chat_msg_dict[user_id])>0:
                user_id_chat_msg_dict[user_id].append({"role":"user","content":q})
            else:
                user_id_chat_msg_dict[user_id] = [{"role":"user","content":q}]
            redis_client.set(lock_redis_key,1,ex=60*30)
            t = threading.Thread(target=stream_generate_response, args=(user_id,q,user_id_chat_msg_dict[user_id],)) 
            t.start()

        res=""
        ending=0
        redis_str=""
        while True:
            tmp = redis_client.rpop(redis_key)
            if not tmp:
                break
            else:
                tmp = str(tmp,encoding="utf8") 
                if tmp == "#znzb_q_end#":
                    ending=1
                    redis_client.delete(lock_redis_key)
                else:
                    redis_str += tmp
                    
        if redis_str:
            if user_id in user_id_chat_msg_dict and len(user_id_chat_msg_dict[user_id])>0:
                latest_chat_item = user_id_chat_msg_dict[user_id][-1]
                if latest_chat_item["role"]!="assistant":
                    user_id_chat_msg_dict[user_id].append({"role":"assistant","content":redis_str})
                else:
                    user_id_chat_msg_dict[user_id][-1]["content"] += redis_str

            if len(user_id_chat_msg_dict[user_id])>10:
                user_id_chat_msg_dict[user_id] = user_id_chat_msg_dict[user_id][-4:]
            res = redis_str.replace("\n","<br/>")

        result = {
            'res': res,
            'ending': ending,
            'msg': 'success'
        }

        return json_http_response(result)
    except:
        return json_http_response({'res': traceback.format_exc(), 'ending': 1, 'msg':"error"})
