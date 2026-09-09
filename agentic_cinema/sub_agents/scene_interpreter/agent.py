from google.adk.agents import Agent

from .prompt import SCENE_INTERPRETER_PROMPT

scene_interpreter_agent = Agent(
    model="gemini-3.6-flash",
    name="scene_interpreter_agent",
    description=(
        "Reads a scene, runs the grounding gate, and recommends a path: "
        "none (existing set), real_location, reference_scan, or digital_scan. "
        "Always call this agent first."
    ),
    instruction=SCENE_INTERPRETER_PROMPT,
    output_key="scene_interpretation",
)
