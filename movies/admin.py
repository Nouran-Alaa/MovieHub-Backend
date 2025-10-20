from django.contrib import admin
from .models import Movie

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'genre', 'release_year', 'status', 'rating', 'created_at')
    list_filter = ('status', 'genre', 'release_year')
    search_fields = ('title', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'watched_date')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'genre', 'release_year')
        }),
        ('Details', {
            'fields': ('plot', 'poster', 'rating')
        }),
        ('Status', {
            'fields': ('status', 'watched_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )