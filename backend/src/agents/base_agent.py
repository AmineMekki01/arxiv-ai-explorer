import os
from agents import Agent, ModelSettings, Runner, SQLiteSession

from src.agents.tools import search_papers
from src.agents.prompts import RESEARCH_ASSISTANT_PROMPT
from src.config import get_settings

from dotenv import load_dotenv
load_dotenv()

class BaseAgent:

    def __init__(self):
        settings = get_settings()

        self.agent = Agent(
            name="ResearchMind Assistant",
            instructions=RESEARCH_ASSISTANT_PROMPT,
            model=settings.openai_model,
            tools=[search_papers],
            model_settings=ModelSettings(
                tool_choice="auto",
            ),
        )


    async def process_query(self, query: str, chat_id: str) -> str:
        session = SQLiteSession(chat_id)
        result = await Runner.run(self.agent, query, session=session)
        return result.final_output
