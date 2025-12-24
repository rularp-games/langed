from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Object, Property
from .serializers import ObjectSerializer, PropertySerializer


