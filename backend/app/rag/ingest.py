"""
Data ingestion script for loading medical datasets into ChromaDB vector store.

Loads text files or JSON datasets, chunks them, generates embeddings,
and stores them in the vector database with disease type metadata.

Usage:
    python ingest.py
    
Features:
    - Automatically detects disease type from folder name (Data/Skin/, Data/Breast/, etc.)
    - Chunks documents with RecursiveCharacterTextSplitter for better context preservation
    - Generates embeddings using SentenceTransformer (all-MiniLM-L6-v2)
    - Stores in ChromaDB with persistence
    - Provides detailed ingestion statistics
"""

import os
import json
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] %(message)s"
)
logger = logging.getLogger("app.rag.ingest")

from embedding_service import EmbeddingModel
from vector_store_service import VectorStore
from constants import CHROMA_DB_PATH, DATA_DIR

# Import text splitter for better chunking
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    HAS_LANGCHAIN = True
    logger.info("[INGEST] LangChain TextSplitter available")
except ImportError:
    HAS_LANGCHAIN = False
    logger.warning("[INGEST] LangChain not available - using fallback text splitter")


class DataIngestionPipeline:
    """
    Pipeline for ingesting medical datasets into the vector store.
    
    Features:
    - Loads text and JSON files from Data/ directory
    - Automatically maps folder names to disease types
    - Chunks documents intelligently with overlap
    - Generates embeddings for all chunks
    - Stores in ChromaDB collections with metadata
    - Provides comprehensive logging
    """
    
    # Mapping of folder names to disease collection names
    FOLDER_TO_DISEASE = {
        "skin": "dermatology",
        "dermatology": "dermatology",
        "lung": "lung_cancer",
        "cancer_lung": "lung_cancer",
        "breast": "breast_cancer",
        "cancer_breast": "breast_cancer",
        "dr": "diabetic_retinopathy",  # Diabetic Retinopathy
        "retinopathy": "diabetic_retinopathy",
        "diabetic": "diabetic_retinopathy",
    }
    
    # Mapping of disease keywords in filenames/content to disease types
    DISEASE_MAPPING = {
        "skin": "dermatology",
        "dermatology": "dermatology",
        "lung": "lung_cancer",
        "cancer_lung": "lung_cancer",
        "breast": "breast_cancer",
        "cancer_breast": "breast_cancer",
        "dr": "diabetic_retinopathy",
        "diabetic retinopathy": "diabetic_retinopathy",
        "retinopathy": "diabetic_retinopathy",
        "diabetic": "diabetic_retinopathy",
    }
    
    def __init__(self, data_dir: str | None = None, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize the ingestion pipeline.
        
        Args:
            data_dir: Directory containing data files. Defaults to DATA_DIR from constants
                     Expected structure: data_dir/Skin/, data_dir/Breast/, data_dir/Lung/, data_dir/DR/
            chunk_size: Target chunk size in tokens (default 500)
            chunk_overlap: Token overlap between chunks (default 50)
        """
        # Use global constant if no path provided
        if data_dir is None:
            self.data_dir = DATA_DIR
        else:
            script_dir = Path(__file__).parent
            self.data_dir = script_dir / data_dir
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        logger.info(f"[INGEST] Initializing DataIngestionPipeline")
        logger.info(f"[INGEST] Data directory: {self.data_dir}")
        logger.info(f"[INGEST] Chunk size: {chunk_size} tokens, overlap: {chunk_overlap} tokens")
        
        # Initialize services
        self.embedding_model = EmbeddingModel()
        logger.info(f"[INGEST] ✓ Embedding model loaded (all-MiniLM-L6-v2, 384-dimensional)")
        
        # Use global CHROMA_DB_PATH constant
        self.vector_store = VectorStore(persist_directory=str(CHROMA_DB_PATH))
        logger.info(f"[INGEST] ✓ Vector store initialized at: {CHROMA_DB_PATH}")
        logger.info(f"[INGEST] Collections: {', '.join(self.vector_store.COLLECTIONS)}")
    
    def detect_disease_type_from_folder(self, filepath: Path) -> str:
        """
        Detect disease type from folder name in the file path.
        
        Looks at the parent folder name to determine disease type.
        Example: Data/Skin/file.txt -> "dermatology"
        
        Args:
            filepath: Full path to the file
            
        Returns:
            Disease type: dermatology, lung_cancer, breast_cancer, or general_diseases
        """
        # Get parent folder name
        parent_folder = filepath.parent.name.lower()
        
        # Check FOLDER_TO_DISEASE mapping
        for keyword, disease_type in self.FOLDER_TO_DISEASE.items():
            if keyword in parent_folder:
                logger.debug(f"[INGEST] Folder '{parent_folder}' -> disease_type='{disease_type}'")
                return disease_type
        
        # Fallback to general_diseases
        return "general_diseases"
    
    def detect_disease_type(self, filename: str, filepath: Path, content: str = "") -> str:
        """
        Detect disease type from folder name (primary), filename, or content.
        
        Args:
            filename: Name of the file
            filepath: Full path to the file
            content: File content for additional context
            
        Returns:
            Disease type: dermatology, lung_cancer, breast_cancer, or general_diseases
        """
        # PRIMARY: Check folder name (most reliable)
        disease_type = self.detect_disease_type_from_folder(filepath)
        if disease_type != "general_diseases":
            return disease_type
        
        # SECONDARY: Check filename
        filename_lower = filename.lower()
        for keyword, disease_type in self.DISEASE_MAPPING.items():
            if keyword in filename_lower:
                logger.debug(f"[INGEST] Filename '{filename}' -> disease_type='{disease_type}'")
                return disease_type
        
        # TERTIARY: Check content
        if content:
            content_lower = content.lower()
            for keyword, disease_type in self.DISEASE_MAPPING.items():
                if keyword in content_lower:
                    logger.debug(f"[INGEST] Content keyword '{keyword}' -> disease_type='{disease_type}'")
                    return disease_type
        
        # FALLBACK: Return general_diseases
        logger.debug(f"[INGEST] No disease type detected for '{filename}', using 'general_diseases'")
        return "general_diseases"
    
    def split_into_chunks(self, text: str, filename: str = "") -> List[Dict[str, Any]]:
        """
        Split text into chunks using RecursiveCharacterTextSplitter.
        
        Uses intelligent recursive splitting to preserve context:
        - Splits by paragraphs first, then sentences, then words
        - Each chunk ~500 characters with 50 character overlap
        - Preserves semantic boundaries for better retrieval
        
        Uses LangChain's RecursiveCharacterTextSplitter if available,
        otherwise falls back to sentence-based splitting.
        
        Args:
            text: Text to split
            filename: Original filename for metadata
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        # Clean text
        text = text.strip()
        if not text:
            logger.debug(f"[INGEST] Empty text for {filename}, skipping")
            return []
        
        chunks = []
        
        # Use LangChain RecursiveCharacterTextSplitter if available
        if HAS_LANGCHAIN:
            try:
                logger.debug(f"[INGEST] Using RecursiveCharacterTextSplitter for '{filename}'")
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=500,      # Target chunk size in characters
                    chunk_overlap=50,     # Overlap between chunks
                    separators=[
                        "\n\n",           # Paragraph breaks
                        "\n",             # Line breaks
                        ". ",             # Sentence boundaries
                        " ",              # Word boundaries
                        ""                # Character boundaries
                    ],
                    length_function=len,
                )
                
                chunk_texts = text_splitter.split_text(text)
                logger.debug(f"[INGEST] RecursiveCharacterTextSplitter created {len(chunk_texts)} chunks")
                
                for i, chunk_text in enumerate(chunk_texts):
                    chunks.append({
                        "text": chunk_text.strip(),
                        "metadata": {
                            "source": filename,
                            "chunk_index": i,
                            "chunk_size": len(chunk_text),
                        }
                    })
            except Exception as e:
                logger.warning(f"[INGEST] RecursiveCharacterTextSplitter failed: {e}, using fallback")
                chunks = self._split_into_chunks_fallback(text, filename)
        else:
            # Fallback: Use sentence-based splitting
            logger.debug(f"[INGEST] Using fallback sentence-based splitter for '{filename}'")
            chunks = self._split_into_chunks_fallback(text, filename)
        
        logger.debug(f"[INGEST] Created {len(chunks)} chunks for '{filename}'")
        return chunks
    
    def _split_into_chunks_fallback(self, text: str, filename: str = "") -> List[Dict[str, Any]]:
        """
        Fallback text splitting method using sentence-based approach.
        
        Used when LangChain is not available.
        
        Args:
            text: Text to split
            filename: Original filename for metadata
            
        Returns:
            List of chunk dictionaries
        """
        # Split by sentences (simple approach)
        sentences = text.replace("\n", " ").split(". ")
        
        chunks = []
        current_chunk = []
        current_size = 0
        target_size = 500
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_size = len(sentence)
            
            # If adding this sentence exceeds target size, save current chunk
            if current_size + sentence_size > target_size and current_chunk:
                chunk_text = ". ".join(current_chunk) + "."
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "source": filename,
                        "chunk_index": len(chunks),
                        "chunk_size": len(chunk_text),
                    }
                })
                
                # Start new chunk with overlap (reuse previous sentences)
                overlap_count = max(1, len(current_chunk) // 3)
                current_chunk = current_chunk[-overlap_count:] + [sentence]
                current_size = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        # Add final chunk
        if current_chunk:
            chunk_text = ". ".join(current_chunk) + "."
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source": filename,
                    "chunk_index": len(chunks),
                    "chunk_size": len(chunk_text),
                }
            })
        
        return chunks
    
    def load_text_file(self, filepath: str) -> Tuple[str, str]:
        """
        Load content from a text file.
        
        Args:
            filepath: Path to text file
            
        Returns:
            Tuple of (content, filename)
        """
        logger.debug(f"[INGEST] Loading text file: {filepath}")
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        
        file_size = len(content.split())
        logger.debug(f"[INGEST] Loaded {file_size} words from {os.path.basename(filepath)}")
        
        return content, os.path.basename(filepath)
    
    def load_json_file(self, filepath: str) -> List[Tuple[str, str]]:
        """
        Load content from a JSON file.
        Expected JSON format: list of objects with 'text' field or single object with 'text'
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            List of tuples (content, source)
        """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        results = []
        filename = os.path.basename(filepath)
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "text" in item:
                    results.append((item["text"], f"{filename}[{len(results)}]"))
                elif isinstance(item, str):
                    results.append((item, f"{filename}[{len(results)}]"))
        elif isinstance(data, dict):
            if "text" in data:
                results.append((data["text"], filename))
            elif "documents" in data:
                for i, doc in enumerate(data["documents"]):
                    text = doc if isinstance(doc, str) else doc.get("text", "")
                    if text:
                        results.append((text, f"{filename}[{i}]"))
        
        return results
    
    def ingest(self) -> Dict[str, int]:
        """
        Main ingestion function. Loads all files, processes them, and stores in vector DB.
        
        Returns:
            Dictionary with ingestion statistics:
            - files_processed: Number of files successfully processed
            - chunks_created: Total chunks created from all documents
            - documents_stored: Total documents (chunks) stored in vector DB
        """
        print("="*70)
        print("[INGEST] Starting data ingestion pipeline")
        print("="*70)
        print()
        
        logger.info("[INGEST] ============================================================")
        logger.info("[INGEST] Starting data ingestion pipeline")
        logger.info("[INGEST] ============================================================")
        
        if not self.data_dir.exists():
            logger.error(f"[INGEST] Data directory not found: {self.data_dir}")
            print(f"⚠️  Data directory not found: {self.data_dir}")
            print(f"Creating data directory: {self.data_dir}")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            print("Please add your medical datasets (.txt or .json files) to the data directory.")
            return {"files_processed": 0, "chunks_created": 0, "documents_stored": 0}
        
        stats = {
            "files_processed": 0,
            "chunks_created": 0,
            "documents_stored": 0
        }
        
        # Find all text and JSON files (recursively in subdirectories)
        # Use **/ pattern to search in subdirectories (e.g., Data/Skin/, Data/Lung/, etc.)
        text_files = sorted(self.data_dir.glob("**/*.txt"))
        json_files = sorted(self.data_dir.glob("**/*.json"))
        
        all_files = text_files + json_files
        
        if not all_files:
            logger.warning(f"[INGEST] No .txt or .json files found in {self.data_dir}")
            print(f"⚠️  No .txt or .json files found in {self.data_dir}")
            return stats
        
        print(f"[INGEST] Found {len(all_files)} file(s) to process")
        print(f"[INGEST] - Text files: {len(text_files)}")
        print(f"[INGEST] - JSON files: {len(json_files)}\n")
        
        logger.info(f"[INGEST] Found {len(all_files)} file(s) to process")
        logger.info(f"[INGEST]   - Text files: {len(text_files)}")
        logger.info(f"[INGEST]   - JSON files: {len(json_files)}")
        
        # Process each file
        for filepath in all_files:
            print(f"[INGEST] Processing: {filepath.name}")
            logger.info(f"[INGEST] Processing: {filepath.name}")
            
            try:
                if filepath.suffix == ".txt":
                    content, source = self.load_text_file(str(filepath))
                    documents_to_process = [(content, source)]
                elif filepath.suffix == ".json":
                    documents_to_process = self.load_json_file(str(filepath))
                else:
                    continue
                
                # Process each document
                for content, source in documents_to_process:
                    if not content.strip():
                        logger.debug(f"[INGEST] Skipping empty document: {source}")
                        continue
                    
                    # Detect disease type (from folder name, filename, or content)
                    disease_type = self.detect_disease_type(source, filepath, content)
                    logger.info(f"[INGEST] Disease type: '{disease_type}' for {source}")
                    
                    # Split into chunks
                    chunks = self.split_into_chunks(content, source)
                    stats["chunks_created"] += len(chunks)
                    
                    if not chunks:
                        logger.warning(f"[INGEST] No chunks created for {source}")
                        continue
                    
                    # Add disease_type to metadata
                    for chunk in chunks:
                        chunk["metadata"]["disease_type"] = disease_type
                    
                    # Generate embeddings
                    chunk_texts = [chunk["text"] for chunk in chunks]
                    embeddings = self.embedding_model.embed_batch(chunk_texts)
                    
                    logger.info(f"[INGEST] Generated {len(embeddings)} embeddings for {source}")
                    print(f"  [INGEST] Generated {len(embeddings)} embeddings for {source}")
                    
                    # Store in vector database
                    self.vector_store.add_documents(disease_type, chunks, embeddings)
                    stats["documents_stored"] += len(chunks)
                    
                    logger.info(f"[INGEST] ✓ {source} → {disease_type}")
                    logger.info(f"[INGEST]   Chunks: {len(chunks)}, Stored: {len(chunks)}")
                    print(f"  [INGEST] ✓ {source} → {disease_type}")
                    print(f"  [INGEST]   Chunks: {len(chunks)}, Stored: {len(chunks)}")
                
                stats["files_processed"] += 1
            
            except Exception as e:
                logger.error(f"[INGEST] Error processing {filepath.name}: {str(e)}", exc_info=True)
                print(f"  [INGEST] ✗ Error processing {filepath.name}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        # Print final statistics
        print("\n" + "="*70)
        print("Ingestion Complete!")
        print("="*70)
        print(f"Files processed: {stats['files_processed']}")
        print(f"Total chunks created: {stats['chunks_created']}")
        print(f"Documents stored: {stats['documents_stored']}")
        
        logger.info("[INGEST] ============================================================")
        logger.info("[INGEST] Ingestion Complete!")
        logger.info("[INGEST] ============================================================")
        logger.info(f"[INGEST] Files processed: {stats['files_processed']}")
        logger.info(f"[INGEST] Total chunks created: {stats['chunks_created']}")
        logger.info(f"[INGEST] Documents stored: {stats['documents_stored']}")
        
        # Print collection stats
        print("\nCollection Statistics:")
        logger.info("[INGEST] Collection Statistics:")
        for collection in self.vector_store.COLLECTIONS:
            count = self.vector_store.get_collection_count(collection)
            print(f"  {collection}: {count} documents")
            logger.info(f"[INGEST]   {collection}: {count} documents")
        
        logger.info("[INGEST] Ingestion pipeline completed successfully")
        
        return stats


def build_index(data_dir: str = "Data", chunk_size: int = 500, chunk_overlap: int = 50) -> Dict[str, int]:
    """
    Build the vector index by ingesting all medical datasets.
    
    This function should be called ONCE before starting the RAG system.
    The index is then persisted in ./chroma_data and reused for all queries.
    
    Args:
        data_dir: Directory containing data files (relative path)
        chunk_size: Target chunk size in tokens
        chunk_overlap: Token overlap between chunks
        
    Returns:
        Dictionary with ingestion statistics
        
    Example:
        >>> stats = build_index()
        >>> print(f"Stored {stats['documents_stored']} documents")
    """
    pipeline = DataIngestionPipeline(
        data_dir=data_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return pipeline.ingest()


def main():
    """
    Main entry point for the ingestion script.
    
    Usage:
        python ingest.py
    """
    print("="*70)
    print("Medical Dataset Ingestion Pipeline")
    print("="*70)
    print()
    
    # Run ingestion with build_index() function
    stats = build_index(
        data_dir="Data",
        chunk_size=500,
        chunk_overlap=50
    )
    
    logger.info(f"Ingestion completed with stats: {stats}")


if __name__ == "__main__":
    main()
