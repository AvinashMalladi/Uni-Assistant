from django.contrib import admin
from .models import Department, SemesterResult, Notice

admin.site.register(Department)
admin.site.register(SemesterResult)
admin.site.register(Notice)
