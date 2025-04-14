# AI_toy
一个基于esp32的全部基于本地简易的AI聊天玩具，包含服务端的demo
将聊天分为三部分
第一部分：ASR部分 使用开源项目sensevoice(https://github.com/FunAudioLLM/SenseVoice)
esp32通过inmp441获取音频数据，将音频数据转换为base64格式数据，通过ws格式传输给server端，服务端为sensevoice服务，将接收的音频数据合并为一个音频文件，对音频文件进行文本识别。

第二部分：LLM聊天
LLM部分寄托于，TTS上，暂时使用的是豆包的doubao-1-5-pro-256k-250115模型，且暂未做流式模型输出，所以文本会全部输出再进行LLM。

第三部分为LLM语音合成，使用开源项目GPT-SoVIT(https://github.com/RVC-Boss/GPT-SoVITS)
项目下载参考连接(https://www.yuque.com/baicaigongchang1145haoyuangong/ib3g1e/dkxgpiy9zb96hob4#KTvnO)

项目部署:
由于ws的funasr库和GPT-SoVITS的库冲突，所以两者分开部署
1：ASR部署
'''
#使用aconda创建环境
conda create -n sensevoice python=3.9
conda activate sensevoice
pip install -r requestmentes
'''

本项目基于https://github.com/MetaWu2077/Esp32_VoiceChat_LLMs修改完成
