# chat/views.py
from django.http import HttpResponse

def chat_room(request):
    return HttpResponse('Hello, world. You\'re at the polls room.')


# ---------------------------------django-channels------------------------------------
from django.shortcuts import render

def index(request):
    return HttpResponse('Hello, world. You\'re at the polls room.')

def room(request, room_name):
    return HttpResponse('Hello, world. You\'re at the polls room.')