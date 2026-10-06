import os

from dotenv import load_dotenv
from openai import OpenAI

# load_dotenv() 会读取同目录下的 .env 文件，
# 把里面的 KEY=VALUE 一行行塞进"环境变量"，之后用 os.getenv 就能取出来
load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise RuntimeError("没找到 DEEPSEEK_API_KEY，请检查 .env 文件是否存在、变量名是否拼对")

# 初始化客户端（DeepSeek 官方兼容写法）
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

# 定义一个最简单的工具：获取当前时间（本地执行，不依赖网络）
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前系统时间",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            },
        }
    }
]

def get_current_time():
    from datetime import datetime

    # astimezone() 把"裸时间"标注成本机时区，返回带时区信息的时间
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

# 第一轮：让模型决定要不要调用工具
messages = [{"role": "user", "content": "现在几点了？请用工具查询。"}]

response = client.chat.completions.create(
    model="deepseek-chat",          # 或者 deepseek-flash / deepseek-v4-pro，按你账号支持的改
    messages=messages,
    tools=tools,
    tool_choice="auto"
)

message = response.choices[0].message
print("=== 第一轮模型返回 ===")
print(message)

# 检查有没有 tool_calls
if message.tool_calls:
    print("\n=== 模型触发了 tool calling ===")
    tool_call = message.tool_calls[0]
    print(f"调用的函数: {tool_call.function.name}")
    print(f"参数: {tool_call.function.arguments}")

    # 本地真正执行工具
    if tool_call.function.name == "get_current_time":
        tool_result = get_current_time()
        print(f"工具执行结果: {tool_result}")

        # 把工具结果回传给模型
        messages.append(message)  # 把模型的 tool_call 消息加进去
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": tool_result
        })

        # 第二轮：模型拿到工具结果后给出最终回答
        final_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools
        )
        print("\n=== 最终回答 ===")
        print(final_response.choices[0].message.content)
else:
    print("模型没有触发 tool calling，直接回答了：")
    print(message.content)