#simcseHandler.py
#simcse模型，用于聚类分析

from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from pprint import pprint
import time
import functools
from concurrent.futures import ThreadPoolExecutor
import os
import re
from collections import Counter

# 检查是否有GPU可用
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"使用设备: {device}")

# 加载 SimCSE 模型和 tokenizer
model_name = "Seznam/simcse-dist-mpnet-czeng-cs-en"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name).to(device)
model.eval()

# 创建向量缓存
embedding_cache = {}

# 创建线程池以优化I/O操作
executor = ThreadPoolExecutor(max_workers=os.cpu_count())

# 批量句向量提取函数（mean pooling）
def get_embeddings_batch(texts, batch_size=16):
    """
    批量计算句子的向量表示，提高性能
    """
    # 检查缓存中是否已有这些句子的向量
    embeddings = []
    texts_to_process = []
    indices_to_process = []
    
    # 先检查哪些已经在缓存里了
    for i, text in enumerate(texts):
        if text in embedding_cache:
            embeddings.append(embedding_cache[text])
        else:
            texts_to_process.append(text)
            indices_to_process.append(i)
    
    # 如果有句子需要处理
    if texts_to_process:
        all_embeddings = []
        
        # 分批处理句子
        for i in range(0, len(texts_to_process), batch_size):
            batch_texts = texts_to_process[i:i+batch_size]
            
            # 对批次进行tokenize
            inputs = tokenizer(batch_texts, padding=True, truncation=True, return_tensors="pt").to(device)
            
            # 获取句子向量
            with torch.no_grad():
                outputs = model(**inputs, return_dict=True)
            
            token_embeddings = outputs.last_hidden_state
            attention_mask = inputs['attention_mask']
            
            # 执行mean pooling
            mask = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            masked_embeddings = token_embeddings * mask
            summed = torch.sum(masked_embeddings, dim=1)
            counts = torch.clamp(mask.sum(1), min=1e-9)
            batch_embeddings = summed / counts
            
            # 转移到CPU并转为numpy数组
            batch_embeddings = batch_embeddings.cpu().numpy()
            all_embeddings.extend(batch_embeddings)
            
            # 更新缓存
            for j, text in enumerate(batch_texts):
                embedding_cache[text] = batch_embeddings[j]
        
        # 将新计算的向量插入到正确的位置
        for idx, embed in zip(indices_to_process, all_embeddings):
            embeddings.insert(idx, embed)
    
    return np.array(embeddings)

# 单个句子的向量提取（兼容旧代码）
def get_embedding(text):
    """
    单个句子的向量提取，使用批处理函数
    """
    if text in embedding_cache:
        return embedding_cache[text]
    
    result = get_embeddings_batch([text])[0]
    return result

# 优化的最佳聚类数量确定函数
@functools.lru_cache(maxsize=32)  # 使用LRU缓存以避免重复计算
def determine_optimal_clusters(embeddings_tuple, max_clusters=5, min_clusters=2):
    """
    使用轮廓系数(Silhouette Score)自动确定最佳聚类数量，使用缓存和快速评估
    
    Args:
        embeddings_tuple: 句子的向量表示（转为元组以便缓存）
        max_clusters: 最大聚类数量
        min_clusters: 最小聚类数量（默认为2）
        
    Returns:
        最佳聚类数量
    """
    # 转换回numpy数组
    embeddings = np.array(embeddings_tuple)
    n_samples = embeddings.shape[0]
    
    # 快速路径：样本数量少时的处理
    if n_samples < 3:
        return 1
    if n_samples <= 4:
        return min(2, n_samples)
        
    # 限制聚类数范围
    max_possible_clusters = min(max_clusters, n_samples - 1)
    
    # 使用较少的聚类数量尝试，提高速度
    # 对于大量样本，我们可以跳过一些聚类数量的尝试
    step_size = 1 if n_samples < 20 else 2
    cluster_range = range(min_clusters, max_possible_clusters + 1, step_size)
    
    # 如果样本数量较少，我们可以使用更低的n_init值
    n_init_value = 5 if n_samples < 50 else 10
    
    # 对于大数据集，使用小型预测来确定大致范围
    if n_samples > 100:
        # 使用样本进行初步评估
        sample_indices = np.random.choice(n_samples, min(100, n_samples), replace=False)
        sample_embeddings = embeddings[sample_indices]
        
        # 在样本上快速尝试不同的聚类数
        quick_scores = []
        for n_clusters in cluster_range:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=3, max_iter=100)
            sample_labels = kmeans.fit_predict(sample_embeddings)
            
            try:
                score = silhouette_score(sample_embeddings, sample_labels)
                quick_scores.append((n_clusters, score))
            except Exception:
                continue
                
        # 如果找到了有效分数，使用最佳的3个进行详细评估
        if quick_scores:
            quick_scores.sort(key=lambda x: x[1], reverse=True)
            cluster_range = [x[0] for x in quick_scores[:3]]
    
    # 尝试不同的聚类数量，选择轮廓系数最高的
    silhouette_scores = []
    
    # 并行执行多个聚类计算
    def evaluate_n_clusters(n_clusters):
        if n_clusters >= n_samples:
            return None
            
        start_time = time.time()
        kmeans = KMeans(
            n_clusters=n_clusters, 
            random_state=42, 
            n_init=n_init_value,
            max_iter=300,  # 提高收敛速度
            tol=1e-4       # 稍微放宽收敛标准
        )
        labels = kmeans.fit_predict(embeddings)
        
        try:
            score = silhouette_score(embeddings, labels)
            print(f"聚类数 {n_clusters}，轮廓系数: {score:.4f}，耗时: {time.time() - start_time:.2f}秒")
            return (n_clusters, score)
        except Exception as e:
            print(f"计算轮廓系数出错 (n_clusters={n_clusters}): {str(e)}")
            return None
    
    # 使用线程池并行计算不同聚类数量的得分
    results = list(executor.map(evaluate_n_clusters, cluster_range))
    silhouette_scores = [r for r in results if r is not None]
    
    # 如果没有有效的轮廓分数，返回默认值
    if not silhouette_scores:
        return min(2, n_samples)
    
    # 选择轮廓系数最高的聚类数量
    best_n_clusters, best_score = max(silhouette_scores, key=lambda x: x[1])
    print(f"最佳聚类数量: {best_n_clusters}，轮廓系数: {best_score:.4f}")
    
    return best_n_clusters

# 聚类摘要生成函数，必要性不是很高，除非用LLM重组句子意思
def generate_cluster_summary(cluster_sentences, cluster_embeddings, cluster_center, tokenizer, model, device):
    """
    生成聚类的综合摘要，考虑聚类中的多个句子内容
    
    Args:
        cluster_sentences: 聚类中的所有句子
        cluster_embeddings: 聚类中所有句子的向量表示
        cluster_center: 聚类中心向量
        tokenizer: 分词器
        model: 模型
        
    Returns:
        生成的摘要
    """
    # 如果只有一个句子，直接返回
    if len(cluster_sentences) == 1:
        return cluster_sentences[0]
        
    # 计算每个句子与聚类中心的相似度
    similarities = cosine_similarity([cluster_center], cluster_embeddings)[0]
    
    # 如果聚类很小 (<=3)，直接返回最相似的句子
    if len(cluster_sentences) <= 3:
        best_index = np.argmax(similarities)
        return cluster_sentences[best_index]
    
    # 对于较大的聚类，我们将考虑更多的信息
    
    # 1. 获取关键词频率
    # 对所有句子进行分词和词频统计
    all_words = []
    for sentence in cluster_sentences:
        # 简单的中文分词处理，按字符和标点符号分割
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', sentence)
        all_words.extend(words)
    
    # 统计词频
    word_counts = Counter(all_words)
    
    # 获取最常见的5个词作为关键词（排除停用词和过短的词）
    common_words = [word for word, count in word_counts.most_common(10) 
                    if len(word) > 1 and count > 1][:5]
    
    # 2. 根据相似度选择Top-N个句子
    top_n = min(3, len(cluster_sentences))
    top_indices = np.argsort(similarities)[-top_n:][::-1]
    top_sentences = [cluster_sentences[i] for i in top_indices]
    
    # 3. 计算每个句子包含关键词的数量
    keyword_scores = []
    for sentence in top_sentences:
        score = sum(1 for word in common_words if word in sentence)
        keyword_scores.append(score)
    
    # 4. 结合相似度和关键词覆盖度选择最佳句子
    combined_scores = []
    for i, idx in enumerate(top_indices):
        # 相似度权重0.6，关键词覆盖权重0.4
        combined_score = 0.6 * similarities[idx] + 0.4 * (keyword_scores[i] / max(1, len(common_words)))
        combined_scores.append(combined_score)
    
    best_index = np.argmax(combined_scores)
    best_sentence = top_sentences[best_index]
    
    return best_sentence

# 优化的聚类分析函数
def analyze_clusters_for_paths(responses):
    """
    对LLM响应的路径和节点进行聚类分析，使用优化的批处理和并行计算
    """
    start_time = time.time()
    cluster_results = {}
    
    # 首先收集所有需要聚类分析的数据
    # 这样我们可以一次性生成所有向量，避免多次模型加载和计算
    all_path_nodes = {}
    node_sentences_map = {}
    
    # 1. 收集所有路径和节点数据
    for response in responses:
        for path_key, path_value in response.items():
            if path_key in ['总结', '最终结果', '引用事件链'] or not isinstance(path_value, dict) or '节点' not in path_value:
                continue
                
            path_title = path_value.get('标题', '未命名路径')
            
            if path_key not in all_path_nodes:
                all_path_nodes[path_key] = {
                    'title': path_title,
                    'nodes': set()
                }
            
            # 收集所有节点
            for node_key in path_value['节点'].keys():
                all_path_nodes[path_key]['nodes'].add(node_key)
                
                # 创建节点的唯一标识符
                node_id = f"{path_key}_{node_key}"
                if node_id not in node_sentences_map:
                    node_sentences_map[node_id] = []
    
    # 2. 收集每个节点的所有句子
    for path_key, path_data in all_path_nodes.items():
        for node_key in path_data['nodes']:
            node_id = f"{path_key}_{node_key}"
            sentences = []
            
            for response_idx, response in enumerate(responses):
                if path_key in response and node_key in response[path_key].get('节点', {}):
                    sentences.append({
                        'text': response[path_key]['节点'][node_key],
                        'response_idx': response_idx
                    })
            
            node_sentences_map[node_id] = sentences
    
    # 3. 批量计算所有句子的向量表示
    all_sentences = []
    sentence_to_idx = {}
    for sentences in node_sentences_map.values():
        for sentence_data in sentences:
            text = sentence_data['text']
            if text not in sentence_to_idx:
                sentence_to_idx[text] = len(all_sentences)
                all_sentences.append(text)
    
    print(f"需要处理的唯一句子总数: {len(all_sentences)}")
    
    # 批量计算所有唯一句子的向量
    if all_sentences:
        print("开始批量计算句子向量...")
        t0 = time.time()
        all_embeddings = get_embeddings_batch(all_sentences)
        print(f"向量计算完成，耗时: {time.time() - t0:.2f}秒")
    
    # 4. 为每个路径的每个节点进行聚类分析
    for path_key, path_data in all_path_nodes.items():
        print(f"分析路径: {path_data['title']}")
        
        # 初始化路径结果
        if path_key not in cluster_results:
            cluster_results[path_key] = {
                'title': path_data['title'],
                'nodes': {}
            }
        
        # 处理每个节点
        for node_key in path_data['nodes']:
            print(f"  分析节点: {node_key}")
            node_id = f"{path_key}_{node_key}"
            sentences_data = node_sentences_map[node_id]
            
            # 如果句子太少，就跳过聚类
            if len(sentences_data) < 2:
                cluster_results[path_key]['nodes'][node_key] = {
                    'sentences': [s['text'] for s in sentences_data],
                    'clusters': [0] * len(sentences_data),
                    'summaries': [sentences_data[0]['text']] if sentences_data else ['无足够数据进行聚类'],
                    'cluster_count': 1
                }
                continue
            
            # 获取该节点所有句子的文本和向量
            node_texts = [s['text'] for s in sentences_data]
            node_embeddings = np.array([all_embeddings[sentence_to_idx[s['text']]] for s in sentences_data])
            
            # 转换为元组以便缓存
            embeddings_tuple = tuple(map(tuple, node_embeddings))
            
            # 动态确定最佳聚类数量
            print("开始确定最佳聚类数量...")
            t0 = time.time()
            num_clusters = determine_optimal_clusters(embeddings_tuple)
            print(f"为节点 {node_key} 确定的最佳聚类数量: {num_clusters}，耗时: {time.time() - t0:.2f}秒")
            
            # 执行聚类
            t0 = time.time()
            kmeans = KMeans(
                n_clusters=num_clusters, 
                random_state=42, 
                n_init='auto',  # 自动确定初始化次数
                max_iter=300
            )
            labels = kmeans.fit_predict(node_embeddings)
            print(f"聚类完成，耗时: {time.time() - t0:.2f}秒")
            
            # 获取每个聚类的代表性总结
            summaries = []
            for cluster_id in range(num_clusters):
                # 获取该聚类的所有句子的索引
                cluster_indices = [i for i, label in enumerate(labels) if label == cluster_id]
                if not cluster_indices:  # 如果该聚类没有句子，跳过
                    continue
                    
                cluster_embeddings = node_embeddings[cluster_indices]
                cluster_sentences = [node_texts[i] for i in cluster_indices]

                # 计算该聚类的中心点
                cluster_center = np.mean(cluster_embeddings, axis=0)

                # 计算每个句子与聚类中心的相似度
                similarities = cosine_similarity([cluster_center], cluster_embeddings)[0]

                # 找到与中心最相似的句子作为该聚类的代表性总结
                best_index = np.argmax(similarities)
                summaries.append(cluster_sentences[best_index])

                # # 使用新的摘要生成方法，综合关键词权重
                # summary = generate_cluster_summary(
                #     cluster_sentences, 
                #     cluster_embeddings, 
                #     cluster_center,
                #     tokenizer,
                #     model,
                #     device
                # )
                # summaries.append(summary)
            
            # 保存聚类结果
            cluster_results[path_key]['nodes'][node_key] = {
                'sentences': node_texts,
                'clusters': labels.tolist(),
                'summaries': summaries,
                'cluster_count': num_clusters
            }
            
            # 输出聚类结果
            print(f"\n聚类分析结果：")
            for idx, label in enumerate(labels):
                print(f"Cluster {label}: {node_texts[idx]}")
            
            print(f"\n该节点的聚类总结:")
            for summary in summaries:
                print(f"  代表性总结: {summary}")
    
    print(f"聚类分析完成，总耗时: {time.time() - start_time:.2f}秒")
    return cluster_results

# 对外暴露的API，用于获取聚类结果
def get_cluster_analysis(responses):
    """
    分析LLM多个回答的聚类结果
    
    Args:
        responses: LLM回答的JSON数据列表
    
    Returns:
        cluster_results: 聚类分析结果
    """
    # 如果输入为空或非列表，返回空结果
    if not responses or not isinstance(responses, list):
        return {"error": "输入数据无效"}

    # 执行聚类分析
    try:
        t0 = time.time()
        print(f"开始聚类分析，共 {len(responses)} 个回答...")
        cluster_results = analyze_clusters_for_paths(responses)
        print(f"聚类分析API调用完成，总耗时: {time.time() - t0:.2f}秒")
        return cluster_results
    except Exception as e:
        print(f"聚类分析出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"聚类分析出错: {str(e)}"}
