import json
import os
import faiss
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from sentence_transformers import SentenceTransformer
import numpy as np
from rank_bm25 import BM25Okapi
from rag_app.models import Chunk, Document
import requests

# Define the paths for the generated files (must match embed_chunks.py)
EMBEDDINGS_DIR = "embeddings"
INDEX_FILE = os.path.join(EMBEDDINGS_DIR, "chunks.index")
MAPPING_FILE = os.path.join(EMBEDDINGS_DIR, "chunk_id_map.json")

# Global variables for all search resources
model = None
faiss_index = None
chunk_id_map = None
bm25_index = None
bm25_id_map = None
chunk_objects = None


def load_resources():
    """Loads all search resources (model, FAISS index, ID map, and BM25 index)."""
    global model, faiss_index, chunk_id_map, bm25_index, bm25_id_map, chunk_objects

    # Check if resources are already loaded
    if model and faiss_index and bm25_index:
        return True, ""

    # Load Sentence Transformer model
    if model is None:
        try:
            model = SentenceTransformer("all-MiniLM-L6-v2")
            print("Sentence Transformer model loaded.")
        except Exception as e:
            return False, f"Failed to load Sentence Transformer model: {e}"

    # Load FAISS index and ID map
    if faiss_index is None:
        if not os.path.exists(INDEX_FILE) or not os.path.exists(MAPPING_FILE):
            return (
                False,
                "Embeddings not found. Please run `python manage.py embed_chunks` first.",
            )
        try:
            faiss_index = faiss.read_index(INDEX_FILE)
            print("FAISS index loaded.")
            with open(MAPPING_FILE, "r") as f:
                chunk_id_map = json.load(f)
            print("Chunk ID mapping loaded.")
        except Exception as e:
            return False, f"Failed to load FAISS index or map: {e}"

    # Load all chunks for BM25 indexing
    if bm25_index is None:
        try:
            chunk_objects = list(Chunk.objects.all().order_by("id"))
            if not chunk_objects:
                return (
                    False,
                    "No chunks found in the database. Please run `import_pdfs` first.",
                )
            tokenized_corpus = [doc.chunk_text.split(" ") for doc in chunk_objects]
            bm25_index = BM25Okapi(tokenized_corpus)
            bm25_id_map = {chunk.id: i for i, chunk in enumerate(chunk_objects)}
            print("BM25 index and ID map created.")
        except Exception as e:
            return False, f"Failed to create BM25 index: {e}"

    return True, ""


def generate_answer(query, contexts):
    """Generates a concise, cited answer using a local Ollama LLM and the provided contexts."""

    context_text = "\n\n".join(
        [f"({i + 1}) {c['text']}" for i, c in enumerate(contexts)]
    )

    prompt = f"""
Use the following pieces of context to answer the question. If the answer is not in the provided context, politely state that you cannot answer from the given information. Provide a short, concise answer and always include the citation number(s) from the context.
Context:
{context_text}
Question:
{query}
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "tinyllama",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 2048,  # Increase context window for better performance
                },
            },
        )
        response.raise_for_status()

        full_response = json.loads(response.text)
        answer = full_response["response"].strip()

        # Add a simple check for "I cannot answer" based on the prompt
        if (
            "cannot answer" in answer.lower()
            or "i am unable to answer" in answer.lower()
        ):
            return (
                "I am unable to answer this question from the provided documents.",
                [],
            )

        # Find the citations and add them
        citations = []
        for c in contexts:
            if c["title"] not in [cite["title"] for cite in citations]:
                citations.append({"title": c["title"], "link": c["link"]})

        return answer, citations

    except requests.exceptions.RequestException as e:
        print(f"Error communicating with Ollama: {e}")
        return "An error occurred during answer generation. Is Ollama running?", []

    except Exception as e:
        print(f"Error during LLM generation: {e}")
        return "An error occurred during answer generation.", []


@csrf_exempt
def ask_question(request):
    """
    Handles a user question and performs either a baseline or reranked search.
    """
    if request.method != "POST":
        return HttpResponseBadRequest("Only POST requests are allowed.")

    success, error_msg = load_resources()
    if not success:
        return JsonResponse({"error": error_msg}, status=500)

    try:
        data = json.loads(request.body)
        query = data.get("q", "")
        k = int(data.get("k", 5))
        mode = data.get("mode", "baseline")

        if not query:
            return JsonResponse({"error": "Query 'q' is required."}, status=400)

        # Step 1: Perform baseline FAISS search
        query_embedding = model.encode([query], convert_to_numpy=True)
        distances, faiss_ids = faiss_index.search(
            query_embedding, k=k * 2
        )  # Retrieve more for reranking

        # Step 2: Retrieve the full chunk objects and their scores
        initial_contexts = []
        for i, faiss_id in enumerate(faiss_ids[0]):
            chunk_db_id = chunk_id_map.get(str(faiss_id))
            if chunk_db_id is not None:
                chunk = next((c for c in chunk_objects if c.id == chunk_db_id), None)
                if chunk:
                    initial_contexts.append(
                        {
                            "id": chunk.id,
                            "text": chunk.chunk_text,
                            "semantic_score": float(distances[0][i]),
                            "document": chunk.document,
                            "reranker_used": mode,
                        }
                    )

        # Check if the user wants to use the reranker
        if mode == "reranker":
            # Step 3: Perform BM25 keyword search
            tokenized_query = query.split(" ")
            bm25_scores = bm25_index.get_scores(tokenized_query)

            # Step 4: Blend semantic and keyword scores
            reranked_contexts = []
            for context in initial_contexts:
                # Find the BM25 score for the chunk using our new map
                bm25_index_id = bm25_id_map.get(context["id"])
                if bm25_index_id is not None:
                    bm25_score = bm25_scores[bm25_index_id]

                    # Simple blending: sum of normalized scores
                    # Note: You may need to tune this blending later, but this is a solid start.
                    blended_score = context["semantic_score"] + bm25_score

                    reranked_contexts.append(
                        {
                            "text": context["text"],
                            "score": blended_score,
                            "link": context["document"].source_url,
                            "title": context["document"].title,
                            "reranker_used": "hybrid",
                        }
                    )

            # Sort by the new blended score
            reranked_contexts.sort(key=lambda x: x["score"], reverse=True)
            # IMPORTANT: Pass only the top 2 chunks to the LLM to prevent context overflow
            contexts_to_return = reranked_contexts[:2]
            reranker_used_label = "hybrid"

        elif mode == "baseline":
            # Baseline mode: just format the initial contexts
            # IMPORTANT: Pass only the top 2 chunks to the LLM to prevent context overflow
            contexts_to_return = [
                {
                    "text": c["text"],
                    "score": c["semantic_score"],
                    "link": c["document"].source_url,
                    "title": c["document"].title,
                    "reranker_used": "baseline",
                }
                for c in initial_contexts[:2]
            ]
            reranker_used_label = "baseline"

        else:
            return JsonResponse(
                {"error": "Invalid mode. Use 'baseline' or 'reranker'."}, status=400
            )

        # Step 5: Generate the real answer using the LLM
        answer, citations = generate_answer(query, contexts_to_return)

        # Build the final response
        response_data = {
            "answer": answer,
            "contexts": contexts_to_return,
            "citations": citations,
            "reranker_used": reranker_used_label,
        }

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON in request body.")
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
