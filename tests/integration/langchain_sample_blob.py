import bs4
from langchain import hub
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_chroma import Chroma
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from monocle_apptrace.instrumentation.common.instrumentor import set_context_properties, setup_monocle_telemetry
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from monocle.tests.common.langhchain_patch import create_history_aware_retriever
from monocle_apptrace.exporters.azure.blob_exporter import AzureBlobSpanExporter
from monocle.tests.common.custom_exporter import CustomConsoleSpanExporter
import os
from dotenv import load_dotenv
import logging
logging.basicConfig(level=logging.INFO)
load_dotenv()


custom_exporter = CustomConsoleSpanExporter()
exporter = AzureBlobSpanExporter()
setup_monocle_telemetry(
            workflow_name="langchain_app_1",
            span_processors=[BatchSpanProcessor(exporter),
                             BatchSpanProcessor(custom_exporter)],
            wrapper_methods=[])

llm = ChatOpenAI(model="gpt-3.5-turbo-0125")

# Load, chunk and index the contents of the blog.
loader = WebBaseLoader(
    web_paths=("https://lilianweng.github.io/posts/2023-06-23-agent/",),
    bs_kwargs=dict(
        parse_only=bs4.SoupStrainer(
            class_=("post-content", "post-title", "post-header")
        )
    ),
)
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
splits = text_splitter.split_documents(docs)
vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings())

# Retrieve and generate using the relevant snippets of the blog.
retriever = vectorstore.as_retriever()
prompt = hub.pull("rlm/rag-prompt")

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

contextualize_q_system_prompt = """Given a chat history and the latest user question \
which might reference context in the chat history, formulate a standalone question \
which can be understood without the chat history. Do NOT answer the question, \
just reformulate it if needed and otherwise return it as is."""
contextualize_q_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)
history_aware_retriever = create_history_aware_retriever(
    llm, retriever, contextualize_q_prompt
)

qa_system_prompt = """You are an assistant for question-answering tasks. \
Use the following pieces of retrieved context to answer the question. \
If you don't know the answer, just say that you don't know. \
Use three sentences maximum and keep the answer concise.\

{context}"""
qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)


question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)

rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

chat_history = []

set_context_properties({"session_id": "0x4fa6d91d1f2a4bdbb7a1287d90ec4a16"})

question = "What is Task Decomposition?"
ai_msg_1 = rag_chain.invoke({"input": question, "chat_history": chat_history})
print(ai_msg_1["answer"])

spans = custom_exporter.get_captured_spans()
for span in spans:
    span_attributes = span.attributes
    if "span.type" in span_attributes and span_attributes["span.type"] == "retrieval":
        # Assertions for all retrieval attributes
        assert span_attributes["entity.1.name"] == "Chroma"
        assert span_attributes["entity.1.type"] == "vectorstore.Chroma"
        assert "entity.1.deployment" in span_attributes
        assert span_attributes["entity.2.name"] == "text-embedding-ada-002"
        assert span_attributes["entity.2.type"] == "model.embedding.text-embedding-ada-002"

    if "span.type" in span_attributes and span_attributes["span.type"] == "inference":
        # Assertions for all inference attributes
        assert span_attributes["entity.1.type"] == "inference.azure_oai"
        assert "entity.1.provider_name" in span_attributes
        assert "entity.1.inference_endpoint" in span_attributes
        assert span_attributes["entity.2.name"] == "gpt-3.5-turbo-0125"
        assert span_attributes["entity.2.type"] == "model.llm.gpt-3.5-turbo-0125"

        # Assertions for metadata
        span_input, span_output, span_metadata = span.events
        assert "completion_tokens" in span_metadata.attributes
        assert "prompt_tokens" in span_metadata.attributes
        assert "total_tokens" in span_metadata.attributes

    if not span.parent and span.name == "langchain.workflow":  # Root span
        assert span_attributes["entity.1.name"] == "langchain_app_1"
        assert span_attributes["entity.1.type"] == "workflow.langchain"

# chat_history.extend([HumanMessage(content=question), ai_msg_1["answer"]])
#
# second_question = "What are common ways of doing it?"
# ai_msg_2 = rag_chain.invoke({"input": second_question, "chat_history": chat_history})
#
# print(ai_msg_2["answer"])

#ndjson format stored on blob

# {"name": "langchain.task.VectorStoreRetriever", "context": {"trace_id": "0x94f6a3d96b14ec831b7f9a3545130fe5", "span_id": "0x447091e285b1da17", "trace_state": "[]"}, "kind": "SpanKind.INTERNAL", "parent_id": "0xa6807c63a68b1cbd", "start_time": "2024-10-22T06:35:07.925768Z", "end_time": "2024-10-22T06:35:08.610434Z", "status": {"status_code": "UNSET"}, "attributes": {"session.session_id": "0x4fa6d91d1f2a4bdbb7a1287d90ec4a16", "span.type": "retrieval", "entity.count": 2, "entity.1.name": "Chroma", "entity.1.type": "vectorstore.Chroma", "entity.2.name": "text-embedding-ada-002", "entity.2.type": "model.embedding.text-embedding-ada-002"}, "events": [{"name": "data.input", "timestamp": "2024-10-22T06:35:07.925905Z", "attributes": {"question": "What is Task Decomposition?"}}, {"name": "data.output", "timestamp": "2024-10-22T06:35:08.610419Z", "attributes": {"response": "Fig. 1. Overview of a LLM-powered autonomous agent system.\nComponent One: Planning#\nA complicated ta..."}}], "links": [], "resource": {"attributes": {"service.name": "langchain_app_1"}, "schema_url": ""}}
# {"name": "langchain.workflow", "context": {"trace_id": "0x94f6a3d96b14ec831b7f9a3545130fe5", "span_id": "0xa6807c63a68b1cbd", "trace_state": "[]"}, "kind": "SpanKind.INTERNAL", "parent_id": "0x23eea25b1a5abbd5", "start_time": "2024-10-22T06:35:07.925206Z", "end_time": "2024-10-22T06:35:08.610466Z", "status": {"status_code": "UNSET"}, "attributes": {"session.session_id": "0x4fa6d91d1f2a4bdbb7a1287d90ec4a16"}, "events": [], "links": [], "resource": {"attributes": {"service.name": "langchain_app_1"}, "schema_url": ""}}
#