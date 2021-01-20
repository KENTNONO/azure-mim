import os
import sys

import speech_recognition as sr

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, Event, FollowEvent, UnfollowEvent,
    AudioMessage, ImageMessage, AudioSendMessage

)

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials
import os, requests, uuid, json
import urllib

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = ''
channel_access_token = ''

if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)




##為了測試是否有收到音
def transcribe(wav_path):
    '''
    Speech to Text by Google free API
    language: en-US, zh-TW
    '''
    
    r = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = r.record(source)
    try:
        return r.recognize_google(audio, language="zh-TW")
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))
    return None

##line 進入點
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

##文字輸入
@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text)
    )
##圖片輸入
@handler.add(MessageEvent,message=ImageMessage)
def audio_event(event):
    print('audio')
    print(event)
    message_content = line_bot_api.get_message_content(event.message.id)
    
    with open('./recordimage.jpg', 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)
    
    subscription_key_pic = ''
    endpoint_pic = ''
    computervision_client_pic = ComputerVisionClient(endpoint_pic, CognitiveServicesCredentials(subscription_key_pic))
    tags_result_remote_pic = ''
    with open('./recordimage.jpg', "rb") as fi:
        tags_result_remote_pic= computervision_client_pic.tag_image_in_stream(fi)

    #把文字存下來
    tags_name_pic1 = tags_result_remote_pic.tags[0].name
    tags_name_pic2 = tags_result_remote_pic.tags[1].name

    #翻譯文字
    # -*- coding: utf-8 -*-
    subscription_key_text = '' # your key
    endpoint_text = ''
    path_text = '/translate?api-version=3.0'

    paramsh_text = '&to=zh-Hant'#中文
    
    constructed_url = endpoint_text + path_text + paramsh_text
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key_text,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    #第一段的文字
    body1 = [{
        'text': tags_name_pic1
    }]

    request1 = requests.post(constructed_url, headers=headers, json=body1)
    response1 = request1.json()
    print(response1)
    text_output1 = response1[0]["translations"][0]["text"]

    #第二段的文字
    body2 = [{
        'text': tags_name_pic2
    }]

    request2 = requests.post(constructed_url, headers=headers, json=body2)
    response2 = request2.json()

    text_output2 = response2[0]["translations"][0]["text"]

    #把他們全部都連接再一起
    output = tags_name_pic1+" "+text_output1+" "+tags_name_pic2+" "+text_output2
    output_url =  urllib.parse.quote(output)
    url = 'https://google-translate-proxy.herokuapp.com/api/tts?query={}&language=zh-tw'.format(output_url)
    line_bot_api.reply_message(
        event.reply_token,
        AudioSendMessage(original_content_url=url,duration=10000)
    )
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=tags_name_pic1+':'+tags_name_pic2)
    )

##音訊輸入
@handler.add(MessageEvent,message=AudioMessage)
def image_event(event):
    print('audio')
    print(event)
    name_mp3 = 'recording.mp3'
    name_wav = 'recording.wav'
    message_content = line_bot_api.get_message_content(event.message.id)

    with open('./'+name_mp3, 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)
    # line_bot_api.reply_message(
    #     event.reply_token,
    #     AudioSendMessage(original_content_url='https://www.sample-videos.com/audio/mp3/crowd-cheering.mp3',duration=10000)
    # )
    ##測試用
    # os.system('ffmpeg -y -i ' + name_mp3 + ' ' + name_wav + ' -loglevel quiet')
    # text = transcribe(name_wav)
    # print('Transcribe:', text)

##剛加入、解黑名單
@handler.add(FollowEvent)
def follow_event(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='歡迎')
    )
    print(event)
##黑名單
@handler.add(UnfollowEvent)
def unfollow_event(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='掰掰')
    )
    print(event)


if __name__ == "__main__":
    # arg_parser = ArgumentParser(
    #     usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    # )
    # arg_parser.add_argument('-p', '--port', default=8000, help='port')
    # arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    # options = arg_parser.parse_args()
    # app.run(debug=options.debug, port=options.port)
    app.run()




