"""
API Serializers - DRF serializers for all models
"""
from rest_framework import serializers
from accounts.models import User
from contests.models import Contest, ContestSession
from questions.models import Question
from submissions.models import Submission
from analytics.models import Leaderboard
from proctoring.models import Violation


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'organization', 'date_joined']


class ContestSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    question_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Contest
        fields = [
            'id', 'title', 'slug', 'description', 'instructions',
            'start_time', 'end_time', 'duration_minutes',
            'status', 'visibility', 'total_marks',
            'enable_proctoring', 'enable_webcam', 'max_violations',
            'created_by_name', 'question_count', 'created_at',
        ]
        read_only_fields = ['slug', 'created_at']


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = [
            'id', 'title', 'question_type', 'difficulty',
            'marks', 'negative_marks', 'order',
        ]


class SubmissionSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    question_title = serializers.CharField(source='question.title', read_only=True)

    class Meta:
        model = Submission
        fields = [
            'id', 'user_email', 'question_title', 'language',
            'verdict', 'score', 'max_score',
            'execution_time_ms', 'memory_used_kb',
            'passed_test_cases', 'total_test_cases',
            'submitted_at', 'is_final',
        ]


class LeaderboardSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = Leaderboard
        fields = ['rank', 'user_name', 'score', 'problems_solved', 'penalty', 'updated_at']


class ViolationSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Violation
        fields = ['id', 'user_email', 'violation_type', 'description', 'created_at']
