import asyncio
import time
import uuid

import aiohttp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import json
import base64
import wave
import os
import torch
import torchaudio
import numpy as np

from funasr import AutoModel
from pydub import AudioSegment

import config
# from mysql_connect import MySQLDataInserter
from doubao import DouBao_chat
from tengxun_tts import synthesize_audio_stream, process
# generate_audio
from xinghuo_tts_utils import generate_audio
model = "iic/SenseVoiceSmall"
model = AutoModel(model=model,
                  vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
                  vad_kwargs={"max_single_segment_time": 30000},
                  trust_remote_code=True,
                  )
doubao = DouBao_chat()

class TOY():
    def __init__(self):
        self.is_playing = False
        self.client = ""
        self.user_sheding = []
        self.prompt_text = ""
        self.platform = ""
        self.device_id = ""
        self.toy_role = ""


emo_dict = {
    "<|HAPPY|>": "😊",
    "<|SAD|>": "😔",
    "<|ANGRY|>": "😡",
    "<|NEUTRAL|>": "",
    "<|FEARFUL|>": "😰",
    "<|DISGUSTED|>": "🤢",
    "<|SURPRISED|>": "😮",
}

event_dict = {
    "<|BGM|>": "🎼",
    "<|Speech|>": "",
    "<|Applause|>": "👏",
    "<|Laughter|>": "😀",
    "<|Cry|>": "😭",
    "<|Sneeze|>": "🤧",
    "<|Breath|>": "",
    "<|Cough|>": "🤧",
}

emoji_dict = {
    "<|nospeech|><|Event_UNK|>": "❓",
    "<|zh|>": "",
    "<|en|>": "",
    "<|yue|>": "",
    "<|ja|>": "",
    "<|ko|>": "",
    "<|nospeech|>": "",
    "<|HAPPY|>": "😊",
    "<|SAD|>": "😔",
    "<|ANGRY|>": "😡",
    "<|NEUTRAL|>": "",
    "<|BGM|>": "🎼",
    "<|Speech|>": "",
    "<|Applause|>": "👏",
    "<|Laughter|>": "😀",
    "<|FEARFUL|>": "😰",
    "<|DISGUSTED|>": "🤢",
    "<|SURPRISED|>": "😮",
    "<|Cry|>": "😭",
    "<|EMO_UNKNOWN|>": "",
    "<|Sneeze|>": "🤧",
    "<|Breath|>": "",
    "<|Cough|>": "😷",
    "<|Sing|>": "",
    "<|Speech_Noise|>": "",
    "<|withitn|>": "",
    "<|woitn|>": "",
    "<|GBG|>": "",
    "<|Event_UNK|>": "",
}

lang_dict =  {
    "<|zh|>": "<|lang|>",
    "<|en|>": "<|lang|>",
    "<|yue|>": "<|lang|>",
    "<|ja|>": "<|lang|>",
    "<|ko|>": "<|lang|>",
    "<|nospeech|>": "<|lang|>",
}

emo_set = {"😊", "😔", "😡", "😰", "🤢", "😮"}
event_set = {"🎼", "👏", "😀", "😭", "🤧", "😷",}

def format_str(s):
    for sptk in emoji_dict:
        s = s.replace(sptk, emoji_dict[sptk])
    return s


def format_str_v2(s):
    sptk_dict = {}
    for sptk in emoji_dict:
        sptk_dict[sptk] = s.count(sptk)
        s = s.replace(sptk, "")
    emo = "<|NEUTRAL|>"
    for e in emo_dict:
        if sptk_dict[e] > sptk_dict[emo]:
            emo = e
    for e in event_dict:
        if sptk_dict[e] > 0:
            s = event_dict[e] + s
    s = s + emo_dict[emo]

    for emoji in emo_set.union(event_set):
        s = s.replace(" " + emoji, emoji)
        s = s.replace(emoji + " ", emoji)
    return s.strip()

def format_str_v3(s):
    def get_emo(s):
        return s[-1] if s[-1] in emo_set else None
    def get_event(s):
        return s[0] if s[0] in event_set else None

    s = s.replace("<|nospeech|><|Event_UNK|>", "❓")
    for lang in lang_dict:
        s = s.replace(lang, "<|lang|>")
    s_list = [format_str_v2(s_i).strip(" ") for s_i in s.split("<|lang|>")]
    new_s = " " + s_list[0]
    cur_ent_event = get_event(new_s)
    for i in range(1, len(s_list)):
        if len(s_list[i]) == 0:
            continue
        if get_event(s_list[i]) == cur_ent_event and get_event(s_list[i]) != None:
            s_list[i] = s_list[i][1:]
        #else:
        cur_ent_event = get_event(s_list[i])
        if get_emo(s_list[i]) != None and get_emo(s_list[i]) == get_emo(new_s):
            new_s = new_s[:-1]
        new_s += s_list[i].strip().lstrip()
    new_s = new_s.replace("The.", " ")
    return new_s.strip()

def model_inference(input_wav, language, fs=16000):
    # task_abbr = {"Speech Recognition": "ASR", "Rich Text Transcription": ("ASR", "AED", "SER")}
    language_abbr = {"auto": "auto", "zh": "zh", "en": "en", "yue": "yue", "ja": "ja", "ko": "ko",
                     "nospeech": "nospeech"}

    # task = "Speech Recognition" if task is None else task
    language = "auto" if len(language) < 1 else language
    selected_language = language_abbr[language]
    # selected_task = task_abbr.get(task)

    # print(f"input_wav: {type(input_wav)}, {input_wav[1].shape}, {input_wav}")

    if isinstance(input_wav, tuple):
        fs, input_wav = input_wav
        input_wav = input_wav.astype(np.float32) / np.iinfo(np.int16).max
        if len(input_wav.shape) > 1:
            input_wav = input_wav.mean(-1)
        if fs != 16000:
            print(f"audio_fs: {fs}")
            resampler = torchaudio.transforms.Resample(fs, 16000)
            input_wav_t = torch.from_numpy(input_wav).to(torch.float32)
            input_wav = resampler(input_wav_t[None, :])[0, :].numpy()


    merge_vad = True #False if selected_task == "ASR" else True
    print(f"language: {language}, merge_vad: {merge_vad}")
    text = model.generate(input=input_wav,
                          cache={},
                          language=language,
                          use_itn=True,
                          batch_size_s=60, merge_vad=merge_vad)

    print(text)
    text = text[0]["text"]
    text = format_str_v3(text)

    print(text)

    return text


def mp3_to_wav(mp3_path):
    """
    将 MP3 音频文件转换为同名的 WAV 格式，并删除源 MP3 文件。

    :param mp3_path: MP3 文件的路径
    """
    try:
        # 检查文件是否为 MP3 格式
        if not mp3_path.lower().endswith('.mp3'):
            print(f"{mp3_path} 不是 MP3 文件，跳过转换。")
            return mp3_path

        # 生成对应的 WAV 文件路径
        wav_path = os.path.splitext(mp3_path)[0] + '.wav'

        # 读取 MP3 文件
        audio = AudioSegment.from_mp3(mp3_path)

        # 保存为 WAV 格式
        audio.export(wav_path, format="wav")
        print(f"成功将 {mp3_path} 转换为 {wav_path}")

        # 删除源 MP3 文件
        os.remove(mp3_path)
        print(f"已删除源文件 {mp3_path}")
        return wav_path
    except Exception as e:
        print(f"转换过程中出现错误: {e}")

async def send_audio_over_ws_tengxun(params, audio_file_path):
    if params["platform"] == "tx":
        result = process(params["text"], audio_file_path, params["voice_type"])+".wav"
    elif params["platform"] == "xh":
        result = generate_audio(params["text"], params["voice_type"], audio_file_path+".mp3")
        # with ThreadPoolExecutor() as executor:
        #     # 使用 zip 函数将三个列表打包，然后使用 map 方法并发调用 generate_audio 方法
        #     results = list(executor.map(generate_audio, texts, res_ids, audio_paths))
    out_pout_path = mp3_to_wav(result)
    print(f"\nTask {result} completed\n")
    # for inner_generator in outer_generator:
    #     # 遍历内层生成器，获取音频数据块
    #     for audio_chunk in inner_generator:
    #         print(f"获取到音频数据块，长度: {len(audio_chunk)} 字节")
    oss_output_path = "1"
    # oss_output_path = oss.upload_file_to_oos(audio_file_path+".wav", out_pout_path)
    return oss_output_path, out_pout_path

async def process_audio_data(websocket, toy, connections, web_socket_id):
    # 当status为2时，将所有音频数据汇总并保存为WAV文件
    if web_socket_id not in connections:
        result_json = {"status": 2, "id": toy.client_id}
        try:
            await websocket.send_text(json.dumps(result_json))
        except Exception as e:
            print(1)
            print(f"发送数据到客户端时出错: {e}")
            # await websocket.close(code=1000, reason="Normal closure")
            return
        # connections[toy.client_id].append(decoded_audio)
    combined_audio = b"".join(connections[web_socket_id])
    connections[web_socket_id] = []
    temp_id = int(time.time())
    # 生成WAV文件
    output_filename = f"output_{str(temp_id)}.wav"
    with wave.open(output_filename, 'wb') as wf:
        # 假设音频参数为单声道，采样率为16000Hz，采样宽度为2字节
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(combined_audio)

    print(f"音频文件已保存为: {output_filename}")
    # 调用模型进行推理
    result_text = model_inference(output_filename, 'zh', fs=16000)
    text = result_text
    # 删除临时音频文件
    if os.path.exists(output_filename):
        os.remove(output_filename)
    toy.is_playing = True
    doubao.start_stream()
    msg = ""
    msg_kongyu = ""
    toy.user_sheding.append({"role": "user", "content": result_text})
    print(toy.user_sheding)
    for chunk in doubao.doubao_chat_stream(toy.user_sheding):
        finish_reason = chunk.choices[0].finish_reason
        message = chunk.choices[0].delta.content
        if finish_reason == "stop":
            break
        msg += message
        msg_kongyu += message
        text_tts, msg_kongyu = doubao.split_text_by_punctuation(msg_kongyu)
        if text_tts != "" and toy.is_playing == True:
            audio_name = uuid.uuid4()
            params = {"text": text_tts, "voice_type": toy.voice_type, "platform": toy.platform}  # 构造参数，根据实际 TTS 接口调整
            print(params)
            audio_file_path = f"output_audio/{toy.client_id}/{audio_name}"
            # 调用 send_audio_over_ws 函数发送音频数据
            oss_output_path, out_pout_path = await send_audio_over_ws_tengxun(params, audio_file_path)
            if os.path.exists(audio_file_path + ".wav"):
                with wave.open(audio_file_path+".wav", 'rb') as wf:
                    print(f"音频文件 {out_pout_path} 已打开.")

                    # 获取音频文件参数
                    chunk_size = 1024  # 每次发送的数据块大小
                    n_channels = wf.getnchannels()
                    sampwidth = wf.getsampwidth()
                    framerate = wf.getframerate()

                    print(f"音频参数: {n_channels} 通道, {sampwidth} 字节样本宽度, {framerate} 采样率.")
                    result_json = {"status": 1, "id": toy.client_id}
                    try:
                        await websocket.send_text(json.dumps(result_json))
                    except Exception as e:
                        print(2)
                        # await websocket.close(code=1000, reason="Normal closure")
                        print(f"发送数据到客户端时出错: {e}")
                        return
                    # 逐块读取音频数据并发送给客户端
                    while (toy.is_playing == True):
                        audio_data = wf.readframes(chunk_size)
                        if not audio_data:  # 如果读取完所有数据，退出循环
                            break
                        # 发送音频数据给客户端
                        try:
                            await websocket.send_bytes(audio_data)
                        except Exception as e:
                            print(3)
                            print(f"发送数据到客户端时出错: {e}")
                            # await websocket.close(code=1000, reason="Normal closure")
                            # async with lock:
                            toy.is_playing = False
                            doubao.stop_stream()
                            break
                        await asyncio.sleep(0.001)  # 确保非阻塞发送，控制发送速度\
            if toy.is_playing == False:
                print("toy.is_playing"+str(toy.is_playing))
                doubao.stop_stream()
                return
            if os.path.exists(output_filename):
                os.remove(output_filename)
    toy.user_sheding.append({"role": "system", "content": msg})
    # await websocket.send_text(json.dumps({"status": 1, "data": "", "id": client_id}))
    result_json = {"status": 2, "id": toy.client_id}
    try:
        await websocket.send_text(json.dumps(result_json))
    except Exception as e:
        print(4)
        print(f"发送数据到客户端时出错: {e}")
        return

import configparser

def write_to_ini(file_path, section, key_value_dict):
    """
    打开指定的 ini 文件并写入多个键值对。

    :param file_path: ini 文件的路径
    :param section: 要写入数据的节名称
    :param key_value_dict: 包含多个键值对的字典
    """
    config = configparser.ConfigParser()

    # 检查文件是否存在，如果存在则读取内容
    if os.path.exists(file_path):
        config.read(file_path)

    # 检查节是否存在，如果不存在则添加
    if not config.has_section(section):
        config.add_section(section)

    # 遍历字典并设置键值对
    for key, value in key_value_dict.items():
        config.set(section, key, str(value))

    # 将修改后的内容写回文件
    with open(file_path, 'w') as configfile:
        config.write(configfile)

def read_from_ini(file_path, section=None):
    """
    读取指定的 ini 文件，根据提供的节名称返回对应节下的键值对。
    如果未提供节名称，则返回所有节名称以及对应节下的键值对。

    :param file_path: ini 文件的路径
    :param section: 要查询的节名称，可选参数
    :return: 若提供节名称，返回该节下的键值对字典；若未提供，返回所有节及对应键值对的字典
    """
    config = configparser.ConfigParser()
    result = {}

    # 检查文件是否存在，如果存在则读取内容
    if os.path.exists(file_path):
        config.read(file_path)

        if section is not None:
            # 如果提供了节名称，检查节是否存在
            if config.has_section(section):
                for key, value in config.items(section):
                    result[key] = value
        else:
            # 未提供节名称，遍历所有节
            for sec in config.sections():
                section_dict = {}
                for key, value in config.items(sec):
                    section_dict[key] = value
                result[sec] = section_dict

    return result

app = FastAPI()

# 用于存储每个连接的音频数据
connections = {}


@app.websocket("/ws/transcribe_chat/{client_id}/{web_socket_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, web_socket_id: str):
    # web_socket_id = id(websocket)
    try:
        os.makedirs(f"output_audio/{client_id}") if not os.path.exists(f"output_audio/{client_id}") else None
        connections[web_socket_id] = []
        doubao.start_stream()
        toy_dict = read_from_ini("config.ini", client_id)
        if toy_dict == {}:
            toy_dict = {"user_sheding": [],
                        "prompt_text": """你是：苏瑶
                                        年龄：17 岁身份：就读于市重点高中的高二学生，担任学校舞蹈社团团长，成绩在年级中上游。二、外貌特征：""",
                        "sound_id": 601012,
                        "platform": "tx",
                        "speech_summary": ""}

        toy = TOY()
        toy.client_id = client_id
        if toy_dict["user_sheding"] != "":
            toy.user_sheding.append({"role": "system", "content": toy_dict["prompt_text"]})
        else:
            json_str = toy_dict["user_sheding"].replace("'", "\"")
            list_data = json.loads(json_str)
            toy.user_sheding = list_data
        toy.prompt_text = toy_dict["prompt_text"]
        toy.is_playing = False
        toy.voice_type = toy_dict["sound_id"]
        # 平台分为星火和腾讯云星火大模型为复刻声音，腾讯云为原生声音
        toy.platform = toy_dict["platform"]
    except Exception as e:
        print(e)
        return
    try:
        await websocket.accept()
        import asyncio
        while True:
            data = await websocket.receive_text()
            # print(data)
            json_data = json.loads(data)  # 尝试解析 JSON 数据
            # 处理解析后的数据
            print(json_data)

            status = json_data["data"]["status"]
            if status == 0:
                toy.is_playing = False
            if "audio" in json_data["data"]:
                audio_data = json_data["data"]["audio"]
            else:
                audio_data = ""
            if audio_data != "":
                # 将Base64编码的音频数据解码
                decoded_audio = base64.b64decode(audio_data)
                if status == 1:
                    # 当status为1时，继续收集音频数据
                    if web_socket_id not in connections:
                        connections[web_socket_id] = []
                    connections[web_socket_id].append(decoded_audio)
                elif status == 2:
                    asyncio.create_task(process_audio_data(websocket, toy, connections, web_socket_id))
    except WebSocketDisconnect:
        # if 'send_task' in locals():
        #     send_task.cancel()
        # 客户端断开连接时，清除该连接的音频数据
        if web_socket_id in connections:
            del connections[web_socket_id]
        print(f"客户端 {web_socket_id} 已断开连接")
        speech_summary = doubao.doubao_zongjie(toy.user_sheding)
        toy_dict["speech_summary"] = speech_summary
        toy_dict["user_sheding"] = toy.user_sheding
        write_to_ini("config.ini", client_id, toy_dict)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=27000, timeout_keep_alive=10)