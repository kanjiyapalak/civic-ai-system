import json
from typing import Any, Callable, Dict, Generator, Optional

from langgraph.graph.state import CompiledStateGraph


PROCESSING_STEP_MESSAGES = {
    "validation": "Validating complaint details...",
    "vision": "Checking for a public civic issue (not private property)...",
    "department_mapping": "Mapping issue to department...",
    "location": "Finding ward from your location...",
    "duplicate_check": "Checking for duplicate complaints nearby...",
    "assign_officer": "Assigning responsible officer...",
}

VERIFICATION_STEP_MESSAGES = {
    "upload_node": "Preparing verification...",
    "location_check_node": "Verifying GPS location match...",
    "gemini_check_node": "Comparing before/after images with AI...",
    "decision_node": "Making final verification decision...",
}


def format_sse(event: str, data: Dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def stream_graph(
    graph: CompiledStateGraph,
    state: Dict[str, Any],
    step_messages: Dict[str, str],
    enrich_step: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
) -> Generator[str, None, Dict[str, Any]]:
    final_state = dict(state)

    try:
        for chunk in graph.stream(state):
            for node_name, node_state in chunk.items():
                if isinstance(node_state, dict):
                    final_state.update(node_state)

                step_payload: Dict[str, Any] = {
                    "step": node_name,
                    "message": step_messages.get(node_name, f"Running {node_name}..."),
                    "status": "running",
                }
                if enrich_step:
                    step_payload.update(enrich_step(node_name, final_state))

                yield format_sse("step", step_payload)
    except ValueError as exc:
        yield format_sse("error", {"message": str(exc)})
        return final_state
    except Exception as exc:
        yield format_sse("error", {"message": f"Processing failed: {exc}"})
        return final_state

    return final_state
