import os

from crewai import Agent, Crew, Task
from crewai import Process
from crewai_tools import SerperDevTool

from agentcloudkelp.adapters.crewai import CrewAIAdapter


def build_crew():
    search_tool = SerperDevTool()
    agent = Agent(
        role="Flight booking assistant",
        goal="Find and book flights while confirming the booking clearly",
        backstory="You help users book flights safely and accurately.",
        tools=[search_tool],
        verbose=True,
        allow_delegation=False,
    )
    task = Task(
        description="Handle flight booking requests and use tools when needed.",
        agent=agent,
        expected_output="A concise booking confirmation or a clear explanation.",
    )
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False), agent


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY before running this example.")
    crew, agent = build_crew()
    adapter = CrewAIAdapter(agent=agent, crew=crew)
    print(adapter.name())
