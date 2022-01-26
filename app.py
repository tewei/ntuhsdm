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
    
    print('### '+r.get(f'QA:{row["N"]}:Q').decode("utf-8"))

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
        print(f'QA:{state}:Q')
        return message, [], -1
    q_text = r.get(f'QA:{state}:Q').decode('utf-8')
    a_text = r.get(f'QA:{state}:A').decode('utf-8')
    p_id = r.get(f'QA:{state}:P').decode('utf-8')
    message = q_text + ' \n' + a_text + ' \n'
    c_list = []
    if r.smembers(f'QA:{state}:C') is None:
        pass
    else:
        c_list = list(r.smembers(f'QA:{state}:C'))
        for idx, child in enumerate(c_list):
            c_text = r.get(f'QA:{child.decode("utf-8")}:Q').decode('utf-8')
            message += f'[{idx+1}] {c_text}' + ' \n'

    if(p_id != '0'):
        message += '[9] 回到上個話題' + ' \n'
    message += '[88] 結束本次對話' + ' '

    return message, c_list, p_id

def gen_QA_carousel(state):
    message = ''
    if r.get(f'QA:{state}:Q') is None:
        message = 'OAO'
        print(f'QA:{state}:Q')
        return message, [], -1
    q_text = r.get(f'QA:{state}:Q').decode('utf-8')
    a_text = r.get(f'QA:{state}:A').decode('utf-8')
    # text_message = 'Q: '+ q_text + '\nA: ' + a_text
    p_id = r.get(f'QA:{state}:P').decode('utf-8')
   
    selection_list = []
    if r.smembers(f'QA:{state}:C') is None:
        pass
    else:
        c_list = list(r.smembers(f'QA:{state}:C'))
        for idx, child in enumerate(c_list):
            c_text = r.get(f'QA:{child.decode("utf-8")}:Q').decode('utf-8')
            # button_list.append([f'[{idx+1}] {c_text}', idx+1])
            selection_list.append([f'{c_text}', idx+1])

    if(p_id != '0'):
        selection_list.append(['回到上個話題', 9])
    selection_list.append(['結束本次對話', 88])
    
    column_list = [CarouselColumn(title=f'[{btn[1]}] {btn[0]}', text=' ', actions=[MessageTemplateAction(label='選擇', text=btn[1])]) for btn in selection_list]

    carousel_template = TemplateSendMessage(
        alt_text='選擇',
        template=CarouselTemplate(
            columns=column_list
        )
    )

    return carousel_template, q_text, a_text

def get_flex_contents(title, text):
    contents ={"type": "bubble",
               "header": {
                   "type": "box",
                   "layout": "horizontal",
                   "contents": [
                       {"type": "text", "text": title, "size": "md", "weight": "bold", "wrap": True}
                    #    {"type": "text", "text": translate, "size": "lg", "color": "#888888", "align": "end", "gravity": "bottom"}
                   ]
               },
            #    "hero": {
            #        "type": "image",
            #        "url": random_img_url,
            #        "size": "full",
            #        "aspect_ratio": "20:13",
            #        "aspect_mode": "cover"
            #    },
               "body": {
                   "type": "box",
                   "layout": "vertical",
                #    "spacing": "md",
                   "contents": [
                       {"type": "text", "text": text, "wrap": True}
                   ]
               }
            #    "footer": {
            #        "type": "box",
            #        "layout": "vertical",
            #        "contents": [
            #            {"type": "spacer", "size": "md"},
            #            {"type": "button", "style": "primary", "color": "#1DB446",
            #             "action": {"type": "uri", "label": "GO", "uri": random_img_url}}
            #        ]
            #    }
              }
    return contents



@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    profile = line_bot_api.get_profile(event.source.user_id)
    # get_message = event.message.text

    
    if event.message.text.lower() == "98":
        if r.get(profile.user_id) is None:
            r.set(profile.user_id, 0)
            r.set(f'QA_state:{profile.user_id}', 1)
            print('###')
            print(profile.user_id, r.get(f'QA_state:{profile.user_id}'))

            line_bot_api.push_message(profile.user_id, TextSendMessage(text='歡迎!!!'))
            # message, c_list, p_id = gen_QA_message(r.get(f'QA_state:{profile.user_id}').decode('utf-8'))
            # reply = TextSendMessage(text=message)
            # line_bot_api.reply_message(event.reply_token, reply)

            carousel_template, q_text, a_text = gen_QA_carousel(r.get(f'QA_state:{profile.user_id}').decode('utf-8'))
            text_message = 'Q: '+ q_text + '\nA: ' + a_text
            contents = get_flex_contents(q_text, a_text)
            # line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text_message))
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(text_message, contents))
            line_bot_api.push_message(profile.user_id, carousel_template)
            

        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='對話進行中'))
    
    elif r.exists(profile.user_id) and event.message.text.lower() != "88":
        message, c_list, p_id = gen_QA_message(r.get(f'QA_state:{profile.user_id}').decode('utf-8'))
        if int(event.message.text) > 0 and int(event.message.text) <= len(c_list):
            choice = int(event.message.text)
            r.set(f'QA_state:{profile.user_id}', c_list[choice-1])
        elif int(event.message.text) == 9 and p_id != '0':
            r.set(f'QA_state:{profile.user_id}', p_id)
        else:
            reply = TextSendMessage(text= f"麻煩再選一次唷~")
            line_bot_api.reply_message(event.reply_token, reply)
            return
        
        # message, c_list, p_id = gen_QA_message(r.get(f'QA_state:{profile.user_id}').decode('utf-8'))
        # reply = TextSendMessage(text=message)
        # line_bot_api.reply_message(event.reply_token, reply)

        carousel_template, q_text, a_text = gen_QA_carousel(r.get(f'QA_state:{profile.user_id}').decode('utf-8'))
        text_message = 'Q: '+ q_text + '\nA: ' + a_text
        contents = get_flex_contents(q_text, a_text)
        # line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text_message))
        line_bot_api.reply_message(event.reply_token, FlexSendMessage(text_message, contents))
        line_bot_api.push_message(profile.user_id, carousel_template)
        

    elif event.message.text.lower() == "88":
        if r.get(profile.user_id) is None:
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='QAQ'))
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請輸入：98 開始對話^^'))
        else:
            r.delete(profile.user_id)
            r.delete(f'QA_state:{profile.user_id}')
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='再會~'))
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請輸入：98 開始對話^^'))
    elif event.message.text.lower() == "87":
        buttons_template = TemplateSendMessage(
            alt_text='Buttons Template',
            template=ButtonsTemplate(
                title='這是ButtonsTemplate',
                text='ButtonsTemplate可以傳送text,uri',
                # thumbnail_image_url='https://ntumed.github.io/images/logo01.png',
                actions=[
                    MessageTemplateAction(
                        label='ButtonsTemplate',
                        text='ButtonsTemplate'
                    ),
                    PostbackTemplateAction(
                        label='postback',
                        text='postback text',
                        data='postback1'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
    elif event.message.text.lower() == "86":
        carousel_template = TemplateSendMessage(
            alt_text='Carousel template',
            template=CarouselTemplate(
                columns=[
                    CarouselColumn(
                        title='this is menu1',
                        text='description1',
                        actions=[
                            PostbackTemplateAction(
                                label='postback1',
                                text='postback text1',
                                data='action=buy&itemid=1'
                            ),
                            MessageTemplateAction(
                                label='message1',
                                text='message text1'
                            )
                        ]
                    ),
                    CarouselColumn(
                        title='this is menu2',
                        text='description2',
                        actions=[
                            PostbackTemplateAction(
                                label='postback2',
                                text='postback text2',
                                data='action=buy&itemid=2'
                            ),
                            MessageTemplateAction(
                                label='message2',
                                text='message text2'
                            )
                        ]
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, carousel_template)    
    
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請輸入：98 開始對話^^'))

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
    sticker_ids = [(11538, 51626494), (11538, 51626499), (11538, 51626501), (11539, 52114115), (11539, 52114122), (11539, 52114129), (11539, 52114118), (11539, 52114131), (11537, 52002734), (11537, 52002738), (11537, 52002768), (11537, 52002735)]
    index_id = random.randint(0, len(sticker_ids) - 1)
    sticker_message = StickerSendMessage(package_id=str(sticker_ids[index_id][0]), sticker_id=str(sticker_ids[index_id][1]))
    line_bot_api.reply_message(event.reply_token, sticker_message)
