from google.adk.agents import Agent

from .prompt import SET_DESIGN_PROMPT

set_design_agent = Agent(
    model="gemini-3.6-flash",
    name="set_design_agent",
    description=(
        "Always run last. Details props, set dressing, camera, and "
        "authenticity; presents up to 3 options and finalizes only after "
        "the filmmaker confirms."
    ),
    instruction=SET_DESIGN_PROMPT,
    output_key="production_brief",
)
