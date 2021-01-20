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

# import for database
import sqlite3

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from msrest.authentication import CognitiveServicesCredentials


# connect to database
connect = sqlite3.connect('guest.db',check_same_thread=False)
cursor = connect.cursor()


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

check = ['@地標','@物品','@商標']

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
    print(event.source)
    print(event.source.user_id)
    checking = True
    for i in range(len(check)):
        if event.message.text == check[i]:
            checking = False
            getId = cursor.execute('''SELECT count(1) FROM reservation WHERE user_id = ?''',[event.source.user_id]).fetchall()[0][0]
            print(getId)
            if getId >0:
                cursor.execute('''UPDATE reservation SET action = ? WHERE user_id = ?''',(i,event.source.user_id))
            else:
                cursor.execute('''INSERT INTO reservation (user_id,action) VALUES (?,?)''',(event.source.user_id,i))
                connect.commit()
    if checking:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='請選擇正確的標示')
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='選擇成功')
        )

##圖片輸入
@handler.add(MessageEvent,message=ImageMessage)
def audio_event(event):
    print('audio')
    print(event)
    get_act = 1
    try:
        get_act = cursor.execute('''SELECT action FROM reservation WHERE user_id = ?''',[event.source.user_id]).fetchall()[0][0]
    except Exception as e:
        print(e)
    print(type(get_act))
    message_content = line_bot_api.get_message_content(event.message.id)
    
    with open('./recordimage.jpg', 'wb') as fd:
        for chunk in message_content.iter_content():
            fd.write(chunk)
    if get_act == '1':
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
        endpoint_text = 'https://api.cognitive.microsofttranslator.com/'
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
            [AudioSendMessage(original_content_url=url,duration=10000),
            TextSendMessage(text=tags_name_pic1+':'+tags_name_pic2),
            TextSendMessage(text=text_output1+':'+text_output2)]
        )
    elif get_act == '0':
        subscription_key_pic = ''
        endpoint_pic = ''
        # Call API
        computervision_client = ComputerVisionClient(endpoint_pic, CognitiveServicesCredentials(subscription_key_pic))

        # Call API
        with open('./recordimage.jpg', "rb") as fi:
            description_results = computervision_client.describe_image_in_stream(fi)

        tags_name_pic = description_results.captions[0].text

        #翻譯文字
        #翻譯
        # -*- coding: utf-8 -*-
        subscription_key_text = '' # your key
        endpoint_text = 'https://api.cognitive.microsofttranslator.com/'
        path_text = '/translate?api-version=3.0'

        paramsh_text = '&to=zh-Hant'#中文
        constructed_url = endpoint_text + path_text + paramsh_text

        headers = {
            'Ocp-Apim-Subscription-Key': subscription_key_text,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }

        body = [{
            'text': tags_name_pic
        }]

        request = requests.post(constructed_url, headers=headers, json=body)
        response = request.json()

        text_output = response[0]["translations"][0]["text"]
        #把他們全部都連接再一起
        output = tags_name_pic+" "+text_output
        output_url =  urllib.parse.quote(output)
        url = 'https://google-translate-proxy.herokuapp.com/api/tts?query={}&language=zh-tw'.format(output_url)


        line_bot_api.reply_message(
            event.reply_token,
            [AudioSendMessage(original_content_url=url,duration=10000),
            TextSendMessage(text=tags_name_pic),
            TextSendMessage(text=text_output)]
        )
    elif get_act=='2':
        
        subscription_key_pic = ''
        endpoint_pic = ''
        # Call API
        #BaseException品牌辨識


        computervision_client = ComputerVisionClient(endpoint_pic, CognitiveServicesCredentials(subscription_key_pic))

        remote_image_features = ["brands"]
        with open('./recordimage.jpg', "rb") as fi:
            # description_results = computervision_client.describe_image_in_stream(fi)
            detect_brands_results_remote = computervision_client.analyze_image_in_stream(fi, remote_image_features)

        tags_name_pic = detect_brands_results_remote.brands[0].name

        #翻譯文字
        #翻譯
        # -*- coding: utf-8 -*-
        subscription_key_text = 'd0ae49b334194d028d97b5ecb802b761' # your key
        endpoint_text = 'https://api.cognitive.microsofttranslator.com/'
        path_text = '/translate?api-version=3.0'

        paramsh_text = '&to=zh-Hant'#中文
        constructed_url = endpoint_text + path_text + paramsh_text

        headers = {
            'Ocp-Apim-Subscription-Key': subscription_key_text,
            'Content-type': 'application/json',
            'X-ClientTraceId': str(uuid.uuid4())
        }

        body = [{
            'text': tags_name_pic
        }]

        request = requests.post(constructed_url, headers=headers, json=body)
        response = request.json()

        text_output = response[0]["translations"][0]["text"]


        #把他們全部都連接再一起
        output = tags_name_pic+" "+text_output
        output_url =  urllib.parse.quote(output)
        url = 'https://google-translate-proxy.herokuapp.com/api/tts?query={}&language=zh-tw'.format(output_url)

        line_bot_api.reply_message(
            event.reply_token,
            [AudioSendMessage(original_content_url=url,duration=10000),
            TextSendMessage(text=tags_name_pic),
            TextSendMessage(text=text_output)]
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


# def insert(id,act):

def object_thing():
    subscription_key_pic = '29e7f8d0f2534f9bba4a014dd550803c'
    endpoint_pic = 'https://tibame666.cognitiveservices.azure.com/'
    computervision_client_pic = ComputerVisionClient(endpoint_pic, CognitiveServicesCredentials(subscription_key_pic))
    tags_result_remote_pic = ''
    with open('./recordimage.jpg', "rb") as fi:
        tags_result_remote_pic= computervision_client_pic.tag_image_in_stream(fi)

    #把文字存下來
    tags_name_pic1 = tags_result_remote_pic.tags[0].name
    tags_name_pic2 = tags_result_remote_pic.tags[1].name

    #翻譯文字
    # -*- coding: utf-8 -*-
    subscription_key_text = '4ef67f6abd204ea9a9124dd4a74edd37' # your key
    endpoint_text = 'https://api.cognitive.microsofttranslator.com/'
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
        [AudioSendMessage(original_content_url=url,duration=10000),
        TextSendMessage(text=tags_name_pic1+':'+tags_name_pic2),
        TextSendMessage(text=text_output1+':'+text_output2)]
    )


def location():
    subscription_key_pic = 'def06337fe264f45acf84addb6e1ccb0'
    endpoint_pic = 'https://computerrrrrrrrrrr.cognitiveservices.azure.com/'
    # Call API
    computervision_client = ComputerVisionClient(endpoint_pic, CognitiveServicesCredentials(subscription_key_pic))

    # Call API
    with open('./recordimage.jpg', "rb") as fi:
        description_results = computervision_client.describe_image_in_stream(fi)

    tags_name_pic = description_results.captions[0].text

    #翻譯文字
    #翻譯
    # -*- coding: utf-8 -*-
    subscription_key_text = '4ef67f6abd204ea9a9124dd4a74edd37' # your key
    endpoint_text = 'https://api.cognitive.microsofttranslator.com/'
    path_text = '/translate?api-version=3.0'

    paramsh_text = '&to=zh-Hant'#中文
    constructed_url = endpoint_text + path_text + paramsh_text

    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key_text,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }

    body = [{
        'text': tags_name_pic
    }]

    request = requests.post(constructed_url, headers=headers, json=body)
    response = request.json()

    text_output = response[0]["translations"][0]["text"]
    #把他們全部都連接再一起
    output = tags_name_pic+" "+text_output
    output_url =  urllib.parse.quote(output)
    url = 'https://google-translate-proxy.herokuapp.com/api/tts?query={}&language=zh-tw'.format(output_url)


    line_bot_api.reply_message(
        event.reply_token,
        [AudioSendMessage(original_content_url=url,duration=10000),
        TextSendMessage(text=tags_name_pic),
        TextSendMessage(text=text_output)]
    )





if __name__ == "__main__":
    # arg_parser = ArgumentParser(
    #     usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    # )
    # arg_parser.add_argument('-p', '--port', default=8000, help='port')
    # arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    # options = arg_parser.parse_args()
    # app.run(debug=options.debug, port=options.port)
    app.run()




