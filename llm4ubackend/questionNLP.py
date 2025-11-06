# questionNLP.py

from llmApi import chat_completion
import csv
import os
import re

# 加载宋朝人物数据作为实体识别参考
def load_song_people():
    """
    加载宋朝人物数据，用于实体识别
    """
    song_people = []
    try:
        #with open('llm4ubackend/SongData/SongPeople.csv', 'r', encoding='utf-8') as f:
        with open('SongData/SongPeople.csv', 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # 跳过表头
            for row in reader:
                if row and len(row) > 2:
                    song_people.append(row[2])  # 添加人名
    except Exception as e:
        print(f"加载宋朝人物数据失败: {str(e)}")
    
    return song_people

# 预定义的问题类型
QUESTION_TYPES = ["时间", "地点", "人物", "事件"]

def analyze_question(question, model=None, **kwargs):
    """
    自动分析问题，提取问题类型和查询实体
    
    Args:
        question: 用户输入的问题
        model: 使用的LLM模型
        **kwargs: 传递给LLM的参数
        
    Returns:
        tuple: (q_type, entity, confidence) 问题类型、查询实体和置信度
    """
    # 加载宋朝人物数据作为辅助识别
    song_people = load_song_people()
    
    # 首先检查是否能从问题中直接提取宋朝人物实体
    song_entity = find_song_entity_in_question(question, song_people)
    
    # 构建提示词
    prompt = f"""
    请分析以下问题，提取出问题类型和查询的实体。
    
    问题类型必须是以下四种之一：时间、地点、人物、事件
    查询实体是问题中涉及的主要人名、地名或事件名。
    
    问题: {question}
    """
    
    # 如果已经找到了匹配的宋朝人物实体，在提示中强调使用这个实体
    if song_entity:
        prompt += f"""
    注意：问题中提到的"{song_entity}"是一个宋朝人物，应该被识别为查询实体。
    """
    
    prompt += """
    你必须严格按照以下JSON格式返回结果，不要包含任何其他文字说明:
    ```json
    {
        "q_type": "问题类型",
        "entity": "查询实体",
        "confidence": 0.9
    }
    ```
    
    其中：
    - q_type必须是"时间"、"地点"、"人物"、"事件"其中之一
    - entity是问题中的实体名称，例如"朱熹"、"王安石"
    - confidence是0到1之间的数字，表示你对分类和实体提取的置信度
    
    请直接返回JSON格式结果，不要添加任何解释或前缀。
    """
    
    # 调用LLM进行分析
    responses = chat_completion([
        {"role": "system", "content": "你是一个擅长分析古代中国历史问题的助手，特别是宋朝历史。你将严格按照指定JSON格式输出，不添加任何其他解释。"},
        {"role": "user", "content": prompt}
    ], model, **kwargs)
    
    # 解析LLM返回的结果
    if responses and len(responses) > 0:
        response = responses[0]
        # 提取JSON部分
        try:
            import json
            import re
            
            # 尝试从回答中提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = re.search(r'{.*}', response, re.DOTALL).group(0)
            
            result = json.loads(json_str)
            q_type = result.get("q_type", "")
            entity = result.get("entity", "")
            confidence = result.get("confidence", 0)
            
            # 验证问题类型是否有效
            if q_type not in QUESTION_TYPES:
                # 回退到默认类型
                q_type = "人物"
                confidence = 0.5
            
            # 确保实体在宋朝人物表中完全匹配
            final_entity = ""
            final_confidence = 0.3  # 默认为较低置信度
            
            # 优先级1：使用预先识别的宋朝人物实体（如果存在）
            if song_entity:
                final_entity = song_entity
                final_confidence = 0.9  # 高置信度，因为是完全匹配
            
            # 优先级2：检查LLM提取的实体是否在宋朝人物列表中
            elif entity and entity in song_people:
                final_entity = entity
                final_confidence = 0.85  # 较高置信度
            
            # 优先级3：检查LLM提取的实体是否包含宋朝人物
            elif entity:
                for person in sorted(song_people, key=len, reverse=True):
                    if person in entity:
                        final_entity = person
                        final_confidence = 0.8  # 中等置信度
                        break
            
            # 如果还没找到匹配的实体，保留LLM提取的实体，但降低置信度
            if not final_entity and entity:
                final_entity = entity
                final_confidence = 0.4  # 较低置信度，因为没有匹配到宋朝人物
            
            # 如果置信度不是由我们设置的，则使用原始置信度
            if final_confidence != 0.3:
                confidence = final_confidence
            
            # 返回最终结果
            return q_type, final_entity if final_entity else entity, confidence
            
        except Exception as e:
            print(f"解析LLM返回结果失败: {str(e)}")
            # 从问题中启发式提取
            return fallback_extraction(question, song_people)
    
    # 如果LLM分析失败，使用启发式方法
    return fallback_extraction(question, song_people)

def find_song_entity_in_question(question, song_people):
    """
    在问题中查找完整匹配的宋朝人物名称
    
    Args:
        question: 用户问题
        song_people: 宋朝人物列表
    
    Returns:
        str: 匹配到的人物名称，如果未匹配则返回空字符串
    """
    if not song_people:
        return ""
    
    # 按照名字长度降序排序，优先匹配较长的名字，避免部分匹配
    sorted_people = sorted(song_people, key=len, reverse=True)
    
    for person in sorted_people:
        if person in question:
            return person
    
    return ""

def extract_potential_entity(question):
    """
    从问题中提取可能的实体名称
    
    Args:
        question: 用户问题
    
    Returns:
        str: 可能的实体名称
    """
    # 使用正则表达式匹配可能的实体（连续的两个或以上汉字）
    matches = re.findall(r'[\u4e00-\u9fa5]{2,}', question)
    if not matches:
        return ""
    
    # 选择长度最长的匹配项作为可能的实体
    return max(matches, key=len)

def fallback_extraction(question, song_people):
    """
    当LLM分析失败时的后备提取方法
    """
    # 默认类型为人物
    q_type = "人物"
    entity = ""
    confidence = 0.3  # 默认较低置信度
    
    # 如果包含具体类型关键词，则设置相应类型
    if any(word in question for word in ["什么时候", "何时", "哪年", "时间"]):
        q_type = "时间"
        confidence = 0.7
    elif any(word in question for word in ["哪里", "何地", "地点", "哪个地方"]):
        q_type = "地点"
        confidence = 0.7
    elif any(word in question for word in ["什么事", "事件", "发生了什么"]):
        q_type = "事件"
        confidence = 0.7
    
    # 首先尝试查找宋朝人物（必须完全匹配）
    song_entity = find_song_entity_in_question(question, song_people)
    if song_entity:
        entity = song_entity
        confidence = max(confidence, 0.8)  # 提高置信度，因为是完全匹配
    else:
        # 如果没找到宋朝人物，尝试提取可能的实体
        extracted_entity = extract_potential_entity(question)
        if extracted_entity:
            # 再检查一次是否与宋朝人物匹配
            for person in sorted(song_people, key=len, reverse=True):
                if person in extracted_entity or extracted_entity in person:
                    entity = person
                    confidence = 0.6
                    break
            
            # 如果还是没匹配到，使用提取的实体但降低置信度
            if not entity:
                entity = extracted_entity
                confidence = 0.4  # 较低置信度
    
    return q_type, entity, confidence

def auto_extract_from_question(question, model=None, **kwargs):
    """
    自动从问题中提取问题类型和查询实体的主函数
    
    Args:
        question: 用户输入的问题
        model: 使用的LLM模型
        **kwargs: 传递给LLM的参数
        
    Returns:
        dict: 包含问题、问题类型和查询实体的字典
    """
    q_type, entity, confidence = analyze_question(question, model, **kwargs)
    
    # 返回结构化的结果
    result = {
        "question": question,
        "q_type": q_type,
        "entity": entity,
        "confidence": confidence
    }
    
    print(f"问题分析结果: {result}")
    return result

# 测试代码
if __name__ == "__main__":
    test_questions = [
        "吕祖谦有哪些朋友？",
        "朱熹是什么时候出生的？",
        "王安石变法发生在哪里？",
        "靖康之难是什么事件？"
    ]
    
    for q in test_questions:
        result = auto_extract_from_question(q)
        print(f"问题: {q}")
        print(f"分析结果: 类型={result['q_type']}, 实体={result['entity']}, 置信度={result['confidence']}")
        print("-" * 50) 