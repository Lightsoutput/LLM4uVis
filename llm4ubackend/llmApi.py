# llmApi.py

import requests

API_URL = "https://api.siliconflow.cn/v1/chat/completions"
API_KEY = "sk-rjpojxsrkxtmkjtihmhlekbavqjhucijaqzgrarfypixqrmq"
DEFAULT_MODEL = "internlm/internlm2_5-7b-chat"

# kwargs可变参数接收前端输入给LLM的多个参数
def chat_completion(messages, model=None, **kwargs):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "response_format": {"type": "text"},
        # 允许自定义参数传入：
        "temperature": kwargs.get("temperature", 0.7),
        "top_p": kwargs.get("top_p", 0.7),
        "top_k": kwargs.get("top_k", 50),
        "frequency_penalty": kwargs.get("frequency_penalty", 0.5),
        "max_tokens": kwargs.get("max_tokens", 1024),
        "stop": kwargs.get("stop"),
        "stream": kwargs.get("stream", False),
        "n": kwargs.get("n", 1)
    }

    try:
        print("目前上传LLM的参数为：")
        print(payload)
        response = requests.post(API_URL, json=payload, headers=headers)
        response.raise_for_status()
        # 返回所有的回答结果
        responses = [choice['message']['content'] for choice in response.json()['choices']]
        print("LLM 所有回答结果：")
        for idx, resp in enumerate(responses, 1):
            print(f"\n回答 {idx}:")
            print(resp)
        return responses
    except Exception as e:
        return [f"API请求失败: {str(e)}"]