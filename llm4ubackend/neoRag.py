# neoRag.py

from neo4j import GraphDatabase
from pprint import pprint

# Neo4j 配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "123456"

class Neo4jQuery:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    # 获取人物的基础信息
    # 注意，地点部分要通过addr为中介，再通过Where找到具体地点
    def get_basic_info(self, person_name):
        query = """
        MATCH (d:Dynasty {name: "宋"})<-[:DynastyIs]-(p:Person)
        WHERE p.name = $name
        OPTIONAL MATCH (p)-[:AddrAssocIs]->(addr)-[:Where]->(addrName)
        OPTIONAL MATCH (p)-[:GenderIs]->(gender)
        OPTIONAL MATCH (p)-[:EthnicityIs]->(eth)
        OPTIONAL MATCH (p)-[:HouseholdIs]->(house)
        OPTIONAL MATCH (p)-[:StatusIs]->(status)
        OPTIONAL MATCH (p)-[:Kin]->(kin)
        OPTIONAL MATCH (p)-[:FirstYear]->(birthYear:Year)
        OPTIONAL MATCH (p)-[:LastYear]->(deathYear:Year)
        RETURN p.name AS person, gender.name AS gender, eth.name AS ethnicity, 
               collect(distinct addrName.name) AS addresses, collect(distinct house.name) AS households,  
               collect(distinct status.name) AS statuses, collect(distinct kin.name) AS relatives,
               birthYear.name AS birthYear, deathYear.name AS deathYear
        """
        with self.driver.session() as session:
            result = session.run(query, name=person_name)
            return result.single()

    # 人物和相关事件
    def get_related_events_with_path(self, person_name):
        query = """
        MATCH path = (d:Dynasty {name: "宋"})<-[:DynastyIs]-(p:Person {name: $name})-[:Do]->(e:AssocEvent)
        OPTIONAL MATCH (e)-[:AssocIs]->(rp:Person)
        OPTIONAL MATCH (e)-[:AssocBelong]->(assoc:Association)
        OPTIONAL MATCH (e)-[:FirstYear]->(fy:Year)
        OPTIONAL MATCH (e)-[:LastYear]->(ly:Year)
        RETURN path, rp.name AS relatedPerson, assoc.name AS relationDesc, 
               fy.name AS firstYear, ly.name AS lastYear
        """
        with self.driver.session() as session:
            result = session.run(query, name=person_name)
            records = []
            for record in result:
                path = record["path"]
                nodes = [node["name"] if "name" in node else str(node) for node in path.nodes]
                relationships = [rel.type for rel in path.relationships]
                records.append({
                    "path_nodes": nodes,
                    "path_relationships": relationships,
                    "related_person": record["relatedPerson"],
                    "relation_description": record["relationDesc"],
                    "first_year": record["firstYear"],
                    "last_year": record["lastYear"]
                })
            return records

    # 写作相关事件
    def get_written_works(self, person_code):
        query = """
        MATCH (p:Person {code: $code})-[:Do]->(w:Write)
        OPTIONAL MATCH (w)-[:TextIs]->(t:Text)
        OPTIONAL MATCH (t)-[:FirstYear]->(y:Year)
        RETURN p.name AS person, t.name AS textTitle, y.name AS year
        """
        with self.driver.session() as session:
            result = session.run(query, code=person_code)
            return [record.data() for record in result]


# 使用示例
if __name__ == "__main__":
    neo4j = Neo4jQuery(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    person_name = "王安石"
    person_code = 1762

    print("人物基础信息:")
    basic_info = neo4j.get_basic_info(person_name)
    pprint(basic_info)

    print("\n相关事件路径链条:")
    paths = neo4j.get_related_events_with_path(person_name)
    for idx, item in enumerate(paths, 1):
        print(f"\n路径 {idx}:")
        # print(" -> ".join(item["path_nodes"])) # 这条是打印节点的属性
        print("关系链：", " -> ".join(item["path_relationships"]))
        print("相关人物：", item["related_person"] or "无")
        print("事件类型：", item["relation_description"] or "无")
        print("开始年份：", item["first_year"] or "无")
        print("结束年份：", item["last_year"] or "无")

    print("\n写作活动记录:")
    writings = neo4j.get_written_works(person_code)
    pprint(writings)

    neo4j.close()
