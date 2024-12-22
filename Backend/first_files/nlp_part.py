import os
import autogen
from pathlib import Path
from typing import List
import filetype
from dotenv import load_dotenv
import shutil
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredPowerPointLoader,
    CSVLoader,
    UnstructuredExcelLoader,
    UnstructuredHTMLLoader,
    UnstructuredXMLLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent

# Configuration
UPLOADS_DIR = "uploads"
VECTOR_DB_PATH = "vectordb"
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(VECTOR_DB_PATH, exist_ok=True)

# Load environment variables and OpenAI configuration
load_dotenv()
# config_list = autogen.config_list_from_json("OAI_CONFIG_LIST.json")

config_list = [
    {
        'model': 'gpt-3.5-turbo',
        'api_key': "",
    }
]

def detect_file_type(file_path: str) -> str:
    """Detects the file type using filetype library."""
    kind = filetype.guess(file_path)
    if kind is None:
        return Path(file_path).suffix.lower()
    return '.' + kind.extension if kind.extension else Path(file_path).suffix.lower()

def load_document(file_path: str, loader_class) -> List[Document]:
    """Loads a document using the specified loader class."""
    try:
        return loader_class(file_path).load()
    except Exception as e:
        print(f"Error loading document {file_path}: {str(e)}")
        return []

def load_documents(uploads_dir: str = UPLOADS_DIR) -> List[Document]:
    """Loads all documents from the uploads directory."""
    loader_map = {
        '.pdf': PyPDFLoader,
        '.txt': TextLoader,
        '.docx': Docx2txtLoader,
        '.pptx': UnstructuredPowerPointLoader,
        '.csv': CSVLoader,
        '.xlsx': UnstructuredExcelLoader,
        '.html': UnstructuredHTMLLoader,
        '.htm': UnstructuredHTMLLoader,
        '.xml': UnstructuredXMLLoader,
    }
    
    all_documents = []
    for file_name in os.listdir(uploads_dir):
        file_path = os.path.join(uploads_dir, file_name)
        if os.path.isfile(file_path):
            ext = detect_file_type(file_path)
            if loader_class := loader_map.get(ext):
                docs = load_document(file_path, loader_class)
                all_documents.extend(docs)
    
    return all_documents

def create_vector_store():
    """Creates and saves the vector store from documents."""
    print("Loading documents...")
    documents = load_documents()
    
    if not documents:
        raise ValueError("No documents were loaded successfully")
    
    print("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
    )
    
    splits = []
    for doc in documents:
        chunks = text_splitter.split_text(doc.page_content)
        for i, chunk in enumerate(chunks):
            splits.append(
                Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        "chunk_id": i,
                        "chunk_total": len(chunks),
                        "source_path": doc.metadata.get("source", ""),
                        "file_type": Path(doc.metadata.get("source", "")).suffix
                    }
                )
            )
    
    print(f"Created {len(splits)} chunks from {len(documents)} documents")
    
    print("Creating embeddings...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    print("Creating and saving vector store...")
    vector_store = FAISS.from_documents(splits, embeddings)
    vector_store.save_local(VECTOR_DB_PATH)
    return vector_store

def setup_rag_chat(vector_store):
    """Sets up and returns the RAG-enabled chat agents."""
    llm_config = {
        "timeout": 600,
        "config_list": config_list,
        "temperature": 0.7,
    }

    assistant = autogen.AssistantAgent(
        name="assistant",
        system_message="""You are a helpful assistant. When answering questions, use the retrieved context 
        to provide accurate and detailed answers. If the context doesn't contain enough information to fully 
        answer a question, acknowledge this and answer with what you can from the available context.""",
        llm_config=llm_config,
    )

    # Initialize the RetrieveUserProxyAgent with the proper configuration
    ragproxyagent = RetrieveUserProxyAgent(
        name="ragproxyagent",
        system_message="Assistant for retrieving information from documents and asking questions.",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=3,
        retrieve_config={
            "task": "qa",
            "docs_path": UPLOADS_DIR,
            "chunk_token_size": 1000,
            "model": config_list[0]["model"],
            "client": vector_store,
            "embedding_model": "sentence-transformers/all-mpnet-base-v2",
            "get_or_create": True,
            "context_max_tokens": 3000,
        },
        code_execution_config=False,
    )
    
    return assistant, ragproxyagent

def start_chat(assistant, ragproxyagent, test_question):
    # # Test the chat
    # test_question = "Who was Louis XVI, explain in detail?"
    # print(f"\nTesting with question: {test_question}")
    
    # Initialize the chat
    chat_result = ragproxyagent.initiate_chat(
        assistant,
        message=test_question,
        max_turns=3,
        clear_history=True
    )
    
    print("\nChat completed successfully!")

    if os.path.exists(UPLOADS_DIR) and os.path.isdir(UPLOADS_DIR):
            shutil.rmtree(UPLOADS_DIR)
    return


def preprocess_documents():
    print("Creating vector store...")
    vector_store = create_vector_store()
    return vector_store
    # Set up RAG-enabled chat
    print("Setting up RAG chat...")
    assistant, ragproxyagent = setup_rag_chat(vector_store)

    start_chat(assistant, ragproxyagent)
    return vector_store
