# RAG-Powered Q&A Service for Machine Safety Documents

## Overview

This project implements a small, self-contained Retrieval-Augmented Generation (RAG) service over a collection of public PDFs on industrial and machine safety. The service is built with **Django** and **Python**, demonstrating:

- A full data ingestion pipeline  
- A two-stage search mechanism (similarity + reranker)  
- An API for generating short, cited answers to user queries  

This solution was developed in accordance with the technical assessment requirements, focusing on a reproducible, CPU-only setup with no paid APIs.

---

## 🔄 System Pipeline

### Data Ingestion

- PDFs are processed, chunked into smaller paragraphs, and stored in a local SQLite database.  
- Document titles and URLs are linked using a robust filename normalization and mapping process.

### Embedding & Indexing

- Each text chunk is converted into a numerical vector embedding using a local **all-MiniLM-L6-v2** model.  
- These embeddings are stored in a **FAISS** vector index for efficient similarity search.

### Baseline Search

- The API performs an initial search for the top k semantically similar chunks based on vector distance.

### Hybrid Reranker

- For improved accuracy, a second search phase re-ranks results by blending semantic similarity with BM25 keyword-based scoring.

### Answer Generation

- The top-ranked chunks are passed to a local, CPU-only **TinyLlama** model running on Ollama, which generates a concise, cited answer grounded in the provided context.

---

## ⚙️ Setup & How to Run

### Dependencies

- Python 3.8+  
- pip  
- [Ollama](https://ollama.com/download) (local LLM engine)  

### Steps

#### Install Ollama & Pull the Model
     ollama pull tinyllama

#### Install Python Packages
    
    # pip install -r requirements.txt
    # Install sentence-transformers or other libraries used for embeddings if needed
    # pip install sentence-transformers
Navigate to your project directory and install the required packages:


#### Running the Project

#### 1. **Ingest Documents**  
  
    python manage.py import_pdfs --purge-and-reimport
  This command processes the PDFs, chunks the text, and correctly links each document to its source URL.
#### 2. **Create Embeddings**  
    
    python manage.py embed_chunks

This command generates embeddings for all chunks and builds the FAISS vector index.

#### 3. **Start the API Server**  
     python manage.py runserver
(Ensure the Ollama application is running in the background.)

---

## Results & Comparison

The reranker is essential for surfacing the most relevant information, especially for conceptual questions. Here is a comparison of the top-ranked answer for a tricky query using both modes.

| Question                                                      | Mode      | Top-Ranked Answer                                                                                           |
|---------------------------------------------------------------|-----------|------------------------------------------------------------------------------------------------------------|
| Explain the concept of functional safety and provide an example. | Baseline  | Functional safety refers to the design and implementation of systems, products, and processes that are designed to prevent or mitigate hazards... |
|                                                               | Reranker  | Functional safety refers to the design and operation of electronic systems that ensure they operate safely, preventing damage...                  |

---

## What I Learned

This project provided valuable insights into building a production-ready RAG pipeline. The main challenge was in the data ingestion stage, where a simple fuzzy string match proved unreliable due to mismatched naming conventions. The solution was to create a robust, deterministic mapping process by normalizing filenames and leveraging the document URLs as a source of truth. 

The most significant learning was debugging the LLM integration, which required switching from an unstable library to a more reliable tool (Ollama). This reinforced the importance of choosing the right tools for the job and the value of a solid debugging process.

---

## Example API Requests

These examples demonstrate how to interact with the Q&A service using `Invoke-WebRequest` in PowerShell.

### 1. Easy Request (Baseline)

This command tests the basic similarity search. It asks a straightforward, keyword-rich question and retrieves 5 relevant chunks without using the reranker.

Invoke-WebRequest -Uri http://127.0.0.1:8000/ask -Method Post -ContentType "application/json" -Body '{"q": "What is the importance of machine guarding?", "k": 5, "mode": "baseline"}' | Select-Object -ExpandProperty Content | ConvertFrom-Json



### 2. Tricky Request (Reranker)

This command tests the full pipeline, including the hybrid reranker. The question is more conceptual, requiring the reranker to blend semantic understanding with keyword relevance to find the best answer.

Invoke-WebRequest -Uri http://127.0.0.1:8000/ask -Method Post -ContentType "application/json" -Body '{"q": "Explain the concept of functional safety and provide an example.", "k": 5, "mode": "reranker"}' | Select-Object -ExpandProperty Content | ConvertFrom-Json


---
