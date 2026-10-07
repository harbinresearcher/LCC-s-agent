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

# 工具列表：用 JSON Schema 描述"有哪些工具可用、每个工具要什么参数"
# 这份描述会随每次请求一起发给模型，模型就是靠它决定该调哪个工具
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
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "列出指定目录下的所有文件，返回文件名列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "要列出的目录路径，默认为当前目录"
                    }
                },
                "required": ["directory"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "执行 shell 命令，返回输出或错误信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的 shell 命令"
                    }
                },
                "required": ["command"]
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


def to_jsonable(obj: Any) -> Any:
    """json.dump 遇到不认识的类型时会调用它：把 openai SDK 的对象转成普通 dict"""
    if hasattr(obj, "model_dump"):  # pydantic v2 模型（当前 openai SDK 用的就是它）
        return obj.model_dump(mode="json")
    return str(obj)  # 兜底：其它怪类型直接转成字符串


def chat_with_tools(messages: list[Any]) -> Any:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    return response.choices[0].message


def list_files(directory: str = ".") -> str:
    """列出指定目录下的所有文件，返回文件名列表"""
    try:
        files = os.listdir(directory)
        return "\n".join(files) if files else "目录为空"
    except OSError as e:
        return f"列出文件失败:{e}"


def run_shell(command: str) -> str:
    """执行 shell 命令，返回输出或错误信息"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return f"执行成功:\n{result.stdout}"
        return f"执行失败(退出码 {result.returncode}):\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "执行失败：命令运行超过 10 秒，已强制终止"
    except OSError as e:
        return f"执行异常: {e}"


# 工具名 -> 真正要执行的 Python 函数。
# 主循环靠这张表，把"模型说要调哪个工具"翻译成"到底该调用哪个函数"
TOOL_FUNCTIONS: dict[str, Any] = {
    "run_python": run_python,
    "write_file": write_file,
    "read_file": read_file,
    "list_files": list_files,
    "run_shell": run_shell,
}


def call_tool(name: str, args: dict[str, Any]) -> str:
    """按名字调用工具，永远返回字符串 —— 出错也返回错误文本，不往外抛异常"""
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"执行失败：没有名为 {name} 的工具"

    try:
        # **args 把字典"展开"成关键字参数：
        #   {"code": "print(1)"}  等价于  func(code="print(1)")
        # 所以工具 schema 里的参数名，必须和函数签名里的参数名一模一样
        return str(func(**args))
    except TypeError as e:
        return f"执行失败：参数与工具定义不匹配（{e}）"


def save_history(messages: list[Any]) -> None:
    """把对话历史存盘，方便调试，也方便下次用 load_history=True 续跑。

    两个坑：
    1. messages 里混着普通 dict 和 SDK 对象，json.dump 不认识后者，
       要靠 default=to_jsonable 告诉它"遇到不认识的类型就调这个函数转换"。
    2. 必须在"这一轮的工具结果都追加完"之后才存。否则存下来的历史末尾，
       会是一条带了 tool_calls 却没有对应 tool 回复的助手消息 ——
       下次 load_history 读回来时会被 API 拒绝。
    """
    with open("history.json", "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2, default=to_jsonable)


# ========== 主循环（你要重点理解这里） ==========
def run_agent(task: str, max_rounds: int = 8, load_history: bool = False) -> str:
    """Agent 循环：模型挑工具 -> 本地执行 -> 结果回传 -> 再问模型，直到模型不再需要工具"""
    if load_history and os.path.exists("history.json"):
        with open("history.json", "r", encoding="utf-8") as f:
            messages = json.load(f)
    else:
        messages = [
            {"role": "system", "content": "你是一个严谨的本地编程助手.你必须通过调用工具来完成任务,禁止直接声称'已完成'而不调用工具.每次获得工具结果之后,根据结果继续下一步操作.如果出错,必须分析错误信息并尝试修正。最终回答前,确保关键步骤都已用工具验证过."},
            {"role": "user", "content": task}
        ]

    for round_num in range(max_rounds):
        print(f"\n===== 第 {round_num + 1} 轮 =====")
        message = chat_with_tools(messages)
        messages.append(message)

        # 如果没有 tool_calls，说明模型认为任务做完了，输出最终回答
        if not message.tool_calls:
            print("模型最终回答：")
            print(message.content)
            save_history(messages)  # 存下完整历史（含所有工具结果）
            return message.content

        # 有 tool_calls，逐个执行
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f"模型要调用 {name}，参数：{args}")

            result = call_tool(name, args)
            print(f"执行结果：\n{result}")

            # 每个 tool_call 都必须回一条 tool 消息，否则下一轮请求会被 API 拒绝
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        # 一轮的工具全部执行完再存盘，保证存下来的历史末尾是完整的
        save_history(messages)

    return "达到最大轮次，未完成"


# 测试
if __name__ == "__main__":
    task = """创建一个简单的计算器项目：
1. 写一个 calc.py，里面有 add、sub、mul、div 四个函数
2. 写一个 test_calc.py，用 assert 测试这四个函数
3. 运行 test_calc.py，确保全部通过
"""
    run_agent(task)