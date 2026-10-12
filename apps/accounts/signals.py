"""
Keeps storage in step with the database: when a document or a profile picture
row goes away (deleted on its own, replaced, or removed together with its Admin /
Seller / Buyer), its file is deleted from storage too, so identity documents do
not linger in the bucket after the account or the document is gone.

The delete runs after the database transaction commits (`transaction.on_commit`),
so a request that fails and rolls back never loses a file it still needs.
"""

from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from config.storage import delete_upload

from .models import Admin, AdminMedia, BuyerMedia, Seller, SellerMedia, User


def _remove_later(path):
    if path:
        transaction.on_commit(lambda: delete_upload(path))


@receiver(post_delete, sender=AdminMedia)
@receiver(post_delete, sender=SellerMedia)
@receiver(post_delete, sender=BuyerMedia)
def remove_media_file(sender, instance, **kwargs):
    _remove_later(instance.media_path)


@receiver(post_delete, sender=Admin)
@receiver(post_delete, sender=Seller)
@receiver(post_delete, sender=User)
def remove_profile_pic_file(sender, instance, **kwargs):
    _remove_later(instance.profile_pic_path)
