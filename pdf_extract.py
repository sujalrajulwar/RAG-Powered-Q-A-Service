import os
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

BASE_FOLDER = r"D:/Assesment/Data"


def extract_text_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except PdfReadError as e:
        print(f"Skipping corrupted PDF '{file_path}': {e}")
        return ""
    except Exception as ex:
        print(f"Unexpected error with '{file_path}': {ex}")
        return ""


def chunk_text(text, chunk_size=500):
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


def main():
    for root, dirs, files in os.walk(BASE_FOLDER):
        for filename in files:
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(root, filename)
                print(f"\nProcessing document: {file_path}")
                text = extract_text_from_pdf(file_path)
                if not text:
                    print("No text extracted; skipping.")
                    continue
                chunks = chunk_text(text)
                print(f"Extracted {len(chunks)} chunks")
                for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks sample
                    print(f"\n--- Chunk {i + 1} ---")
                    print(chunk)


if __name__ == "__main__":
    main()
