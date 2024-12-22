import os
from typing import List, Dict, Any
from pathlib import Path
import filetype
from unstructured.partition.auto import partition
from unstructured.staging.base import elements_to_json
from unstructured.documents.elements import Text, NarrativeText, Title
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
import autogen
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import shutil

class DocumentProcessor:
    """Handles document processing using unstructured.io and prepares them for vectorization."""
    
    def __init__(self, uploads_dir: str = "uploads"):
        self.uploads_dir = uploads_dir
        os.makedirs(uploads_dir, exist_ok=True)
        
    def detect_file_type(self, file_path: str) -> str:
        """Detects the file type using filetype library."""
        kind = filetype.guess(file_path)
        if kind is None:
            return Path(file_path).suffix.lower()
        return '.' + kind.extension if kind.extension else Path(file_path).suffix.lower()
    
    def process_file(self, file_path: str) -> List[Document]:
        """Process a single file using unstructured.io."""
        try:
            # Extract elements using unstructured
            elements = partition(filename=file_path)
            
            # Convert elements to structured format
            processed_elements = []
            
            for element in elements:
                # Handle different element types
                if isinstance(element, (Text, NarrativeText, Title)):
                    text = str(element)
                    if text.strip():  # Only include non-empty text
                        processed_elements.append(
                            Document(
                                page_content=text,
                                metadata={
                                    "source": file_path,
                                    "file_type": self.detect_file_type(file_path),
                                    "element_type": element.__class__.__name__
                                }
                            )
                        )
            
            return processed_elements
            
        except Exception as e:
            print(f"Error processing file {file_path}: {str(e)}")
            return []
    
    def process_documents(self) -> List[Document]:
        """Process all documents in the uploads directory."""
        all_documents = []
        
        for file_name in os.listdir(self.uploads_dir):
            file_path = os.path.join(self.uploads_dir, file_name)
            if os.path.isfile(file_path):
                documents = self.process_file(file_path)
                all_documents.extend(documents)
        # print("returned")
        return all_documents
    
    def create_chunks(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks for vectorization."""
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
                            "chunk_total": len(chunks)
                        }
                    )
                )
        # print("split")
        return splits


class RAGChatManager:
    def __init__(self, vector_store_base_path: str = "vectordb", config_list: list = None):
        self.vector_store_base_path = vector_store_base_path
        self.config_list = config_list or [
            {
                'model': 'gpt-3.5-turbo',
                'api_key': "your-api-key-here",
            }
        ]
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )

    def load_vector_store(self, user_id: str, filename: str) -> FAISS:
        """Load the vector store for a specific user and file."""
        vector_store_path = os.path.join(self.vector_store_base_path, user_id, filename)
        if not os.path.exists(vector_store_path):
            raise ValueError(f"Vector store not found for user {user_id} and file {filename}")
        
        return FAISS.load_local(vector_store_path, self.embeddings)

    def setup_rag_chat(self):
        """Sets up and returns the RAG-enabled chat agents for a specific vector store."""
        vector_store = FAISS.load_local("vectordb", embeddings=self.embeddings, allow_dangerous_deserialization=True)
        print("vector Store loaded")

        llm_config = {
            "timeout": 600,
            "config_list": self.config_list,
            "temperature": 0.7,
        }

        assistant = autogen.AssistantAgent(
            name="assistant",
            system_message="""You are a helpful assistant. When answering questions, use the retrieved context 
            to provide accurate and detailed answers. If the context doesn't contain enough information to fully 
            answer a question, acknowledge this and answer with what you can from the available context.""",
            llm_config=llm_config,
        )

        ragproxyagent = RetrieveUserProxyAgent(
            name="ragproxyagent",
            system_message="Assistant for retrieving information from documents and asking questions.",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=3,
            retrieve_config={
                "task": "qa",
                "docs_path": self.vector_store_base_path,
                "chunk_token_size": 1000,
                "model": self.config_list[0]["model"],
                "client": vector_store,
                "embedding_model": "sentence-transformers/all-mpnet-base-v2",
                "get_or_create": True,
                "context_max_tokens": 3000,
            },
            code_execution_config=False,
        )

        return assistant, ragproxyagent

    def start_chat(self, question: str):
        """Starts a chat session with the specified question."""
        try:
            assistant, ragproxyagent = self.setup_rag_chat()
            
            chat_result = ragproxyagent.initiate_chat(
                assistant,
                message=question,
                max_turns=3,
                clear_history=True
            )

            if os.path.exists(self.vector_store_base_path):
                shutil.rmtree(self.vector_store_base_path)
                print(f"Cleaned up vector store at {self.vector_store_base_path}")

            
            return chat_result
            
        except Exception as e:
            print(f"Error in chat: {str(e)}")
            raise