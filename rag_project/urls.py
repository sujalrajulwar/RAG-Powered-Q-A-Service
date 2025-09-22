from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    # Add a new path for your rag_app's URLs
    path("", include("rag_app.urls")),
]
