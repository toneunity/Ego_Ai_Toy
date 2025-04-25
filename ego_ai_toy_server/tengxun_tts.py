# -*- coding: utf-8 -*-
# 引用 SDK

import sys

import config

sys.path.append("../..")

import wave
import time
import queue
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

from common import credential
from tts import speech_synthesizer_ws
from common.log import logger
from common.utils import is_python3

APPID = config.TENGXUN_APP_ID
SECRET_ID = config.TENGXUN_SECRET_ID
SECRET_KEY = config.TENGXUN_SECRET_KEY

# VOICETYPE = 601012  # 音色类型
FASTVOICETYPE = ""
CODEC = "pcm"  # 音频格式：pcm/mp3
SAMPLE_RATE = 16000  # 音频采样率：8000/16000
ENABLE_SUBTITLE = True


class MySpeechSynthesisListener(speech_synthesizer_ws.SpeechSynthesisListener):

    def __init__(self, id, codec, sample_rate, audio_path, voice_type=601012):
        self.start_time = time.time()
        self.id = id
        self.codec = codec.lower()
        self.sample_rate = sample_rate
        self.voice_type = voice_type
        self.audio_file = ""
        self.audio_data = bytes()
        self.audio_data_queue = queue.Queue()  # 用于存储音频数据的队列
        self.synthesis_ended = False
        self.audio_path = audio_path

    def set_audio_file(self, filename):
        self.audio_file = filename

    def on_synthesis_start(self, session_id):
        '''
        session_id: 请求session id，类型字符串
        '''
        super().on_synthesis_start(session_id)

        # TODO 合成开始，添加业务逻辑
        if not self.audio_file:
            self.audio_file = self.audio_path
        self.audio_data = bytes()

    def on_synthesis_end(self):
        super().on_synthesis_end()
        self.synthesis_ended = True

        # TODO 合成结束，添加业务逻辑
        logger.info("write audio file, path={}, size={}".format(
            self.audio_file, len(self.audio_data)
        ))
        logger.info("synthesis end, cost={}s".format(
            time.time() - self.start_time
        ))
        # logger.info("audio_data = {}".format(
        #     self.audio_data
        # ))
        if self.codec == "pcm":
            wav_fp = wave.open(self.audio_file + ".wav", "wb")
            wav_fp.setnchannels(1)
            wav_fp.setsampwidth(2)
            wav_fp.setframerate(self.sample_rate)
            wav_fp.writeframes(self.audio_data)
            wav_fp.close()
        elif self.codec == "mp3":
            fp = open(self.audio_file, "wb")
            fp.write(self.audio_data)
            fp.close()
        else:
            logger.info("codec {}: sdk NOT implemented, please save the file yourself".format(
                self.codec
            ))

    def on_audio_result(self, audio_bytes):
        '''
        audio_bytes: 二进制音频，类型 bytes
        '''
        super().on_audio_result(audio_bytes)

        # TODO 接收到二进制音频数据，添加实时播放或保存逻辑
        self.audio_data += audio_bytes
        self.audio_data_queue.put(audio_bytes)  # 将音频数据放入队列

    def on_text_result(self, response):
        '''
        response: 文本结果，类型 dict，如下
        字段名       类型         说明
        code        int         错误码（无需处理，SpeechSynthesizer中已解析，错误消息路由至 on_synthesis_fail）
        message     string      错误信息
        session_id  string      回显客户端传入的 session id
        request_id  string      请求 id，区分不同合成请求，一次 websocket 通信中，该字段相同
        message_id  string      消息 id，区分不同 websocket 消息
        final       bool        合成是否完成（无需处理，SpeechSynthesizer中已解析）
        result      Result      文本结果结构体

        Result 结构体
        字段名       类型                说明
        subtitles   array of Subtitle  时间戳数组

        Subtitle 结构体
        字段名       类型     说明
        Text        string  合成文本
        BeginTime   int     开始时间戳
        EndTime     int     结束时间戳
        BeginIndex  int     开始索引
        EndIndex    int     结束索引
        Phoneme     string  音素
        '''
        super().on_text_result(response)

        # TODO 接收到文本数据，添加业务逻辑
        result = response["result"]
        subtitles = []
        if "subtitles" in result and len(result["subtitles"]) > 0:
            subtitles = result["subtitles"]

    def on_synthesis_fail(self, response):
        '''
        response: 文本结果，类型 dict，如下
        字段名 类型
        code        int         错误码
        message     string      错误信息
        '''
        super().on_synthesis_fail(response)

        # TODO 合成失败，添加错误处理逻辑
        err_code = response["code"]
        err_msg = response["message"]

    def audio_data_generator(self):
        print("audio_data_generator")
        while True:
            try:
                # 从队列中获取音频数据，设置超时时间为 0.1 秒
                audio_bytes = self.audio_data_queue.get(timeout=0.1)
                yield audio_bytes
            except queue.Empty:
                # 若队列为空且合成已结束，则退出循环
                if self.synthesis_ended:  # 假设存在一个标志位表示合成结束
                    break

def synthesize_audio_stream(text, audio_path, voice_type):
    """
    流式调用语音合成方法并返回音频数据生成器。

    :param text: 要合成的文本
    :return: 音频数据生成器
    """
    id = int(time.time())
    listener = MySpeechSynthesisListener(id, CODEC, SAMPLE_RATE, audio_path, voice_type)
    credential_var = credential.Credential(SECRET_ID, SECRET_KEY)
    synthesizer = speech_synthesizer_ws.SpeechSynthesizer(
        APPID, credential_var, listener)
    synthesizer.set_text(text)
    synthesizer.set_voice_type(listener.voice_type)
    synthesizer.set_codec(CODEC)
    synthesizer.set_sample_rate(SAMPLE_RATE)
    synthesizer.set_enable_subtitle(ENABLE_SUBTITLE)
    synthesizer.set_fast_voice_type(FASTVOICETYPE)

    synthesizer.start()

    yield listener.audio_data_generator()

def process(text, audio_path, voice_type):
    id = int(time.time())
    logger.info("process start: idx={} text={}".format(id, text))
    listener = MySpeechSynthesisListener(id, CODEC, SAMPLE_RATE, audio_path, voice_type)
    credential_var = credential.Credential(SECRET_ID, SECRET_KEY)
    synthesizer = speech_synthesizer_ws.SpeechSynthesizer(
        APPID, credential_var, listener)
    synthesizer.set_text(text)
    synthesizer.set_voice_type(listener.voice_type)
    synthesizer.set_codec(CODEC)
    synthesizer.set_sample_rate(SAMPLE_RATE)
    synthesizer.set_enable_subtitle(ENABLE_SUBTITLE)
    synthesizer.set_fast_voice_type(FASTVOICETYPE)

    synthesizer.start()
    # wait for processing complete
    synthesizer.wait()

    logger.info("process done: idx={} text={}".format(id, text))
    return audio_path


def read_tts_text():
    lines_list = ["你好,恭喜发财，今天的生活是否足够愉快，你是否很开心可以进行交流？", "今天过得怎么样", "是否像昨天一样开心", "你喜欢什么音乐", "你有什么爱好", "你有什么秘密", "你有什么问题", "你有什么建议", "你有什么想法", "你有什么梦想", "你有什么梦想"]
    # with open('tts_text.txt', 'r', encoding='utf-8') as file:
    #     for line in file:
    #         lines_list.append(line.strip())
    # print("total read {} lines".format(len(lines_list)))
    return lines_list


if __name__ == "__main__":
    if not is_python3():
        print("only support python3")
        sys.exit(0)

        # 测试 synthesize_audio_stream 方法
    test_text = "请输出数据格式"
    # audio_generator = synthesize_audio_stream(test_text)
    # 调用 synthesize_audio_stream 函数获取生成器
    outer_generator = synthesize_audio_stream(test_text, "output_audio.pcm", 601012)
    # 遍历外层生成器
    # for inner_generator in outer_generator:
    #     # 遍历内层生成器，获取音频数据块
    #     for audio_chunk in inner_generator:
    #         print(f"获取到音频数据块，长度: {len(audio_chunk)} 字节")

    buffer = b""  # 初始化缓冲区
    # 遍历外层生成器
    wav_fp = wave.open('output.pcm_1.wav', "wb")
    wav_fp.setnchannels(1)
    wav_fp.setsampwidth(2)
    wav_fp.setframerate(16000)
    for inner_generator in outer_generator:
        # 遍历内层生成器，获取音频数据块
        for audio_chunk in inner_generator:
            buffer += audio_chunk  # 将新的音频数据添加到缓冲区
            while len(buffer) >= 1024:
                # 提取 1024 字节的数据
                data_to_process = buffer[:1024]
                print(f"获取到 1024 字节的音频数据块")
                # 这里可以添加处理 1024 字节数据的逻辑
                # 例如保存到文件
                # with open('output.pcm_1.wav', 'ab') as f:
                # wav_fp = wave.open(self.audio_file + ".wav", "wb")

                wav_fp.writeframes(data_to_process)
                # f.write(data_to_process)
                # 从缓冲区中移除已处理的数据
                buffer = buffer[1024:]

    # 处理缓冲区中剩余的数据
    if buffer:
        print(f"获取到剩余的 {len(buffer)} 字节音频数据块")
        wav_fp.writeframes(buffer)
        # f.write(data_to_process)
    wav_fp.close()
    # 模拟流式处理音频数据
    # output_file = "stream_synthesis_output.pcm_l"
    # with open(output_file, 'wb') as f:
    #     for audio_chunk in audio_generator:
    #         f.write(audio_chunk)
    #
    # print(f"流式合成的音频已保存到 {output_file}")
    # if not is_python3():
    #     print("only support python3")
    #     sys.exit(0)
    #
    # # 读取示例文本
    # lines = read_tts_text()
    #
    # #### 示例一：单线程串行调用 ####
    # for idx, line in enumerate(lines):
    #     result = process(idx, line)
    #     print(f"\nTask {result} completed\n")
    # lines = ["你好", "今天怎么样", "你喜欢什么音乐", "你有什么秘密", "你有什么问题", "你有什么建议", "你有什么想法", "你有什么梦想"]
    # ### 示例二：多线程调用 ####
    # thread_concurrency_num = 3 # 最大线程数
    # with ThreadPoolExecutor(max_workers=thread_concurrency_num) as executor:
    #     futures = [executor.submit(process, idx, line) for idx, line in enumerate(lines)]
    #     for future in as_completed(futures):
    #         result = future.result()
    #         print(f"\nTask {result} completed\n")

    ### 示例三：多进程调用（适用于高并发场景） ####
    # process_concurrency_num = 3 # 最大进程数
    # with ProcessPoolExecutor(max_workers=process_concurrency_num) as executor:
    #     futures = [executor.submit(process, idx, line) for idx, line in enumerate(lines)]
    #     for future in as_completed(futures):
    #         result = future.result()
    #         print(f"\nTask {result} completed\n")
    #         print(f"\nTask {result} completed\n")
    #         print(f"\nTask {result} completed\n")