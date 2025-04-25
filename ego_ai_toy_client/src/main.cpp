#include <Arduino.h>
#include "base64.h"
#include "HTTPClient.h"
#include "Audio1.h"
#include <ArduinoJson.h>
#include <ArduinoWebsockets.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <Preferences.h>
#include <DNSServer.h>
#include <WiFi.h>
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

const int BOOT_BUTTON_PIN = 0;

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
bool ws_connected = false;
WebsocketsClient webSocketClient1;
HTTPClient https;
Audio1 audio1;
// Audio audio;
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
bool motionDetected = false, isServoStopped = false, bootButtonPressed=false;
bool ledstatus = true, startPlay = false, type_audio_play=false;

int noise = 100, answer_int = 0, isplaying = 0;
unsigned long time_now = 0, lastMoveTime = 0;
String mac_s = "";

// 基础 WebSocket 服务器地址
String baseUrl1 = "ws://localhost:27000/ws/transcribe_chat/";
String url1;
const char charset[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
int speaker_time = 0;
// 互斥锁
SemaphoreHandle_t xMutex;

#define AUDIO_BUFFER_SIZE 8192
uint8_t audioBuffer[AUDIO_BUFFER_SIZE];
size_t bufferPos = 0;

/**
 * @brief 配置并初始化 I2S 接口，用于音频数据的传输。
 * 
 * 此函数设置 I2S 接口的工作模式、采样率、数据格式等参数，并将其与特定的引脚关联。
 * 同时，它会安装 I2S 驱动，清零 DMA 缓冲区，并验证实际的采样率。
 */
void setupI2S() {
    // I2S配置
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = 16000,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 1024,
        .use_apll = true,      // 使用APLL获得更精确的时钟
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0
    };

    // I2S引脚配置
    i2s_pin_config_t pin_config = {
        .bck_io_num = 26,     // BCLK引脚
        .ws_io_num = 25,      // LRC引脚
        .data_out_num = 27,   // DATA输出引脚
        .data_in_num = I2S_PIN_NO_CHANGE
    };

    // 安装并配置I2S驱动
    i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_NUM_0, &pin_config);
    i2s_zero_dma_buffer(I2S_NUM_0);

    // 验证实际采样率（修正后的调用方式）
    float actual_rate = i2s_get_clk(I2S_NUM_0);
    Serial.printf("Actual I2S sample rate: %.0f Hz\n", actual_rate);
}

/**
 * @brief 处理 WebSocket 接收到的消息的回调函数
 * 
 * 该函数会根据 BOOT 按钮的状态、消息类型（文本或二进制）进行不同的处理。
 * 当 BOOT 按钮被按下时，会发送特定的 JSON 消息；
 * 当接收到文本消息时，会尝试解析 JSON 数据；
 * 当接收到二进制消息时，会将数据写入 I2S 缓冲区。
 * 
 * @param message 接收到的 WebSocket 消息对象
 */
void onMessageCallback1(WebsocketsMessage message) {
    Serial.print("bootButtonPressed:" +String(bootButtonPressed));
    if (bootButtonPressed){
        DynamicJsonDocument doc(3000);
        JsonObject data = doc.createNestedObject("data");
        data["status"] = 0;
        data["mac_s"] = mac_s;
        String jsonString;
        serializeJson(doc, jsonString);
        webSocketClient1.send(jsonString);
        isplaying = 1;
        type_audio_play = true;
        Serial.println("Send message to server");
        return;
    }
    if (message.isText()) {
        Serial.println(message.data());
        // 处理文本消息
        StaticJsonDocument<2048> jsonDocument;
        DeserializationError error = deserializeJson(jsonDocument, message.data());
        if (error) {
            Serial.print(F("反序列化失败: "));
            Serial.println(error.f_str());
        } else {
            // 反序列化成功，可以访问 JSON 数据
            Serial.println("JSON 解析成功");
            // 示例：访问 JSON 中的键值对
            if (jsonDocument["status"] == 2) {
                Serial.print("key 的值是: ");
                type_audio_play =true;
                isplaying = 1;
                return;
            }
        }
    }
    if (message.isBinary()) {
        // 处理二进制数据
        size_t len = message.length();
        Serial.printf("Received binary data of length: %zu\n", len);

        size_t byte_written;
        esp_err_t err = i2s_write(I2S_NUM_0, message.c_str(), len, &byte_written, portMAX_DELAY);
        if(err == ESP_OK) {
            if(byte_written == len) {
                type_audio_play = true; 
                // 所有数据已成功写入I2S缓冲区
                Serial.println("All data written to I2S");
            } else {
                // 只有部分数据被写入
                Serial.printf("Partial write: %d/%d bytes\n", byte_written, len);
            }
        } else {
            Serial.printf("I2S write error: %d\n", err);
        }
    }

}


/**
 * @brief 采集音频数据并发送到云服务器
 * 
 * 此函数会持续采集音频数据，计算音频的均方根值（RMS），根据 RMS 值判断音频是否静音。
 * 当检测到静音状态达到一定时长时，会发送特定状态的 JSON 消息到云服务器，然后退出循环。
 * 在首次发送和非首次发送时，会发送不同状态的 JSON 消息。
 * 这里使用了基于声音能量的检测，当声音能量低于设定的噪声阈值时，认为处于静音状态。
 * 同时，为了避免频繁发送消息，会在静音状态持续一段时间后才发送消息。
 * 但是这里会有识别问题，有时候一句话没识别完成就关闭了。
 * 后续更新代码后会进行优化。
 */
void audio_get(){
    Serial.println("Send message to server");
    int silence = 0, firstframe = 1, j = 0, voicebegin = 0, voice = 0, readyStartSleep = 0;
    DynamicJsonDocument doc(3000);

    while (true) {
        digitalWrite(LED, HIGH);
        ledstatus = !ledstatus;
        doc.clear();
        JsonObject data = doc.createNestedObject("data");
        audio1.Record();
        float rms = calculateRMS((uint8_t *)audio1.wavData[0], 1280);
        unsigned long currentTime = millis();
        Serial.println(rms);
        if (rms < noise) {   
            readyStartSleep++;
            if (voicebegin == 1) silence++;
        } else {
            voice++;
            if (voice >= 5) voicebegin = 1;
            else voicebegin = 0;
            silence = 0;
        }

        if (silence == 10) {   
            readyStartSleep = 0;
            data["status"] = 2;
            data["format"] = "audio/L16;rate=8000";
            String base64Audio = base64::encode((byte *)audio1.wavData[0], 1280);
            const char* utf8Audio = base64Audio.c_str();
            data["audio"] = utf8Audio;
            data["mac_s"] = mac_s;
            data["encoding"] = "raw";
            j++;
            String jsonString;
            serializeJson(doc, jsonString);
            webSocketClient1.send(jsonString);
            delay(40);
            isplaying = 0;
            type_audio_play = false;
            bootButtonPressed = false;
            digitalWrite(LED, LOW);
            break;
        }
        
        if (firstframe == 1) {
            j++;
            firstframe = 0;
            delay(40);
        } else {   
            data["status"] = 1;
            data["format"] = "audio/L16;rate=8000";
            String base64Audio = base64::encode((byte *)audio1.wavData[0], 1280);
            const char* utf8Audio = base64Audio.c_str();
            data["audio"] = utf8Audio;
            data["mac_s"] = mac_s;
            data["encoding"] = "raw";
            String jsonString;
            serializeJson(doc, jsonString);
            webSocketClient1.send(jsonString);
            readyStartSleep = 0;
            delay(40);
        }
    }
    doc.clear();
}

/**
 * @brief WebSocket 事件回调函数，处理不同类型的 WebSocket 事件
 * 
 * 当 WebSocket 连接打开时，该函数会持续采集音频数据，计算音频的均方根值（RMS），
 * 根据 RMS 值判断音频是否静音。当检测到静音状态达到一定时长时，会发送特定状态的 JSON 消息到服务器。
 * 当 WebSocket 连接关闭、收到 Ping 或 Pong 消息时，会打印相应的日志信息。
 * 这里有些问题，这里的回调函数因该是用于连接的鉴权等功能，因为为开源版本，所以删去这个功能，用于音频的采集和发送。
 * @param event WebSocket 事件类型
 * @param data 与事件相关的数据
 */
void onEventsCallback1(WebsocketsEvent event, String data) {
    if (event == WebsocketsEvent::ConnectionOpened) {
        Serial.println("Send message to xunfeiyun");
        int silence = 0, firstframe = 1, j = 0, voicebegin = 0, voice = 0, readyStartSleep = 0;
        DynamicJsonDocument doc(3000);

        while (true) {
            digitalWrite(LED, HIGH);
            ledstatus = !ledstatus;
            doc.clear();
            JsonObject data = doc.createNestedObject("data");
            audio1.Record();
            float rms = calculateRMS((uint8_t *)audio1.wavData[0], 1280);
            unsigned long currentTime = millis();
            Serial.println(rms);
            if (rms < noise) {   
                readyStartSleep++;
                if (voicebegin == 1) silence++;
            } else {
                voice++;
                if (voice >= 5) voicebegin = 1;
                else voicebegin = 0;
                silence = 0;
            }

            if (silence == 10) {   
                readyStartSleep = 0;
                data["status"] = 2;
                data["format"] = "audio/L16;rate=8000";
                String base64Audio = base64::encode((byte *)audio1.wavData[0], 1280);
                const char* utf8Audio = base64Audio.c_str();
                data["audio"] = utf8Audio;
                data["mac_s"] = mac_s;
                data["encoding"] = "raw";
                j++;
                String jsonString;
                serializeJson(doc, jsonString);
                webSocketClient1.send(jsonString);
                delay(40);
                isplaying = 0;
                type_audio_play = false;
                digitalWrite(LED, LOW);
                break;
            }
            
            if (firstframe == 1) {
                j++;
                firstframe = 0;
                delay(40);
            } else {   
                data["status"] = 1;
                data["format"] = "audio/L16;rate=8000";
                String base64Audio = base64::encode((byte *)audio1.wavData[0], 1280);
                const char* utf8Audio = base64Audio.c_str();
                data["audio"] = utf8Audio;
                data["mac_s"] = mac_s;
                data["encoding"] = "raw";
                String jsonString;
                serializeJson(doc, jsonString);
                webSocketClient1.send(jsonString);
                readyStartSleep = 0;
                delay(40);
            }
        }
        doc.clear();
    } else if (event == WebsocketsEvent::ConnectionClosed) {
        ws_connected = false;
        Serial.println("Connnection1 Closed");
    } else if (event == WebsocketsEvent::GotPing) {
        // type_audio_play =true;
        // isplaying = 1;
        Serial.println("Got a Ping!");
    } else if (event == WebsocketsEvent::GotPong) {
        Serial.println("Got a Pong!");
    }
}
/**
 * @brief 生成一个随机的 6 位字符串
 * 
 * 该字符串由大写字母、小写字母和数字组成。
 * 
 * @return String 生成的随机 6 位字符串
 */
String generateRandomString() {
    const char charset[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    const int length = 6;
    String randomString = "";

    // 初始化随机数种子
    srand(time(NULL));

    for (int i = 0; i < length; i++) {
        int index = rand() % sizeof(charset);
        randomString += charset[index];
    }

    return randomString;
}



/**
 * @brief 连接到 WebSocket 服务器1
 * 
 * 此函数用于尝试连接到指定的 WebSocket 服务器。在连接之前，会获取互斥锁以确保线程安全。
 * 它会构建完整的 WebSocket 服务器 URL，设置消息和事件的回调函数，然后尝试建立连接。
 * 连接成功或失败后会打印相应的日志信息，并释放互斥锁。
 * 互斥锁是之前的项目里，由于打断音频时会有声音的冲突导致的，现在的项目中仍保留这个功能，防止音频的堵塞
 */
void ConnServer1() {
    if (xSemaphoreTake(xMutex, portMAX_DELAY) == pdTRUE) {
        // xTaskCreate(audioPlayTask, "AudioPlayTask", 4096, NULL, 1, NULL);
        String randomStr = generateRandomString();
        url1 = baseUrl1 + mac_s + "/" + randomStr;
        Serial.println("url1:" + url1);
        webSocketClient1.onMessage(onMessageCallback1);
        webSocketClient1.onEvent(onEventsCallback1);
        Serial.println("Begin connect to server1......");
        if (webSocketClient1.connect(url1.c_str())) { 
            ws_connected = true;
            Serial.println("Connected to server1!");
        } else {
            Serial.println("Failed to connect to server1!");
        }
        xSemaphoreGive(xMutex);
    }
}

// 启动 Captive Portal 配置 WiFi
/**
 * @brief 启动 Captive Portal 模式以配置 WiFi
 * 
 * 此函数将设备设置为 AP 模式，创建一个热点供用户连接。
 * 同时启动 DNS 服务器，拦截所有域名解析请求，将用户重定向到 WiFi 配置页面。
 * 用户可以通过访问配置页面输入 WiFi 的 SSID 和密码，配置信息将保存到 NVS 中，
 * 设备随后会重启以尝试连接新配置的 WiFi。
 */
void startCaptivePortal() {    
    // 设置 AP 模式
    WiFi.mode(WIFI_AP);
    WiFi.softAP("EgoStar_"+mac_s, "");
    WiFi.softAPConfig(apIP, apIP, IPAddress(255, 255, 255, 0)); // 设置静态 IP
    Serial.println("AP 模式启动，SSID: ESP32_Config，密码: 12345678");
    Serial.println("请连接 WiFi 并访问 http://192.168.4.1 配置 WiFi");
    // 启动 DNS 服务器
    dnsServer.start(DNS_PORT, "*", apIP); // 拦截所有域名解析

    // 配置主页面，将所有请求重定向到配置WiFi页面
    server.onNotFound([](AsyncWebServerRequest *request) {
        request->redirect("/setwifi");
    });

    // 配置页面，提交 WiFi 配置
    server.on("/setwifi", HTTP_GET, [](AsyncWebServerRequest *request) {
        String html = R"rawliteral(
          <!DOCTYPE html>
          <html lang="zh-CN">
          <head>
          <meta charset="UTF-8">
          <title>配置 WiFi</title>
          </head>
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
        request->send(200, "text/html; charset=UTF-8", html);
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
            String successHtml = R"rawliteral(
              <!DOCTYPE html>
              <html lang="zh-CN">
              <head>
              <meta charset="UTF-8">
              <title>配置成功</title>
              <script>
                window.onload = function() {
                  setTimeout(function() {
                    window.location.href = 'http://192.168.4.1';
                  }, 3000);
                };
              </script>
              </head>
              <body>
              <h1>配置成功！正在尝试连接 WiFi...</h1>
              <p>请断开 ESP32 热点，连接您的 WiFi 网络。</p>
              </body>
              </html>
            )rawliteral";
            request->send(200, "text/html; charset=UTF-8", successHtml);
            delay(1000);
            ESP.restart(); // 重启设备以尝试连接配置的 WiFi
        } else {
            request->send(400, "text/plain; charset=UTF-8", "缺少参数");
        }
    });
    server.begin();
}

// 连接到 WiFi
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
        wifi_success = 1;
        Serial.println("\nWiFi 已连接！");
        Serial.print("IP 地址: ");
        Serial.println(WiFi.localIP());
        digitalWrite(LED, HIGH);
        isAPMode = false; // 确保标志切换到正常模式
        wifi_type = 1;
        ConnServer1(); // 连接 WebSocket 服务器
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
        WiFi.reconnect();
    }
}

// 之前的64x64位图片转换函数
void invertImage(const uint8_t *input, uint8_t *output) {
    int totalBytes = (48 * 48) / 8;
    for (int i = 0; i < totalBytes; i++) {
        output[i] = ~input[i];
    }
}

/**
 * @brief 计算输入数据的 CRC-16 校验值
 * 
 * 此函数使用 CRC-16-CCITT 算法计算给定数据缓冲区的 CRC-16 校验值。
 * CRC-16-CCITT 多项式为 0x1021，初始值为 0xFFFF。
 * 
 * @param data 指向要计算 CRC 的数据缓冲区的指针
 * @param length 数据缓冲区的长度（字节数）
 * @return uint16_t 计算得到的 CRC-16 校验值
 */
uint16_t crc16(const uint8_t *data, size_t length) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < length; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; j++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}

// 新函数：用于在线程中检测 BOOT 按钮是否被按下
/**
 * @brief 检测 BOOT 按钮是否被按下
 */
void bootButtonCheckTask(void *parameter) {
    while (true) {
        // 读取 BOOT 按钮状态
        bool buttonState = digitalRead(BOOT_BUTTON_PIN) == LOW;
        if (buttonState) {
            bootButtonPressed = true;
            Serial.println("BOOT 按钮被按下");
        } 
        // 适当延迟以减少 CPU 使用率
        vTaskDelay(100 / portTICK_PERIOD_MS);
    }
}

void setup() {
    Serial.begin(115200);
    pinMode(led1, OUTPUT);
    pinMode(led2, OUTPUT);
    audio1.init();
    setupI2S();

    // audio.setPinout(I2S_BCLK, I2S_LRC, I2S_DOUT);
    // audio.setVolume(20);
    uint8_t mac[6];
    esp_err_t err = esp_efuse_mac_get_default(mac);
    Serial.print("MAC地址: ");
    if (err == ESP_OK) {
        // 计算 CRC-16 哈希值
        uint16_t hash = crc16(mac, 6);

        for (int i = 0; i < 6; i++) {
            int index = hash % sizeof(charset);
            mac_s = charset[index] + mac_s;
            hash /= sizeof(charset);
        }

        Serial.println("6位字符串: " + mac_s);
    } else {
        Serial.printf("读取 MAC 地址失败。错误代码: 0x%x\n", err);
    }
    pinMode(VIBRATION_SENSOR_PIN, INPUT_PULLUP);
    // xServo.attach(xServoPin);
    // yServo.attach(yServoPin);
    pinMode(pirPin, INPUT);
    // u8g2.begin();
    // xTaskCreate(oledTask, "OLED Task", 4096, NULL, 1, NULL);
    xMutex = xSemaphoreCreateMutex();
    if (xMutex == NULL) {
        Serial.println("Mutex creation failed");
    }
    pinMode(LED, OUTPUT);
    digitalWrite(LED, LOW);
    // 注册 WiFi 断开事件处理
    WiFi.onEvent(WiFiEvent);
    connectToWiFi(); // 尝试连接 WiFi
    pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);
    xTaskCreate(bootButtonCheckTask, "BootButtonCheck", 1024, NULL, 1, NULL);

    Serial.println("系统初始化完成");
}

void loop() {
    // 检测 BOOT 按钮是否被按下
    if (digitalRead(BOOT_BUTTON_PIN) == LOW) {
        bootButtonPressed = true;
            
    } 
    if (WiFi.status() != WL_CONNECTED) {
        if (ledstatus) {
            digitalWrite(LED, HIGH);
        }
        else {
            digitalWrite(LED, LOW);
        }
        ledstatus = !ledstatus;

        // dnsServer.processNextRequest();
        Serial.println("DNS Server is running");
        // audio.connecttoFS(SPIFFS, "/WiFidisconnect.mp3");
    }
    else{
        delay(1);
        if (webSocketClient1.available()) {
            // Serial.println("WebSocket is connected");
            // 可以在这里处理接收到的数据
            webSocketClient1.poll();
            if (type_audio_play == true && isplaying == 1) {
                delay(500);
                audio_get();
            }
        } else {
            Serial.println("WebSocket is not connected");
            // 可以尝试重新连接
            Serial.println("WebSocket is not connected");
            ConnServer1();
            delay(10000);
        }

    }
}

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