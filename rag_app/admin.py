from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Document, Chunk

admin.site.register(Document)
admin.site.register(Chunk)
