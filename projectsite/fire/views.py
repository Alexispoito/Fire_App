from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.db.models import Q
from django.urls import reverse_lazy

from django.contrib import messages

from fire.models import Locations, Incident, FireStation, WeatherConditions, FireTruck, Firefighters, Boat
from fire.forms import Loc_Form, Incident_Form, FireStationzForm, Weather_condition, Firetruckform, FirefightersForm
from django.db.models.query import QuerySet

from django.views.generic.list import ListView
from django.db import connection
from django.http import JsonResponse
from django.db.models.functions import ExtractMonth

from django.db.models import Count
from datetime import datetime


class HomePageView(ListView):
    model = Locations
    context_object_name = 'home'
    template_name = "home.html"


class ChartView(ListView):
    template_name = 'chart.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_queryset(self, *args, **kwargs):
        pass


def PieCountbySeverity(request):
    query = '''
    SELECT severity_level, COUNT(*) as count
    FROM fire_incident
    GROUP BY severity_level
    '''
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    data = {severity: count for severity, count in rows} if rows else {}
    return JsonResponse(data)

def LineCountbyMonth(request):

    current_year = datetime.now().year

    result = {month: 0 for month in range(1, 13)}

    incidents_per_month = Incident.objects.filter(date_time__year=current_year) \
        .values_list('date_time', flat=True)

    # Counting the number of incidents per month
    for date_time in incidents_per_month:
        month = date_time.month
        result[month] += 1

    # If you want to convert month numbers to month names, you can use a dictionary mapping
    month_names = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }
    
    return JsonResponse({month_names[month]: count for month, count in result.items()})

def MultilineIncidentTop3Country(request):

    query = '''
        SELECT 
        fl.country,
        strftime('%m', fi.date_time) AS month,
        COUNT(fi.id) AS incident_count
    FROM 
        fire_incident fi
    JOIN 
        fire_locations fl ON fi.location_id = fl.id
    WHERE 
        fl.country IN (
            SELECT 
                fl_top.country
            FROM 
                fire_incident fi_top
            JOIN 
                fire_locations fl_top ON fi_top.location_id = fl_top.id
            WHERE 
                strftime('%Y', fi_top.date_time) = strftime('%Y', 'now')
            GROUP BY 
                fl_top.country
            ORDER BY 
                COUNT(fi_top.id) DESC
            LIMIT 3
        )
        AND strftime('%Y', fi.date_time) = strftime('%Y', 'now')
    GROUP BY 
        fl.country, month
    ORDER BY 
        fl.country, month;
    '''

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    # Initialize a dictionary to store the result
    result = {}

    # Initialize a set of months from January to December
    months = set(str(i).zfill(2) for i in range(1, 13))

    # Loop through the query results
    for country, month, count in rows:
        if country not in result:
            result[country] = {m: 0 for m in months}
        result[country][month] = count

    while len(result) < 3:
        result[f"Country {len(result) + 1}"] = {m: 0 for m in months}

    return JsonResponse({k: dict(sorted(v.items())) for k, v in result.items()})

def MultipleBarbySeverity(request):
    query = '''
    SELECT 
        fi.severity_level,
        strftime('%m', fi.date_time) AS month,
        COUNT(fi.id) AS incident_count
    FROM 
        fire_incident fi
    GROUP BY fi.severity_level, month
    '''

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    months = set(str(i).zfill(2) for i in range(1, 13))
    result = {}

    for level, month, count in rows:
        if level not in result:
            result[str(level)] = {m: 0 for m in months}
        result[str(level)][month] = count

    return JsonResponse({k: dict(sorted(v.items())) for k, v in result.items()})

def map_station(request):
    fireStations = FireStation.objects.values('name', 'latitude', 'longitude')

    for fs in fireStations:
        fs['latitude'] = float(fs['latitude'])
        fs['longitude'] = float(fs['longitude'])
    
    fireStation_list = list(fireStations)

    context = {
        'fireStation': fireStation_list,  
    }
    return render(request, 'map_station.html', context)

def map_incident(request):
    fireIncidents = Locations.objects.values('name', 'latitude', 'longitude')

    for fs in fireIncidents:
        fs['latitude'] = float(fs['latitude'])
        fs['longitude'] = float(fs['longitude'])

    fireIncidents_list = list(fireIncidents)

    context = {
        'fireIncidents': fireIncidents_list,
    }

    return render(request, 'map_incident.html', context)

class BaseListView(ListView):
    paginate_by = 10
    context_object_name = 'object_list'
    
    def get_queryset(self):
        qs = super().get_queryset()
        if query := self.request.GET.get("q"):
            qs = qs.filter(self.get_search_filter(query))
        return qs
    
    def get_search_filter(self, query):
        return Q()

class BaseCreateView(CreateView):
    def form_valid(self, form):
        messages.success(self.request, f"{self.model._meta.verbose_name} created successfully!")
        return super().form_valid(form)

class BaseUpdateView(UpdateView):
    def form_valid(self, form):
        messages.success(self.request, f"{self.model._meta.verbose_name} updated successfully!")
        return super().form_valid(form)
    
class BaseDeleteView(DeleteView):
    def form_valid(self, form):
        messages.success(self.request, f"{self.model._meta.verbose_name} deleted successfully!")
        return super().form_valid(form)


class FireStationListView(ListView):
    model = FireStation
    template_name = 'station_list.html'
    context_object_name = 'object_list'
    paginate_by = 10
    
    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(
                Q(name__icontains=query) |
                Q(address__icontains=query) |
                Q(city__icontains=query) |
                Q(country__icontains=query)
            )
        return qs

class FireStationCreateView(CreateView):
    model = FireStation
    form_class = FireStationzForm
    template_name = 'station_add.html'
    success_url = reverse_lazy('station-list')

    def form_valid(self, form):
        station_name = form.instance.name
        messages.success(self.request, f'Fire Station "{station_name}" created successfully!')
        return super().form_valid(form)

class FireStationUpdateView(UpdateView):
    model = FireStation
    form_class = FireStationzForm
    template_name = 'station_edit.html'
    success_url = reverse_lazy('station-list')

    def form_valid(self, form):
        station_name = form.instance.name
        messages.success(self.request, f'Fire Station "{station_name}" updated successfully!')
        return super().form_valid(form)
    
class FireStationDeleteView(DeleteView):
    model = FireStation
    template_name= 'station_del.html'
    success_url = reverse_lazy('station-list')
    
    def form_valid(self, form):
        station_name = form.instance.name
        messages.success(self.request, f'Fire Station "{station_name}" deleted successfully!')
        return super().form_valid(form)
    

class ConditionListView(ListView):
    model = WeatherConditions
    context_object_name = 'object_list'
    template_name = 'weather_list.html'
    paginate_by = 10

    def get_queryset(self, *args, **kwargs):
        qs = super(ConditionListView, self).get_queryset(*args, **kwargs)
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(incident__location__name__icontains=query) | 
                Q(temperature__icontains=query) |
                Q(humidity__icontains=query) |
                Q(wind_speed__icontains=query) |
                Q(weather_description__icontains=query)
            )
        return qs

class ConditionCreateView(CreateView):
    model = WeatherConditions
    form_class = Weather_condition
    template_name = 'weather_add.html'
    success_url = reverse_lazy('weather-list')

    def form_valid(self, form):
        location = form.instance.incident.location.name
        messages.success(self.request, f'Weather condition for "{location}" created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['weather_list'] = self.success_url
        return context

class ConditionUpdateView(UpdateView):
    model = WeatherConditions
    form_class = Weather_condition
    template_name = 'weather_edit.html'
    success_url = reverse_lazy('weather-list')
    context_object_name = 'weather'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Update Weather Conditions - Record #{self.object.id}"
        return context

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            location = form.instance.incident.location.name
            messages.success(
                self.request,
                f'Successfully updated weather conditions for "{location}"',
                extra_tags='alert-success'
            )
            return response
        except Exception as e:
            messages.error(
                self.request,
                f'Error updating weather conditions: {str(e)}',
                extra_tags='alert-danger'
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        print("Form errors:", form.errors)
        messages.error(
            self.request,
            'Please correct the errors below.',
            extra_tags='alert-danger'
        )
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['weather_list'] = self.success_url
        return context

class ConditionDeleteView(DeleteView):
    model = WeatherConditions
    template_name = 'weather_del.html'
    success_url = reverse_lazy('weather-list')
    context_object_name = 'weather'

    def form_valid(self, form):
        try:
            location = self.object.incident.location.name
            response = super().form_valid(form)
            messages.success(
                self.request, 
                f'Weather condition "{location}" was successfully deleted!'
            )
            return response
        except Exception as e:
            messages.error(
                self.request,
                f'Error deleting weather condition: {str(e)}'
            )
            return super().form_invalid(form)
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['weather_list'] = self.success_url
        return context


class FiretruckListView(ListView):
    model = FireTruck
    context_object_name = 'firetruck'
    template_name = 'firetruck_list.html'
    paginate_by = 10
    ordering = ['-id']

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        query = self.request.GET.get("q")
        
        if query:
            qs = qs.filter(
                Q(truck_number__icontains=query) | 
                Q(model__icontains=query) | 
                Q(capacity__icontains=query) | 
                Q(station__name__icontains=query)
            ).order_by('-id')
            
        return qs

class FiretruckCreateView(CreateView):
    model = FireTruck
    form_class = Firetruckform
    template_name = 'firetruck_add.html'
    success_url = reverse_lazy('fireTruck-list')

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            truck_number = form.instance.truck_number
            messages.success(
                self.request, 
                f'Fire Truck #{truck_number} was successfully created!',
                extra_tags='success'
            )
            return response
        except Exception as e:
            messages.error(
                self.request,
                f'Error creating fire truck: {str(e)}',
                extra_tags='danger'
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Add New Fire Truck'
        return context
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['firetruck_list'] = self.success_url
        return context

class FiretruckUpdateView(UpdateView):
    model = FireTruck
    form_class = Firetruckform
    template_name = 'firetruck_edit.html'
    success_url = reverse_lazy('fireTruck-list')
    context_object_name = 'firetruck'

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            truck_number = form.instance.truck_number
            messages.success(
                self.request,
                f'Fire Truck #{truck_number} was successfully updated!',
                extra_tags='success'
            )
            return response
        except Exception as e:
            messages.error(
                self.request,
                f'Error updating fire truck: {str(e)}',
                extra_tags='danger'
            )
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Update Fire Truck #{self.object.truck_number}'
        return context
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['firetruck_list'] = self.success_url
        return context
    
class FiretruckDeleteView(DeleteView):
    model = FireTruck
    template_name = 'firetruck_del.html'
    success_url = reverse_lazy('fireTruck-list')
    context_object_name = 'firetruck'

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f'Delete Fire Truck #{self.object.truck_number}'
        return context

    def form_valid(self, form):
        try:
            truck_number = self.object.truck_number
            response = super().form_valid(form)
            messages.success(
                self.request,
                f'Fire Truck #{truck_number} was successfully deleted!',
                extra_tags='success'
            )
            return response
        except Exception as e:
            messages.error(
                self.request,
                f'Error deleting fire truck: {str(e)}',
                extra_tags='danger'
            )
            return self.form_invalid(form)
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['firetruck_list'] = self.success_url
        return context

class FirefightersListView(ListView):
    model = Firefighters
    context_object_name = 'firefighters'
    template_name = 'firefighter_list.html'
    paginate_by = 10 
    
    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(Q(name__icontains=query))
        return qs

class FirefightersCreateView(CreateView):
    model = Firefighters
    form_class = FirefightersForm
    template_name = 'firefighter_add.html'
    success_url = reverse_lazy('firefighters-list')

    def form_valid(self, form):
        name = form.instance.name
        messages.success(self.request, f'Firefighter "{name}" created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['firefighter_list'] = self.success_url
        return context

class FirefightersUpdateView(UpdateView):
    model = Firefighters
    form_class = FirefightersForm
    template_name = 'firefighter_edit.html'
    success_url = reverse_lazy('firefighters-list')

    def form_valid(self, form):
        name = form.instance.name
        messages.success(self.request, f'Firefighter "{name}" updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['firefighter_list'] = self.success_url
        return context

    
class FirefightersDeleteView(DeleteView):
    model = Firefighters
    template_name = 'firefighter_del.html'
    success_url = reverse_lazy('firefighters-list')
    
    def form_valid(self, form):
        firefighter = self.get_object()
        name = firefighter.name
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Firefighter "{name}" was deleted successfully!',
            extra_tags='toast success'
        )
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['firefighter_list'] = self.success_url
        return context


class IncidentListView(ListView):
    model = Incident
    template_name = 'incident_list.html'
    paginate_by = 10
    ordering = ['-reported_date']
    
    def get_queryset(self):
        return super().get_queryset().select_related('location')
    

class IncidentCreateView(CreateView):
    model = Incident
    form_class = Incident_Form
    template_name = 'incident_add.html'
    success_url = reverse_lazy('incident-list')

    def form_valid(self, form):
        description = form.instance.description[:50] + "..." if len(form.instance.description) > 50 else form.instance.description
        messages.success(self.request, f'Incident "{description}" created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['incident_list'] = self.success_url
        return context

class IncidentUpdateView(UpdateView):
    model = Incident
    form_class = Incident_Form
    template_name = 'incident_edit.html'
    success_url = reverse_lazy('incident-list')

    def form_valid(self, form):
        description = form.instance.description[:50] + "..." if len(form.instance.description) > 50 else form.instance.description
        messages.success(self.request, f'Incident "{description}" updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['incident_list'] = self.success_url
        return context

class IncidentDeleteView(DeleteView):
    model = Incident
    template_name = 'incident_del.html'
    success_url = reverse_lazy('incident-list')
    context_object_name = 'incident'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Delete Incident #{self.object.id}"
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        description = self.object.description[:50] + "..." if len(self.object.description) > 50 else self.object.description
        messages.success(self.request, f'Successfully deleted incident: "{description}"')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['incident_list'] = self.success_url
        return context


class IncidentListView(ListView):
    model = Incident
    template_name = 'incident_list.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(
                Q(description__icontains=query) |
                Q(severity_level__icontains=query) |
                Q(location__name__icontains=query) |
                Q(date_time__icontains=query)
            )
        return qs

class LocationListView(ListView):
    model = Locations
    template_name = 'loc_list.html'
    context_object_name = 'object_list'
    paginate_by = 10

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        query = self.request.GET.get("q")
        if query:
            qs = qs.filter(
                Q(name__icontains=query) |
                Q(address__icontains=query) |
                Q(city__icontains=query) |
                Q(country__icontains=query)
            )
        return qs
class LocationCreateView(CreateView):
    model = Locations
    form_class = Loc_Form
    template_name = 'loc_add.html'
    success_url = reverse_lazy('loc-list')

    def form_valid(self, form):
        name = form.instance.name
        messages.success(self.request, f'Location "{name}" created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['loc_list'] = self.success_url
        return context

class LocationUpdateView(UpdateView):
    model = Locations
    form_class = Loc_Form
    template_name = 'loc_edit.html'
    success_url = reverse_lazy('loc-list')

    def form_valid(self, form):
        name = form.instance.name
        messages.success(self.request, f'Location "{name}" updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['loc_list'] = self.success_url

class LocationDeleteView(DeleteView):
    model = Locations
    template_name = 'loc_del.html'
    success_url = reverse_lazy('loc-list')
    context_object_name = 'location'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Delete Location #{self.object.id}"
        return context

    def form_valid(self, form):
        name = self.object.name
        response = super().form_valid(form)
        messages.success(self.request, 
            f'Location "{name}" was successfully deleted.',
            extra_tags='danger'
        )
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['loc_list'] = self.success_url
        return context


class BoatListView(ListView):
    model = Boat
    template_name = "boats/boat_form.html"
    context_object_name = "boats"

    def get_search_filter(self, query):
        return (Q(name__icontains=query) |
                Q(boat_type__icontains=query) |
                Q(status__icontains=query) |
                Q(location__name__icontains=query))

class BoatCreateView(BaseCreateView):
    model = Boat
    fields = "__all__"
    template_name = "boats/boat_form.html"
    success_url = reverse_lazy('boat-list')

    def validate_dimensions(self, form_data):
        errors = []
        dimension_fields = ['length', 'width', 'height']
        
        for field in dimension_fields:
            value = form_data.get(field)
            try:
                if float(value) <= 0:
                    errors.append(f"{field.capitalize()} must be greater than 0.")
            except (ValueError, TypeError):
                errors.append(f"{field.capitalize()} must be a valid number.")
        return errors

    def form_valid(self, form):
        errors = self.validate_dimensions(form.cleaned_data)
        if errors:
            for error in errors:
                messages.error(self.request, error)
            return self.form_invalid(form)
        
        boat_name = form.instance.name if form.instance.name else "New Boat"
        messages.success(self.request, f'Boat "{boat_name}" was created successfully!')
        return super().form_valid(form)

class BoatUpdateView(BaseUpdateView):
    model = Boat
    fields = "__all__"
    template_name = "boats/boat_form.html"
    success_url = reverse_lazy('boat-list')

    def validate_dimensions(self, form_data):
        errors = []
        dimension_fields = ['length', 'width', 'height']
        
        for field in dimension_fields:
            value = form_data.get(field)
            try:
                if float(value) <= 0:
                    errors.append(f"{field.capitalize()} must be greater than 0.")
            except (ValueError, TypeError):
                errors.append(f"{field.capitalize()} must be a valid number.")
        return errors

    def form_valid(self, form):
        errors = self.validate_dimensions(form.cleaned_data)
        if errors:
            for error in errors:
                messages.error(self.request, error)
            return self.form_invalid(form)
        
        boat_name = form.instance.name if form.instance.name else "Boat"
        messages.success(self.request, f'Boat "{boat_name}" was updated successfully!')
        return super().form_valid(form)
    
       
def dashboard_chart(request):
    context = {

    }
    return render(request, 'dashboard/chart.html', context)