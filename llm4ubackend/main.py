# main.py

from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Prompt

from questionHandler import get_prompt_by_type, wrap_with_rag
from jsonHandler import parse_response_to_json, save_structured_json
from rag2llm import build_rag_context
from neoRag import Neo4jQuery, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from llmApi import chat_completion

console = Console()

def main():
    console.print("[bold green]请输入你的问题，输入 'exit' 退出[/]")
    neo4j = Neo4jQuery(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    while True:
        question = Prompt.ask("[bold cyan]你的问题内容[/]").strip()
        if question.lower() in ['exit', 'quit']:
            break

        q_type = Prompt.ask("[bold cyan]请输入问题类型（时间/地点/人物/事件）[/]").strip()
        entity = Prompt.ask("[bold cyan]请输入实体名称（如人物名）用于检索知识图谱[/]").strip()

        base_prompt = get_prompt_by_type(question, q_type)
        rag_limited, full_rag_json = build_rag_context(entity, neo4j)

        full_prompt = wrap_with_rag(rag_limited, base_prompt)
        messages = [{"role": "user", "content": full_prompt}]

        console.print("[italic yellow]思考中...[/]")
        response = chat_completion(messages)

        if response:
            console.print("\n[bold magenta]回答:[/]")
            console.print(Markdown(response))
            console.print("\n" + "-" * 60 + "\n")
            structured = parse_response_to_json(response, q_type, question, rag_limited)
            save_structured_json(structured, q_type, question)

    neo4j.close()

if __name__ == "__main__":
    main()
