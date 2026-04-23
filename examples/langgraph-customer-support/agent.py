import os

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI


class SupportState(dict):
    pass


def build_graph():
    llm = ChatOpenAI(model="gpt-4o-mini")

    async def assistant(state: SupportState):
        messages = state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": messages + [response]}

    graph = StateGraph(SupportState)
    graph.add_node("assistant", assistant)
    graph.set_entry_point("assistant")
    graph.add_edge("assistant", END)
    return graph.compile()


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY before running this example.")
    compiled = build_graph()
    print(compiled)
