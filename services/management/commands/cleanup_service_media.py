from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from services.models import ServiceRequestMedia
import os

class Command(BaseCommand):
    help = 'Deletes ServiceRequestMedia files older than 24 hours'

    def handle(self, *args, **kwargs):
        cutoff_time = timezone.now() - timedelta(hours=24)
        old_media = ServiceRequestMedia.objects.filter(created_at__lte=cutoff_time)
        
        count = old_media.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No old media files found to delete.'))
            return

        for media in old_media:
            # Delete physical file
            if media.file:
                if os.path.isfile(media.file.path):
                    os.remove(media.file.path)
                    self.stdout.write(f'Deleted file: {media.file.path}')
            
            # Delete database record
            media.delete()

        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} old media entries.'))
