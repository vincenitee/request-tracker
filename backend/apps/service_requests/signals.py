from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Attachment


@receiver(post_delete, sender=Attachment)
def delete_attachment_file(sender, instance, **kwargs):
    """Remove the stored file once the row deletion is committed (also on cascade from Request).

    on_commit means a rolled-back delete never loses the file.
    """
    if not instance.file:
        return
    storage, name = instance.file.storage, instance.file.name
    transaction.on_commit(lambda: storage.delete(name))
