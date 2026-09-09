import os

from parallel import Parallel


def search_locations(scene_summary: str, recommended_path: str) -> dict:
    """Find up to 3 real, filmable location options for a scene using
    Parallel's Task API. Blocks until the research is fully complete —
    never returns a partial or in-progress result.

    Args:
        scene_summary: A short description of the scene, its mood, and
            what kind of place is needed.
        recommended_path: One of "real_location", "reference_scan", or
            "digital_scan" — what kind of research is needed.

    Returns:
        A dict with an "options" list. Each option has: name,
        why_it_fits, accessibility_and_permits, safety_flags, logistics.
        Returns {"options": []} if the research fails.
    """
    try:
        client = Parallel(api_key=os.environ["PARALLEL_API_KEY"])
        task_run = client.task_run.create(
            input=(
                f"Scene: {scene_summary}. Recommended approach: "
                f"{recommended_path}. Find up to 3 real, filmable "
                f"location options. For each, check accessibility, "
                f"permits, and safety (including proximity to sensitive "
                f"or restricted areas like international borders). Use "
                f"simple, everyday English, no technical jargon."
            ),
            task_spec={
                "output_schema": {
                    "type": "json",
                    "json_schema": {
                        "type": "object",
                        "properties": {
                            "options": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "why_it_fits": {"type": "string"},
                                        "accessibility_and_permits": {
                                            "type": "string"
                                        },
                                        "safety_flags": {"type": "string"},
                                        "logistics": {"type": "string"},
                                    },
                                    "required": [
                                        "name",
                                        "why_it_fits",
                                        "accessibility_and_permits",
                                        "safety_flags",
                                        "logistics",
                                    ],
                                },
                            }
                        },
                        "required": ["options"],
                    },
                }
            },
            processor="core",
        )
        result = client.task_run.result(task_run.run_id, api_timeout=180)
        return result.output.content
    except Exception:
        return {"options": []}