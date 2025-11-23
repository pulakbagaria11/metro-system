from django.contrib import admin
from .models import MetroLine, Station, Ticket, StationFootfall

admin.site.register(MetroLine)
admin.site.register(Station)
admin.site.register(Ticket)
admin.site.register(StationFootfall)