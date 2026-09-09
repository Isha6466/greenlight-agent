from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

_pkg_dir = Path(__file__).resolve().parent
load_dotenv(_pkg_dir.parent / ".env")
load_dotenv(_pkg_dir / ".env")

from .location_dossier import get_location_dossier
from .report_generator import is_confirmed_brief, write_report_from_state
from .sub_agents.location_research.agent import location_research_agent
from .sub_agents.scene_interpreter.agent import scene_interpreter_agent
from .sub_agents.set_design.agent import set_design_agent


def _user_text(callback_context: CallbackContext) -> str:
    content = callback_context.user_content
    if not content or not content.parts:
        return ""
    return "\n".join(
        part.text for part in content.parts if getattr(part, "text", None)
    ).strip()


def _capture_scene(callback_context: CallbackContext) -> None:
    """Store the original scene and the latest filmmaker message in session state."""
    text = _user_text(callback_context)
    if not text:
        return None
    callback_context.state["latest_user_message"] = text
    if not callback_context.state.get("scene_text"):
        callback_context.state["scene_text"] = text
    return None


def _tool_response_text(tool_response: Any) -> str:
    if tool_response is None:
        return ""
    if isinstance(tool_response, str):
        return tool_response
    if isinstance(tool_response, dict):
        for key in ("result", "output", "content"):
            if key in tool_response:
                return str(tool_response[key])
        return str(tool_response)
    return str(tool_response)


def _extract_location_name(brief_text: str, state: dict) -> str:
    """Best-effort guess at the confirmed location's name for the dossier query."""
    selected = state.get("latest_user_message") or ""
    if selected and len(selected) < 200:
        return selected
    return brief_text[:200]


def _after_tool(
    tool: BaseTool,
    args: dict[str, Any],
    tool_context: ToolContext,
    tool_response: Any,
) -> Any:
    """After a confirmed set-design brief, run the location dossier and write the PDF."""
    if getattr(tool, "name", "") != "set_design_agent":
        return None
    brief_text = _tool_response_text(tool_response)
    if not is_confirmed_brief(brief_text):
        return None

    location_name = _extract_location_name(brief_text, tool_context.state)
    dossier = get_location_dossier(location_name)
    tool_context.state["location_dossier"] = dossier

    pdf_path = write_report_from_state(
        tool_context.state,
        final_brief=brief_text,
        selected_option=tool_context.state.get("latest_user_message"),
    )
    tool_context.state["pdf_report_path"] = pdf_path
    note = (
        f"\n\n---\nPDF report saved to:\n{pdf_path}\n"
        "Include this full local path in your final reply to the filmmaker."
    )
    if isinstance(tool_response, str) or tool_response is None:
        return brief_text + note
    if isinstance(tool_response, dict):
        updated = dict(tool_response)
        updated["pdf_report_path"] = pdf_path
        if "result" in updated:
            updated["result"] = str(updated["result"]) + note
        else:
            updated["result"] = brief_text + note
        return updated
    return brief_text + note


root_agent = Agent(
    model="gemini-3.6-flash",
    name="greenlight_root_agent",
    description=(
        "Greenlight pipeline: scene gate → optional location research → "
        "set/VFX brief with filmmaker confirmation."
    ),
    instruction="""
You are Greenlight, a 3-agent production pipeline. You orchestrate; you do
not replace the specialists. Answer one question well: does this scene
need the real world, and if so, exactly how.

## Tools (call them in this order — never skip Agent 1 or Agent 3)
- scene_interpreter_agent — Agent 1, always first
- location_research_agent — Agent 2, ONLY if Agent 1 set grounding_needed=true
- set_design_agent — Agent 3, always last

## Pipeline
1. Call scene_interpreter_agent with the filmmaker's scene. Surface its
   gate decision and reason to the filmmaker (never hide a skip).
2. If grounding_needed is true:
   Call location_research_agent with the scene plus Agent 1's research
   brief and recommended path. Do not call it for any other reason.
3. If grounding_needed is false:
   Do NOT call location_research_agent. Go straight to Agent 3. This
   saves cost and avoids unused Parallel API calls.
4. Always call set_design_agent at the end, passing:
   - the original scene
   - Agent 1's full output
   - Agent 2's options if they exist, otherwise note "existing/generic set"
5. After Agent 3 presents options, stay in the confirmation loop: if the
   filmmaker picks or asks a follow-up, call set_design_agent again with
   that reply. Do not invent a "final" brief yourself. Agent 3 finalizes
   only after explicit filmmaker sign-off.
6. When set_design_agent returns a confirmed final brief, a PDF report is
   generated automatically from this session's state. If that result
   includes a line "PDF report saved to:", copy the full local file path
   into your reply so the filmmaker can open the file. Never invent a path.

## Hard rules
- Never call location_research_agent before scene_interpreter_agent.
- Never call location_research_agent when grounding_needed is false.
- Never skip set_design_agent on a new scene.
- Never claim a brief is finalized unless Agent 3 labeled it confirmed.
""",
    tools=[
        AgentTool(agent=scene_interpreter_agent),
        AgentTool(agent=location_research_agent),
        AgentTool(agent=set_design_agent),
    ],
    before_agent_callback=_capture_scene,
    after_tool_callback=_after_tool,
)