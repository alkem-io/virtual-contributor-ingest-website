from config import env
from typing import Dict, List
import re
import requests
from bs4 import BeautifulSoup
from graph import document_graph, bok_graph
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from urllib.parse import urlparse
import asyncio

from local_types import DocumentType
from url_utils import is_file_link

from alkemio_virtual_contributor_engine import (
    ingest_documents,
    AlkemioVirtualContributorEngine,
    IngestWebsite,
    IngestionResult,
    IngestWebsiteResult,
    setup_logger
)

logger = setup_logger(__name__)


def get_pages(base_url, current_url, found_pages={}) -> Dict[str, BeautifulSoup]:
    parsed = urlparse(base_url)
    domain = f"{parsed.scheme}://{parsed.netloc}"

    current_url = re.sub(r"#.*", "", current_url)

    should_return = False
    if current_url in found_pages:
        should_return = True
        logger.info(f"Already processed {current_url}")
    if len(found_pages) > env.process_pages_limit:
        should_return = True
        logger.info(f"Reached limit of {env.process_pages_limit}")
    if not current_url.startswith(base_url) and not current_url.startswith("/"):
        should_return = True
        logger.info(f"Outside of domain {current_url}")
    is_file, extension = is_file_link(current_url)
    if is_file:
        should_return = True
        logger.info(f"Not a page link - {extension}")

    if should_return:
        return found_pages

    logger.info(f"Processing {current_url}")
    try:
        page = requests.get(current_url, timeout=3)
        page.raise_for_status()
        soup = BeautifulSoup(page.content, "html.parser")
    except (requests.RequestException, requests.Timeout) as e:
        logger.error(e)
        logger.error(f"Failed to fetch {current_url}")
        return found_pages
    found_pages[current_url] = soup
    links = soup.find_all("a")
    logger.info(f"Found {len(links)} links")
    logger.debug(f"Links: {list(map(lambda link: link.get('href', '/'), links))}")
    for link in links:
        found_link = link.get("href", "/")
        found_link = re.sub(r"\.+\/", "/", found_link)
        found_link = re.sub(r"(?<!:)\/\/+", "/", found_link)
        found_link = re.sub(r"\/+$", "", found_link)
        if found_link.startswith("/"):
            found_link = domain + found_link
        link_pages = get_pages(base_url, found_link, found_pages)
        found_pages = found_pages | link_pages

    return found_pages


def get_documents(
    base_url: str, pages: Dict[str, BeautifulSoup]
) -> Dict[str, Document]:
    documents: Dict[str, Document] = {}
    tags = ["p", "section", "article", "title", "h1"]
    for url, page in pages.items():
        logger.info(f"Processing {url}")
        page_elements = []
        for tag in tags:
            matches = page.find_all(tag)
            for match in matches:
                page_elements.append(match.get_text())
        page_content = re.sub(r"\n\n*", "\n", "".join(page_elements))
        document_id = url.replace(base_url, "")
        if not document_id or document_id == "":
            document_id = "root"
        documents[url] = Document(
            page_content=page_content,
            metadata={
                "documentId": document_id,
                "source": url,
                "title": page.title.getText() if page.title else "",
                "type": DocumentType.WEBPAGE.value,
            },
        )
    return documents


async def prepare_documents(base_url: str, documents: Dict[str, Document]):

    for_embed: list[Document] = []
    summaries: list[str] = []

    for url, document in documents.items():
        logger.info(f"Preparing {url}")
        if len(document.page_content) >= env.chunk_size:
            logger.info(f"Splitting {url}; length: {len(document.page_content)}")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=env.chunk_size, chunk_overlap=env.chunk_size // 5
            )

            splitted = text_splitter.split_documents([document])
            logger.info(f"Split into {len(splitted)} chunks")
            for index, chunk in enumerate(splitted):
                chunk.metadata.update(
                    {
                        "documentId": f"{chunk.metadata['documentId']}-chunk{index}",
                        "embeddingType": "chunk",
                        "chunkIndex": index,
                    }
                )

            for_embed += splitted

            if len(splitted) > 3:
                # Document fragmented into many chunks — summarize to preserve coherence
                logger.info(f"Summarizing {url}: {len(splitted)} chunks (>3 threshold)")
                try:
                    result = await document_graph.ainvoke(
                        {"chunks": list(splitted)},
                        {"recursion_limit": len(splitted) * 2 + 10},
                    )
                    summary_text = result["summary"]
                    summary_doc = Document(
                        page_content=summary_text,
                        metadata={
                            "documentId": f"{document.metadata['documentId']}-summary",
                            "source": document.metadata["source"],
                            "title": document.metadata["title"],
                            "type": document.metadata["type"],
                            "embeddingType": "summary",
                        },
                    )
                    logger.info(f"Summary length: {len(summary_text)} chars")
                    for_embed.append(summary_doc)
                    summaries.append(summary_text)
                except Exception as e:
                    logger.error(f"Failed to summarize {url}: {e}")
                    summaries.append(document.page_content)
            else:
                # Few chunks — use raw content for BoK input
                logger.info(f"{url}: {len(splitted)} chunks, using chunks directly")
                for chunk in splitted:
                    summaries.append(chunk.page_content)
        else:
            for_embed.append(document)
            summaries.append(document.page_content)

    # Body-of-knowledge summarization
    if summaries:
        logger.info(f"Starting body-of-knowledge summarization from {len(summaries)} summaries")
        try:
            bok_text = "\n\n".join(summaries)
            bok_splitter = RecursiveCharacterTextSplitter(
                chunk_size=env.chunk_size, chunk_overlap=env.chunk_size // 5
            )
            bok_chunks = bok_splitter.create_documents([bok_text])
            logger.info(f"BoK split into {len(bok_chunks)} chunks")

            result = await bok_graph.ainvoke(
                {"chunks": list(bok_chunks)},
                {"recursion_limit": len(bok_chunks) * 2 + 10},
            )
            bok_summary = result["summary"]

            parsed = urlparse(base_url)
            bok_doc = Document(
                page_content=bok_summary,
                metadata={
                    "documentId": "body-of-knowledge-summary",
                    "source": base_url,
                    "title": parsed.netloc,
                    "type": "bodyOfKnowledgeSummary",
                    "embeddingType": "summary",
                },
            )
            logger.info(f"BoK summary length: {len(bok_summary)} chars")
            for_embed.append(bok_doc)
        except Exception as e:
            logger.error(f"Failed to create BoK summary: {e}")

    return for_embed


def embed_documents(base_url: str, for_embed: List[Document]):
    collection_name = f"{urlparse(base_url).netloc}-knowledge".replace(":", "-")
    ingest_documents(collection_name, for_embed)


async def query(input: IngestWebsite) -> IngestWebsiteResult:
    logger.info(f"Handler invoked for base URL: {input.base_url}")
    pages = get_pages(input.base_url, input.base_url, {})

    if len(pages) == 0:
        logger.error("No pages found")
        return IngestWebsiteResult(
            result=IngestionResult.FAILURE,
            error="No pages found.",
        )
    logger.info(f"Pages found: {len(pages)}")
    documents = get_documents(input.base_url, pages)
    logger.info(f"Documents found: {len(documents)}")
    prepared_documents = await prepare_documents(input.base_url, documents)
    logger.info(f"Prepared documents: {len(prepared_documents)}")
    embed_documents(input.base_url, prepared_documents)
    logger.info("Done")
    return IngestWebsiteResult(result=IngestionResult.SUCCESS)


engine = AlkemioVirtualContributorEngine()
engine.register_handler(query)
asyncio.run(engine.start())
