import os
from datetime import datetime
import random
import csv

from flask import Flask, abort, request
import redis
import pandas as pd

# https://github.com/line/line-bot-sdk-python
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("CHANNEL_SECRET"))
r = redis.from_url(os.environ.get("REDIS_URL"))


df = pd.read_csv('https://raw.githubusercontent.com/tewei/ntuhsdm/main/QA_data.csv',sep=",")
for index, row in df.iterrows():
    r.set(f'QA:{row["N"]}:Q', row["Q"]) # question
    r.set(f'QA:{row["N"]}:A', row["A"]) # answer
    r.set(f'QA:{row["N"]}:P', row["P"]) # parent
    r.sadd(f'QA:{row["P"]}:C', row["N"]) # child

@app.route("/", methods=["GET", "POST"])
def callback():

    if request.method == "GET":
        return "<h1> NTUH SDM Chatbot </h1> <h2> LINE ID: @867yrtyy </h2>"
    if request.method == "POST":
        signature = request.headers["X-Line-Signature"]
        body = request.get_data(as_text=True)

        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            abort(400)

        return "OK"

def gen_QA_message(state):
    message = ''
    if r.get(f'QA:{state}:Q') is None:
        message = 'OAO'
        return message, [], -1
    q_text = r.get(f'QA:{state}:Q')
    a_text = r.get(f'QA:{state}:A')
    p_id = r.get(f'QA:{state}:P')
    message = q_text + ' %0D%0A ' + a_text + ' %0D%0A '
    c_list = []
    if r.smembers(f'QA:{row[3]}:C') is None:
        pass
    else:
        c_list = list(r.smembers(f'QA:{row[3]}:C'))
        for idx, child in enumerate(c_list):
            c_text = r.get(f'QA:{child}:Q')
            message += f'[{idx+1}] {c_text}' + ' %0D%0A '

    if(p_id != '0'):
        message += '[9] 回到上個話題' + ' %0D%0A '
    message += 'end 結束本次對話' + ' %0D%0A '

    return message, c_list, p_id

    

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    profile = line_bot_api.get_profile(event.source.user_id)
    # get_message = event.message.text

    
    if event.message.text.lower() == "start":
        if r.get(profile.user_id) is None:
            r.set(profile.user_id, str(0))
            r.set(f'QA_state:{profile.user_id}', str(1))

            line_bot_api.push_message(profile.user_id, TextSendMessage(text='歡迎'))
            message, c_list, p_id = gen_QA_message(str(r.get(f'QA_state:{profile.user_id}')))
            
            reply = TextSendMessage(text=message)
            line_bot_api.reply_message(event.reply_token, reply)
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='對話進行中'))
    
    elif r.exists(profile.user_id) and event.message.text.lower() != "end":
        message, c_list, p_id = gen_QA_message(str(r.get(f'QA_state:{profile.user_id}')))
        if int(event.message.text) > 0 and int(event.message.text) <= len(c_list):
            choice = int(event.message.text)
            r.set(f'QA_state:{profile.user_id}', c_list[choice-1])
        elif int(event.message.text) == 9 and p_id != '0':
            r.set(f'QA_state:{profile.user_id}', p_id)
        else:
            reply = TextSendMessage(text= f"麻煩再選一次唷")
            line_bot_api.reply_message(event.reply_token, reply)
            return
        
        message, c_list, p_id = gen_QA_message(r.get(f'QA_state:{profile.user_id}'))
        reply = TextSendMessage(text=message)
        line_bot_api.reply_message(event.reply_token, reply)

    elif event.message.text.lower() == "end":
        if r.get(profile.user_id) is None:
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='QQ'))
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請輸入：start 開始對話'))
        else:
            r.delete(profile.user_id)
            r.delete(f'QA_state:{profile.user_id}')
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='再會'))
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請輸入：start 開始對話'))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請輸入：start 開始對話'))

    # Send To Line
    
    # Usage: 
    # reply = TextSendMessage(text= f"{get_message}")
    # line_bot_api.reply_message(event.reply_token, reply)
    # line_bot_api.push_message(profile.user_id, TextSendMessage(text='Hello'))




@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker_message(event):
    print("package_id:", event.message.package_id)
    print("sticker_id:", event.message.sticker_id)
    # ref. https://developers.line.me/media/messaging-api/sticker_list.pdf
    sticker_ids = [(11538, 51626494), (11538, 51626499), (11538, 51626500), (11538, 51626501), (11539, 52114110), (11539, 52114113), (11538, 52114115), (11539, 52114122), (11539, 52114123), (11539, 52114129), (11539, 52114118), (11539, 52114131), (11539, 52114117)]
    index_id = random.randint(0, len(sticker_ids) - 1)
    sticker_message = StickerSendMessage(package_id=str(sticker_ids[index_id][0]), sticker_id=str(sticker_ids[index_id][1]))
    line_bot_api.reply_message(event.reply_token, sticker_message)
