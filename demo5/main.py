# --- 工具初始化与使用示例 ---

from demo4.ToolExecutor import ToolExecutor
from demo4.search import search
from dotenv import load_dotenv
from demo3.main import HelloAgentsLLM
from demo5.ReActAgent import ReActAgent

load_dotenv()

if __name__ == '__main__':
    # 1. 初始化工具执行器
    helloAgentsLLM = HelloAgentsLLM()
    toolExecutor = ToolExecutor()
    # 2. 注册我们的实战搜索工具
    search_description = "一个网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，应使用此工具。"
    toolExecutor.registerTool("Search", search_description, search)

    # 3. 打印可用的工具
    print("\n--- 可用的工具 ---")
    print(toolExecutor.getAvailableTools())

    # 4. 智能体的Action调用，这次我们问一个实时性的问题
    # print("\n--- 执行 Action: Search['华为最新发布的手机型号及特点是什么'] ---")
    tool_name = "Search"
    tool_input = "钱大妈什么时候上市"

    agent = ReActAgent(helloAgentsLLM,toolExecutor)
    agent.run(tool_input)