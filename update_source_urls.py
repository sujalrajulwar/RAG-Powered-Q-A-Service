import os
import django
import json
import re
from rapidfuzz import fuzz

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rag_project.settings")
django.setup()

from rag_app.models import Document

SOURCE_JSON_PATH = r"D:/Assesment/Data/sources.json"


def normalize(text):
    return re.sub(r"\W+", "", text).lower()


def update_source_urls():
    with open(SOURCE_JSON_PATH, encoding="utf-8") as f:
        sources = json.load(f)

    updated_count = 0
    unmatched = []

    for doc in Document.objects.all():
        doc_name_norm = normalize(os.path.splitext(doc.title)[0])

        highest_score = 0
        best_url = None

        for source in sources:
            source_title_norm = normalize(source["title"])
            score = fuzz.partial_ratio(doc_name_norm, source_title_norm)
            if score > 60 and score > highest_score:
                highest_score = score
                best_url = source["url"]

        if best_url and (not doc.source_url or doc.source_url.strip() == ""):
            doc.source_url = best_url
            doc.save()
            updated_count += 1
            print(f"Updated source_url for: {doc.title} with score: {highest_score}")
        else:
            print(f"No good match found for document title: {doc.title}")
            unmatched.append(doc.title)  # Collect unmatched inside loop

    print(f"\nTotal documents updated: {updated_count}")
    print("Documents without good matches:")
    for title in unmatched:
        print(title)


if __name__ == "__main__":
    update_source_urls()
