from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.function_tool import FunctionTool

from .parallel_search import search_locations
from .prompt import LOCATION_RESEARCH_PROMPT

_pkg_dir = Path(__file__).resolve().parents[2]
load_dotenv(_pkg_dir.parent / ".env")
load_dotenv(_pkg_dir / ".env")

location_research_agent = Agent(
    model="gemini-3.6-flash",
    name="location_research_agent",
    description=(
        "Researches real locations, reference-scan sites, or digital-scan "
        "sites via Parallel's Task API. Call ONLY when Scene Interpreter "
        "set grounding_needed=true."
    ),
    instruction=LOCATION_RESEARCH_PROMPT,
    tools=[FunctionTool(func=search_locations)],
    output_key="location_research",
)