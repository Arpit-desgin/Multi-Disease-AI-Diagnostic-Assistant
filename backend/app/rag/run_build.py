"""
Build and Execute Script for RAG Vector Index

This script builds the ChromaDB vector index from medical datasets.
It checks if the index already exists to avoid rebuilding.

Usage:
    python run_build.py
"""

import os
import sys
import logging
from pathlib import Path

from constants import CHROMA_DB_PATH, DATA_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("build.log")
    ]
)
logger = logging.getLogger("RAG-BUILD")


def main():
    """Main build execution function."""
    
    # Use constants for paths
    chroma_data_dir = Path(CHROMA_DB_PATH)
    data_dir = Path(DATA_DIR)
    
    print("="*70)
    print("RAG Vector Index Builder")
    print("="*70)
    print()
    
    # Check if index already exists
    if chroma_data_dir.exists() and (chroma_data_dir / "uuids" / "5e14f8b61f5f4029821a46f28b3ce410").exists():
        print("✓ Vector index already exists!")
        print(f"  Location: {chroma_data_dir}")
        print()
        logger.info("Vector index already exists. Skipping rebuild.")
        print("  To rebuild from scratch, delete the 'chroma_data' directory and re-run.")
        print()
        return 0
    
    # Check if data directory exists
    if not data_dir.exists():
        print(f"✗ Data directory not found: {data_dir}")
        logger.error(f"Data directory not found: {data_dir}")
        return 1
    
    # Check if there are any data files
    text_files = list(data_dir.glob("**/*.txt"))
    json_files = list(data_dir.glob("**/*.json"))
    total_files = len(text_files) + len(json_files)
    
    if total_files == 0:
        print(f"✗ No data files found in {data_dir}")
        logger.error(f"No data files found in {data_dir}")
        return 1
    
    print(f"📂 Data Directory: {data_dir}")
    print(f"📄 Files found: {total_files} total ({len(text_files)} txt, {len(json_files)} json)")
    print()
    print("Starting ingestion pipeline...")
    print("-"*70)
    print()
    
    try:
        # Import and run the ingestion pipeline
        from ingest import build_index
        
        logger.info("Starting RAG vector index build")
        logger.info(f"Data directory: {data_dir}")
        logger.info(f"Total files to process: {total_files}")
        
        # Run ingestion using build_index function
        stats = build_index(
            data_dir="Data",
            chunk_size=500,
            chunk_overlap=50
        )
        
        print()
        print("="*70)
        print("✓ BUILD SUCCESSFUL!")
        print("="*70)
        logger.info("RAG vector index build completed successfully")
        logger.info(f"Statistics: {stats}")
        print()
        print(f"Summary:")
        print(f"  • Files processed: {stats['files_processed']}")
        print(f"  • Chunks created: {stats['chunks_created']}")
        print(f"  • Documents stored: {stats['documents_stored']}")
        print()
        print(f"Vector index saved to: {chroma_data_dir}")
        print()
        
        return 0
    
    except Exception as e:
        print()
        print("="*70)
        print(f"✗ BUILD FAILED!")
        print("="*70)
        print(f"Error: {str(e)}")
        logger.error(f"RAG vector index build failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
