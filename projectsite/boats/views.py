from django.shortcuts import render

def boat_list(request):
    return render(request, 'boats/boat_list.html')
