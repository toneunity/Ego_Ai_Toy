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
```ruby
  #使用aconda创建环境
  conda create -n sensevoice python=3.9
  conda activate sensevoice
  pip install -r requirements.txt
  python wss_socket.py
```
2:GPT-SoVITS下载
windows电脑可以直接下载整合包，然后进行修改
从连接(https://www.yuque.com/baicaigongchang1145haoyuangong/ib3g1e/dkxgpiy9zb96hob4#KTvnO)下载最新的整合包
然后再**火山引擎模型广场开通模型服务**[https://console.volcengine.com/ark/region:ark+cn-beijing/model?vendor=Bytedance&view=LIST_VIEW]
将api_key填入文件doubao.py指定位置。将文件api_v2_1.py和文件doubao.py放到GPT-SoVITS根目录下，在根目录下打开com窗口
```
  runtime\python.exe runtime\Scripts\pip.exe install 'volcengine-python-sdk[ark]'
  runtime\python.exe api_v2_1.py
```
3:esp32代码烧录
使用vscode上的platformio配置烧录
在烧录前进行esp32的连线

inmp441 -> esp32 -> max98357
|inmp441|esp32|  
|-------|-----|
|GND    |GND  |
|VDD    |3.3v |
|SD     |22   |
|SCK    |4    |
|WS     |15   |

|max98357|esp32|
|------- |-----|
|GND     |GND  |
|Vin     |3.3v |
|LRC     |25   |
|BLCK    |26   |
|Din     |27   |

可以在I2S.cpp文件和main.cpp文件下分别修改inmp441和max98357的引脚定义
![image](https://github.com/user-attachments/assets/9267d6d4-a788-4c96-9956-8cf511b21bcc)
![image](https://github.com/user-attachments/assets/6fd8161c-65bc-45ad-b41e-949a7c53a48d)

然后修改main.py文件夹下的ws地址和http地址
![image](https://github.com/user-attachments/assets/cda02159-3338-467f-9426-77686e354c42)
烧录成功重启可对话。
本项目基于(https://github.com/MetaWu2077/Esp32_VoiceChat_LLMs)修改完成
