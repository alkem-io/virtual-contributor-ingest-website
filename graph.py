from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langchain_core.documents import Document
from typing_extensions import TypedDict
from alkemio_virtual_contributor_engine import mistral_medium as llm
from dotenv import load_dotenv
load_dotenv()


system_prompt = (
    "You are tasked with concising summaries based entirely on the user "
    "input. While doing so preserve as much information as possible like "
    "names, references titles, dates, etc."
)
"""
   In your summary preserve as much information as possible, including:
   - References and connections between documents
   - Names of participants and their roles
   - Titles, dates, and temporal relationships
   - Key concepts and their relationships within the body of knowledge
   Focus on maintaining the coherence of information across document boundaries.`

"""
summarize_prompt = (
    "Write a detailed summary, no more than {summaryLength} characters "
    "of the following: {context}"
)
refine_prompt = """
    `Produce a final detailed summary, no more than {summaryLength} characters.
     Existing summary up to this point:

     {currentSummary}

     New context: {context}

     Given the new context, refine the original summary.`
"""


class State(TypedDict):
    chunks: list[Document]
    index: int
    summary: Document


def initial_summary(state: State):
    chunk = state["chunks"][0]

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=summarize_prompt.format(
                summaryLength=1000, context=chunk.page_content
            )
        ),
    ])

    chain = prompt | llm
    result = chain.invoke({})

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
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=refine_prompt.format(
                summaryLength=1000,
                currentSummary=state["summary"].page_content,
                context=state["chunks"][state["index"]].page_content,
            )
        ),
    ])

    chain = prompt | llm
    result = chain.invoke({})

    return {
        "index": state["index"] + 1,
        "summary": Document(
            page_content=result.content, metadata=state["summary"].metadata
        ),
    }


def should_refine(state: State):
    if state["index"] >= len(state["chunks"]):
        return END
    return "refine_summary"


graph = (
    StateGraph(State)
    .add_node("initial_summary", initial_summary)
    .add_node("refine_summary", refine_summary)
    .add_edge(START, "initial_summary")
    .add_conditional_edges("initial_summary", should_refine, ["refine_summary", END])
    .add_conditional_edges("refine_summary", should_refine, ["refine_summary", END])
    .compile()
)
