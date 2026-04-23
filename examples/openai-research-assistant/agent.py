import os

from agents import Agent, Runner


def build_agent():
    return Agent(
        name="research-assistant",
        instructions="Answer questions with concise, sourced research summaries.",
        model="gpt-4o-mini",
    )


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY before running this example.")
    agent = build_agent()
    result = Runner.run(agent, "Summarize the latest battery storage trends in 3 bullet points.")
    print(result.final_output)
