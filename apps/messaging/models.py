"""
Messaging (DB Redesign doc, Section 3.9).

Renames `chats` to `Conversation` for clarity and collapses the legacy
per-message, seven-way shop-id context columns down to one `listing` on
the conversation itself, now that the catalog is unified. Replaces chats,
messages.
"""

from django.db import models

from apps.core.models import AuditedModel


class Conversation(AuditedModel):
    buyer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="conversations", db_column="buyerId"
    )
    seller = models.ForeignKey(
        "accounts.Seller", on_delete=models.CASCADE, related_name="conversations", db_column="sellerId"
    )
    listing = models.ForeignKey(
        "catalog.Listing", on_delete=models.SET_NULL, null=True, blank=True, related_name="conversations",
        db_column="listingId",
    )

    class Meta:
        db_table = "conversations"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Conversation #{self.pk} (buyer {self.buyer_id} / seller {self.seller_id})"


class Message(AuditedModel):
    class SenderType(models.TextChoices):
        BUYER = "buyer", "Buyer"
        SELLER = "seller", "Seller"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages", db_column="conversationId"
    )
    # Polymorphic reference into users or sellers depending on sender_type.
    sender_id = models.BigIntegerField(db_column="senderId")
    sender_type = models.CharField(db_column="senderType", max_length=10, choices=SenderType.choices)
    body = models.TextField(null=True, blank=True)
    attachment_path = models.CharField(db_column="attachmentPath", max_length=255, null=True, blank=True)
    attachment_url = models.URLField(db_column="attachmentUrl", max_length=500, null=True, blank=True)
    seen_at = models.DateTimeField(db_column="seenAt", null=True, blank=True)

    class Meta:
        db_table = "messages"
        ordering = ["created_at"]

    def __str__(self):
        return f"Message #{self.pk} in conversation {self.conversation_id}"
