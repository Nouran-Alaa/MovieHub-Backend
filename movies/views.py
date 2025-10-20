from rest_framework import viewsets, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone
from django.conf import settings
from datetime import datetime
from .models import Movie
from .serializers import (
    MovieSerializer, UserSerializer,
    RegisterSerializer, MovieStatsSerializer
)
import requests
from django.core.cache import cache
import concurrent.futures

# -------------------------------
# AUTH & USER VIEWS
# -------------------------------

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


# -------------------------------
# MOVIE CRUD VIEWSET
# -------------------------------

class MovieViewSet(viewsets.ModelViewSet):
    serializer_class = MovieSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = Movie.objects.filter(user=self.request.user)

        # Filters
        status = self.request.query_params.get('status')
        genre = self.request.query_params.get('genre')
        search = self.request.query_params.get('search')

        if status:
            queryset = queryset.filter(status=status)
        if genre:
            queryset = queryset.filter(genre__iexact=genre)
        if search:
            queryset = queryset.filter(title__icontains=search)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_watched(self, request, pk=None):
        movie = self.get_object()
        movie.status = 'watched'
        movie.watched_date = timezone.now()
        movie.save()
        return Response(self.get_serializer(movie).data)

    @action(detail=True, methods=['post'])
    def mark_unwatched(self, request, pk=None):
        movie = self.get_object()
        movie.status = 'unwatched'
        movie.watched_date = None
        movie.save()
        return Response(self.get_serializer(movie).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        user_movies = Movie.objects.filter(user=request.user)
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        stats = {
            'total_movies': user_movies.count(),
            'watched_movies': user_movies.filter(status='watched').count(),
            'unwatched_movies': user_movies.filter(status='unwatched').count(),
            'watched_this_month': user_movies.filter(
                status='watched', watched_date__gte=month_start
            ).count(),
            'by_genre': dict(
                user_movies.values('genre').annotate(count=Count('id')).values_list('genre', 'count')
            ),
            'recent_watched': MovieSerializer(
                user_movies.filter(status='watched').order_by('-watched_date')[:5],
                many=True
            ).data
        }

        serializer = MovieStatsSerializer(stats)
        return Response(serializer.data)


# -------------------------------
# OMDB SEARCH & INTEGRATION
# -------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_movie(request):
    """Search for movies in OMDb API and return results with IMDb IDs."""
    title = request.GET.get('title', '').strip()
    api_key = settings.OMDB_API_KEY

    if not title:
        # Return default popular movies
        return _get_default_movies(api_key, request.user)

    # Check cache first
    cache_key = f"omdb_search_{title.lower()}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    try:
        # Search OMDb API
        res = requests.get(
            f"https://www.omdbapi.com/?apikey={api_key}&s={title}",
            timeout=5
        )
        data = res.json()

        if data.get("Response") == "False":
            return Response({"results": []})

        # Format results with IMDb IDs
        movies = []
        for m in data.get("Search", [])[:10]:  # Limit to 10 results
            movie_data = {
                "imdb_id": m.get("imdbID"),
                "title": m.get("Title"),
                "release_year": m.get("Year", "").split("–")[0],  # Handle year ranges
                "poster": m.get("Poster") if m.get("Poster") != "N/A" else None,
                "status": "unwatched",
                "is_saved": False  # Will be checked below
            }
            
            # Check if user already saved this movie
            if Movie.objects.filter(user=request.user, imdb_id=m.get("imdbID")).exists():
                movie_data["is_saved"] = True
            
            movies.append(movie_data)

        cache.set(cache_key, {"results": movies}, timeout=3600)
        return Response({"results": movies})

    except Exception as e:
        return Response({"error": "Failed to search movies", "details": str(e)}, status=500)


def _get_default_movies(api_key, user):
    """Fetch popular default movies in parallel."""
    default_titles = [
        "Inception", "The Dark Knight", "Interstellar", "Avatar", "Titanic",
        "The Matrix", "Gladiator", "Avengers", "Joker", "Fight Club"
    ]

    def fetch_movie(t):
        try:
            res = requests.get(
                f"https://www.omdbapi.com/?apikey={api_key}&t={t}",
                timeout=4
            )
            data = res.json()
            if data.get("Response") == "True":
                movie_data = {
                    "imdb_id": data.get("imdbID"),
                    "title": data.get("Title"),
                    "release_year": data.get("Year"),
                    "poster": data.get("Poster") if data.get("Poster") != "N/A" else None,
                    "rating": data.get("imdbRating"),
                    "status": "unwatched",
                    "is_saved": False
                }
                
                # Check if saved
                if Movie.objects.filter(user=user, imdb_id=data.get("imdbID")).exists():
                    movie_data["is_saved"] = True
                
                return movie_data
        except:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(fetch_movie, default_titles))

    movies = [m for m in results if m]
    return Response({"results": movies})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_movie_details(request, imdb_id):
    """Fetch detailed movie information from OMDb by IMDb ID."""
    api_key = settings.OMDB_API_KEY
    
    cache_key = f"omdb_details_{imdb_id}"
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    try:
        res = requests.get(
            f"https://www.omdbapi.com/?apikey={api_key}&i={imdb_id}",
            timeout=5
        )
        data = res.json()

        if data.get("Response") == "False":
            return Response({"error": "Movie not found"}, status=404)

        movie = {
            "imdb_id": data.get("imdbID"),
            "title": data.get("Title"),
            "release_year": data.get("Year"),
            "genre": data.get("Genre", "").split(",")[0].strip().lower(),  # Take first genre
            "plot": data.get("Plot"),
            "poster": data.get("Poster") if data.get("Poster") != "N/A" else None,
            "rating": data.get("imdbRating"),
            "status": "unwatched",
        }
        
        cache.set(cache_key, movie, timeout=3600)
        return Response(movie)

    except Exception as e:
        return Response({"error": "Failed to fetch movie details"}, status=500)