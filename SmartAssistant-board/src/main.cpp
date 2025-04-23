#include <Arduino.h>
#include "base64.h"
#include "HTTPClient.h"
#include "Audio1.h"
#include "Audio.h"
#include <ArduinoJson.h>
#include <ArduinoWebsockets.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <Preferences.h>
#include <ESP32Servo.h>
#include <DNSServer.h>
#include <U8g2lib.h>
#include <WiFi.h>
#include <fennu_in.h>
#include <fennu_xunhuan.h>
#include <zhayan_once.h>
#include <zhayan_twice.h>
#include <fennu_out.h>
#include <buxie_in.h>
#include <buxie_out.h>
#include <buxie_xunhuan.h>
#include "SPIFFS.h"
#include "FS.h"

using namespace websockets;
// 引脚定义
#define KEY 1
#define ADC 32
#define LED 2
#define led1 33
#define led2 19
#define VIBRATION_SENSOR_PIN GPIO_NUM_34
#define THRESHOLD 4000
#define I2S_DOUT 27
#define I2S_BCLK 26
#define I2S_LRC 25
#define I2S_BUFFER_SIZE 2048

AsyncWebServer server(80);       // 创建 HTTP 服务器
DNSServer dnsServer;        // 创建 DNS 服务器
bool isAPMode = false; // 标志当前是否处于 AP 模式

Preferences preferences;
const byte DNS_PORT = 53;   // DNS 服务器端口
IPAddress apIP(192, 168, 4, 1); // ESP32 AP 模式下的固定 IP

int wifi_type = 0;
// 存储WiFi配置的全局变量
String wifi_ssid = "";
String wifi_pass = "";
U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE, 17, 16);
WebsocketsClient webSocketClient1;
HTTPClient https;
Audio1 audio1;
Audio audio;
Servo xServo, yServo;
int http_tts(String issue, String peompt, String refer_wav_path);
float calculateRMS(uint8_t *buffer, int bufferSize);
int xuanzhuan=0;
int zhuangtai = 0,
changci = 1,
currentFrame = 0;
unsigned long previousTime = 0;
const unsigned long interval = 2000; // 2秒，单位是毫秒
int wifi_success = 0;
// 引脚定义
const int pirPin = 21;      // HR-SR602传感器引脚
const int xServoPin = 5;   // X轴舵机引脚
const int yServoPin = 23;   // Y轴舵机引脚
int xPosition = 0, yPosition = 0, start_other = 0;
bool motionDetected = false, isServoStopped = false;
bool ledstatus = true, startPlay = true;
int noise = 50, answer_int = 0, isplaying = 0;
unsigned long time_now = 0, lastMoveTime = 0;
String mac_s = ""; 
StaticJsonDocument<2048> jsonDoc;

// String serverUrl = "http:///zero_shot";
const char* answer_audio = "";
String url1 = "ws://服务器ip/chatToySocket/";
const char* audioStreamUrl = "http://服务器ip/make_audio_new";  //公司官网

// 互斥锁
SemaphoreHandle_t xMutex;

void connectToAudioHost(const char* url_audio) {
    if (xSemaphoreTake(xMutex, portMAX_DELAY) == pdTRUE) {
        audio.connecttohost(url_audio);
        answer_int = 0;
        isplaying = 0;
        xSemaphoreGive(xMutex);
    }
}

void onMessageCallback1(WebsocketsMessage message) {
    answer_int = 1;
    isplaying = 1;
    StaticJsonDocument<2048> jsonDocument;
    DeserializationError error = deserializeJson(jsonDocument, message.data());
    Serial.println(message.data());
    if (!error) {
        if (jsonDocument["audio"]) {
            connectToAudioHost(jsonDocument["audio"]);
        }
        if (jsonDocument["issue"]) {
            String issue = jsonDocument["issue"];
            // Serial.println(issue);
            if (issue.indexOf("惊讶") != -1) Serial.println("Surprise");
            else if (issue.indexOf("恐惧") != -1) Serial.println("Fear");
            else if (issue.indexOf("快乐") != -1) Serial.println("Joy");
            else if (issue.indexOf("信任") != -1) Serial.println("Trust");
            else if (issue.indexOf("悲伤") != -1) Serial.println("Sadness");
            else if (issue.indexOf("不屑") != -1) {
                zhuangtai = 3;
                changci = 1;
                Serial.println("Disgust");
            }
            else if (issue.indexOf("愤怒") != -1) {
                zhuangtai = 1;
                changci = 1;
                Serial.println("Anger");
            }
            else if (issue.indexOf("再见") != -1) {
                webSocketClient1.close();
                Serial.println("拜拜拜");
                start_other = false;
                Serial.println("进入睡眠");
                // esp_sleep_enable_ext0_wakeup((gpio_num_t)VIBRATION_SENSOR_PIN, 1);
                esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, 0);  // 0 表示按下按键时唤醒
                esp_light_sleep_start();
            }
            xuanzhuan = 0;
            int httpResponseCode = http_tts(issue, jsonDocument["peompt"], jsonDocument["modelId"]);
            if (httpResponseCode == 200) {
                connectToAudioHost(answer_audio);
            }
        }
    }
    answer_int = 0;
    isplaying = 0;
    webSocketClient1.close();
}

void servoTask_xuanzhuan(void *parameter) {
    int jiaodu = 20;
    while (true){
        ESP.getFreeHeap();
        motionDetected = digitalRead(pirPin);
        xPosition = (xServo.read() + jiaodu) % 180;
        yPosition = (yServo.read() + jiaodu) % 180;
        xServo.write(xPosition);
        yServo.write(yPosition);
        Serial.print("X轴角度: ");
        Serial.print(xPosition);
        Serial.print("  Y轴角度: ");
        Serial.println(yPosition);
        delay(400);

        if (xuanzhuan == 0){
            vTaskDelete(NULL);
            return;
        }
        jiaodu=-jiaodu;
    }
}

void onEventsCallback1(WebsocketsEvent event, String data) {
    if (event == WebsocketsEvent::ConnectionOpened) {
        xTaskCreate(servoTask_xuanzhuan, "Servo_Task_Xuanzhuan", 2048, NULL, 1, NULL);
        xuanzhuan = 1;
        Serial.println("Send message to xunfeiyun");
        int silence = 0, firstframe = 1, j = 0, voicebegin = 0, voice = 0, readyStartSleep = 0;
        DynamicJsonDocument doc(3000);
        while (1) {
            digitalWrite(led1, ledstatus);
            ledstatus = !ledstatus;
            doc.clear();
            JsonObject data = doc.createNestedObject("data");
            audio1.Record();
            float rms = calculateRMS((uint8_t *)audio1.wavData[0], 1280);
            unsigned long currentTime = millis();
            Serial.print(rms);
            if (rms < noise) {
                readyStartSleep++;
                if (voicebegin == 1) silence++;
            } else {
                voice++;
                if (voice >= 5) voicebegin = 1;
                else voicebegin = 0;
                silence = 0;
            }

            if (silence == 6) {
                readyStartSleep = 0;
                data["status"] = 2;
                data["format"] = "audio/L16;rate=8000";
                data["audio"] = base64::encode((byte *)audio1.wavData[0], 1280);
                data["encoding"] = "raw";
                j++;
                String jsonString;
                serializeJson(doc, jsonString);
                webSocketClient1.send(jsonString);
                delay(40);
                break;
            }

            if (firstframe == 1) {
                j++;
                firstframe = 0;
                delay(40);
            } else {
                data["status"] = 1;
                data["format"] = "audio/L16;rate=8000";
                data["audio"] = base64::encode((byte *)audio1.wavData[0], 1280);
                data["encoding"] = "raw";
                String jsonString;
                serializeJson(doc, jsonString);
                webSocketClient1.send(jsonString);
                readyStartSleep = 0;
                delay(40);
            }
        }
        doc.clear();
        xuanzhuan = 0;
    } else if (event == WebsocketsEvent::ConnectionClosed) {
        Serial.println("Connnection1 Closed");
    } else if (event == WebsocketsEvent::GotPing) {
        Serial.println("Got a Ping!");
    } else if (event == WebsocketsEvent::GotPong) {
        Serial.println("Got a Pong!");
    }
    ledstatus = false;
    digitalWrite(led1, ledstatus);
}

void ConnServer1() {
    if (xSemaphoreTake(xMutex, portMAX_DELAY) == pdTRUE) {
        isplaying = 1;
        Serial.println("url1:" + url1);
        webSocketClient1.onMessage(onMessageCallback1);
        webSocketClient1.onEvent(onEventsCallback1);
        Serial.println("Begin connect to server1......");
        if (webSocketClient1.connect(url1.c_str())) {
            Serial.println("Connected to server1!");
        } else {
            Serial.println("Failed to connect to server1!");
            isplaying = 0;
        }
        xSemaphoreGive(xMutex);
    }
}

// 启动 Captive Portal 配置 WiFi
void startCaptivePortal() {

    // 设置 AP 模式
    WiFi.mode(WIFI_AP);
    WiFi.softAP("ESP32_Config", "12345678");
    WiFi.softAPConfig(apIP, apIP, IPAddress(255, 255, 255, 0)); // 设置静态 IP

    Serial.println("AP 模式启动，SSID: ESP32_Config，密码: 12345678");
    Serial.println("请连接 WiFi 并访问 http://192.168.4.1 配置 WiFi");

    // 启动 DNS 服务器
    dnsServer.start(DNS_PORT, "*", apIP); // 拦截所有域名解析

    // 配置主页面
    server.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
        String html = R"rawliteral(
          <!DOCTYPE html>
          <html>
          <head>
          <meta http-equiv="refresh" content="3;url=/setwifi">
          </head>
          <body>
          <h1>请稍候...</h1>
          <p>正在将你重定向到 WiFi 配置页面。</p>
          </body>
          </html>
        )rawliteral";
        request->send(200, "text/html", html);
    });
    // 配置页面，提交 WiFi 配置
    server.on("/setwifi", HTTP_GET, [](AsyncWebServerRequest *request) {
        String html = R"rawliteral(
          <!DOCTYPE html>
          <html>
          <body>
          <h1>配置 WiFi</h1>
          <form action="/setwifi" method="POST">
            SSID: <input type="text" name="ssid"><br>
            Password: <input type="password" name="pass"><br>
            <input type="submit" value="保存">
          </form>
          </body>
          </html>
        )rawliteral";
        request->send(200, "text/html", html);
    });

    // 保存 WiFi 配置
    server.on("/setwifi", HTTP_POST, [](AsyncWebServerRequest *request) {
        if (request->hasParam("ssid", true) && request->hasParam("pass", true)) {
            wifi_ssid = request->getParam("ssid", true)->value();
            wifi_pass = request->getParam("pass", true)->value();

            // 保存 WiFi 配置到 NVS
            preferences.begin("wifi-config", false);
            preferences.putString("ssid", wifi_ssid);
            preferences.putString("pass", wifi_pass);
            preferences.end();

            Serial.printf("配置的 WiFi SSID: %s, Password: %s\n", wifi_ssid.c_str(), wifi_pass.c_str());

            // 返回保存成功页面
            request->send(200, "text/html", "<h1>配置成功！正在尝试连接 WiFi...</h1><p>请断开 ESP32 热点，连接您的 WiFi 网络。</p>");

            delay(1000);
            ESP.restart(); // 重启设备以尝试连接配置的 WiFi
        } else {
            request->send(400, "text/plain", "缺少参数");
        }
    });

    server.begin();
}

void connectToWiFi() {
    WiFi.mode(WIFI_STA);

    // 从 NVS 加载 WiFi 配置
    preferences.begin("wifi-config", true);
    wifi_ssid = preferences.getString("ssid", "");
    wifi_pass = preferences.getString("pass", "");
    preferences.end();

    if (wifi_ssid == "" || wifi_pass == "") {
        Serial.println("未找到 WiFi 配置信息，启动 AP 模式...");
        isAPMode = true;  // 切换为 AP 模式
        startCaptivePortal();
        return;
    }

    Serial.printf("尝试连接 WiFi，SSID: %s\n", wifi_ssid.c_str());
    WiFi.begin(wifi_ssid.c_str(), wifi_pass.c_str());

    int retry = 0;
    while (WiFi.status() != WL_CONNECTED && retry < 20) {
        delay(500);
        Serial.print(".");
        retry++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        wifi_success == 1;
        Serial.println("\nWiFi 已连接！");
        Serial.print("IP 地址: ");
        Serial.println(WiFi.localIP());
        digitalWrite(LED, HIGH);
        isAPMode = false; // 确保标志切换到正常模式
        wifi_type = 1;
    } else {
        Serial.println("\n连接 WiFi 失败，启动 AP 模式...");
        isAPMode = true; // 切换为 AP 模式
        startCaptivePortal();
    }
}
// 处理 WiFi 断开事件
void WiFiEvent(WiFiEvent_t event) {
    if (event == SYSTEM_EVENT_STA_DISCONNECTED) {
        Serial.println("WiFi 连接丢失，尝试重新连接...");
        WiFi.reconnect();  // 尝试重新连接 WiFi
    }
}

// int http_tts(String issue, String peompt, String refer_wav_path) {
//     if (xSemaphoreTake(xMutex, portMAX_DELAY) == pdTRUE) {
//         HTTPClient http;
//         http.begin(serverUrl);
//         http.setTimeout(20000);
//         http.addHeader("Content-Type", "application/x-www-form-urlencoded");
//         String postData = "refer_wav_path=1451697773a";
//         postData += "&prompt=你面对的是小朋友们，你很爱他们，并可以在他们难过时给予一定的帮助，对他们的行为给以鼓励";
//         postData += "&prompt_language=zh";
//         postData += "&text="+issue;
//         postData += "&text_language=zh";
//         int httpResponseCode = http.POST(postData);
//         if (httpResponseCode > 0) {
//             String response = http.getString();
//             Serial.println(httpResponseCode);
//             Serial.println(response);
//             delay(50);
//             DynamicJsonDocument doc(4096);
//             DeserializationError error = deserializeJson(doc, response);

//             if (!error) {
//                 answer_audio = doc["audio"];
//                 Serial.print("Audio: ");
//                 http.end();
//                 Serial.println(answer_audio);
//                 answer_int=0;
//                 isplaying=0;
//                 xSemaphoreGive(xMutex);
//                 return httpResponseCode;
//             }
//             http.end();
//         }
//         xSemaphoreGive(xMutex);
//     }
//     return -1;
// }

int http_tts(String issue, String peompt, String refer_wav_path) {
    if (xSemaphoreTake(xMutex, portMAX_DELAY) == pdTRUE) {
        HTTPClient http;
        http.begin(audioStreamUrl);
        http.setTimeout(20000);
        http.addHeader("Content-Type", "application/json");
        jsonDoc["text"] = issue;
        jsonDoc["text_split_method"] = "cut5";
        jsonDoc["batch_size"] = 1;
        jsonDoc["media_type"] = "wav";
        jsonDoc["streaming_mode"] = true;
        jsonDoc["speed_factor"] = 1.0;
        jsonDoc["device_id"] = mac_s;
        // jsonDoc["user_id"] = mac_s;
        String jsonString;
        serializeJson(jsonDoc, jsonString);
        Serial.println(jsonString);
        int httpResponseCode = http.POST(jsonString);
        if (httpResponseCode == 200) {
            Serial.println("开始接收音频流");
            WiFiClient * stream = http.getStreamPtr();            
            while (http.connected()) {
                // 获取 HTTP 流对象
                String chunkLengthStr = stream->readStringUntil('\n');
                int chunkLength = strtol(chunkLengthStr.c_str(), NULL, 16);
    
                if (chunkLength == 0) {
                    Serial.println("音频流接收完成");
                    break;
                }
    
                size_t bytesRead = 0;
                while (bytesRead < chunkLength && http.connected()) {
                   
                    size_t bufferSize = 1024;
                    if (chunkLength - bytesRead < bufferSize) {
                        bufferSize = chunkLength - bytesRead;
                    }
                    uint8_t buffer[bufferSize];
                    int bytesReadThisTime = stream->readBytes(buffer, bufferSize);
    
                    if (bytesReadThisTime > 0) {
                        size_t bytesWritten;
                        // 获取互斥锁
                        // 播放音频数据
                        if (i2s_write(I2S_NUM_0, buffer, bytesReadThisTime, &bytesWritten, portMAX_DELAY) != ESP_OK) {
                            Serial.println("I2S 数据写入失败");
                        }
                        bytesRead += bytesReadThisTime;
                    }
                    delay(1);
                }
                stream->readStringUntil('\n'); // 跳过块结束符
            }
            Serial.println("音频流播放完成");
        } else {
            Serial.printf("HTTP 请求失败，状态码: %d\n", httpResponseCode);
        }
        answer_int=0;
        isplaying=0;
    
        // 确保 HTTP 连接关闭
        if (http.connected()) {
            http.end();
            Serial.println("HTTP 连接已关闭");
        }
        xSemaphoreGive(xMutex);
    }
    return -1;
}

void invertImage(const uint8_t *input, uint8_t *output) {
    int totalBytes = (48 * 48) / 8;
    for (int i = 0; i < totalBytes; i++) {
        output[i] = ~input[i];
    }
}

void input_video(const uint8_t *input, int num) {
    uint8_t inverted_image[(48 * 48) / 8];
    invertImage(input, inverted_image);
    u8g2.drawXBM(30, 0, 48, 48, inverted_image);
    u8g2.sendBuffer();

    if (++currentFrame >= num) {
        currentFrame = 0;
        changci++;
    }
    vTaskDelay(100 / portTICK_PERIOD_MS);
}

void oledTask(void *pvParameters) {
    while (true) {
        u8g2.clearBuffer();
        if (zhuangtai == 0) {
            input_video(zhanyanjing_once[currentFrame], zhanyanjing_once_num);
        } else if (zhuangtai == 1) {
            if (changci == 1) {
                input_video(fennu_in_all[currentFrame], fennu_in_all_num);
            } else if (changci == 2) {
                input_video(fennu_xunhuan_all[currentFrame], fennu_xunhuan_all_num);
            } else if (changci == 3) {
                input_video(fennu_out_all[currentFrame], fennu_out_all_num);
                changci = 1;
                zhuangtai = 2;
            }
        } else if (zhuangtai == 2) {
            input_video(zhanyanjing_twice[currentFrame], zhanyanjing_twice_num);
            changci = 1;
        } else if (zhuangtai = 3) {
            if (changci == 1) {
                input_video(buxie_in_all[currentFrame], buxie_in_all_num);
            } else if (changci == 2) {
                input_video(buxie_xunhuan_all[currentFrame], buxie_xunhuan_all_num);
            } else if (changci == 3) {
                input_video(buxie_out_all[currentFrame], buxie_out_all_num);
                changci = 1;
                zhuangtai = 2;
            }
        }
    }
}



void servoTask(void *parameter) {
    while (true){
        ESP.getFreeHeap();
        motionDetected = digitalRead(pirPin);

        if (motionDetected && !isServoStopped) {
            Serial.println("检测到人体，停止旋转并记录当前位置");
            xPosition = xServo.read();
            yPosition = yServo.read();
            isServoStopped = true;
            time_now = 0;
            vTaskDelete(NULL);
            return;
        } else if (!motionDetected && isServoStopped) {
            Serial.println("无人检测到，继续旋转");
            isServoStopped = false;
            lastMoveTime = millis();
            time_now = lastMoveTime;
        }

        if (!motionDetected && !isServoStopped && (millis() - lastMoveTime > 100)) {
            lastMoveTime = millis();
            xPosition = (xPosition + 5) % 180;
            yPosition = (yPosition + 3) % 90;
            xServo.write(xPosition);
            yServo.write(yPosition);

            Serial.print("X轴角度: ");
            Serial.print(xPosition);
            Serial.print("  Y轴角度: ");
            Serial.println(yPosition);
        }
    }
}


void setup() {
    Serial.begin(115200);
    pinMode(led1, OUTPUT);
    pinMode(led2, OUTPUT);
    audio1.init();
    audio.setPinout(I2S_BCLK, I2S_LRC, I2S_DOUT);
    audio.setVolume(100);
    // 初始化SPIFFS
    if (!SPIFFS.begin()) {
        Serial.println("An error has occurred while mounting SPIFFS");
    }
    else{
        Serial.println("An success has occurred while mounting SPIFFS");

    }
    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);
    Serial.print("MAC地址: ");
    for (int i = 0; i < 6; i++) {
      Serial.printf("%02X", mac[i]);
      mac_s=mac_s + mac[i];
    }
    url1=url1+mac_s;
    Serial.println(url1);
    pinMode(VIBRATION_SENSOR_PIN, INPUT_PULLUP);
    xServo.attach(xServoPin);
    yServo.attach(yServoPin);
    pinMode(pirPin, INPUT);
    u8g2.begin();
    xTaskCreate(oledTask, "OLED Task", 4096, NULL, 1, NULL);
    xServo.write(xPosition);
    yServo.write(yPosition);
    xTaskCreate(servoTask, "Servo Task", 2048, NULL, 1, NULL);

    // 初始化互斥锁
    xMutex = xSemaphoreCreateMutex();
    if (xMutex == NULL) {
        Serial.println("Mutex creation failed");
    }
    pinMode(LED, OUTPUT);
    digitalWrite(LED, LOW);

    // 注册 WiFi 断开事件处理
    WiFi.onEvent(WiFiEvent);

    connectToWiFi(); // 尝试连接 WiFi
    pinMode(0, INPUT_PULLUP);
    Serial.println("系统初始化完成");
}


void loop() {
    if (isAPMode) {
        dnsServer.processNextRequest();
        Serial.println("开始播放音频");
        unsigned long currentTime = millis();
        if ((currentTime - previousTime >= interval )and (audio.isRunning()==0)) {
            audio.connecttoFS(SPIFFS, "/1733972530306.mp3");
            previousTime = currentTime;
        }
        audio.loop();
        return; // 避免后续逻辑干扰 AP 模式
    }

    if (WiFi.status() != WL_CONNECTED and wifi_type==1) {
        wifi_type=0;
        connectToWiFi(); // 如果 WiFi 断开，重新连接
    }
    if (WiFi.status() == WL_CONNECTED and wifi_type==1)
    {
        UBaseType_t stackHighWaterMark = uxTaskGetStackHighWaterMark(NULL);
        webSocketClient1.poll();
        delay(20);
        motionDetected = digitalRead(pirPin);
        int sensorValue = analogRead(VIBRATION_SENSOR_PIN);
        // Serial.println("\nboot按键状态");  // 输出 GPIO0 的状态
        // Serial.println(digitalRead(0));  // 输出 GPIO0 的状态
        if (digitalRead(0) == LOW){
            Serial.print(ESP.getFreeHeap());
            time_now=0;
            start_other = 1;
            Serial.print("\n振动传感器值: ");
            Serial.println(sensorValue);
            if (xSemaphoreTake(xMutex, portMAX_DELAY) == pdTRUE) {
                audio.stopSong();
                xSemaphoreGive(xMutex);
            }
        }
        start_other = 1;
        if (start_other == 1){
            if (isplaying == 0 && audio.isRunning()==0){
                Serial.print(ESP.getFreeHeap());
                Serial.print("audio is not playing");
                ConnServer1();
                time_now=0;
            }
            if (audio.isRunning()==0){
                if (time_now == 0) {
                    time_now = millis();
                } else if ((millis() - time_now) > 30000) {
                    isplaying == 0;
                }
            }

        }
    }

    audio.loop();
}

// void audio_info(const char *info){
//     Serial.print("info        "); Serial.println(info);
// }
// void audio_id3data(const char *info){
//     Serial.print("id3data     ");Serial.println(info);
// }
// void audio_eof_mp3(const char *info){
//     isplaying=0;
//     Serial.print("eof_mp3     ");Serial.println(info);
// }
// void audio_showstation(const char *info){
//     Serial.print("station     ");Serial.println(info);
// }
// void audio_showstreamtitle(const char *info){
//     Serial.print("streamtitle ");Serial.println(info);
// }
// void audio_bitrate(const char *info){
//     Serial.print("bitrate     ");Serial.println(info);
// }
// void audio_commercial(const char *info){
//     Serial.print("commercial  ");Serial.println(info);
// }
// void audio_icyurl(const char *info){
//     Serial.print("icyurl      ");Serial.println(info);
// }
// void audio_lasthost(const char *info){
//     Serial.print("lasthost    ");Serial.println(info);
// }
// void audio_eof_speech(const char *info){
//     Serial.print("eof_speech  ");Serial.println(info);
// }

float calculateRMS(uint8_t *buffer, int bufferSize) {
    float sum = 0;
    int16_t sample;

    for (int i = 0; i < bufferSize; i += 2) {
        sample = (buffer[i + 1] << 8) | buffer[i];
        sum += sample * sample;
    }

    sum /= (bufferSize / 2);

    return sqrt(sum);
}