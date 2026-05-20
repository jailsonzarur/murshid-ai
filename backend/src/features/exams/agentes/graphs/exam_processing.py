from __future__ import annotations

from typing import cast

from src.features.exams.agentes.nodes import (
    answer_key_inference_node,
    process_layout_node,
    save_results_node,
    text_structuring_node,
    vision_extraction_node,
)
from src.features.exams.agentes.state import ExamProcessingState


def build_exam_processing_graph():
    from langgraph.graph import END, START, StateGraph

    graph = StateGraph(ExamProcessingState)
    graph.add_node("process_layout_node", process_layout_node)
    graph.add_node("vision_extraction_node", vision_extraction_node)
    graph.add_node("text_structuring_node", text_structuring_node)
    graph.add_node("answer_key_inference_node", answer_key_inference_node)
    graph.add_node("save_results_node", save_results_node)

    graph.add_edge(START, "process_layout_node")
    graph.add_edge("process_layout_node", "vision_extraction_node")
    graph.add_edge("vision_extraction_node", "text_structuring_node")
    graph.add_edge("text_structuring_node", "answer_key_inference_node")
    graph.add_edge("answer_key_inference_node", "save_results_node")
    graph.add_edge("save_results_node", END)

    return graph.compile()


async def run_exam_processing_graph(initial_state: ExamProcessingState) -> ExamProcessingState:
    graph = build_exam_processing_graph()
    result = await graph.ainvoke(initial_state)
    return cast(ExamProcessingState, result)
