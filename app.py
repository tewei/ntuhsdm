import os
from datetime import datetime

from flask import Flask, abort, request

import os
import json

# https://github.com/line/line-bot-sdk-python
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("CHANNEL_SECRET"))



user_data = {}
if os.path.isfile('user_data.data'):
    with open('user_data.data') as json_file:
        user_data = json.load(json_file)
else:
    with open('user_data.data') as json_file:
        json.dump(user_data, json_file)



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
    get_message = event.message.text

    profile = line_bot_api.get_profile(user_id)

    # Send To Line
    reply = TextSendMessage(text=f"{get_message}")
    line_bot_api.reply_message(event.reply_token, reply)

    reply = TextSendMessage(text=profie.user_id)
    line_bot_api.reply_message(event.reply_token, reply)
