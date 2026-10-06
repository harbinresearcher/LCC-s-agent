import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # 读取同目录下的 .env，把里面的 KEY=VALUE 塞进环境变量

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise RuntimeError("没找到 DEEPSEEK_API_KEY，请检查 .env 文件是否存在、变量名是否拼对")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)

# 定义一个工具：执行Python代码
tools = [
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "在本地执行一段Python代码，并返回执行结果或报错信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要执行的完整Python代码"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "把内容写入本地文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "文件名，例如 fib.py"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的完整内容"
                    }
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取本地文件内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "文件名，例如 fib.py"
                    }
                },
                "required": ["filename"]
            }
        }
    }
]


def run_python(code: str) -> str:
    """本地真正执行Python代码，返回stdout或报错"""
    try:
        # 用临时目录：代码执行完目录自动删除，不会往项目里丢 temp_code.py 垃圾文件
        # ⚠️ 注意：写文件这一步本身不提供任何安全保护 —— 这段代码是在你本机、以你的权限真实运行的
        with tempfile.TemporaryDirectory() as tmpdir:
            script = Path(tmpdir) / "temp_code.py"
            script.write_text(code, encoding="utf-8")

            result = subprocess.run(
                [sys.executable, str(script)],  # sys.executable = 当前正在跑的这个 python 解释器
                capture_output=True,
                text=True,
                # Windows 控制台默认是 GBK，模型生成的代码里只要有 ✓/emoji/中文就可能
                # UnicodeEncodeError 崩掉。这两组参数强制子进程输出和读取都用 UTF-8。
                encoding="utf-8",
                errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                timeout=10,
                check=False,  # 退出码非 0 时不抛异常，下面手动看 returncode
            )

        if result.returncode == 0:
            return f"执行成功:\n{result.stdout}"
        return f"执行失败(退出码 {result.returncode}):\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "执行失败：代码运行超过 10 秒，已强制终止"
    except OSError as e:
        return f"执行异常: {e}"


def write_file(filename: str, content: str) -> str:
    """把内容写入本地文件，返回成功/失败信息"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"写入成功:{filename}"
    except OSError as e:
        return f"写入失败:{e}"


def read_file(filename: str) -> str:
    """读取本地文件内容，返回文件内容或失败信息"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        return f"读取成功:\n{content}"
    except OSError as e:
        return f"读取失败:{e}"


def chat_with_tools(messages: list[Any]) -> Any:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    return response.choices[0].message

# ========== 主循环（你要重点理解这里） ==========
def run_agent(task: str, max_rounds: int = 8) -> str:
    messages = [
        {"role": "system", "content": "你是一个能写代码并测试的助手。需要执行代码时，必须调用run_python工具。"},
        {"role": "user", "content": task}
    ]

    for round_num in range(max_rounds):
        print(f"\n===== 第 {round_num + 1} 轮 =====")
        message = chat_with_tools(messages)
        messages.append(message)
        
        # 如果没有tool_calls，说明模型认为已经完成
        if not message.tool_calls:
            print("模型最终回答：")
            print(message.content)
            return message.content
        
        # 有tool_calls，执行工具
        for tool_call in message.tool_calls:
            if tool_call.function.name == "run_python":
                args = json.loads(tool_call.function.arguments)
                code = args.get("code", "")
                print(f"模型要执行的代码：\n{code}")
                
                # 真正执行
                result = run_python(code)
                print(f"执行结果：\n{result}")
                
                # 把结果回传
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            elif tool_call.function.name == "write_file":
                args = json.loads(tool_call.function.arguments)
                filename = args.get("filename", "")
                content = args.get("content", "")
                print(f"模型要写入的文件：\n{filename}")
                print(f"模型要写入的内容：\n{content}")
                
                # 真正执行
                result = write_file(filename, content)
                print(f"执行结果：\n{result}")
                
                # 把结果回传
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            elif tool_call.function.name == "read_file":
                args = json.loads(tool_call.function.arguments)
                filename = args.get("filename", "")
                print(f"模型要读取的文件：\n{filename}")
                
                # 真正执行
                result = read_file(filename)
                print(f"执行结果：\n{result}")
                
                # 把结果回传
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
    
    return "达到最大轮次，未完成"

# 测试
if __name__ == "__main__":
    task = "读取 fib.py 的内容，在文件末尾追加一行注释 # tested by mini_agent，然后把修改后的完整内容重新写回 fib.py。"
    run_agent(task)