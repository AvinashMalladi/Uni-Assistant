from django.shortcuts import render
from .models import Notice


def home(request):
    notices = Notice.objects.order_by('-posted_on')[:5]
    return render(request, 'portal/home.html', {
        'notices': notices,
        'active_page': 'home',
    })


def academics(request):
    return render(request, 'portal/academics.html', {'active_page': 'academics'})


def results(request):
    return render(request, 'portal/results.html', {'active_page': 'results'})


def about(request):
    return render(request, 'portal/about.html', {'active_page': 'about'})
