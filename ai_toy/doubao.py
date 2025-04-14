import os
from volcenginesdkarkruntime import Ark
# # 从环境变量中获取您的API KEY，配置方法见：https://www.volcengine.com/docs/82379/1399008
#
# completion = client.chat.completions.create(
#     # 替换 <Model> 为模型的Model ID
#     model="doubao-1-5-pro-32k-250115",
#     messages = [
#         {"role": "system", "content": "你是豆包，是由字节跳动开发的 AI 人工智能助手"},
#     ],
# )
# print(completion.choices[0].message.content)

class DouBao_chat():
    def __init__(self):
        self.client = Ark(
                            api_key="自己的api_key",
                            base_url="https://ark.cn-beijing.volces.com/api/v3",
                        )
        self.user_message = {}

    def doubao_chat_all(self, text, user_id, user_sheding):
        if user_id not in self.user_message.keys():
            self.user_message[user_id] = user_sheding
        message = self.user_message[user_id]
        message.append({"role": "user", "content": text})
        completion = self.client.chat.completions.create(
            # 替换 <Model> 为模型的Model ID
            model="doubao-1-5-pro-256k-250115",
            messages=message
        )
        print(completion.choices[0].message.content)
        message.append({"role": "system", "content": completion.choices[0].message.content})
        self.user_message[user_id] = message
        print(completion)
        return completion.choices[0].message.content

    def doubao_chat(self, message):
        completion = self.client.chat.completions.create(
            # 替换 <Model> 为模型的Model ID
            model="doubao-1-5-pro-256k-250115",
            messages=message
        )
        print(completion.choices[0].message.content)
        print(completion)
        return completion.choices[0].message.content

if __name__ == "__main__":
    doubao = DouBao_chat()
    while True:
        text = input("输入对话")
        doubao.doubao_chat_all(text, "123")
# from volcenginesdkarkruntime import Ark
#
# client = Ark(
#     api_key="",
#     base_url="https://ark.cn-beijing.volces.com/api/v3",
# )
#
# # Non-streaming:
# print("----- standard request -----")
# completion = client.chat.completions.create(
#     model="doubao-1-5-pro-32k-250115",
#     messages = [
#         {"role": "system", "content": "你是人工智能助手"},
#         {"role": "user", "content": "常见的十字花科植物有哪些？"},
#     ],
# )
# print(completion.choices[0].message.content)
#
# # Streaming:
# print("----- streaming request -----")
# stream = client.chat.completions.create(
#     model="doubao-1-5-pro-32k-250115",
#     messages = [
#         {"role": "system", "content": "你是人工智能助手"},
#         {"role": "user", "content": "常见的十字花科植物有哪些？"},
#     ],
#     stream=True
# )
# for chunk in stream:
#     if not chunk.choices:
#         continue
#     print(chunk.choices[0].delta.content, end="")
# print()