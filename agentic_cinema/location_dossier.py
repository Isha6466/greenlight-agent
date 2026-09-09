import os

from parallel import Parallel


def get_location_dossier(location_name: str) -> dict:
    empty = {
        "best_shooting_season": "",
        "weather_risks": "",
        "security_notes": "",
        "nearest_hospital": "",
    }
    try:
        client = Parallel(api_key=os.environ["PARALLEL_API_KEY"])
        task_run = client.task_run.create(
            input=(
                f"Location: {location_name}. Find the best shooting season, "
                f"weather risks, security/permit considerations, and "
                f"nearest hospital for a film production at this location. "
                f"Use simple, everyday English, no technical jargon."
            ),
            task_spec={
                "output_schema": {
                    "type": "json",
                    "json_schema": {
                        "type": "object",
                        "properties": {
                            "best_shooting_season": {"type": "string"},
                            "weather_risks": {"type": "string"},
                            "security_notes": {"type": "string"},
                            "nearest_hospital": {"type": "string"},
                        },
                        "required": [
                            "best_shooting_season",
                            "weather_risks",
                            "security_notes",
                            "nearest_hospital",
                        ],
                    },
                }
            },
            processor="core",
        )
        result = client.task_run.result(task_run.run_id, api_timeout=180)
        return result.output.content
    except Exception:
        return empty
        