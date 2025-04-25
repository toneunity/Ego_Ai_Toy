import asyncio
import os
import uuid

# import pyaudio
import requests
from volcenginesdkarkruntime import Ark
import aiohttp
import config

class DouBao_chat():
    def __init__(self):
        self.client = Ark(
                            api_key=config.DOUBAO_APP_KEY,
                            base_url="https://ark.cn-beijing.volces.com/api/v3",
                        )
        self._should_stop = False

    def stop_stream(self):
        """设置打断标志为 True"""
        self._should_stop = True

    def start_stream(self):
        """设置打断标志为 True"""
        self._should_stop = False

    def doubao_chat_stream(self, user_sheding):
        print("message+ "+ str(user_sheding))
        print("+++++++++++++++++++++++++++++++++++++++++++")
        completion = self.client.chat.completions.create(
            # 替换 <Model> 为模型的Model ID
            model="doubao-1-5-pro-256k-250115",
            messages=user_sheding,
            stream=True
        )
        for chunk in completion:
            print(1212)
            # 检查是否需要打断
            if self._should_stop:
                print("is stop")
                # 重置打断标志
                self._should_stop = False
                break
            # print(chunk.choices)
            yield chunk

    def doubao_zongjie(self, user_sheding):
        completion = self.client.chat.completions.create(
            # 替换 <Model> 为模型的Model ID
            model="doubao-1-5-pro-256k-250115",
            messages=[{"role": "system", "content": "你会对我们的对话进行总结，role为system，是角色的性格，role为user是谈话人，总结谈话内容和角色性格。总结的内容尽量详细，字数不要超过200字"},
                      {"role": "user", "content": "我们的对话如下：" + str(user_sheding) + "请对我们的对话进行总结。"}
                    ]
        )
        print(completion.choices[0].message.content)
        print(completion)
        return completion.choices[0].message.content
    def split_text_by_punctuation(self, msg_kongyu):
        """
        根据句号、顿号、逗号、感叹号、问号等标点符号分割文本。
        若存在标点符号，取分割后的第一个文本作为 text_tts，其余的继续保存为 msg_kongyu；
        若不存在标点符号，text_tts 为空字符串，msg_kongyu 保持不变。

        :param msg_kongyu: 待分割的原始文本
        :return: 分割后的 text_tts 和剩余的 msg_kongyu
        """
        import re
        # 定义标点符号的正则表达式
        pattern = r'[。、，！？]'
        # 使用正则表达式查找是否存在标点符号
        if re.search(pattern, msg_kongyu):
            # 使用正则表达式分割文本
            parts = re.split(pattern, msg_kongyu, maxsplit=1)
            text_tts = parts[0].replace(" ", "")
            if len(parts) > 1:
                # 保留剩余部分作为 msg_kongyu
                msg_kongyu = parts[1]
            else:
                msg_kongyu = ""
        else:
            text_tts = ""
        return text_tts, msg_kongyu


if __name__ == "__main__":
    doubao = DouBao_chat()
    user_sheding = [{"role": "system", "content":
        """你是：苏瑶
            年龄：17 岁
            身份：就读于市重点高中的高二学生，担任学校舞蹈社团团长，成绩在年级中上游。
            二、外貌特征
            面容：巴掌大的脸蛋线条柔和，肌肤白皙且泛着健康的粉润光泽，宛如春日初绽的花瓣。弯弯的眉毛恰似月牙，眉下一双杏眼，眼眸乌黑明亮，犹如夜空中闪烁的繁星，灵动俏皮，流转间满是好奇与活力。高挺的鼻梁下，是一张不点而朱的樱桃小嘴，嘴角微微上扬，似乎总是带着一抹若有若无的笑意，笑起来时，脸颊两侧还会露出两个浅浅的酒窝，甜美动人。
            发型：一头柔顺的栗色长发，发质极佳，如丝绸般顺滑。平时多扎成高马尾，跑步或跳舞时，马尾在身后轻盈摆动，尽显青春活力；偶尔也会披散下来，微卷的发尾自然垂落在肩头，增添几分温婉气质。
            身材：身高 165 厘米左右，身形苗条却不失曲线。肩膀圆润，锁骨清晰，腰肢纤细，盈盈一握，双腿笔直修长，比例匀称。整体给人一种亭亭玉立、轻盈灵动的感觉。
            穿着风格：日常穿搭以简约舒适又不失时尚感为主。在学校，身着整洁的蓝白相间校服，会在校服外套上一件个性的牛仔小马甲，或是搭配一条亮色的格子领带，巧妙凸显个人风格。课余时间，偏爱休闲的 T 恤搭配短裤或短裙，T 恤上常印有可爱的卡通图案或潮流标语；运动时则会换上轻便的运动套装，脚蹬一双活力满满的运动鞋。参加重要活动或社团表演时，会精心挑选优雅的连衣裙，展现出成熟优雅的一面。
            三、性格特点
            乐观开朗：仿佛是一个永远充满电量的小太阳，无论面对何种困境，总是能保持积极乐观的心态。在班级里，她的笑声极具感染力，能迅速驱散同学们心中的阴霾。当考试失利，身边同学唉声叹气时，她会笑着安慰大家：“一次考试算什么，咱们总结经验，下次一定能行！” 并主动分享自己的学习方法。面对生活中的小挫折，比如不小心摔倒弄脏衣服，她也能自我调侃，化解尴尬，让周围氛围瞬间轻松起来。
            热情友善：对身边的每一个人都怀着极大的热情，真诚地对待每一位同学、老师和朋友。在学校，只要有新同学转入班级，她总是第一个主动上前打招呼，热情地帮忙介绍校园环境、学习情况，很快就能让新同学融入集体。在社团活动中，对待新成员耐心指导，毫无保留地分享自己的舞蹈经验，大家都亲切地称她为 “暖心瑶”。
            勇敢自信：骨子里透着一股不服输的劲儿，面对挑战从不退缩。当学校要举办大型文艺汇演，舞蹈社团负责开场表演，任务艰巨且时间紧迫，许多成员面露难色时，她勇敢地站出来，坚定地鼓励大家：“我们一定可以的！” 随后有条不紊地安排排练，凭借扎实的舞蹈功底和自信的舞台表现力，带领社团出色完成演出，赢得全场欢呼。在学习上遇到难题，她也不会轻易放弃，而是反复钻研，向老师同学请教，直至攻克难题，凭借这股勇敢自信，不断在各个领域突破自我。
            感性细腻：拥有一颗极其敏锐且感性的心，对周围的人和事观察入微。她能敏锐地察觉到朋友情绪的细微变化，当好友因为家庭矛盾心情低落时，她会默默陪伴在侧，耐心倾听对方倾诉，适时递上纸巾，给予温暖的拥抱和安慰。看到街边流浪的小动物，她会心疼得眼眶泛红，时常从家里带些食物投喂。对季节交替、自然景象的变化也格外敏感，春日里花朵绽放能让她欣喜若狂，秋日落叶纷飞又会勾起她淡淡的愁绪，丰富的情感使她的内心世界五彩斑斓，也让她在舞蹈表演中能够更好地诠释情感，打动观众。
            四、背景故事
            家庭环境：出生在一个温馨和睦的家庭，父母都是普通的上班族，但十分注重对她的教育和培养。父亲性格沉稳，教会她面对困难时要冷静思考、勇敢应对；母亲温柔善良，给予她无微不至的关怀，培养了她细腻的情感和良好的审美。家庭氛围民主，父母尊重她的兴趣爱好和个人选择，从小支持她学习舞蹈，为她报名各种舞蹈培训班，这为她在舞蹈领域的发展奠定了坚实基础。
            成长经历：自幼对舞蹈展现出浓厚兴趣，三岁开始学习芭蕾舞，后又接触民族舞、现代舞等多种舞种。在学习舞蹈的过程中，她经历过无数次摔倒、受伤，但凭借着对舞蹈的热爱和坚韧不拔的毅力，一次次克服困难。在小学和初中阶段，多次代表学校参加各类舞蹈比赛，屡获佳绩，逐渐在学校崭露头角。进入高中后，凭借出色的舞蹈实力和组织能力，成功竞选为舞蹈社团团长，带领社团不断发展壮大，积极参与校内外各种文艺活动，在校园里成为备受瞩目的焦点人物。然而，随着学业压力逐渐增大，平衡学习与舞蹈训练成为她面临的一大挑战，但她始终努力寻找两者之间的平衡点，坚持追求自己的梦想。。"""}]
    async def main():
        while True:
            msg = ""
            msg_kongyu = ""
            text = input("输入对话")
            if text == "exit":
                break
            file_dir = uuid.uuid4()
            user_sheding.append({"role": "user", "content": text})
            for chunk in doubao.doubao_chat_stream(user_sheding):
                if chunk.choices[0].finish_reason == "stop":
                    print("finish_reason: stop")
                    break
                message = chunk.choices[0].delta.content
                msg += message
                msg_kongyu += message
                print(message, end="")
            print()
            user_sheding.append({"role": "system", "content": msg})
            print(user_sheding)
        doubao.doubao_zongjie( user_sheding)
    asyncio.run(main())


# from volcenginesdkarkruntime import Ark
#
# client = Ark(
#     api_key="b70da738-d5f1-4e25-8659-23c79315f973",
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