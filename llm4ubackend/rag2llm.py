# rag2llm.py
from neoRag import Neo4jQuery
from typing import List, Dict, Any, Tuple
import re
from datetime import datetime
import os
import csv

def calculate_event_relevance(event: Dict[str, Any], query_keywords: List[str] = None) -> float:
    """
    计算事件的相关性分数
    
    参数:
    - event: 事件字典
    - query_keywords: 查询关键词列表(可选)
    
    返回:
    - 相关性分数 (0.0-1.0)
    """
    relevance_score = 0.0
    base_score = 0.5  # 基础分数
    
    # 如果有关联人，增加分数
    if event.get('related_person'):
        relevance_score += 0.2
    
    # 如果有事件类型描述，增加分数
    if event.get('relation_description'):
        relevance_score += 0.1
    
    # # 如果有年份信息，增加分数
    # if event.get('first_year') or event.get('last_year'):
    #     relevance_score += 0.15
    
    # 如果路径关系包含更多步骤，可能包含更多信息
    path_length = len(event.get('path_relationships', []))
    if path_length > 0:
        # 路径长度得分，但过长的路径可能不太相关
        path_score = min(0.1 * path_length, 0.3)
        relevance_score += path_score
    
    # 如果提供了查询关键词，检查事件中是否包含这些关键词
    if query_keywords:
        event_text = ' '.join([
            ' '.join(event.get('path_relationships', [])),
            event.get('related_person', ''),
            event.get('relation_description', ''),
            event.get('first_year', ''),
            event.get('last_year', '')
        ]).lower()
        
        for keyword in query_keywords:
            if keyword.lower() in event_text:
                relevance_score += 0.2
                break
    
    # 规范化分数到0.0-1.0范围，使用比例放缩而不是简单取最小值
    # 计算理论上最大可能分数（基础分数加上所有可能的加分项）
    max_possible_score = base_score + 0.2 + 0.1 + 0.15 + 0.3 + 0.2  # 基础分数 + 所有加分项最大值
    # 按比例放缩
    normalized_score = (base_score + relevance_score) / max_possible_score
    
    return min(normalized_score, 1.0)  # 确保不超过1.0

def filter_events(events: List[Dict[str, Any]], query_keywords: List[str] = None, 
                 min_relevance: float = 0.5, max_events: int = 10) -> List[Dict[str, Any]]:
    """
    根据相关性筛选事件
    
    参数:
    - events: 事件列表
    - query_keywords: 查询关键词列表(可选)
    - min_relevance: 最小相关性分数
    - max_events: 最大事件数量
    
    返回:
    - 筛选后的事件列表
    """
    # 计算每个事件的相关性分数
    for event in events:
        event['relevance_score'] = calculate_event_relevance(event, query_keywords)
    
    # 筛选出相关性超过阈值的事件
    filtered_events = [e for e in events if e['relevance_score'] >= min_relevance]
    
    # 按相关性排序并限制数量
    sorted_events = sorted(filtered_events, key=lambda x: x['relevance_score'], reverse=True)
    return sorted_events[:max_events]

# 单独处理地点类型事件
# 对宋朝地名数据进行处理
def load_song_addresses():
    """
    加载宋朝地名数据
    
    返回:
    - 宋朝地名列表
    """
    song_addresses = []
    try:
        # 加载SongAddr.csv文件
        csv_path = os.path.join(os.path.dirname(__file__), 'SongData', 'SongAddr.csv')
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # 跳过表头
            for row in reader:
                if row and len(row) > 2:  # 确保有name列
                    song_addresses.append(row[2])  # name列
    except Exception as e:
        print(f"加载宋朝地名数据失败: {str(e)}")
    
    return song_addresses

def build_rag_context(name: str, neo4j: Neo4jQuery, max_length: int = 1000, 
                     query_keywords: List[str] = None, min_relevance: float = 0.5,
                     max_events: int = 100) -> Tuple[str, Dict]:
    """
    构建RAG上下文，从知识图谱提取信息，筛选、排序后提供给LLM
    
    参数:
    - name: 查询的人物名称
    - neo4j: Neo4j查询对象
    - max_length: 最大上下文长度
    - query_keywords: 查询关键词，用于筛选相关事件
    - min_relevance: 最小相关性分数
    - max_events: 最大事件数量
    
    返回:
    - 格式化的RAG上下文文本
    - 包含基础信息和事件路径的字典
    """
    basic_info = neo4j.get_basic_info(name)
    if not basic_info:
        error_msg = f"未在图谱中找到与\"{name}\"相关的实体信息。"
        return error_msg, {}

    basic_text = f"""【人物基础信息】
    姓名: {basic_info['person']}
    性别: {basic_info['gender'] or '未知'}
    民族: {basic_info['ethnicity'] or '未知'}
    生年: {basic_info['birthYear'] or '未知'}
    卒年: {basic_info['deathYear'] or '未知'}
    地址: {', '.join(filter(None, basic_info['addresses'])) or '无'}
    户籍: {', '.join(filter(None, basic_info['households'])) or '无'}
    身份: {', '.join(filter(None, basic_info['statuses'])) or '无'}
    亲属: {', '.join(filter(None, basic_info['relatives'])) or '无'}"""

    # 获取事件路径
    event_paths = neo4j.get_related_events_with_path(name)
    
    # 筛选和排序事件
    filtered_events = filter_events(
        event_paths, 
        query_keywords=query_keywords,
        min_relevance=min_relevance,
        max_events=max_events
    )
    
    # 构建事件文本
    event_lines = []
    
    # 从事件路径中提取朝代信息
    dynasty_name = "宋朝"  # 默认朝代
    for e in filtered_events:
        if e['path_nodes'] and len(e['path_nodes']) > 0:
            for node in e['path_nodes']:
                if "Dynasty" in node or "朝" in node:
                    dynasty_name = node.replace("Dynasty", "").strip()
                    if not dynasty_name.endswith("朝"):
                        dynasty_name += "朝"
                    break
            if dynasty_name != "宋朝":  # 如果找到了非默认朝代，退出循环
                break
    
    for idx, e in enumerate(filtered_events, 1):
        # 添加相关性分数
        relevance_tag = f"[相关性: {e['relevance_score']:.2f}]"
        
        # 获取年份信息
        year_info = ""
        if e['first_year'] and e['last_year'] and e['first_year'] != e['last_year']:
            year_info = f"年份: {e['first_year']}年-{e['last_year']}年"
        elif e['first_year']:
            year_info = f"年份: {e['first_year']}年"
        elif e['last_year']:
            year_info = f"年份: {e['last_year']}年"
        
        # 替换关系描述中的特定术语
        relationships = []
        dynasty_found = False
        
        for rel in e['path_relationships']:
            if rel == "DynastyIs" and not dynasty_found:
                relationships.append(dynasty_name)
                dynasty_found = True
            elif rel == "Do":
                relationships.append("")
            else:
                relationships.append(rel)
        
        # 构建事件文本行
        if year_info:
            line = f"事件链{idx}: {' -> '.join(relationships)}相关人: {e['related_person'] or '无'} | 事件类型: {e['relation_description'] or '无'} | {year_info}"
        else:
            line = f"事件链{idx}: {' -> '.join(relationships)}相关人: {e['related_person'] or '无'} | 事件类型: {e['relation_description'] or '无'}"
        
        event_lines.append(line)
    
    if event_lines:
        event_text = "【事件路径信息】\n" + "\n".join(event_lines)
    else:
        event_text = "【事件路径信息】\n无相关事件路径"
    
    # 加载宋代地名数据
    song_addresses = load_song_addresses()
    # 构建宋代地名提示文本
    if song_addresses:
        # 选取合适的地名数量，筛选出精确到府、州、县级别的地名
        county_level_terms = ["州", "府", "县", "郡", "寺", "城", "镇"]
        filtered_addresses = []
        
        for addr in song_addresses:
            for term in county_level_terms:
                if term in addr:
                    filtered_addresses.append(addr)
                    break
        
        # 如果筛选后太少，再适当补充一些
        if len(filtered_addresses) < 50 and song_addresses:
            additional_needed = min(50 - len(filtered_addresses), len(song_addresses))
            for addr in song_addresses:
                if addr not in filtered_addresses:
                    filtered_addresses.append(addr)
                    additional_needed -= 1
                    if additional_needed <= 0:
                        break
        
        # 选取前80个地名作为示例
        sample_addresses = filtered_addresses[:80] if filtered_addresses else song_addresses[:80]
        
        # 构建地名文本，强调限制规则
        address_text = f"""【{dynasty_name}地名参考】
以下是一些{dynasty_name[:-1]}时期的府、州、县级地名，回答地点问题时请优先使用这些历史地名表述，但在最终结果中要去掉行政区划后缀：
{", ".join(sample_addresses)}

请注意：
1. 最终结果中的地名必须是独立的不带从属关系的地名，不能包含诸如"江西抚州"这样的复合地名
2. 最终结果中不能包含"县"、"州"、"府"、"郡"、"城"等行政区划后缀，例如应该用"临川"而不是"临川县"，用"开封"而不是"开封府"
3. 请优先选择具体的地名，例如府、州、县所在地，而非大范围的区域"""
    else:
        address_text = ""

    # 组合完整RAG上下文
    full_rag = f"{basic_text}\n\n{event_text}"
    if address_text:
        full_rag += f"\n\n{address_text}"
    
    # 如果超出最大长度，进行智能截断
    if len(full_rag) > max_length:
        # 计算每个事件的长度
        event_lengths = [len(line) for line in event_lines]
        
        # 如果有事件，进行智能截断
        if event_lengths:
            remaining_length = max_length - len(basic_text) - len("【事件路径信息】\n")
            
            # 为地名数据预留一些空间
            if address_text:
                remaining_length -= len("\n\n") + min(len(address_text), 600)  # 预留600字符
            
            # 智能选择最重要的事件，直到达到长度限制
            included_events = []
            current_length = 0
            
            # 按相关性排序的事件
            for line in event_lines:
                if current_length + len(line) + 1 <= remaining_length:  # +1 为换行符
                    included_events.append(line)
                    current_length += len(line) + 1
                else:
                    break
            
            event_text_cut = "【事件路径信息】\n" + "\n".join(included_events)
            if address_text:
                address_text_short = address_text[:600] if len(address_text) > 600 else address_text
                rag_limited = f"{basic_text}\n\n{event_text_cut}\n\n{address_text_short}"
            else:
                rag_limited = f"{basic_text}\n\n{event_text_cut}"
        else:
            if address_text:
                address_text_short = address_text[:600] if len(address_text) > 600 else address_text
                rag_limited = f"{basic_text}\n\n【事件路径信息】\n无相关事件路径\n\n{address_text_short}"
            else:
                rag_limited = f"{basic_text}\n\n【事件路径信息】\n无相关事件路径"
    else:
        rag_limited = full_rag

    return rag_limited, {
        "基础信息": basic_text,
        "事件路径": event_lines,
        "筛选后事件数": len(filtered_events),
        "原始事件数": len(event_paths),
        "朝代": dynasty_name
    }

def build_rag_context_with_query(name: str, query: str, neo4j: Neo4jQuery, 
                               max_length: int = 1000) -> Tuple[str, Dict]:
    """
    根据查询内容构建RAG上下文
    
    参数:
    - name: 查询的人物名称
    - query: 用户查询文本
    - neo4j: Neo4j查询对象
    - max_length: 最大上下文长度
    
    返回:
    - 格式化的RAG上下文文本
    - 包含基础信息和事件路径的字典
    """
    # 从查询中提取关键词
    # 简单实现：去除停用词，提取2-4个字的词语
    stopwords = {'的', '了', '是', '在', '有', '和', '与', '或', '什么', '如何', '谁', '为什么', '怎么'}
    words = re.findall(r'[\u4e00-\u9fa5]{2,4}', query)
    keywords = [word for word in words if word not in stopwords]
    
    # 根据关键词构建RAG上下文
    return build_rag_context(
        name=name,
        neo4j=neo4j,
        max_length=max_length,
        query_keywords=keywords,
        min_relevance=0.4,  # 为查询调整相关性阈值
        max_events=15       # 为查询调整最大事件数
    )

def clean_results(result_dict: dict, entity_name: str) -> dict:
    """
    清理LLM回答结果，移除最终结果中出现的查询实体本身
    
    参数:
    - result_dict: LLM回答结果字典
    - entity_name: 查询实体名称
    
    返回:
    - 清理后的结果字典
    """
    # 深拷贝结果字典，避免修改原始数据
    import copy
    cleaned_result = copy.deepcopy(result_dict)
    
    # 检查并清理最终结果
    if "最终结果" in cleaned_result:
        # 分割最终结果为列表
        results = [r.strip() for r in cleaned_result["最终结果"].split(',')]
        
        # 移除与查询实体相同的结果
        filtered_results = [r for r in results if r != entity_name]
        
        # 如果有变化，更新最终结果
        if len(filtered_results) != len(results):
            if filtered_results:
                cleaned_result["最终结果"] = ", ".join(filtered_results)
            else:
                # 如果过滤后没有结果，添加说明
                cleaned_result["最终结果"] = "无匹配结果"
                
                # 在总结中添加说明
                if "总结" in cleaned_result:
                    cleaned_result["总结"] += "\n\n注意：查询结果中只包含查询实体本身，已被过滤。"
                else:
                    cleaned_result["总结"] = "查询结果中只包含查询实体本身，已被过滤。"
    
    return cleaned_result

def clean_location_results(result_dict: dict) -> dict:
    """
    专门处理地点类型查询的结果，去除地名中的行政区划后缀和从属关系
    
    参数:
    - result_dict: LLM回答结果字典
    
    返回:
    - 清理后的结果字典
    """
    # 深拷贝结果字典，避免修改原始数据
    import copy
    cleaned_result = copy.deepcopy(result_dict)
    
    # 检查并清理最终结果
    if "最终结果" in cleaned_result:
        # 分割最终结果为列表
        results = [r.strip() for r in cleaned_result["最终结果"].split(',')]
        
        # 清理地名后缀和从属关系
        cleaned_locations = []
        for location in results:
            # 去除行政区划后缀
            for suffix in ["县", "州", "府", "郡", "城", "寺", "镇"]:
                if location.endswith(suffix):
                    location = location[:-len(suffix)]
            
            # 检查是否包含从属关系（如"江西抚州"）
            combined_location = False
            for province in ["江西", "浙江", "河南", "河北", "山东", "山西", "湖南", "湖北", "广东", "广西", "四川", "云南", "贵州", "福建", "安徽"]:
                if location.startswith(province) and len(location) > len(province):
                    # 有从属关系，分别添加省名和地名
                    if province not in cleaned_locations:
                        cleaned_locations.append(province)
                    
                    # 截取省名后的地名部分
                    sub_location = location[len(province):]
                    # 再次检查后缀
                    for suffix in ["县", "州", "府", "郡", "城", "寺", "镇"]:
                        if sub_location.endswith(suffix):
                            sub_location = sub_location[:-len(suffix)]
                    
                    if sub_location and sub_location not in cleaned_locations:
                        cleaned_locations.append(sub_location)
                    
                    combined_location = True
                    break
            
            # 如果不是组合地名，直接添加
            if not combined_location and location and location not in cleaned_locations:
                cleaned_locations.append(location)
        
        # 更新最终结果
        if cleaned_locations:
            cleaned_result["最终结果"] = ", ".join(cleaned_locations)
        else:
            cleaned_result["最终结果"] = "无法确定具体地点"
    
    return cleaned_result

def process_llm_responses(responses: list, entity_name: str, query_type: str = None) -> list:
    """
    处理LLM回答列表，清理每个回答中的结果
    
    参数:
    - responses: LLM回答列表
    - entity_name: 查询实体名称
    - query_type: 查询类型（如"地点"、"时间"等）
    
    返回:
    - 处理后的回答列表
    """
    processed_responses = []
    
    for response in responses:
        # 根据查询类型选择不同的清理函数
        if query_type == "地点":
            # 先去除后缀等，再清理实体名
            cleaned_response = clean_location_results(response)
            cleaned_response = clean_results(cleaned_response, entity_name)
        else:
            # 其他类型查询只清理实体名
            cleaned_response = clean_results(response, entity_name)
        
        processed_responses.append(cleaned_response)
    
    return processed_responses

# 在app.py中导入并使用上述函数，处理返回结果
# 例如：result["responses"] = process_llm_responses(result["responses"], result["meta"]["entity"])
