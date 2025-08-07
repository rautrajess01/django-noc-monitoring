import hashlib
from datetime import timedelta
from datetime import date

from django.db import models
from django.utils import timezone


class NetworkEvent(models.Model):
    name = models.CharField(max_length=100)
    down_time = models.DateTimeField(null=True, blank=True, db_index=True)
    up_time = models.DateTimeField(null=True, blank=True)
    date = models.CharField(max_length=100)
    type = models.CharField(max_length=100, db_index=True)
    region = models.CharField(max_length=100, db_index=True)
    reason = models.CharField(max_length=100)
    solar = models.CharField(max_length=100)
    remarks = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=100)
    down_count = models.IntegerField(default=0)

    # Add computed fields for better performance
    duration_seconds = models.IntegerField(
        null=True, blank=True, help_text="Duration in seconds"
    )
    unique_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA256 hash for duplicate prevention",
    )
    base_hash = models.CharField(max_length=64, db_index=True, help_text="Base hash for update comparison", null=True, blank=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Remove the complex unique constraint and use hash-based approach instead
        indexes = [
            models.Index(fields=["name", "down_time"]),
            models.Index(fields=["type", "down_time"]),
            models.Index(fields=["region", "down_time"]),
            models.Index(fields=["down_time"]),
            models.Index(fields=["unique_hash"]),  # Fast duplicate checking
        ]
        ordering = ["-down_time"]

    @property
    def is_today(self):
        """Check if the event occurred today"""
        if not self.down_time:
            return False
        return self.down_time.date() == date.today()

    @property
    def is_current_week(self):
        """Check if the event occurred in the current week"""
        if not self.down_time:
            return False
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return start_of_week <= self.down_time.date() <= end_of_week

    def generate_unique_hash(self):
        """Generate SHA256 hash for duplicate detection including all relevant fields"""
        # Include all fields except down_count, created_at, updated_at for duplicate detection
        data_string = "|".join(
            [
                str(self.name or "").strip().lower(),
                str(self.down_time) if self.down_time else "",
                str(self.up_time) if self.up_time else "",
                str(self.date or "").strip().lower(),
                str(self.type or "").strip().lower(),
                str(self.region or "").strip().lower(),
                str(self.reason or "").strip().lower(),
                str(self.solar or "").strip().lower(),
                str(self.remarks or "").strip().lower(),
                str(self.category or "").strip().lower(),
            ]
        )
        return hashlib.sha256(data_string.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        # Generate unique hash before saving
        self.unique_hash = self.generate_unique_hash()

        # Calculate duration in seconds for better performance
        if self.down_time and self.up_time:
            duration = self.up_time - self.down_time
            self.duration_seconds = int(duration.total_seconds())
        elif self.down_time:
            # For ongoing events, calculate duration from down_time to now
            now = timezone.now()
            if timezone.is_aware(now) and timezone.is_naive(self.down_time):
                now = now.replace(tzinfo=None)
            duration = now - self.down_time
            self.duration_seconds = int(duration.total_seconds())
        else:
            self.duration_seconds = 0

        super().save(*args, **kwargs)

    
    def duration(self):
        """Return duration as timedelta object"""
        if self.duration_seconds is not None:
            return timedelta(seconds=self.duration_seconds)

        if self.down_time and self.up_time:
        # Ensure both datetimes are either aware or naive
            if timezone.is_naive(self.down_time) and timezone.is_aware(self.up_time):
                self.down_time = timezone.make_aware(self.down_time)
            elif timezone.is_aware(self.down_time) and timezone.is_naive(self.up_time):
                self.up_time = timezone.make_aware(self.up_time)

            return self.up_time.replace(microsecond=0) - self.down_time.replace(microsecond=0)

        elif self.down_time:
            now = timezone.now()
        # Ensure both down_time and now are aware
            if timezone.is_naive(self.down_time):
                self.down_time = timezone.make_aware(self.down_time)

            return now.replace(microsecond=0) - self.down_time.replace(microsecond=0)

        return timedelta(seconds=0)

    def __str__(self):
        return f"{self.name} | {self.down_time} - {self.up_time}"

    @classmethod
    def check_duplicate_exists(cls, **kwargs):
        """Check if a duplicate exists based on the hash"""
        temp_instance = cls(**kwargs)
        unique_hash = temp_instance.generate_unique_hash()
        return cls.objects.filter(unique_hash=unique_hash).exists()
    @classmethod
    def create_or_update_event(cls, **kwargs):
        """
    Create or update a NetworkEvent based on base_hash.
    Returns: (instance, created, updated)
    """
    # Normalize & generate base_hash for matching "core" event
        temp = cls(**kwargs)
        base_data_string = "|".join([
        (temp.name or "").strip().lower(),
        str(temp.down_time) if temp.down_time else "",
        (temp.type or "").strip().lower(),
        (temp.region or "").strip().lower(),
    ])
        base_hash = hashlib.sha256(base_data_string.encode('utf-8')).hexdigest()

    # Add base_hash to kwargs for saving later
        kwargs['base_hash'] = base_hash

        try:
            existing = cls.objects.get(base_hash=base_hash)
            updated = False

        # Check fields that matter for update
            fields_to_check = [
            'up_time', 'date', 'reason', 'solar', 'remarks',
            'category', 'down_count',
        ]
            for field in fields_to_check:
                new_val = kwargs.get(field)
                old_val = getattr(existing, field)
                if new_val != old_val:
                    setattr(existing, field, new_val)
                    updated = True

            if updated:
                existing.save()
                return existing, False, True  # updated
            else:
                return existing, False, False  # duplicate, no changes

        except cls.DoesNotExist:
        # No existing event, create new
            new_event = cls(**kwargs)
            new_event.save()
            return new_event, True, False  # created

class NetworkEventImport(models.Model):
    csv_file = models.FileField(upload_to="uploads/events/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_rows = models.IntegerField(default=0)
    created_events = models.IntegerField(default=0)
    updated_events = models.IntegerField(default=0)
    duplicate_events = models.IntegerField(default=0)
    processing_status = models.CharField(
        max_length=20,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
    )
    error_message = models.TextField(null=True, blank=True)
    skipped_rows_file = models.FileField(
        upload_to="skipped_logs/",
        null=True,
        blank=True,
        verbose_name="Skipped Rows Log"
    )


    def __str__(self):
        return f"{self.csv_file.name} - {self.processing_status}"

    class Meta:
        verbose_name = "Network Event CSV Import"
        verbose_name_plural = "Network Event CSV Imports"
        ordering = ["-uploaded_at"]
