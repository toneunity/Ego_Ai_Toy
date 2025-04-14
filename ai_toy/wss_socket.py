from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
import json
import base64
import wave
import os
import torch
import torchaudio


from funasr import AutoModel

model = "iic/SenseVoiceSmall"
model = AutoModel(model=model,
				  vad_model="iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
				  vad_kwargs={"max_single_segment_time": 30000},
				  trust_remote_code=True,
				  )

import re

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

app = FastAPI()

# 用于存储每个连接的音频数据
connections = {}


@app.websocket("/ws/transcribe")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = id(websocket)
    connections[client_id] = []

    try:
        while True:
            data = await websocket.receive_text()
            print(data)
            json_data = json.loads(data)  # 尝试解析 JSON 数据
            # 处理解析后的数据
            print(json_data)

            status = json_data["data"]["status"]
            audio_data = json_data["data"]["audio"]

            if audio_data:
                # 将Base64编码的音频数据解码
                decoded_audio = base64.b64decode(audio_data)
                if status == 1:
                    # 当status为1时，继续收集音频数据
                    connections[client_id].append(decoded_audio)
                elif status == 2:
                    # 当status为2时，将所有音频数据汇总并保存为WAV文件
                    connections[client_id].append(decoded_audio)
                    combined_audio = b"".join(connections[client_id])

                    # 生成WAV文件
                    output_filename = f"output_{client_id}.wav"
                    with wave.open(output_filename, 'wb') as wf:
                        # 假设音频参数为单声道，采样率为16000Hz，采样宽度为2字节
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(16000)
                        wf.writeframes(combined_audio)

                    print(f"音频文件已保存为: {output_filename}")

                    # 调用模型进行推理
                    try:
                        # 假设语言为 'zh'，可根据实际情况修改
                        result_text = model_inference(output_filename, 'zh', fs=16000)
                        issue_json = {"issue": result_text}
                        data_result = json.dumps(issue_json)
                        # 将推理结果发送给客户端
                        await websocket.send_text(data_result)
                    except Exception as e:
                        print(f"推理过程中出现错误: {e}")
                        await websocket.send_text("推理过程中出现错误")

                    # 删除临时音频文件
                    if os.path.exists(output_filename):
                        os.remove(output_filename)

                    # 清除该连接的音频数据
                    del connections[client_id]
                    break
    except WebSocketDisconnect:
        # 客户端断开连接时，清除该连接的音频数据
        if client_id in connections:
            del connections[client_id]
        print(f"客户端 {client_id} 已断开连接")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=27000)