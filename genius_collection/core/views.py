from django.contrib.auth.models import User, Group
from rest_framework import viewsets
from rest_framework import permissions
from genius_collection.core.serializers import UserSerializer, GroupSerializer, CardSerializer
from django.http import HttpResponse
from django.shortcuts import render

from .models import Card, Question


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class CardViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows cards to be viewed or edited.
    """
    queryset = Card.objects.all()
    serializer_class = CardSerializer

    # permission_classes = [permissions.IsAuthenticated]


def details(request):
    print('You reached the details')
    return HttpResponse('Successful Detail')


def questions(request):
    latest_question_list = Question.objects.order_by("-pub_date")[:5]
    context = {"latest_question_list": latest_question_list}
    return render(request, "core/index.html", context)
