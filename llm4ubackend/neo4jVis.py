# Neo4jVis.py
# 对知识图谱内容进行可视化

from neo4j import GraphDatabase
from pprint import pprint
from flask import Flask, request, jsonify

# Neo4j 配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "123456"

class Neo4jService:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        
    def close(self):
        self.driver.close()
    
    def get_person_graph(self, person_name):
        # 存储节点和关系
        nodes = []
        links = []
        node_ids = set()  # 更高效的去重方式
        name = person_name

        # 可视化查询语句（返回路径，通用处理）
        query = """
        MATCH path1 = (p:Person {name: $name})<-[:DynastyIs]-(d:Dynasty {name: "宋"})

        WITH p, collect(path1) AS paths

        // AddrAssocIs 限制 3 个
        OPTIONAL MATCH (p)-[:AddrAssocIs]->(:Address)-[:Where]->(addrName)
        WITH p, paths + collect((p)-[:AddrAssocIs]->(:Address)-[:Where]->(addrName))[..3] AS paths

        // Gender
        OPTIONAL MATCH path3 = (p)-[:GenderIs]->(gender)
        WITH p, paths + collect(path3) AS paths

        // Ethnicity
        OPTIONAL MATCH path4 = (p)-[:EthnicityIs]->(eth)
        WITH p, paths + collect(path4) AS paths

        // HouseholdIs 限制 3 个
        OPTIONAL MATCH path5_full = (p)-[:HouseholdIs]->(house)
        WITH p, paths + collect(path5_full)[..3] AS paths

        // StatusIs 限制 3 个
        OPTIONAL MATCH path6_full = (p)-[:StatusIs]->(status)
        WITH p, paths + collect(path6_full)[..3] AS paths

        // Kin 限制 3 个
        OPTIONAL MATCH path7_full = (p)-[:Kin]->(kin)
        WITH p, paths + collect(path7_full)[..3] AS paths

        // FirstYear
        OPTIONAL MATCH path8 = (p)-[:FirstYear]->(birthYear)
        WITH p, paths + collect(path8) AS paths

        // LastYear
        OPTIONAL MATCH path9 = (p)-[:LastYear]->(deathYear)
        WITH p, paths + collect(path9) AS paths

        // Do (事件)，包括扩展的 AssocIs 和 AssocBelong，限制 3 个
        OPTIONAL MATCH path10_1 = (p)-[:Do]->(event:AssocEvent)
        WITH p, paths + collect(path10_1)[..3] AS paths

        OPTIONAL MATCH path10_2 = (p)-[:Do]->(event:AssocEvent)-[:AssocIs]->(assocPerson:Person)
        WITH p, paths + collect(path10_2)[..3] AS paths

        OPTIONAL MATCH path10_3 = (p)-[:Do]->(event:AssocEvent)-[:AssocBelong]->(assoc:Association)
        WITH p, paths + collect(path10_3)[..3] AS paths


        // Text (文献) 限制 3 个
        OPTIONAL MATCH path11_full = (p)-[:Do]->(:Write)-[:TextIs]->(text:Text)
        WITH paths + collect(path11_full)[..3] AS paths

        // 返回所有路径，供程序统一解析 nodes / relationships
        UNWIND paths AS path
        RETURN path
        """

        # 对路径的通用 实体-关系 抽取处理方法
        with self.driver.session() as session:
            result = session.run(query, name=person_name)

            for record in result:
                for value in record.values():
                    # 如果是路径，提取节点和关系
                    if hasattr(value, 'nodes') and hasattr(value, 'relationships'):
                        for node in value.nodes:
                            if node.id not in node_ids:
                                node_data = dict(node.items())
                                node_data['id'] = node.id
                                node_data['type'] = list(node.labels)[0] if node.labels else 'Unknown'
                                nodes.append(node_data)
                                node_ids.add(node.id)

                        for rel in value.relationships:
                            links.append({
                                'id': rel.id,
                                'source': rel.start_node.id,
                                'target': rel.end_node.id,
                                'type': rel.type
                            })

                    # 如果是单独的节点
                    elif hasattr(value, 'labels'):
                        if value.id not in node_ids:
                            node_data = dict(value.items())
                            node_data['id'] = value.id
                            node_data['type'] = list(value.labels)[0] if value.labels else 'Unknown'
                            nodes.append(node_data)
                            node_ids.add(value.id)

                    # 如果是单独的关系
                    elif hasattr(value, 'type') and hasattr(value, 'start_node') and hasattr(value, 'end_node'):
                        links.append({
                            'id': value.id,
                            'source': value.start_node.id,
                            'target': value.end_node.id,
                            'type': value.type
                        })

        return {'nodes': nodes, 'links': links}
