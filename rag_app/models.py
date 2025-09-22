from django.db import models


class Document(models.Model):
    title = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    source_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Chunk(models.Model):
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="chunks"
    )
    chunk_text = models.TextField()
    chunk_order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chunk {self.chunk_order} of {self.document.title}"
