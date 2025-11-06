# jsonHandler.py

import re
import json
import os
from datetime import datetime
from llmApi import chat_completion

def analyze_question_info(question: str) -> dict:
    """
    使用LLM分析问题中涉及的时间、地点、人物、事件信息
    
    参数:
    - question: 用户的问题文本
    
    返回:
    - 包含各类信息的字典
    """
    prompt = f"""请分析以下问题中涉及的时间、地点、人物、事件信息，以JSON格式返回。
如果某项信息不存在，则返回空字符串。
问题：{question}

请按以下格式返回：
{{
    "time": "时间信息",
    "location": "地点信息",
    "person": "人物信息",
    "event": "事件信息"
}}"""

    messages = [
        {"role": "system", "content": "你是一个专门用于分析问题中各类信息的助手。请只返回JSON格式的结果，不要包含其他说明文字。"},
        {"role": "user", "content": prompt}
    ]
    
    try:
        responses = chat_completion(messages, temperature=0.3)
        if responses and responses[0]:
            # 尝试从响应中提取JSON
            response_text = responses[0]
            # 查找JSON部分
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
    except Exception as e:
        print(f"分析问题信息时出错: {str(e)}")
    
    # 如果出错，返回空字典
    return {
        "time": "",
        "location": "",
        "person": "",
        "event": ""
    }

def parse_response_to_json(response: str, question_type: str, question_content: str, rag_context: dict) -> dict:
    lines = response.strip().split("\n")
    
    # 处理RAG内容，确保它是字典格式
    processed_rag = process_rag_content(rag_context)
    
    result_json = {
        "知识图谱补充信息": processed_rag  # 保存处理后的RAG信息
    }

    current_path_key = None
    current_title = ""
    current_nodes = {}
    all_paths = {}
    final_summary = None
    final_result = None
    current_node_key = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        path_match = re.match(r"路径(\d+)：(.+)", line)
        if path_match:
            if current_path_key and current_nodes:
                all_paths[current_path_key] = {"标题": current_title, "节点": current_nodes}
            current_path_key = f"路径{path_match.group(1)}"
            current_title = path_match.group(2).strip()
            current_nodes = {}
            current_node_key = None
            continue
        node_match = re.match(r"(节点\d+)：(.*)", line)
        if node_match:
            current_node_key = node_match.group(1).strip()
            current_nodes[current_node_key] = node_match.group(2).strip()
            continue
        if line.startswith("总结："):
            final_summary = line.replace("总结：", "").strip()
            continue
        if line.startswith("最终结果："):
            final_result = line.replace("最终结果：", "").strip()
            continue
        # 兼容旧版输出格式
        if line.startswith("结果：") and not final_summary:
            final_summary = line.replace("结果：", "").strip()
            continue
        if current_node_key:
            current_nodes[current_node_key] += "\n" + line.strip()

    if current_path_key and current_nodes:
        all_paths[current_path_key] = {"标题": current_title, "节点": current_nodes}

    result_json.update(all_paths)
    if final_summary:
        result_json["总结"] = final_summary
    if final_result:
        result_json["最终结果"] = final_result

    return result_json

def process_rag_content(rag_context: dict) -> dict:
    """处理RAG内容，将其转换为结构化的字典格式
    
    参数:
    - rag_context: 包含RAG信息的字典，通常包含基础信息和事件路径
    
    返回:
    - 处理后的RAG字典，包含基础信息、处理后RAG内容和事件路径
    """
    if not rag_context:
        return {}
    
    # 创建结果字典
    rag_dict = {}
    
    # 复制原始信息
    if "基础信息" in rag_context:
        rag_dict["基础信息"] = rag_context["基础信息"]
    else:
        rag_dict["基础信息"] = ""
    
    # 添加处理后RAG内容部分（在基础信息和事件路径之间）
    processed_content = generate_processed_rag_content(rag_context)
    rag_dict["处理后RAG内容"] = processed_content
    
    # 处理事件路径信息
    if "事件路径" in rag_context:
        if isinstance(rag_context["事件路径"], list):
            rag_dict["事件路径"] = "\n".join(rag_context["事件路径"])
        else:
            rag_dict["事件路径"] = str(rag_context["事件路径"])
    else:
        rag_dict["事件路径"] = ""
    
    # # 复制其他可能存在的字段
    # for key, value in rag_context.items():
    #     if key not in ["基础信息", "事件路径"] and key not in rag_dict:
    #         rag_dict[key] = value
    
    return rag_dict

def generate_processed_rag_content(rag_context: dict) -> str:
    """根据RAG内容生成处理后的附加信息
    
    这个函数可以根据实际需求添加更复杂的处理逻辑
    """
    processed_content = "【处理后的RAG内容】\n"
    
    # 提取人物名称（如果有）
    basic_info = rag_context.get("基础信息", "")
    name_match = re.search(r"姓名:\s*([^\n]+)", basic_info)
    person_name = name_match.group(1) if name_match else "未知人物"
    
    # 统计事件数量
    event_count = rag_context.get("筛选后事件数", 0)
    original_event_count = rag_context.get("原始事件数", 0)
    
    # 生成简要统计信息
    processed_content += f"人物: {person_name}\n"
    processed_content += f"相关事件总数: {original_event_count}\n"
    processed_content += f"筛选后事件数: {event_count}\n"
    
    # 如果有事件路径，可以添加一些事件分析
    if event_count > 0 and isinstance(rag_context.get("事件路径"), list):
        processed_content += "\n事件分析:\n"
        processed_content += f"- 找到了 {event_count} 条与查询相关的事件路径\n"
        # 这里可以添加更多事件分析，如时间分布、关键人物等
    
    return processed_content

def save_structured_json(structured_data: list, q_type: str, question: str, entity=""):
    os.makedirs("JsonOutputs", exist_ok=True)
    short_question = ''.join(c for c in question if c.isalnum())[:20]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{q_type}_{short_question}_{timestamp}_multi.json"
    filepath = os.path.join("JsonOutputs", filename)

    # 从第一个回答中提取知识图谱信息
    knowledge_graph_info = structured_data[0].get("知识图谱补充信息")
    if not knowledge_graph_info:
        print("警告：未找到知识图谱信息")

    # 移除所有回答中的知识图谱信息
    cleaned_responses = []
    for response in structured_data:
        response_copy = response.copy()
        if "知识图谱补充信息" in response_copy:
            del response_copy["知识图谱补充信息"]
        cleaned_responses.append(response_copy)

    # 分析问题中的各类信息
    question_info = analyze_question_info(question)

    output_data = {
        "meta": {
            "question": question,
            "q_type": q_type,
            "entity": entity,  # 添加实体信息
            "total_responses": len(structured_data),
            "timestamp": timestamp,
            "knowledge_graph": knowledge_graph_info,
            "infos": question_info  # 添加问题中涉及的各类信息
        },
        "responses": cleaned_responses
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n已保存 {len(structured_data)} 个结构化结果到文件: {filepath}")
    if knowledge_graph_info:
        print("知识图谱信息已统一保存在meta数据中")
    print("问题中涉及的各类信息已保存到infos字段中")
    return filepath