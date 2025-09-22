import os
import json
import re
from django.core.management.base import BaseCommand
from rag_app.models import Document, Chunk
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

BASE_FOLDER = r"D:/Assesment/Data"
SOURCES_JSON_PATH = os.path.join(BASE_FOLDER, "sources.json")


def normalize_filename(name):
    """
    Normalizes a filename string to a consistent format for matching.
    e.g., "My File Name.pdf" -> "my-file-name.pdf"
    """
    name = name.lower()
    # Replace non-alphanumeric characters with a hyphen
    name = re.sub(r"[^a-z0-9.]+", "-", name)
    # Remove leading/trailing hyphens
    name = name.strip("-")
    return name


def create_url_mapping(sources_file_path):
    """
    Creates a mapping from URL filenames to source metadata (title and url).
    This function uses a normalized filename for reliable matching.
    """
    url_to_source_map = {}
    try:
        with open(sources_file_path, "r", encoding="utf-8") as f:
            sources_data = json.load(f)
            for source in sources_data:
                url = source.get("url")
                if url:
                    # Extracts and normalizes the filename from the URL
                    filename = os.path.basename(url)
                    normalized_filename = normalize_filename(filename)
                    url_to_source_map[normalized_filename] = {
                        "title": source.get("title"),
                        "url": url,
                    }
    except FileNotFoundError:
        print(
            f"Error: {sources_file_path} not found. Proceeding without source mapping."
        )
    except Exception as e:
        print(f"Error loading sources.json: {e}")
    return url_to_source_map


class Command(BaseCommand):
    help = "Import PDFs from folder and save chunks to database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--purge-and-reimport",
            action="store_true",
            help="Deletes all existing documents and chunks before re-importing.",
        )

    def extract_text_from_pdf(self, file_path):
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except PdfReadError as e:
            self.stdout.write(
                self.style.WARNING(f"Skipping corrupted PDF '{file_path}': {e}")
            )
            return ""
        except Exception as ex:
            self.stdout.write(
                self.style.WARNING(f"Unexpected error with '{file_path}': {ex}")
            )
            return ""

    def chunk_text(self, text, chunk_size=500):
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    def handle(self, *args, **kwargs):
        if kwargs["purge_and_reimport"]:  # Corrected key
            self.stdout.write(
                self.style.WARNING("Purging all existing documents and chunks...")
            )
            Chunk.objects.all().delete()
            Document.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Purge complete."))

        self.stdout.write("Creating URL to source mapping...")
        url_to_source_map = create_url_mapping(SOURCES_JSON_PATH)

        if not url_to_source_map:
            self.stdout.write(
                self.style.ERROR("No source data found. Proceeding without citations.")
            )

        for root, dirs, files in os.walk(BASE_FOLDER):
            for filename in files:
                if filename.lower().endswith(".pdf"):
                    file_path = os.path.join(root, filename)

                    self.stdout.write(f"\nProcessing document: {file_path}")

                    # Normalize the local filename before looking it up
                    normalized_filename = normalize_filename(filename)
                    source_data = url_to_source_map.get(normalized_filename)

                    doc_title = (
                        source_data.get("title", filename) if source_data else filename
                    )
                    doc_url = source_data.get("url", "") if source_data else ""

                    if (
                        not kwargs["purge_and_reimport"]
                        and Document.objects.filter(file_path=file_path).exists()
                    ):  # Corrected key
                        self.stdout.write(
                            self.style.NOTICE(f"Document already imported: {file_path}")
                        )
                        continue

                    text = self.extract_text_from_pdf(file_path)
                    if not text:
                        self.stdout.write(
                            self.style.WARNING("No text extracted; skipping.")
                        )
                        continue

                    doc = Document.objects.create(
                        title=doc_title, file_path=file_path, source_url=doc_url
                    )
                    chunks = self.chunk_text(text)
                    self.stdout.write(f"Extracted {len(chunks)} chunks")

                    for idx, chunk_text in enumerate(chunks):
                        Chunk.objects.create(
                            document=doc, chunk_text=chunk_text, chunk_order=idx + 1
                        )

                    self.stdout.write(
                        self.style.SUCCESS(f"Saved document and chunks for: {filename}")
                    )
