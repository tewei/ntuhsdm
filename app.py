import os
from datetime import datetime

from flask import Flask, abort, request

import redis

# https://github.com/line/line-bot-sdk-python
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("CHANNEL_SECRET"))
r = redis.from_url(os.environ.get("REDIS_URL"))


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


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    profile = line_bot_api.get_profile(event.source.user_id)
    get_message = event.message.text

    
    if event.message.text.lower() == "start":
        if r.get(profile.user_id) is None:
            r.set(profile.user_id, 0)
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='歡迎'))
        else:
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='已經註冊'))
    
    if event.message.text.lower() == "end":
        if r.get(profile.user_id) is None:
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='錯誤'))
        else:
            r.delete(profile.user_id)
            line_bot_api.push_message(profile.user_id, TextSendMessage(text='再會'))


    # Send To Line
    reply = TextSendMessage(text= f"{get_message}")
    line_bot_api.reply_message(event.reply_token, reply)
    line_bot_api.push_message(profile.user_id, TextSendMessage(text='您好~~'))




