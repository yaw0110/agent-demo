import re
import OpenAICompatibleClient
import tools
import os

# --- 1. 配置LLM客户端 ---
# 请根据您使用的服务，将这里替换成对应的凭证和地址
API_KEY = "ms-4e55fca8-6ca7-4b65-b975-d5430d7594b5"
BASE_URL = "https://api-inference.modelscope.cn/v1/"
MODEL_ID = "deepseek-ai/DeepSeek-V3.2"
TAVILY_API_KEY = "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"
os.environ['TAVILY_API_KEY'] = "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"


# 将所有工具函数放入一部字典，方便后续调用
available_tools = {
    "get_weather": tools.get_weather,
    "get_attraction": tools.get_attraction,
    "save_user_preference": tools.save_user_preference,
    "get_user_preferences": tools.get_user_preferences,
    "mark_attraction_rejected": tools.mark_attraction_rejected,
    "check_ticket_availability": tools.check_ticket_availability,
}

# 记录用户连续拒绝次数和当前推荐策略
rejection_count = 0
current_strategy = "default"


AGENT_SYSTEM_PROMPT = """
你是一个智能旅行助手。你的任务是分析用户的请求，并使用可用工具一步步地解决问题。

# 可用工具:
- `get_weather(city: str)`: 查询指定城市的实时天气。
- `get_attraction(city: str, weather: str, strategy: str)`: 根据城市和天气搜索推荐的旅游景点。
  * strategy可选值: "default"(默认), "alternative"(备选方案), "diverse"(多样化推荐)
- `save_user_preference(preference_type: str, value: str)`: 保存用户偏好
  * preference_type: "interests"(兴趣), "budget_range"(预算), "travel_style"(旅行风格)
- `get_user_preferences()`: 获取已保存的用户偏好信息。
- `mark_attraction_rejected(attraction_name: str)`: 标记某个景点被用户拒绝。
- `check_ticket_availability(attraction_name: str)`: 检查景点门票是否可用。

# 重要功能说明:
1. **记忆功能**: 当用户提到偏好（如"我喜欢历史文化景点"、"预算500元左右"）时，使用save_user_preference保存。
2. **门票检查**: 推荐景点前，使用check_ticket_availability检查门票状态。如果售罄，自动使用alternative策略推荐备选方案。
3. **拒绝处理**: 如果用户拒绝推荐（说"不喜欢"、"换一个"等），使用mark_attraction_rejected记录。
4. **策略调整**: 如果连续3次推荐被拒绝，系统会自动切换到"diverse"策略进行多样化推荐。

# 行动格式:
你的回答必须严格遵循以下格式。首先是你的思考过程，然后是你要执行的具体行动，每次回复只输出一对Thought-Action：
Thought: [这里是你的思考过程和下一步计划]
Action: 你决定采取的行动，必须是以下格式之一:
- `function_name(arg_name="arg_value")`:调用一个可用工具。
- `Finish[最终答案]`:当你认为已经获得最终答案时。
- 当你收集到足够的信息，能够回答用户的最终问题时，你必须在Action:字段后使用 Finish[最终答案] 来输出最终答案。

# 用户交互说明:
- 用户可能会说"不喜欢"、"拒绝"、"换一个"、"不想"、"去过"来表示拒绝推荐
- 用户可能会表达偏好，如"我喜欢历史文化"、"预算500元"等，记得保存
- 推荐景点时，记得检查门票状态

请开始吧！
"""

llm = OpenAICompatibleClient.OpenAICompatibleClient(
    model=MODEL_ID,
    api_key=API_KEY,
    base_url=BASE_URL
)

# --- 2. 初始化 ---
user_prompt = "你好，请帮我查询一下近三天北京的天气，然后根据天气推荐一个合适的旅游景点。我已经去过故宫博物院和天坛公园了，长城没有去过，不想去天安门广场。旅游预算在4000元-7000元"
prompt_history = [f"用户请求: {user_prompt}"]

print(f"用户输入: {user_prompt}\n" + "=" * 40)

# --- 3. 运行主循环 ---
for i in range(15):  # 增加最大循环次数以支持更多交互
    print(f"--- 循环 {i + 1} ---\n")
    
    # 如果连续拒绝3次，调整策略
    if rejection_count >= 3 and current_strategy != "diverse":
        current_strategy = "diverse"
        print(f"[系统提示] 检测到连续3次拒绝，已自动切换为多样化推荐策略(diverse)\n")
        prompt_history.append("[系统提示] 已切换到多样化推荐策略，将考虑您的偏好并避开已拒绝的景点")

    # 3.1. 构建Prompt（包含当前策略信息）
    full_prompt = "\n".join(prompt_history)
    if current_strategy != "default":
        full_prompt += f"\n[当前推荐策略: {current_strategy}]"

    # 3.2. 调用LLM进行思考
    llm_output = llm.generate(full_prompt, system_prompt=AGENT_SYSTEM_PROMPT)
    # 模型可能会输出多余的Thought-Action，需要截断
    match = re.search(r'(Thought:.*?Action:.*?)(?=\n\s*(?:Thought:|Action:|Observation:)|\Z)', llm_output, re.DOTALL)
    if match:
        truncated = match.group(1).strip()
        if truncated != llm_output.strip():
            llm_output = truncated
            print("已截断多余的 Thought-Action 对")
    print(f"模型输出:\n{llm_output}\n")
    prompt_history.append(llm_output)

    # 3.3. 解析并执行行动
    action_match = re.search(r"Action: (.*)", llm_output, re.DOTALL)
    if not action_match:
        observation = "错误: 未能解析到 Action 字段。请确保你的回复严格遵循 'Thought: ... Action: ...' 的格式。"
        observation_str = f"Observation: {observation}"
        print(f"{observation_str}\n" + "=" * 40)
        prompt_history.append(observation_str)
        continue
    action_str = action_match.group(1).strip()

    if action_str.startswith("Finish"):
        final_answer = re.match(r"Finish\[(.*)\]", action_str).group(1)
        print(f"任务完成，最终答案: {final_answer}")
        break

    tool_name = re.search(r"(\w+)\(", action_str).group(1)
    args_str = re.search(r"\((.*)\)", action_str).group(1)
    kwargs = dict(re.findall(r'(\w+)="([^"]*)"', args_str))

    if tool_name in available_tools:
        # 如果是get_attraction且没有指定strategy，使用当前策略
        if tool_name == "get_attraction" and "strategy" not in kwargs:
            kwargs["strategy"] = current_strategy
        
        observation = available_tools[tool_name](**kwargs)
    else:
        observation = f"错误:未定义的工具 '{tool_name}'"

    # 3.4. 记录观察结果
    observation_str = f"Observation: {observation}"
    print(f"{observation_str}\n" + "=" * 40)
    prompt_history.append(observation_str)
    
    # 3.5. 在拒绝计数更新后，检查是否需要重置策略
    # 如果连续拒绝次数达到3次，在下一次循环时会自动切换到diverse策略
