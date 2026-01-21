import requests
import os
from tavily import TavilyClient
import random

# 全局记忆存储（在实际应用中应该使用数据库或文件持久化）
user_memory = {
    "preferences": {
        "interests": ["自然风光", "美食"],  # 如：["历史文化", "自然风光", "美食"]
        "budget_range": None,  # 如："100-500元"
        "travel_style": "休闲",  # 如："休闲", "探险"
    },
    "rejected_attractions": [],  # 记录被拒绝的景点
    "visited_attractions": [],  # 记录已访问的景点
}

# 模拟门票状态（实际应用中应该调用真实API）
ticket_status_cache = {}


def save_user_preference(preference_type: str, value: str) -> str:
    """
    保存用户的偏好信息。
    preference_type: "interests"（兴趣）, "budget_range"（预算范围）, "travel_style"（旅行风格）
    value: 偏好的具体值
    """
    try:
        if preference_type == "interests":
            if value not in user_memory["preferences"]["interests"]:
                user_memory["preferences"]["interests"].append(value)
                return f"已记录您的兴趣偏好: {value}"
            else:
                return f"您的兴趣偏好中已包含: {value}"
        elif preference_type == "budget_range":
            user_memory["preferences"]["budget_range"] = value
            return f"已记录您的预算范围: {value}"
        elif preference_type == "travel_style":
            user_memory["preferences"]["travel_style"] = value
            return f"已记录您的旅行风格: {value}"
        else:
            return f"错误:未知的偏好类型 '{preference_type}'，支持的类型: interests, budget_range, travel_style"
    except Exception as e:
        return f"错误:保存偏好失败 - {e}"


def get_user_preferences() -> str:
    """
    获取已保存的用户偏好信息。
    """
    prefs = user_memory["preferences"]
    result = []
    
    if prefs["interests"]:
        result.append(f"兴趣爱好: {', '.join(prefs['interests'])}")
    if prefs["budget_range"]:
        result.append(f"预算范围: {prefs['budget_range']}")
    if prefs["travel_style"]:
        result.append(f"旅行风格: {prefs['travel_style']}")
    
    if result:
        return "已记录的偏好信息:\n" + "\n".join(f"- {item}" for item in result)
    else:
        return "暂未记录任何偏好信息。"


def mark_attraction_rejected(attraction_name: str) -> str:
    """
    标记某个景点被用户拒绝。
    """
    if attraction_name not in user_memory["rejected_attractions"]:
        user_memory["rejected_attractions"].append(attraction_name)
    return f"已记录您拒绝了景点: {attraction_name}"


def check_ticket_availability(attraction_name: str) -> str:
    """
    检查景点门票是否可用（模拟实现）。
    实际应用中应该调用真实的门票API。
    """
    # 模拟：某些热门景点可能售罄（30%概率）
    if attraction_name not in ticket_status_cache:
        ticket_status_cache[attraction_name] = random.random() > 0.3
    
    if ticket_status_cache[attraction_name]:
        return f"门票状态: {attraction_name} 门票可用"
    else:
        return f"门票状态: {attraction_name} 门票已售罄"


def get_weather(city: str) -> str:
    """
    通过调用 wttr.in API 查询真实的天气信息。
    """
    # API端点，我们请求JSON格式的数据
    url = f"https://wttr.in/{city}?format=j1"

    try:
        # 发起网络请求
        response = requests.get(url)
        # 检查响应状态码是否为200 (成功)
        response.raise_for_status()
        # 解析返回的JSON数据
        data = response.json()

        # 提取当前天气状况
        current_condition = data['current_condition'][0]
        weather_desc = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']

        # 格式化成自然语言返回
        return f"{city}当前天气:{weather_desc}，气温{temp_c}摄氏度"

    except requests.exceptions.RequestException as e:
        # 处理网络错误
        return f"错误:查询天气时遇到网络问题 - {e}"
    except (KeyError, IndexError) as e:
        # 处理数据解析错误
        return f"错误:解析天气数据失败，可能是城市名称无效 - {e}"


def get_attraction(city: str, weather: str, strategy: str = "default") -> str:
    """
    根据城市和天气，使用Tavily Search API搜索并返回优化后的景点推荐。
    
    strategy: 推荐策略 ("default", "alternative", "diverse")
    - "default": 默认推荐
    - "alternative": 备选方案（避开已拒绝的景点）
    - "diverse": 多样化推荐（避开已拒绝的景点，考虑用户偏好）
    """
    # 1. 从环境变量中读取API密钥
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return "错误:未配置TAVILY_API_KEY环境变量。"

    # 2. 初始化Tavily客户端
    tavily = TavilyClient(api_key=api_key)

    # 3. 根据策略和用户偏好构造查询
    prefs = user_memory["preferences"]
    query_parts = [f"'{city}'", f"'{weather}'天气"]
    
    if strategy == "diverse":
        # 多样化策略：考虑用户偏好
        if prefs["interests"]:
            query_parts.append(f"喜欢{','.join(prefs['interests'])}类型")
        if prefs["budget_range"]:
            query_parts.append(f"预算{prefs['budget_range']}")
    
    query = "在".join(query_parts) + "最值得去的旅游景点推荐及理由"
    
    # 如果使用备选或多样化策略，避免推荐已拒绝的景点
    if strategy in ["alternative", "diverse"]:
        rejected = user_memory["rejected_attractions"]
        if rejected:
            query += f"，避开这些景点：{','.join(rejected)}"

    try:
        # 4. 调用API，include_answer=True会返回一个综合性的回答
        response = tavily.search(query=query, search_depth="basic", include_answer=True)

        # 5. Tavily返回的结果已经非常干净，可以直接使用
        if response.get("answer"):
            result = response["answer"]
            
            # 附加策略信息
            if strategy != "default":
                result += f"\n[推荐策略: {strategy}]"
            
            return result

        # 如果没有综合性回答，则格式化原始结果
        formatted_results = []
        for result in response.get("results", []):
            formatted_results.append(f"- {result['title']}: {result['content']}")

        if not formatted_results:
            return "抱歉，没有找到相关的旅游景点推荐。"

        result = "根据搜索，为您找到以下信息:\n" + "\n".join(formatted_results)
        if strategy != "default":
            result += f"\n[推荐策略: {strategy}]"
        
        return result

    except Exception as e:
        return f"错误:执行Tavily搜索时出现问题 - {e}"



if __name__ == "__main__":
    # print(get_weather("北京"))
    print(get_attraction("北京", "晴"))