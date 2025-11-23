from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random

class MetroLine(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Station(models.Model):
    name = models.CharField(max_length=100)
    line = models.ForeignKey(MetroLine, on_delete=models.CASCADE, related_name='stations')
    sequence_number = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['sequence_number']

    def __str__(self):
        return f"{self.name}"

class Ticket(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('IN_USE', 'In Use'),
        ('USED', 'Used'),
        ('EXPIRED', 'Expired'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    source = models.ForeignKey(Station, related_name='departures', on_delete=models.PROTECT)
    destination = models.ForeignKey(Station, related_name='arrivals', on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    purchase_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ACTIVE')

    def __str__(self):
        return f"Ticket #{self.id}"

class StationFootfall(models.Model):
    station = models.ForeignKey(Station, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    entry_count = models.PositiveIntegerField(default=0)
    exit_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('station', 'date')



class TransactionOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Store the pending ticket details so we don't lose them
    source = models.ForeignKey(Station, related_name='otp_source', on_delete=models.CASCADE)
    destination = models.ForeignKey(Station, related_name='otp_dest', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    def is_valid(self):
        # OTP is valid for 5 minutes
        now = timezone.now()
        diff = now - self.created_at
        return diff.total_seconds() < 300 # 300 seconds = 5 mins

    def __str__(self):
        return f"OTP for {self.user.username}"