import websocket
import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import time
import ssl
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
import _thread as thread
import os
import config


STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


class Ws_Param(object):
    # 初始化
    def __init__(self, APPID, APIKey, APISecret, Text, res_id):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text

        # 公共参数(common)
        # 在这里通过res_id 来设置通过哪个音库合成
        self.CommonArgs = {"app_id": self.APPID, "res_id": res_id, "status": 2}
        # 业务参数(business)，更多个性化参数可在官网查看
        self.BusinessArgs = {
            "tts": {
                "rhy": 1,
                "vcn": "x5_clone",  # 固定值
                "volume": 50,  # 设置音量大小
                "rhy": 0,
                "pybuffer": 1,
                "speed": 50,  # 设置合成语速，值越大，语速越快
                "pitch": 50,  # 设置振幅高低，可通过该参数调整效果
                "bgs": 0,
                "reg": 0,
                "rdn": 0,
                "audio": {
                    "encoding": "lame",  # 合成音频格式
                    "sample_rate": 16000,  # 合成音频采样率
                    "channels": 1,
                    "bit_depth": 16,
                    "frame_size": 0
                },
                "pybuf": {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "plain"
                }
            }
        }
        self.Data = {
            "text": {
                "encoding": "utf8",
                "compress": "raw",
                "format": "plain",
                "status": 2,
                "seq": 0,
                "text": str(base64.b64encode(self.Text.encode('utf-8')), "UTF8")  # 待合成文本base64格式
            }
        }


class AssembleHeaderException(Exception):
    def __init__(self, msg):
        self.message = msg


class Url:
    def __init__(self, host, path, schema):
        self.host = host
        self.path = path
        self.schema = schema


# calculate sha256 and encode to base64
def sha256base64(data):
    sha256 = hashlib.sha256()
    sha256.update(data)
    digest = base64.b64encode(sha256.digest()).decode(encoding='utf-8')
    return digest


def parse_url(requset_url):
    stidx = requset_url.index("://")
    host = requset_url[stidx + 3:]
    schema = requset_url[:stidx + 3]
    edidx = host.index("/")
    if edidx <= 0:
        raise AssembleHeaderException("invalid request url:" + requset_url)
    path = host[edidx:]
    host = host[:edidx]
    u = Url(host, path, schema)
    return u


# build websocket auth request url
def assemble_ws_auth_url(requset_url, method="GET", api_key="", api_secret=""):
    u = parse_url(requset_url)
    host = u.host
    path = u.path
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    signature_origin = "host: {}\ndate: {}\n{} {} HTTP/1.1".format(host, date, method, path)
    signature_sha = hmac.new(api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                             digestmod=hashlib.sha256).digest()
    signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
    authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
        api_key, "hmac-sha256", "host date request-line", signature_sha)
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
    values = {
        "host": host,
        "date": date,
        "authorization": authorization
    }

    return requset_url + "?" + urlencode(values)


def on_message(ws, message, audio_path):
    try:
        message = json.loads(message)
        code = message["header"]["code"]
        sid = message["header"]["sid"]
        if "payload" in message:
            audio = message["payload"]["audio"]['audio']
            audio = base64.b64decode(audio)
            status = message["payload"]['audio']["status"]
            if status == 2:
                print("ws is closed")
                ws.close()
            if code != 0:
                errMsg = message["message"]
                print("sid:%s call error:%s code is:%s" % (sid, errMsg, code))
            else:
                with open(audio_path, 'ab') as f:
                    f.write(audio)
    except Exception as e:
        print("receive msg,but parse exception:", e)


# 收到websocket错误的处理
def on_error(ws, error):
    print("### error:", error)


# 收到websocket关闭的处理
def on_close(ws, ts, end):
    pass


# 收到websocket连接建立的处理
def on_open(ws, wsParam, audio_path):
    def run(*args):
        d = {
            "header": wsParam.CommonArgs,
            "parameter": wsParam.BusinessArgs,
            "payload": wsParam.Data
        }
        d = json.dumps(d)
        print("------>开始发送文本数据")
        ws.send(d)
        if os.path.exists(audio_path):
            os.remove(audio_path)

    thread.start_new_thread(run, ())


def generate_audio(TEXT, res_id, audio_path):
    """
    生成语音音频文件。

    :param TEXT: 待合成的文本内容
    :param res_id: 训练完成后得到的音库id
    :param audio_path: 生成音频文件的保存路径
    :return: 生成音频文件的路径
    """
    appid = config.XINGHUO_APP_ID
    apisecret = config.XINGHUO_APP_SECRET
    apikey = config.XINGHUO_APP_KEY

    wsParam = Ws_Param(APPID=appid, APISecret=apisecret,
                       APIKey=apikey, Text=TEXT, res_id=res_id)
    websocket.enableTrace(False)
    requrl = 'wss://cn-huabei-1.xf-yun.com/v1/private/voice_clone'
    wsUrl = assemble_ws_auth_url(requrl, "GET", apikey, apisecret)

    def wrapped_on_message(ws, message):
        on_message(ws, message, audio_path)

    def wrapped_on_open(ws):
        on_open(ws, wsParam, audio_path)

    ws = websocket.WebSocketApp(wsUrl, on_message=wrapped_on_message, on_error=on_error, on_close=on_close)
    ws.on_open = wrapped_on_open
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    return audio_path

from concurrent.futures import ThreadPoolExecutor
# from xinghuo_tts_utils import generate_audio


if __name__ == "__main__":
    # 示例数据
    # 不同的 res_id 列表
    res_ids = [
        "",
        "",
        # ""
    ]

    # 不同的文本内容列表
    texts = [
        "第一题的解题思路是这样的。",
        "求这个函数的导数。",
        # "接下来讲解几何图形的性质。"
    ]

    # 不同的音频保存路径列表
    audio_paths = [
        "audio_1.mp3",
        "audio_2.mp3",
        # "audio_3.mp3"
    ]

    # 确保三个列表长度一致
    if len(res_ids) != len(texts) or len(texts) != len(audio_paths):
        raise ValueError("res_ids、texts 和 audio_paths 列表的长度必须一致")

    # with ThreadPoolExecutor() as executor:
    #     # 使用 zip 函数将三个列表打包，然后使用 map 方法并发调用 generate_audio 方法
    #     results = list(executor.map(generate_audio, texts, res_ids, audio_paths))
    result = generate_audio("第一题的解题思路是这样的。", "", "test_demo.wav")
    # print("所有音频生成完成，路径如下：")
    # for path in result:
    #     print(path)
    print(result)