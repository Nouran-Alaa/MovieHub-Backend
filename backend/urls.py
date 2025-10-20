from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from movies.views import (
    MovieViewSet, RegisterView, UserProfileView, 
    search_movie, get_movie_details
)

# Swagger configuration
schema_view = get_schema_view(
    openapi.Info(
        title="Movie Watchlist API",
        default_version='v1',
        description="API for managing personal movie watchlist",
        contact=openapi.Contact(email="contact@moviewatchlist.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Router for ViewSets
router = DefaultRouter()
router.register(r'movies', MovieViewSet, basename='movie')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # Authentication
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),

    
    # Movies API
    path('api/', include(router.urls)),
    
    # External API Search
    path('api/search-movie/', search_movie, name='search-movie'),
    path('api/movie-details/<str:imdb_id>/', get_movie_details, name='movie-details'),
]