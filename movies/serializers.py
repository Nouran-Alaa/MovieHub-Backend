from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Movie
from django.utils import timezone

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'first_name', 'last_name')
        
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

class MovieSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = Movie
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')
        
    def validate_release_year(self, value):
        current_year = timezone.now().year
        if value < 1888 or value > current_year + 5:
            raise serializers.ValidationError(
                f"Release year must be between 1888 and {current_year + 5}"
            )
        return value
    
    def update(self, instance, validated_data):
        # If status is being changed to 'watched', set watched_date
        if validated_data.get('status') == 'watched' and instance.status != 'watched':
            validated_data['watched_date'] = timezone.now()
        # If status is being changed from 'watched' to 'unwatched', clear watched_date
        elif validated_data.get('status') == 'unwatched' and instance.status == 'watched':
            validated_data['watched_date'] = None
            
        return super().update(instance, validated_data)

class MovieStatsSerializer(serializers.Serializer):
    total_movies = serializers.IntegerField()
    watched_movies = serializers.IntegerField()
    unwatched_movies = serializers.IntegerField()
    watched_this_month = serializers.IntegerField()
    by_genre = serializers.DictField()
    recent_watched = MovieSerializer(many=True)