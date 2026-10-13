"""
Keeps storage in step with the database: when a listing's media row goes away
(deleted in an edit, or removed with its listing), its file is deleted from
storage too. The delete runs after the transaction commits, so a request that
fails and rolls back never loses a file it still needs. (The accounts app does
the same for documents and photos.)
"""

from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from config.storage import delete_upload

from .models import ListingMedia


@receiver(post_delete, sender=ListingMedia)
def remove_listing_media_file(sender, instance, **kwargs):
    path = instance.media_path
    if path:
        transaction.on_commit(lambda: delete_upload(path))
