# questionHandler.py

from prompts import TIME_PROMPT, LOCATION_PROMPT, PERSON_PROMPT, EVENT_PROMPT, RAG_WRAPPER_TEMPLATE
from rag2llm import build_rag_context
from llmApi import chat_completion
from jsonHandler import parse_response_to_json, save_structured_json
from neoRag import Neo4jQuery, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

def generate_final_result(question: str, q_type: str, raw_response: dict, neo4j, model: str = None, llm_args: dict = {}):
    """
    专门生成最终结果的函数，用于修复没有最终结果的回答
    """
    # 准备提示词，要求模型只输出逗号分隔的关键词列表
    result_prompt = f"""
    针对问题【{question}】，你需要提取关键词作为最终结果。
    
    我已经有了以下分析：
    {raw_response.get('总结', '无总结信息')}
    
    现在我只需要你提供最终结果，请直接输出逗号分隔的关键词列表，不要有任何其他文字或说明。
    例如: 宋朝,南宋,12世纪,1127年
    """
    
    messages = [{"role": "user", "content": result_prompt}]
    responses = chat_completion(messages, model=model, **llm_args)
    
    if responses and len(responses) > 0:
        # 清理结果，去除可能的额外文本
        final_result = responses[0].strip()
        # 移除可能存在的"最终结果："前缀
        if "最终结果：" in final_result:
            final_result = final_result.split("最终结果：")[1].strip()
        # 移除可能的额外说明
        if "\n" in final_result:
            final_result = final_result.split("\n")[0].strip()
            
        print(f"生成的最终结果: {final_result}")
        return final_result
    
    return None

def validate_response(structured_response, question, q_type, entity, neo4j, model, llm_args):
    """
    验证结构化响应是否有效，如果没有最终结果则尝试修复
    """
    # 检查是否存在最终结果且不为空
    if "最终结果" not in structured_response or not structured_response["最终结果"].strip():
        print("检测到回答缺少最终结果，尝试重新生成...")
        final_result = generate_final_result(question, q_type, structured_response, neo4j, model, llm_args)
        if final_result:
            structured_response["最终结果"] = final_result
            print("已成功补充最终结果")
        else:
            print("无法生成最终结果，将使用空结果")
            structured_response["最终结果"] = ""
    
    return structured_response

def handle_question_request(question: str, q_type: str, entity: str, model: str = None, llm_args: dict = {}) -> dict:
    neo4j = Neo4jQuery(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    try:
        base_prompt = get_prompt_by_type(question, q_type)
        rag_limited, full_rag_json = build_rag_context(entity, neo4j)
        full_prompt = wrap_with_rag(rag_limited, base_prompt)
        messages = [{"role": "user", "content": full_prompt}]
        responses = chat_completion(messages, model=model, **llm_args)

        if responses:
            print("开始处理多个LLM回答...")
            structured_responses = []
            for idx, response in enumerate(responses, 1):
                print(f"\n处理第 {idx} 个回答：")
                print(response)
                structured = parse_response_to_json(response, q_type, question, full_rag_json)
                
                # 验证并修复响应
                structured = validate_response(structured, question, q_type, entity, neo4j, model, llm_args)
                
                structured_responses.append(structured)
            
            # 保存所有结构化结果
            save_structured_json(structured_responses, q_type, question, entity)
            return {
                "responses": structured_responses,
                "meta": {
                    "question": question,
                    "q_type": q_type,
                    "entity": entity,
                    "total_responses": len(structured_responses)
                }
            }
        else:
            return {"error": "模型无响应"}
    finally:
        neo4j.close()


def get_prompt_by_type(question: str, q_type: str) -> str:
    q_type = q_type.strip().lower()
    if q_type == "时间":
        return TIME_PROMPT.format(question=question)
    elif q_type == "地点":
        return LOCATION_PROMPT.format(question=question)
    elif q_type == "人物":
        return PERSON_PROMPT.format(question=question)
    elif q_type == "事件":
        return EVENT_PROMPT.format(question=question)
    else:
        raise ValueError("未知的问题类型，请输入：时间、地点、人物 或 事件")

def wrap_with_rag(rag_context: str, base_prompt: str) -> str:
    return RAG_WRAPPER_TEMPLATE.format(rag_context=rag_context.strip(), task_prompt=base_prompt.strip())