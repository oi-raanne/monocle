

import os

from datasets import load_dataset
from haystack import Document, Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.embedders import (
    SentenceTransformersDocumentEmbedder,
    SentenceTransformersTextEmbedder,
)
from haystack.components.generators import OpenAIGenerator
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.retrievers.in_memory.embedding_retriever import (
    InMemoryDocumentStore,
)
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.utils import Secret
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from monocle_apptrace.instrumentor import setup_monocle_telemetry
from monocle_apptrace.wrap_common import llm_wrapper, task_wrapper
from monocle_apptrace.wrapper import WrapperMethod

def haystack_app():

    setup_monocle_telemetry(
            workflow_name="haystack_app_1",
            span_processors=[BatchSpanProcessor(ConsoleSpanExporter())],
            wrapper_methods=[
                ])

    # initialize
    api_key = os.getenv("OPENAI_API_KEY")
    generator = OpenAIGenerator(
        api_key=Secret.from_token(api_key), model="gpt-3.5-turbo"
    )

    # initialize document store, load data and store in document store
    document_store = InMemoryDocumentStore()
    dataset = load_dataset("bilgeyucel/seven-wonders", split="train")
    docs = [Document(content=doc["content"], meta=doc["meta"]) for doc in dataset]

    doc_embedder = SentenceTransformersDocumentEmbedder(
        model="sentence-transformers/all-MiniLM-L6-v2"
    )
    doc_embedder.warm_up()
    docs_with_embeddings = doc_embedder.run(docs)
    document_store.write_documents(docs_with_embeddings["documents"])

    # embedder to embed user query
    text_embedder = SentenceTransformersTextEmbedder(
        model="sentence-transformers/all-MiniLM-L6-v2"
    )

    # get relevant documents from embedded query
    retriever = InMemoryEmbeddingRetriever(document_store)

    # use documents to build the prompt
    template = """
    Given the following information, answer the question.

    Context:
    {% for document in documents %}
        {{ document.content }}
    {% endfor %}

    Question: {{question}}
    Answer:
    """

    prompt_builder = PromptBuilder(template=template)

    basic_rag_pipeline = Pipeline()
    # Add components to your pipeline
    basic_rag_pipeline.add_component("text_embedder", text_embedder)
    basic_rag_pipeline.add_component("retriever", retriever)
    basic_rag_pipeline.add_component("prompt_builder", prompt_builder)
    basic_rag_pipeline.add_component("llm", generator)

    # Now, connect the components to each other
    basic_rag_pipeline.connect("text_embedder.embedding", "retriever.query_embedding")
    basic_rag_pipeline.connect("retriever", "prompt_builder.documents")
    basic_rag_pipeline.connect("prompt_builder", "llm")

    question = "What does Rhodes Statue look like?"

    response = basic_rag_pipeline.run(
        {"text_embedder": {"text": question}, "prompt_builder": {"question": question}}
    )

    # print(response["llm"]["replies"][0])


haystack_app()

# {
#     "name": "haystack.retriever",
#     "context": {
#         "trace_id": "0x3a350c422d4897c7ff7fb43ac05bac3c",
#         "span_id": "0xbccb663f616a53f8",
#         "trace_state": "[]"
#     },
#     "kind": "SpanKind.INTERNAL",
#     "parent_id": "0x356e1d6b5f632527",
#     "start_time": "2024-11-27T04:10:25.447082Z",
#     "end_time": "2024-11-27T04:10:25.462024Z",
#     "status": {
#         "status_code": "UNSET"
#     },
#     "attributes": {
#         "span.type": "retrieval",
#         "entity.count": 2,
#         "entity.1.name": "InMemoryDocumentStore",
#         "entity.1.type": "vectorstore.InMemoryDocumentStore",
#         "entity.2.name": "sentence-transformers/all-MiniLM-L6-v2",
#         "entity.2.type": "model.embedding.sentence-transformers/all-MiniLM-L6-v2"
#     },
#     "events": [
#         {
#             "name": "data.input",
#             "timestamp": "2024-11-27T04:10:25.447110Z",
#             "attributes": {
#                 "input": "What does Rhodes Statue look like?"
#             }
#         },
#         {
#             "name": "data.output",
#             "timestamp": "2024-11-27T04:10:25.462000Z",
#             "attributes": {
#                 "response": "Within it, too, are to be seen large masses of rock, by the weight of which the artist steadied it w..."
#             }
#         }
#     ],
#     "links": [],
#     "resource": {
#         "attributes": {
#             "service.name": "haystack_app_1"
#         },
#         "schema_url": ""
#     }
# },
# {
#     "name": "haystack.components.generators.openai.OpenAIGenerator",
#     "context": {
#         "trace_id": "0x3a350c422d4897c7ff7fb43ac05bac3c",
#         "span_id": "0x8d618c0dc5ed2b96",
#         "trace_state": "[]"
#     },
#     "kind": "SpanKind.INTERNAL",
#     "parent_id": "0x356e1d6b5f632527",
#     "start_time": "2024-11-27T04:10:25.462579Z",
#     "end_time": "2024-11-27T04:10:28.695766Z",
#     "status": {
#         "status_code": "UNSET"
#     },
#     "attributes": {
#         "span.type": "inference",
#         "entity.count": 2,
#         "entity.1.type": "inference.azure_oai",
#         "entity.1.inference_endpoint": "https://api.openai.com/v1/",
#         "entity.2.name": "gpt-3.5-turbo",
#         "entity.2.type": "model.llm.gpt-3.5-turbo"
#     },
#     "events": [
#         {
#             "name": "data.input",
#             "timestamp": "2024-11-27T04:10:28.695339Z",
#             "attributes": {
#                 "system": "",
#                 "user": "What does Rhodes Statue look like?"
#             }
#         },
#         {
#             "name": "data.output",
#             "timestamp": "2024-11-27T04:10:28.695406Z",
#             "attributes": {
#                 "assistant": "The Rhodes Statue, also known as the Colossus of Rhodes, was a statue of the Greek sun-god Helios. It was approximately 70 cubits, or 33 meters (108 feet) tall. While scholars do not know exactly what the entire statue looked like, they do have a good idea of what the head and face looked like. The head would have had curly hair with evenly spaced spikes of bronze or silver flame radiating, similar to the images found on contemporary Rhodian coins."
#             }
#         },
#         {
#             "name": "metadata",
#             "timestamp": "2024-11-27T04:10:28.695734Z",
#             "attributes": {
#                 "completion_tokens": 102,
#                 "prompt_tokens": 2464,
#                 "total_tokens": 2566
#             }
#         }
#     ],
#     "links": [],
#     "resource": {
#         "attributes": {
#             "service.name": "haystack_app_1"
#         },
#         "schema_url": ""
#     }
# },
# {
#     "name": "haystack.core.pipeline.pipeline.Pipeline",
#     "context": {
#         "trace_id": "0x3a350c422d4897c7ff7fb43ac05bac3c",
#         "span_id": "0x356e1d6b5f632527",
#         "trace_state": "[]"
#     },
#     "kind": "SpanKind.INTERNAL",
#     "parent_id": null,
#     "start_time": "2024-11-27T04:10:25.437432Z",
#     "end_time": "2024-11-27T04:10:28.696077Z",
#     "status": {
#         "status_code": "UNSET"
#     },
#     "attributes": {
#         "monocle_apptrace.version": "0.2.0",
#         "span.type": "workflow",
#         "entity.1.name": "haystack_app_1",
#         "entity.1.type": "workflow.haystack"
#     },
#     "events": [
#         {
#             "name": "data.input",
#             "timestamp": "2024-11-27T04:10:25.437901Z",
#             "attributes": {
#                 "input": "What does Rhodes Statue look like?"
#             }
#         },
#         {
#             "name": "data.output",
#             "timestamp": "2024-11-27T04:10:28.696062Z",
#             "attributes": {
#                 "response": "The Rhodes Statue, also known as the Colossus of Rhodes, was a statue of the Greek sun-god Helios. It was approximately 70 cubits, or 33 meters (108 feet) tall. While scholars do not know exactly what the entire statue looked like, they do have a good idea of what the head and face looked like. The head would have had curly hair with evenly spaced spikes of bronze or silver flame radiating, similar to the images found on contemporary Rhodian coins."
#             }
#         }
#     ],
#     "links": [],
#     "resource": {
#         "attributes": {
#             "service.name": "haystack_app_1"
#         },
#         "schema_url": ""
#     }
# }
