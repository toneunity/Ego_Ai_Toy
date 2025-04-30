此版本添加了服务端后台和esp32端的代码，以下为一个详细的教程
1:硬件连接
inmp441 -> esp32 -> max98357
### 麦克风连接
| 引脚名称 | 连接电平/引脚 |
| ---- | ---- |
| GND | GND |
| VDD | 3.3v |
| SD | D22 |
| SCK | D4 |
| WS | D15 |

### 音频放大连接
| 引脚名称 | 连接电平/引脚 |
| ---- | ---- |
| Vin | Vin |
| GND | GND |
| LRC | D25 |
| BCLK | D26 |
| Din | D27 |

**说明**：加粗为模块引脚，正常为板子引脚 。 

如需连接其他引脚，可以在ego_ai_toy_client/src/main.cpp中的setupI2S方法中修改max98357的引脚定义
```c
i2s_pin_config_t pin_config = {
        .bck_io_num = 26,     // BCLK引脚
        .ws_io_num = 25,      // LRC引脚
        .data_out_num = 27,   // DATA输出引脚
        .data_in_num = I2S_PIN_NO_CHANGE
    };
```
在ego_ai_toy_client/src/I2S.cpp中修改inmp441的引脚定义
```c
#define PIN_I2S_BCLK 4
#define PIN_I2S_LRC 15
#define PIN_I2S_DIN 22
```
连接效果如图![28ae1b68a0b6531e8f073f27fb691fd](https://github.com/user-attachments/assets/8cd12727-9350-443b-a634-f4afb8fa0887)

2:代码
2.1:服务端
配置。

语音识别项目为funasr，对话为豆包流式对话，TTS为腾讯云的语音合成和星火的语音复刻合成，所以需要添加一些id信息
**火山引擎**
火山引擎，如下图所示，找到需要使用的模型后，点击立即体验，在上方API接入处获取对应的api_key（注，本项目中使用的是doubao-1-5-pro-256k-250115，如需更改，请在ego_ai_toy/ego_ai_toy_server/doubao.py处修改）
![image](https://github.com/user-attachments/assets/d4601113-62af-46dc-9f9c-356d5c3edd28)

**腾讯云**
需要实名认证，然后在(https://console.cloud.tencent.com/tts/resourcebundle)获取免费的资源包
音色列表如下
(https://cloud.tencent.com/document/product/1073/92668?from=console_document_search)
**appid等在密钥管理台进行获取，secret_key只能在创建时进行下载，妥善保存！！！**
(https://console.cloud.tencent.com/cam/capi)

**星火**
在认知大模型中使用一句话复刻(https://console.xfyun.cn/services/oneSentence)
点击复制右侧的id等信息
使用星火复刻声音时，需要先使用tts_clone.py文件进行复刻，并将获取的id记录

将上述的信息填到ego_ai_toy/ego_ai_toy_server/config.py的对应位置

```
git clone https://github.com/toneunity/Ego_Ai_Toy.git
cd ego_ai_toy/ego_ai_toy_server
# 这里使用的是conda环境
conda create --name ego_ai_toy python=3.11
conda activate ego_ai_toy
pip install -r requirements.txt
```
需要添加默认的角色信息，可以自行修改。platform为平台xh和ts二选一，prompt_text为人物角色设定，sound_id为声音id，在腾讯云平台或者星火clone后的id填入，user_sheding为对话信息默认不填入，speech_summery为聊天对话的总结，默认不填入

```
toy_dict = {"user_sheding": [],
            "prompt_text": """你是：苏瑶
                            年龄：17 岁身份：就读于市重点高中的高二学生，担任学校舞蹈社团团长，成绩在年级中上游。二、外貌特征：""",
            "sound_id": 601012,
            "platform": "tx/xh",
            "speech_summary": ""}
```
然后运行程序

```
python wss_socket.py
```
打开后显示表示服务端启动成功
```
INFO:     Started server process [9816]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:27001 (Press CTRL+C to quit)
```
2.2:esp32端
该项目使用vscode的platformio平台开发。
platformio安装教程，打开vscode，在拓展栏中查找Platformio，点击安装，在侧边栏中出现头像后表示连接成功
![image](https://github.com/user-attachments/assets/6816fe4f-200b-4b57-b714-3788709b52a5)
将项目在vscode中打开，找到，将其中的localhost更换为自己电脑的ip+端口，查找IP，打开电脑cmd窗口（Windows下按键 win+R ，输入cmd，回车，在弹出的cmd窗口中输入 ipconfig，复制IPv4的地址
```
String baseUrl1 = "ws://localhost:27001/ws/transcribe_chat/";
```
![image](https://github.com/user-attachments/assets/8340fe9f-9514-4be9-b2a7-25035ce5b6af)
点击platform Upload进行烧录(下边栏 -> 按钮）
烧录成功后可以在串口中选择对应串口，波特率为115200，查看返回的信息

程序启动完成，重启esp32,待灯光闪烁可在手机上连接热点  EgoStar_+mac地址。然后可以连接服务端对话，对话完成后会自动总结对话，更新性格和聊天记忆。在聊天时可以按键Boot进行打断。


本项目基于(https://github.com/MetaWu2077/Esp32_VoiceChat_LLMs) 修改完成
