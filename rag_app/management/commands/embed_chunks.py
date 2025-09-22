import os
import faiss
import numpy as np
import json
from django.core.management.base import BaseCommand
from sentence_transformers import SentenceTransformer
from rag_app.models import Chunk

# Define the paths for the generated files
EMBEDDINGS_DIR = "embeddings"
INDEX_FILE = os.path.join(EMBEDDINGS_DIR, "chunks.index")
MAPPING_FILE = os.path.join(EMBEDDINGS_DIR, "chunk_id_map.json")


class Command(BaseCommand):
    help = "Generates embeddings for all document chunks and builds a FAISS index."

    def handle(self, *args, **kwargs):
        # Create the embeddings directory if it doesn't exist
        os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
        self.stdout.write("Initializing Sentence Transformer model...")

        # Step 1: Load the pre-trained Sentence Transformer model
        # The assessment specifies 'all-MiniLM-L6-v2'
        model = SentenceTransformer("all-MiniLM-L6-v2")
        self.stdout.write(self.style.SUCCESS("Model loaded successfully."))

        # Step 2: Retrieve all text chunks from the database
        self.stdout.write("Fetching chunks from the database...")
        chunks = list(Chunk.objects.all().order_by("id"))
        if not chunks:
            self.stdout.write(
                self.style.ERROR(
                    "No chunks found in the database. Please run `import_pdfs` first."
                )
            )
            return

        chunk_texts = [chunk.chunk_text for chunk in chunks]

        # Step 3: Generate embeddings for all chunks
        self.stdout.write(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = model.encode(chunk_texts, convert_to_numpy=True)
        self.stdout.write(self.style.SUCCESS("Embeddings generated."))

        # Step 4: Create a FAISS index
        # We need the dimensionality of our embeddings. all-MiniLM-L6-v2 is 384.
        dimension = embeddings.shape[1]
        self.stdout.write(f"Creating a FAISS index with dimension {dimension}...")

        # We'll use an IndexFlatL2, which is a simple and effective index for L2 (Euclidean) distance
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)

        self.stdout.write(
            self.style.SUCCESS(f"FAISS index created with {index.ntotal} vectors.")
        )

        # Step 5: Save the index and a mapping of chunk IDs
        self.stdout.write("Saving FAISS index and ID mapping...")
        faiss.write_index(index, INDEX_FILE)

        # Create a mapping from the FAISS index ID to your Django Chunk ID
        chunk_id_map = {i: chunk.id for i, chunk in enumerate(chunks)}
        with open(MAPPING_FILE, "w") as f:
            json.dump(chunk_id_map, f)

        self.stdout.write(self.style.SUCCESS(f"Index saved to {INDEX_FILE}"))
        self.stdout.write(self.style.SUCCESS(f"ID mapping saved to {MAPPING_FILE}"))
        self.stdout.write(self.style.SUCCESS("Embedding process complete."))
