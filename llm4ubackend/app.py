# app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
from questionHandler import handle_question_request, generate_final_result
from simcseHandler import get_cluster_analysis
from questionNLP import auto_extract_from_question
from llmApi import chat_completion
from rag2llm import build_rag_context_with_query, process_llm_responses
from locationService import analyze_location_hierarchy
from neo4jVis import Neo4jService, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

app = Flask(__name__)
CORS(app)

# 初始化Neo4j服务
neo4j_service = Neo4jService(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

@app.route("/api/llm/chat", methods=["POST"])
def llm_chat():
    """
    直接与LLM聊天API，允许前端发送任意消息并获取回复
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
            
        messages = data.get("messages", [])
        model = data.get("model")
        
        if not messages:
            return jsonify({"error": "缺少messages参数，请提供聊天消息"}), 400
        
        # 提取其他LLM参数
        llm_args = {
            "temperature": data.get("temperature", 0.7),
            "top_p": data.get("top_p", 0.7),
            "top_k": data.get("top_k", 50),
            "frequency_penalty": data.get("frequency_penalty", 0.5),
            "max_tokens": data.get("max_tokens", 1024),
            "stop": data.get("stop"),
            "stream": data.get("stream", False),
            "n": data.get("n", 1)
        }
        
        # 调用LLM API
        responses = chat_completion(messages, model, **llm_args)
        
        # 返回第一个回复
        response = responses[0] if responses else "无回复"
        
        return jsonify({"response": response})
        
    except Exception as e:
        return jsonify({"error": f"LLM请求失败: {str(e)}"}), 500

@app.route("/api/staticData")
def get_data():
    question = "请告诉我吕祖谦的朋友主要有哪些"
    q_type = "人物"
    entity = "吕祖谦"
    # 调用问题处理函数，将Json结果存到result变量里
    result = handle_question_request(question, q_type, entity)
    # 控制台调试部分测试
    # print("已完成处理，结构化结果如下：")
    # print(json.dumps(result, indent=2, ensure_ascii=False))
    return jsonify(result)

@app.route("/api/query", methods=["POST"])
def query():
    data = request.json
    question = data.get("question")
    model = data.get("model")

    llm_args = {
        "temperature": data.get("temperature", 0.7),
        "top_p": data.get("top_p", 0.7),
        "top_k": data.get("top_k", 50),
        "frequency_penalty": data.get("frequency_penalty", 0.5),
        "max_tokens": data.get("max_tokens", 1024),
        "stop": data.get("stop"),
        "stream": data.get("stream", False),
        "n": data.get("n", 1)
    }

    # 检查是否提供了问题类型和实体
    q_type = data.get("q_type")
    entity = data.get("entity")
    
    # 如果没有提供问题类型或实体，尝试自动提取
    if not all([q_type, entity]) and question:
        extracted_data = auto_extract_from_question(question, model, **llm_args)
        q_type = extracted_data.get("q_type")
        entity = extracted_data.get("entity")
    
    if not question:
        return jsonify({"error": "参数不完整，请提供问题"}), 400

    # 处理问题并返回结果
    result_json = handle_question_request(question, q_type, entity, model, llm_args)
    
    # 处理LLM回答，移除查询实体自身
    if "responses" in result_json:
        result_json["responses"] = process_llm_responses(result_json["responses"], entity)
    
    return jsonify(result_json)

@app.route("/api/generate-result", methods=["POST"])
def generate_result():
    """
    针对没有生成最终结果的回答，单独生成最终结果
    """
    data = request.json
    question = data.get("question", "")
    q_type = data.get("q_type", "")
    entity = data.get("entity", "")
    model = data.get("model", "internlm/internlm2_5-7b-chat")
    
    # 如果没有提供必要信息，使用自动分析尝试提取
    if not q_type or not entity:
        analysis_result = auto_extract_from_question(question, model)
        q_type = q_type or analysis_result['q_type']
        entity = entity or analysis_result['entity']
    
    if not question or not q_type or not entity:
        return jsonify({'error': '缺少必要的参数'}), 400
    
    # 构建Prompt，调用handle_question_request生成结果
    result = handle_question_request(question, q_type, entity, model, data)
    
    # 处理LLM回答，移除查询实体自身
    if "responses" in result:
        result["responses"] = process_llm_responses(result["responses"], entity)
    
    return jsonify(result)

@app.route("/api/cluster-analysis", methods=["POST"])
def cluster_analysis():
    """
    对LLM回答的JSON结果进行聚类分析
    请求体应包含一个responses字段，其中是LLM回答的JSON数据列表
    """
    data = request.json
    responses = data.get("responses", [])
    
    if not responses:
        return jsonify({"error": "缺少responses参数，请提供LLM回答的JSON数据"}), 400
    
    # 调用SimCSE处理模块进行聚类分析
    cluster_results = get_cluster_analysis(responses)
    return jsonify(cluster_results)

@app.route("/api/analyze-question", methods=["POST"])
def analyze_question():
    """
    分析问题，提取问题类型和查询实体
    """
    data = request.json
    question = data.get("question")
    model = data.get("model")
    
    if not question:
        return jsonify({"error": "缺少question参数"}), 400
    
    # 使用问题分析模块提取问题类型和查询实体
    result = auto_extract_from_question(question, model)
    return jsonify(result)

@app.route("/api/analyze-location-hierarchy", methods=["POST"])
def location_hierarchy():
    """
    分析地点之间的从属层次关系
    请求体应包含一个keywords字段，其中是地点关键词列表
    可选地包含一个records字段，提供已知的地点从属关系记录
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400
            
        keywords = data.get("keywords", [])
        records = data.get("records", [])
        
        if not keywords:
            return jsonify({"error": "缺少keywords参数，请提供地点关键词"}), 400
        
        # 准备关键词字符串
        keywords_str = ", ".join([k["keyword"] if isinstance(k, dict) else k for k in keywords])
        
        # 准备记录字符串
        records_str = ""
        if records:
            records_str = "\n".join([f"{r['Addr1']} 属于 {r['Addr2']} 属于 {r['Addr3']}" for r in records])
        
        # 调用LLM分析地点层次关系
        result = analyze_location_hierarchy(keywords_str, records_str)
        return result
        
    except Exception as e:
        return jsonify({"error": f"请求处理失败: {str(e)}"}), 500

@app.route("/api/neo4j/graph", methods=["POST"])
def get_graph():
    """
    获取Neo4j知识图谱数据
    """
    data = request.json
    person_name = data.get("personName", "")

    try:
        graph_data = neo4j_service.get_person_graph(person_name)
        return jsonify(graph_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/llm-analysis', methods=['POST'])
def llm_analysis():
    try:
        print("收到LLM分析请求")
        print("请求头:", dict(request.headers))
        print("请求方法:", request.method)
        
        data = request.get_json()
        print("请求数据:", data)
        
        prompt = data.get('prompt', '')
        print("提取的提示词:", prompt)
        
        if not prompt:
            return jsonify({'error': '缺少分析提示词'}), 400
        
        # 调用LLM进行分析
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的推理链条分析专家，擅长分析不同推理路径的差异和相似性。请根据提供的信息进行深入分析。"
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]
        
        # 调用LLM API
        responses = chat_completion(
            messages=messages,
            temperature=0.3,  # 降低随机性，提高分析的一致性
            max_tokens=2048,  # 增加token数量以获得更详细的分析
            top_p=0.8
        )
        
        if responses and len(responses) > 0:
            analysis_result = responses[0]
            return jsonify({
                'success': True,
                'analysis': analysis_result,
                'content': analysis_result
            })
        else:
            return jsonify({'error': 'LLM分析失败，未获得有效响应'}), 500
            
    except Exception as e:
        print(f"LLM分析API错误: {str(e)}")
        return jsonify({'error': f'分析失败: {str(e)}'}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)