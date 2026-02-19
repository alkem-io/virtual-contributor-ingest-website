import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langchain_core.documents import Document
from typing_extensions import TypedDict
from config import env
from dotenv import load_dotenv
from alkemio_virtual_contributor_engine import setup_logger
load_dotenv()

logger = setup_logger(__name__)


def calculate_progressive_length(
    current_chunk: int,
    total_chunks: int,
    target_length: int
) -> int:
    """Calculate progressive summary length based on chunk progress."""
    min_ratio = 0.4
    progress_ratio = current_chunk / total_chunks
    return round(target_length * max(min_ratio, progress_ratio))


system_prompt = """Expert at creating structured, information-dense summaries \
for semantic search and vector retrieval.

FORMAT:
- Use markdown headers (### or **bold**) to organize content by theme
- Use bullet points for lists of related facts
- Each bullet must contain specific facts with dates, names, or numbers

REQUIREMENTS:
- Preserve ALL key entities: names, titles, dates, numbers, technical terms, URLs, references
- Use concrete, factual language - no vague descriptions
- Include domain-specific terminology and searchable keywords
- Maximize information density - every sentence must convey specific facts

FORBIDDEN:
- No repetitive sentence patterns ("He is a member of...", "He has also been involved in...")
- No generic filler statements without specific details
- No vague phrases like "various things" or "several aspects"
- No interpretations or opinions not in source
- Never repeat the same information twice"""

summarize_prompt = """Create a structured summary of the following content \
using markdown headers and bullet points.
Include only essential facts and entities - no filler or repetition.
Maximum length: {maxSummaryLength} characters.

Content:
{context}

Summary:"""

refine_prompt = """Refine this summary by integrating new information.
Maintain markdown structure with headers and bullet points.
Maximum length: {maxSummaryLength} characters.

Current summary:
{currentSummary}

New content to integrate:
{context}

Instructions:
1. Merge new facts into existing sections or create new sections as needed
2. Remove any redundancy - never repeat the same fact twice
3. Preserve ALL specific entities, dates, and details from both sources
4. Keep bullet points factual and specific - no generic statements

Refined summary:"""


class State(TypedDict):
    chunks: list[Document]
    index: int
    summary: Document


def build_graph(llm: BaseChatModel):
    """Build summarization graph with the specified LLM model."""
    model_name = getattr(llm, 'azure_deployment', None) or getattr(llm, 'model', None) or getattr(llm, 'model_name', 'unknown')

    def initial_summary(state: State):
        start_time = time.time()
        chunk = state["chunks"][0]
        total_chunks = len(state["chunks"])

        max_summary_length = calculate_progressive_length(
            1, total_chunks, env.summary_length
        )
        logger.info(
            f"Starting initial summary: processing chunk 1 of {total_chunks} "
            f"(max length: {max_summary_length})"
        )

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=summarize_prompt.format(
                    maxSummaryLength=max_summary_length, context=chunk.page_content
                )
            ),
        ])

        chain = prompt | llm
        result = chain.invoke({})

        duration = f"{time.time() - start_time:.2f}"
        logger.info(
            f"Initial summary complete: {len(result.content)} chars "
            f"in {duration}s (model: {model_name})"
        )

        return {
            "index": 1,
            "summary": Document(
                page_content=result.content,
                metadata={
                    "source": chunk.metadata["source"],
                    "title": chunk.metadata["title"],
                    "type": chunk.metadata["type"],
                    "embeddingType": "summary",
                },
            ),
        }

    def refine_summary(state: State):
        start_time = time.time()
        total_chunks = len(state["chunks"])
        current_index = state["index"]

        max_summary_length = calculate_progressive_length(
            current_index + 1, total_chunks, env.summary_length
        )
        progress_percent = round(((current_index + 1) / total_chunks) * 100)
        logger.info(
            f"Refining summary: chunk {current_index + 1} of {total_chunks} "
            f"({progress_percent}%, max length: {max_summary_length})"
        )

        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=refine_prompt.format(
                    maxSummaryLength=max_summary_length,
                    currentSummary=state["summary"].page_content,
                    context=state["chunks"][current_index].page_content,
                )
            ),
        ])

        chain = prompt | llm
        result = chain.invoke({})

        duration = f"{time.time() - start_time:.2f}"
        logger.info(
            f"Refinement complete: {len(result.content)} chars "
            f"in {duration}s (model: {model_name})"
        )

        return {
            "index": current_index + 1,
            "summary": Document(
                page_content=result.content, metadata=state["summary"].metadata
            ),
        }

    def should_refine(state: State):
        if state["index"] >= len(state["chunks"]):
            logger.info(
                f"Summary complete: processed all {len(state['chunks'])} chunks"
            )
            return END
        return "refine_summary"

    return (
        StateGraph(State)
        .add_node("initial_summary", initial_summary)
        .add_node("refine_summary", refine_summary)
        .add_edge(START, "initial_summary")
        .add_conditional_edges(
            "initial_summary", should_refine, ["refine_summary", END]
        )
        .add_conditional_edges(
            "refine_summary", should_refine, ["refine_summary", END]
        )
        .compile()
    )
