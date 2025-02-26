from typing import Dict, List
import re
import requests
from bs4 import BeautifulSoup
from graph import graph
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from urllib.parse import urlparse
import asyncio

from ai_models import embedding_function

from local_types import DocumentType


from alkemio_virtual_contributor_engine.chromadb_client import chromadb_client
from alkemio_virtual_contributor_engine.alkemio_vc_engine import (
    AlkemioVirtualContributorEngine,
    setup_logger,
)
from alkemio_virtual_contributor_engine.events.ingest_website import IngestWebsite
from alkemio_virtual_contributor_engine.events.response import Response

from config import env

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
    if current_url.endswith(".pdf"):
        should_return = True

    if should_return:
        return found_pages

    logger.info(f"Processing {current_url}")
    page = requests.get(current_url)
    soup = BeautifulSoup(page.content, "html.parser")
    found_pages[current_url] = soup
    links = soup.find_all("a")
    logger.info(f"Found {len(links)} links")
    logger.debug(f"Links: {list(map( lambda link: link.get('href', '/'), links))}")
    for a in links:
        found_link = a.get("href", "/")
        found_link = re.sub(r"\.+\/", "/", found_link)
        found_link = re.sub(r"\/\/+", "/", found_link)
        found_link = re.sub(r"\/+$", "", found_link)
        if found_link.startswith("/"):
            found_link = domain + found_link
            link_pages = get_pages(base_url, found_link, found_pages)
            found_pages = found_pages | link_pages

    return found_pages


def get_docuemnts(
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
                "title": page.title and page.title.getText(),
                "type": DocumentType.WEBPAGE.value,
            },
        )
    return documents


async def prepare_documents(documents: Dict[str, Document]):

    for_embed: list[Document] = []
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
            # summarise only if there are more than one chunk and less than 10 to save resources
            if len(splitted) > 1 and len(splitted) < 10:
                logger.info(f"Summarizing {url}")
                summary = (await graph.ainvoke({"chunks": list(splitted)}))["summary"]
                summary.metadata.update(
                    {
                        "documentId": f"{document.metadata['documentId']}-summary",
                        "embeddingType": "summary",
                    }
                )
                logger.info(f"Summary length: {len(summary.page_content)}")
                for_embed += [summary]
        else:
            for_embed += [document]
    return for_embed


def embed_documents(base_url: str, for_embed: List[Document]):
    collection_name = f"{urlparse(base_url).netloc}-knowledge".replace(":", "-")
    try:
        collection = chromadb_client.get_collection(collection_name)
        if collection:
            logger.info(f"Collection: {collection.name} exists. Deleting...")
        chromadb_client.delete_collection(collection_name)
    except Exception as e:
        logger.info("Collection not found")
        logger.error(e)

    collection = chromadb_client.get_or_create_collection(collection_name)
    logger.info(f"Collection: {collection.name} created.")

    batch_size = 10
    for batch_index in range(0, len(for_embed), batch_size):
        batch = for_embed[batch_index : batch_index + batch_size]
        documents, embeddings, metadatas, ids = [], [], [], []
        for doc in batch:
            documents.append(doc.page_content)
            metadatas.append(doc.metadata)
            ids.append(doc.metadata["documentId"])
        logger.info(f"Embedding {len(documents)} documents")
        embeddings = embedding_function(documents)
        logger.info(f"Upserting {len(documents)} documents")

        collection.upsert(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info(f"Upserted {len(documents)} documents")


async def query(input: IngestWebsite) -> Response:
    logger.info(f"Handler invoked for base URL: {input.base_url}")
    pages = get_pages(input.base_url, input.base_url, {})
    logger.info(f"Pages found: {len(pages)}")
    documents = get_docuemnts(input.base_url, pages)
    logger.info(f"Documents found: {len(documents)}")
    prepared_documents = await prepare_documents(documents)
    logger.info(f"Prepared documents: {len(prepared_documents)}")
    embed_documents(input.base_url, prepared_documents)
    logger.info("Done")
    return Response()


engine = AlkemioVirtualContributorEngine()
engine.register_handler(query)
asyncio.run(engine.start())
