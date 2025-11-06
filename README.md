## **简介**

这是一篇将“**LLM多路径推理综合可视分析**”通用方法运用在“**历史人物不确定性**”专业领域的解决方案，核心思想是利用 **RAG + CoT_Prompt + SimCSE + 动态聚类 + 桑基图**的方法对LLM推理结果文本逻辑可视化。

主要技术栈为**前端Vue.js + 后端Flask + 图数据库Neo4j**。

1.将数据库以知识图谱的形式存储，方便在检索时提取链式路径信息，对其进行翻译，然后将提取的信息按规则定义的重要性进行排序，以RAG的形式提供给LLM，作为参考知识库；

2.定义CoT式Prompt，让LLM可以按链式逻辑思考并按规定的格式回答，比如“回答x-路径y-节点z”，每一轮回答“**相同位置**”的节点都按相同规则，有可能给出相似的逻辑；

3.利用SimCSE将回答文本转化为句向量，通过计算余弦相似度找到在向量空间中彼此靠近的句子，对其按轮廓系数进行动态聚类，得到该“**位置**”下各种回答逻辑；

4.最后，利用桑基图的载体，将每一条推理逻辑转化成一个个具体的桑基图流向，通过流向来展示回答链式逻辑链条，然后再补充一些交互展示信息+搜索高亮+具体逻辑选择等功能。


## **摘要**
对历史人物的研究不仅有助于理解人物生平轨迹与社会关系网络，也能推动对历史事件、思想文化发展的深入解读。在数字人文领域中，历史人物研究常因史料残缺、记载分歧等原因，面临大量缺失或冲突的数据，这就是历史人物数据的不确定性，这些不确定性数据的存在使历史学家在分析时难以获得准确的信息。传统不确定性推理方法不仅高度依赖专家的历史知识与推理经验，而且在面对大规模史料数据时效率低下。为应对这一问题，本文提出基于LLM的不确定性推理方法，通过检索CBDB知识图谱增强LLM的生成结果，并通过多轮推理为专家提供启发式结果。然而，目前仍缺乏能够对LLM多轮推理过程进行可视化和交互式分析的有效工具。为此，本文开发了历史人物不确定性推理可视分析系统LLM4uVis，针对时间、地点、人物和事件四类核心不确定性数据，对LLM各轮回答之间的相似推理逻辑进行语义聚类，并支持以桑基图形式展现多条推理路径及其逻辑差异，专家可以对推理过程与结果进行交叉验证与标注。通过两个不确定性推理案例与专家访谈，验证了该系统的可理解性和有效性。

## **技术路线**
<img width="2276" height="817" alt="image" src="https://github.com/user-attachments/assets/0077eb5d-1a3f-42cb-a494-cce99eec3a05" />

## **系统界面视图**
<img width="2262" height="1254" alt="image" src="https://github.com/user-attachments/assets/78fbaf7e-e5a7-4ee5-96e5-e850fd34c3cd" />

- (A)控制面板，(B)基础信息，(C) LLM多路径推理桑基图，(D)回答/链条统计信息可视化，(E)推理链条综合分析

### **桑基图意义说明**
<img width="1509" height="697" alt="image" src="https://github.com/user-attachments/assets/10aa67e2-263e-49ef-bf07-0b288347de1b" />

### **桑基图流向展示**
<img width="2039" height="963" alt="image" src="https://github.com/user-attachments/assets/31b6c33b-1433-4f2f-a5e1-8c532bb10c8c" />

### **添加链条预览**
<img width="1182" height="515" alt="image" src="https://github.com/user-attachments/assets/6a66a1cd-16ef-4027-a49a-928b8b972bdd" />

### **单选链条预览**
<img width="1177" height="513" alt="image" src="https://github.com/user-attachments/assets/403fa714-0a7a-4179-a67b-1122e079ff26" />

### **多选链条预览**
<img width="1200" height="525" alt="image" src="https://github.com/user-attachments/assets/46652bd9-d925-49d5-ba6a-20c49c478613" />

### **桑基图分析示例**
<img width="2329" height="1139" alt="image" src="https://github.com/user-attachments/assets/4710d6c2-bb1c-4eda-a510-dc2eae585b1e" />

## **链条对比分析和标注示例**
<img width="1318" height="953" alt="image" src="https://github.com/user-attachments/assets/d7b42614-7ffb-45a7-a763-850bdbc5f4ab" />
