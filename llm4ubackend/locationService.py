from llmApi import chat_completion
import json

# 定义JSON格式模板
LOCATION_HIERARCHY_TEMPLATE = {
    "层次关系": [
        {
            "大地点": "省级地点名",
            "中级地点": [
                {
                    "名称": "市级地点名",
                    "包含": ["县级地点1", "县级地点2"]
                }
            ]
        }
    ]
}

# 系统提示词
SYSTEM_PROMPT = """你是一个专门分析地理位置从属关系的助手。你必须严格按照以下规则返回结果：
1. 只返回JSON格式数据，不要包含任何其他解释性文字
2. JSON必须完全符合以下结构：
{
    "层次关系": [
        {
            "大地点": "省/自治区/直辖市名称",
            "中级地点": [
                {
                    "名称": "地级市/自治州名称",
                    "包含": ["县/区/县级市名称"]
                }
            ]
        }
    ]
}
3. 所有地名必须是标准的行政区划名称
4. 如果无法确定某个地点的从属关系，不要在JSON中包含该地点
5. 数组可以为空，但不能缺少任何字段"""

def _build_user_prompt(keywords_str: str, records_str: str = "") -> str:
    """构建用户提示词"""
    if not records_str:
        return f"""请分析以下地点的从属关系并返回JSON格式结果：{keywords_str}
严格按照指定的JSON格式返回，不要包含任何其他文字。"""
    
    return f"""请分析以下地点的从属关系：{keywords_str}

已知的地址从属关系：
{records_str}

请基于上述信息返回JSON格式结果，不要包含任何其他文字。"""

def analyze_location_hierarchy(keywords_str: str, records_str: str = "") -> str:
    """
    调用LLM分析地点之间的从属关系
    
    Args:
        keywords_str: 需要分析的地点列表字符串
        records_str: 已知的地址从属关系记录字符串
    
    Returns:
        包含地点层次结构的JSON字符串
    """
    try:
        # 构建消息
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(keywords_str, records_str)}
        ]
        
        # 调用LLM，使用较低的温度以获得更确定性的结果
        # 使用DeepSeek-V3模型，保证输出准确性
        responses = chat_completion(
            messages=messages,
            temperature=0.1,  # 降低温度以获得更稳定的输出
            max_tokens=1024,
            model="deepseek-ai/DeepSeek-V3"
        )
        
        # 只取第一个响应
        if responses and len(responses) > 0:
            try:
                response_text = responses[0]
                # 查找JSON开始和结束的位置
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    # 验证JSON是否有效
                    json_data = json.loads(json_text)
                    
                    # 验证JSON结构是否符合模板
                    if not isinstance(json_data, dict) or "层次关系" not in json_data:
                        return json.dumps({"error": "响应格式不符合要求：缺少层次关系字段"})
                    
                    if not isinstance(json_data["层次关系"], list):
                        return json.dumps({"error": "响应格式不符合要求：层次关系必须是数组"})
                    
                    # 验证每个层级的数据结构
                    for item in json_data["层次关系"]:
                        if not isinstance(item, dict) or "大地点" not in item or "中级地点" not in item:
                            return json.dumps({"error": "响应格式不符合要求：层级结构不完整"})
                        
                        if not isinstance(item["中级地点"], list):
                            return json.dumps({"error": "响应格式不符合要求：中级地点必须是数组"})
                        
                        for city in item["中级地点"]:
                            if not isinstance(city, dict) or "名称" not in city or "包含" not in city:
                                return json.dumps({"error": "响应格式不符合要求：中级地点结构不完整"})
                            
                            if not isinstance(city["包含"], list):
                                return json.dumps({"error": "响应格式不符合要求：包含字段必须是数组"})
                    
                    return json.dumps(json_data, ensure_ascii=False)
                else:
                    return json.dumps({
                        "error": "无法从响应中提取JSON数据",
                        "raw_response": response_text
                    })
            except json.JSONDecodeError:
                return json.dumps({
                    "error": "LLM返回的不是有效的JSON格式",
                    "raw_response": response_text
                })
        
        return json.dumps({"error": "未获得有效响应"})
    
    except Exception as e:
        return json.dumps({"error": f"分析过程发生错误: {str(e)}"}) 