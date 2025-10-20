from django.db import models
from django.contrib.auth.models import User

class Movie(models.Model):
    STATUS_CHOICES = [
        ('watched', 'Watched'),
        ('unwatched', 'Unwatched'),
    ]
    
    GENRE_CHOICES = [
        ('action', 'Action'),
        ('comedy', 'Comedy'),
        ('drama', 'Drama'),
        ('horror', 'Horror'),
        ('sci-fi', 'Sci-Fi'),
        ('thriller', 'Thriller'),
        ('romance', 'Romance'),
        ('documentary', 'Documentary'),
        ('animation', 'Animation'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='movies')
    imdb_id = models.CharField(max_length=20, blank=True, null=True)  # NEW: Store IMDb ID
    title = models.CharField(max_length=255)
    genre = models.CharField(max_length=50, choices=GENRE_CHOICES)
    release_year = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unwatched')
    plot = models.TextField(blank=True, null=True)
    poster = models.URLField(blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    watched_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        # Ensure user can't add same movie twice
        unique_together = [['user', 'imdb_id']]
        
    def __str__(self):
        return f"{self.title} ({self.release_year})"