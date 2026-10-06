# LCC-s-agent

一个不到 200 行、不依赖 LangChain/LangGraph 等任何 Agent 框架的手写 coding agent —— 靠 DeepSeek 的 tool calling 让模型自己决定何时执行代码、读写文件，循环执行直到任务完成。

运行：`pip install -r requirements.txt && python mini_agent.py`（需先把 `DEEPSEEK_API_KEY` 填进同目录的 `.env`，可复制 `.env.example` 改名）

支持 3 个工具：`run_python`（本地执行 Python 代码）、`write_file`（写入文件）、`read_file`（读取文件）。

