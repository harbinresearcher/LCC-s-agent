# LCC-s-agent

一个不依赖 LangChain/LangGraph 等任何 Agent 框架的手写 coding agent —— 靠 DeepSeek 的 tool calling 让模型自己决定何时执行命令、读写文件，循环执行直到任务完成。

运行：`pip install -r requirements.txt && python mini_agent.py`（需先把 `DEEPSEEK_API_KEY` 填进同目录的 `.env`，可复制 `.env.example` 改名）

支持 5 个工具：

- `run_python` —— 本地执行一段 Python 代码
- `read_file` —— 读取文件内容
- `write_file` —— 写入文件
- `list_files` —— 列出目录下的文件
- `run_shell` —— 执行 shell 命令

`examples/` 目录里是 agent 自己跑出来的产物（不是手写代码），可以看它实际输出长什么样。


