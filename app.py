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

NUM_SDM = -1
NUM_QUIZ = -1
df = pd.read_csv('https://raw.githubusercontent.com/tewei/ntuhsdm/main/QA_data.csv',sep=",")
for index, row in df.iterrows():
    r.set(f'QA:{row["N"]}:Q', row["Q"]) # question
    r.set(f'QA:{row["N"]}:A', row["A"]) # answer
    r.set(f'QA:{row["N"]}:P', row["P"]) # parent
    r.sadd(f'QA:{row["P"]}:C', row["N"]) # child
    print('### '+r.get(f'QA:{row["N"]}:Q').decode("utf-8"))

df = pd.read_csv('https://raw.githubusercontent.com/tewei/ntuhsdm/main/SDM_data.csv',sep=",")
for index, row in df.iterrows():
    r.set(f'SDM:{row["N"]}:Q', row["Q"]) # question
    r.set(f'SDM:{row["N"]}:A', row["A"]) # answer
    print('### '+r.get(f'QA:{row["N"]}:Q').decode("utf-8"))
    NUM_SDM = int(row["N"])

df = pd.read_csv('https://raw.githubusercontent.com/tewei/ntuhsdm/main/QUIZ_data.csv',sep=",")
for index, row in df.iterrows():
    r.set(f'QUIZ:{row["N"]}:Q', row["Q"]) # question
    r.set(f'QUIZ:{row["N"]}:A', row["A"]) # answer
    print('### '+r.get(f'QA:{row["N"]}:Q').decode("utf-8"))
    NUM_QUIZ = int(row["N"])

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
    message += '[88] 了解' + ' '

    return message, c_list, p_id

def gen_carousel(selection_list):
    column_list = [CarouselColumn(title=f'{s[0]}', text=f'{s[1]}', actions=[MessageTemplateAction(label=f'{s[2]}', text=s[3])]) for s in selection_list]
    carousel_template = TemplateSendMessage(
        alt_text='請選擇',
        template=CarouselTemplate(
            columns=column_list
        )
    )
    return carousel_template

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
            selection_list.append([f'{c_text}', ' ', '前往查看', str(idx+1)])

    if(p_id != '0'):
        selection_list.append(['回到上個話題', ' ', '查看上個選單', '9'])
    
    carousel_template = gen_carousel(selection_list)

    return carousel_template, q_text, a_text

def gen_SDM_flex(state):
    q_text = r.get(f'SDM:{state}:Q').decode('utf-8')
    a_text = r.get(f'SDM:{state}:A').decode('utf-8')
    choices = [{"type": "button", "style": "link", "color": "#1DB446", "action": {"type": "message", "label": '★'*i+'☆'*(5-i), "text": i}} for i in range(1,6)]
    choices += [{"type": "button", "style": "link", "color": "#1DB446", "action": {"type": "message", "label": '結束 (不會計算結果)', "text": '結束'}} ]
    contents = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": f'# {state}/{NUM_SDM}題：' + q_text, "size": "md", "weight": "bold", "wrap": True}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": a_text, "wrap": True}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": choices
        }
    }
    return contents, q_text, a_text


def gen_QUIZ_template(state):
    q_text = r.get(f'QUIZ:{state}:Q').decode('utf-8')
    a_text = r.get(f'QUIZ:{state}:A').decode('utf-8')
    
    confirm_template_message = TemplateSendMessage(
        alt_text='Confirm template',
        template=ConfirmTemplate(
            text=f'# {state}/{NUM_QUIZ}題：' + q_text,
            actions=[
                MessageAction(
                    label='O',
                    text='O'
                ),
                MessageAction(
                    label='X',
                    text='X'
                )
            ]
        )
    )

    return confirm_template_message, q_text

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
        },
       "footer": {
           "type": "box",
           "layout": "vertical",
           "contents": [
               {"type": "button", "style": "link", "color": "#1DB446", "action": {"type": "message", "label": "了解", "text": "結束"}}
           ]
       }
    }
    return contents

def get_main_buttons():
    buttons_template = TemplateSendMessage(
        alt_text='請選擇功能^^',
        template=ButtonsTemplate(
            title='認識兒童尿路逆流',
            text='您好，我是醫病共享決策chatbot，請選擇功能^^',
            actions=[
                MessageTemplateAction(
                    label='問答集',
                    text='開始問答集'
                ),
                MessageTemplateAction(
                    label='共享決策',
                    text='開始共享決策'
                ),
                MessageTemplateAction(
                    label='小測驗',
                    text='開始小測驗'
                )
            ]
        )
    )
    return buttons_template

def calculate_SDM_score(user_id):
    ans_list = []
    message = ''
    for st in range(1, NUM_SDM+1):
        score = int(r.hget(f'SDM_ans:{user_id}', st).decode('utf-8'))
        ans_list.append(score)
        message += f'第{st}題：{score}分 \n'
    if ans_list[0]+ans_list[1]+ans_list[2]+ans_list[3] < 12:
        message += '計算後您的偏好為「預防性抗生素治療」'
    elif ans_list[4]+ans_list[5]+ans_list[6] < 9:
        message += '計算後您的偏好為「玻尿酸注射」'
    else:
        message += '計算後您的偏好為「手術」'

    message += '\n請將本結果截圖後於診間與醫師討論，謝謝！'
    return message

def calculate_QUIZ_score(user_id):
    ans_list = []
    message = ''
    num_correct = 0
    for st in range(1, NUM_QUIZ+1):
        ans = r.hget(f'QUIZ_ans:{user_id}', st).decode('utf-8')
        truth = r.get(f'QUIZ:{st}:A').decode('utf-8')
        ans_list.append(ans)
        if ans == truth:
            num_correct += 1
        message += f'第{st}題 作答：{ans} 解答：{truth} \n'
        
    message += f'\n 您的分數為 {num_correct} / {NUM_QUIZ} ！'
    return message

#新好友
@handler.add(FollowEvent)
def handle_follow(event):
    profile = line_bot_api.get_profile(event.source.user_id)
    buttons_template = get_main_buttons()
    line_bot_api.push_message(profile.user_id, buttons_template)
    if r.exists(profile.user_id):
        chat_mode = r.get(f'{profile.user_id}').decode('utf-8')
        if chat_mode == 'QA':
            r.delete(f'QA_state:{profile.user_id}')
        elif chat_mode == 'SDM':
            r.delete(f'SDM_state:{profile.user_id}')
        elif chat_mode == 'QUIZ':
            r.delete(f'QUIZ_state:{profile.user_id}')
        r.delete(profile.user_id)


#新訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    profile = line_bot_api.get_profile(event.source.user_id)
    # get_message = event.message.text

    if r.get(profile.user_id) is None:
        if event.message.text == "開始問答集":
            r.set(profile.user_id, 'QA')
            r.set(f'QA_state:{profile.user_id}', 1)
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='歡迎來到問答集!!!'))

            carousel_template, q_text, a_text = gen_QA_carousel(r.get(f'QA_state:{profile.user_id}').decode('utf-8'))
            text_message = 'Q: '+ q_text + '\nA: ' + a_text
            contents = get_flex_contents(q_text, a_text)
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(text_message, contents))
            line_bot_api.push_message(profile.user_id, carousel_template)

        elif event.message.text == "開始小測驗": 
            r.set(profile.user_id, 'QUIZ')
            r.set(f'QUIZ_state:{profile.user_id}', 1)
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='歡迎挑戰小測驗!!!'))

            quiz_template, q_text = gen_QUIZ_template('1')
            line_bot_api.reply_message(event.reply_token, quiz_template)

        elif event.message.text == "開始共享決策":
            r.set(profile.user_id, 'SDM')
            r.set(f'SDM_state:{profile.user_id}', 1)
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='歡迎進行共享決策!!!'))
            
            contents, q_text, a_text = gen_SDM_flex('1')
            text_message = q_text + ' \n' + a_text
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(text_message, contents))


        else:
            buttons_template = get_main_buttons()
            line_bot_api.reply_message(event.reply_token, buttons_template)

    elif event.message.text == "結束":
        chat_mode = r.get(f'{profile.user_id}').decode('utf-8')
        if chat_mode == 'QA':
            r.delete(f'QA_state:{profile.user_id}')
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='謝謝您瀏覽問答集！'))
        elif chat_mode == 'SDM':
            r.delete(f'SDM_state:{profile.user_id}')
            if r.exists(f'SDM_ans:{profile.user_id}'):
                r.delete(f'SDM_ans:{profile.user_id}')
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='謝謝您參與尿路逆流醫病共享決策！'))
        elif chat_mode == 'QUIZ':
            r.delete(f'QUIZ_state:{profile.user_id}')
            if r.exists(f'QUIZ_ans:{profile.user_id}'):
                r.delete(f'QUIZ_ans:{profile.user_id}')
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='謝謝您參與小測驗！'))
        r.delete(profile.user_id)
        line_bot_api.push_message(profile.user_id, TextSendMessage(text='若尚有不清楚的問題，請主動向醫療人員說出您的疑慮或擔心的事情！'))
        buttons_template = get_main_buttons()
        line_bot_api.reply_message(event.reply_token, buttons_template)

    elif r.exists(profile.user_id):
        chat_mode = r.get(f'{profile.user_id}').decode('utf-8')
        if chat_mode == 'QA':
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
            
            carousel_template, q_text, a_text = gen_QA_carousel(r.get(f'QA_state:{profile.user_id}').decode('utf-8'))
            text_message = 'Q: '+ q_text + '\nA: ' + a_text
            contents = get_flex_contents(q_text, a_text)
            line_bot_api.reply_message(event.reply_token, FlexSendMessage(text_message, contents))
            line_bot_api.push_message(profile.user_id, carousel_template)

        elif chat_mode == 'SDM':
            SDM_state = int(r.get(f'SDM_state:{profile.user_id}').decode('utf-8'))
            
            if int(event.message.text) > 0 and int(event.message.text) <= 5:
                choice = int(event.message.text)
                r.hset(f'SDM_ans:{profile.user_id}', SDM_state, choice)
                if SDM_state == NUM_SDM:
                    # 回傳結果
                    message = calculate_SDM_score(profile.user_id)
                    contents = get_flex_contents("共享決策回答結果", message)
                    text_message = message
                    
                else:
                    r.set(f'SDM_state:{profile.user_id}', SDM_state + 1)
                    contents, q_text, a_text = gen_SDM_flex(str(SDM_state + 1))
                    text_message = q_text + ' \n' + a_text
                
                line_bot_api.reply_message(event.reply_token, FlexSendMessage(text_message, contents))
                
            else:
                reply = TextSendMessage(text= f"麻煩再選一次唷~")
                line_bot_api.reply_message(event.reply_token, reply)
                return

        elif chat_mode == 'QUIZ':
            QUIZ_state = int(r.get(f'QUIZ_state:{profile.user_id}').decode('utf-8'))
            
            if event.message.text == 'O' or event.message.text == 'X':               
                r.hset(f'QUIZ_ans:{profile.user_id}', QUIZ_state, event.message.text)
                if QUIZ_state == NUM_QUIZ:
                    # 回傳結果
                    message = calculate_QUIZ_score(profile.user_id)
                    contents = get_flex_contents("測驗回答結果", message)
                    text_message = message
                    line_bot_api.reply_message(event.reply_token, FlexSendMessage(text_message, contents))
                else:
                    r.set(f'QUIZ_state:{profile.user_id}', QUIZ_state + 1)
                    quiz_template, q_text = gen_QUIZ_template(str(QUIZ_state + 1))
                    line_bot_api.reply_message(event.reply_token, quiz_template)
                
            else:
                reply = TextSendMessage(text= f"麻煩再選一次唷~")
                line_bot_api.reply_message(event.reply_token, reply)
                return
    
    # if event.message.text.lower() == "98":
    #     if r.get(profile.user_id) is None:
    #         r.set(profile.user_id, 0)
    #         r.set(f'QA_state:{profile.user_id}', 1)
    #         print('###')
    #         print(profile.user_id, r.get(f'QA_state:{profile.user_id}'))

    #         line_bot_api.push_message(profile.user_id, TextSendMessage(text='歡迎!!!'))
    #         # message, c_list, p_id = gen_QA_message(r.get(f'QA_state:{profile.user_id}').decode('utf-8'))
    #         # reply = TextSendMessage(text=message)
    #         # line_bot_api.reply_message(event.reply_token, reply)

    #         carousel_template, q_text, a_text = gen_QA_carousel(r.get(f'QA_state:{profile.user_id}').decode('utf-8'))
    #         text_message = 'Q: '+ q_text + '\nA: ' + a_text
    #         contents = get_flex_contents(q_text, a_text)
    #         # line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text_message))
    #         line_bot_api.reply_message(event.reply_token, FlexSendMessage(text_message, contents))
    #         line_bot_api.push_message(profile.user_id, carousel_template)
    #     else:
    #         line_bot_api.reply_message(event.reply_token, TextSendMessage(text='對話進行中'))
    
    # elif r.exists(profile.user_id) and event.message.text.lower() != "88":
    #     message, c_list, p_id = gen_QA_message(r.get(f'QA_state:{profile.user_id}').decode('utf-8'))
    #     if int(event.message.text) > 0 and int(event.message.text) <= len(c_list):
    #         choice = int(event.message.text)
    #         r.set(f'QA_state:{profile.user_id}', c_list[choice-1])
    #     elif int(event.message.text) == 9 and p_id != '0':
    #         r.set(f'QA_state:{profile.user_id}', p_id)
    #     else:
    #         reply = TextSendMessage(text= f"麻煩再選一次唷~")
    #         line_bot_api.reply_message(event.reply_token, reply)
    #         return
        
    #     # message, c_list, p_id = gen_QA_message(r.get(f'QA_state:{profile.user_id}').decode('utf-8'))
    #     # reply = TextSendMessage(text=message)
    #     # line_bot_api.reply_message(event.reply_token, reply)

    #     carousel_template, q_text, a_text = gen_QA_carousel(r.get(f'QA_state:{profile.user_id}').decode('utf-8'))
    #     text_message = 'Q: '+ q_text + '\nA: ' + a_text
    #     contents = get_flex_contents(q_text, a_text)
    #     # line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text_message))
    #     line_bot_api.reply_message(event.reply_token, FlexSendMessage(text_message, contents))
    #     line_bot_api.push_message(profile.user_id, carousel_template)
        

    # elif event.message.text.lower() == "88":
    #     if r.get(profile.user_id) is None:
    #         line_bot_api.push_message(profile.user_id, TextSendMessage(text='QAQ'))
    #         line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請輸入：98 開始對話^^'))
    #     else:
    #         r.delete(profile.user_id)
    #         r.delete(f'QA_state:{profile.user_id}')
    #         line_bot_api.push_message(profile.user_id, TextSendMessage(text='再會~'))
    #         line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請輸入：98 開始對話^^'))
    # elif event.message.text.lower() == "87":
    #     buttons_template = TemplateSendMessage(
    #         alt_text='Buttons Template',
    #         template=ButtonsTemplate(
    #             title='這是ButtonsTemplate',
    #             text='ButtonsTemplate可以傳送text,uri',
    #             # thumbnail_image_url='https://ntumed.github.io/images/logo01.png',
    #             actions=[
    #                 MessageTemplateAction(
    #                     label='ButtonsTemplate',
    #                     text='ButtonsTemplate'
    #                 ),
    #                 PostbackTemplateAction(
    #                     label='postback',
    #                     text='postback text',
    #                     data='postback1'
    #                 )
    #             ]
    #         )
    #     )
    #     line_bot_api.reply_message(event.reply_token, buttons_template)
    # elif event.message.text.lower() == "86":
    #     carousel_template = TemplateSendMessage(
    #         alt_text='Carousel template',
    #         template=CarouselTemplate(
    #             columns=[
    #                 CarouselColumn(
    #                     title='this is menu1',
    #                     text='description1',
    #                     actions=[
    #                         PostbackTemplateAction(
    #                             label='postback1',
    #                             text='postback text1',
    #                             data='action=buy&itemid=1'
    #                         ),
    #                         MessageTemplateAction(
    #                             label='message1',
    #                             text='message text1'
    #                         )
    #                     ]
    #                 ),
    #                 CarouselColumn(
    #                     title='this is menu2',
    #                     text='description2',
    #                     actions=[
    #                         PostbackTemplateAction(
    #                             label='postback2',
    #                             text='postback text2',
    #                             data='action=buy&itemid=2'
    #                         ),
    #                         MessageTemplateAction(
    #                             label='message2',
    #                             text='message text2'
    #                         )
    #                     ]
    #                 )
    #             ]
    #         )
    #     )
    #     line_bot_api.reply_message(event.reply_token, carousel_template)    
    
    else:
        buttons_template = get_main_buttons()
        line_bot_api.reply_message(event.reply_token, buttons_template)
        # buttons_template = TemplateSendMessage(
        #     alt_text='請選擇功能^^',
        #     template=ButtonsTemplate(
        #         title='認識兒童尿路逆流',
        #         text='您好，我是醫病共享決策chatbot，請選擇功能^^',
        #         # thumbnail_image_url='https://ntumed.github.io/images/logo01.png',
        #         actions=[
        #             MessageTemplateAction(
        #                 label='問答集',
        #                 text='START QA'
        #             ),
        #             MessageTemplateAction(
        #                 label='共享決策',
        #                 text='START SDM'
        #             ),
        #             MessageTemplateAction(
        #                 label='小測驗',
        #                 text='START QUIZ'
        #             )
        #             # PostbackTemplateAction(
        #             #     label='postback',
        #             #     text='postback text',
        #             #     data='postback1'
        #             # )
        #         ]
        #     )
        # )
        # line_bot_api.reply_message(event.reply_token, buttons_template)
        # line_bot_api.reply_message(event.reply_token, TextSendMessage(text='請輸入：98 開始對話^^'))

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
