import base64
import datetime
from collections import Counter, defaultdict
from datetime import time, timedelta
import re 
import json
from django.contrib import messages
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from .utils import find_likely_root_cause 
from django.views.decorators.csrf import csrf_exempt

from .models import NetworkEvent
from .services import sync_network_events_from_google_sheet


def get_time_range(request):
    events = NetworkEvent.objects.all()
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if start_date and end_date:
        start_time = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end_time = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    else:
        start_time, end_time = None, None
        for event in events:
            if event.date == "1st Baisakh":
                start_time = event.down_time
        end_time = datetime.datetime.now().replace(microsecond=0)

    if start_time:
        start_time = datetime.datetime.combine(start_time, time.min)
    return start_time, end_time


from django.db.models import Q

from .models import NetworkEvent  # Make sure to import your model


def get_query(request):
    """
    Builds a filtered queryset for NetworkEvent objects based on GET parameters.
    """
    print("RECEIVED FILTERS:", request.GET)
    name_query = request.GET.get("name", None)
    start_date = request.GET.get("start_date", None)
    end_date = request.GET.get("end_date", None)
    type_query = request.GET.get("type", None)

    # Start with a clean queryset
    queryset = NetworkEvent.objects.all()

    # Apply text search filter for name and reason
    if name_query:
        # The OR condition should only apply to text-like fields
        queryset = queryset.filter(
            Q(name__icontains=name_query)
            | Q(reason__icontains=name_query)
            | Q(date__icontains=name_query)
        )

    # Apply date range filters
    if start_date:
        queryset = queryset.filter(down_time__date__gte=start_date)

    if end_date:
        queryset = queryset.filter(down_time__date__lte=end_date)

    # Apply type filter
    if type_query:
        queryset = queryset.filter(type__iexact=type_query)

    # The final ordering should be done here
    return queryset.order_by("down_time")


def display(request):
    total_events = get_query(request).count()
    type_query = request.GET.get("type")
    page = "index.html"
    events = get_query(request)
    start_time, end_time = get_time_range(request)
    total_seconds = (end_time - start_time).total_seconds()
    other_events = get_query(request).filter
    pendings = events.filter(up_time__isnull=True)
    host_map = {}
    other_events = {}
    total_switch = 0
    total_mpls = 0
    for i in events:
        if i.name in host_map:
            host_map[i.name]["duration"] += i.duration()
            host_map[i.name]["count"] += 1
            host_map[i.name]["reasons_list"].append(i.reason)
        else:
            if i.type and i.type.lower() in ["switch", "mpls"]:
                host_map[i.name] = {
                    "name": i.name,
                    "encoded_name": base64.urlsafe_b64encode(i.name.encode()).decode(),
                    "count": 1,
                    "duration": i.duration(),
                    "uptime": 0,
                    "reasons_list": [i.reason],
                    "type": i.type.lower() if i.type else None,
                }
            else:
                other_events[i.name] = {
                    "date": i.date,
                    "name": i.name,
                    "encoded_name": base64.urlsafe_b64encode(i.name.encode()).decode(),
                    "count": 1,
                    "downtime": i.down_time,
                    "uptime": i.up_time,
                    "duration": i.duration(),
                    "reasons_list": [i.reason],
                    "type": i.type.lower() if i.type else None,
                }

    total_switch = sum(1 for h in host_map.values() if h["type"] == "switch")
    total_mpls = sum(1 for h in host_map.values() if h["type"] == "mpls")
    host_details = list(host_map.values())
    other_events = list(other_events.values())
    for host in host_details:
        downtime_percent = (host["duration"].total_seconds() / total_seconds) * 100
        host["uptime"] = round(100 - downtime_percent, 2)
        host["reason"] = find_likely_root_cause(host["reasons_list"])

    host_details = sorted(
        host_details,
        key=lambda x: (x["count"], x["duration"], x["uptime"]),
        reverse=True,
    )
    for host in other_events:
        host["reason"] = find_likely_root_cause(host["reasons_list"])

    context = {
        "host_details": host_details,
        "page": page,
        "start_time": start_time,
        "end_time": end_time,
        "pendings": pendings,
        "type_query": type_query,
        "name_query": request.GET.get("name", None),
        "type_query_cap": (
            ""
            if not type_query
            else (
                type_query.upper()
                if type_query in ["crc", "mpls"]
                else type_query.title()
            )
        ),
        "total_events": total_events,
        "total_switch": total_switch,
        "total_mpls": total_mpls,
        "other_events": other_events,
    }
    return render(request, "base/index.html", context)


def per_host_details(request, pk):
    decoded_pk = base64.urlsafe_b64decode(pk.encode()).decode()
    page = "per_host.html"
    events = get_query(request).filter(name=decoded_pk)
    return render(
        request,
        "base/per_host.html",
        {"events": events, "page": page, "pk": pk},
    )


def aggregate_uptime_api(request):
    start_time, end_time = get_time_range(request)
    total_seconds = (end_time - start_time).total_seconds()
    events = get_query(request).filter(
        Q(type__iexact="switch") | Q(type__iexact="mpls")
    )

    downtime_per_device = defaultdict(timedelta)
    device_types = {}

    for event in events:
        downtime_per_device[event.name] += event.duration()
        if event.name not in device_types:
            device_types[event.name] = event.type.lower()

    switch_uptimes = []
    mpls_uptimes = []

    for device_name, total_downtime in downtime_per_device.items():
        downtime_percent = (total_downtime.total_seconds() / total_seconds) * 100
        uptime_percent = 100 - downtime_percent

        if device_types[device_name] == "switch":
            switch_uptimes.append(uptime_percent)
        elif device_types[device_name] == "mpls":
            mpls_uptimes.append(uptime_percent)

    chart_data = {
        "labels": ["Switch", "MPLS"],
        "data": [
            (
                round(sum(switch_uptimes) / len(switch_uptimes), 2)
                if switch_uptimes
                else 0
            ),
            round(sum(mpls_uptimes) / len(mpls_uptimes), 2) if mpls_uptimes else 0,
        ],
    }
    return JsonResponse(chart_data)


def host_all_charts_api(request, pk):
    name = base64.urlsafe_b64decode(pk.encode()).decode()
    start_time, end_time = get_time_range(request)
    total_minutes = (end_time - start_time).total_seconds() / 60

    events = get_query(request).filter(
        name=name, down_time__range=(start_time, end_time)
    )

    total_downtime = sum((e.duration() for e in events), timedelta())
    downtime_minutes = total_downtime.total_seconds() / 60
    uptime_minutes = total_minutes - downtime_minutes

    # Pie Chart
    uptime_pie = {
        "labels": ["Uptime", "Downtime"],
        "data": [round(uptime_minutes, 2), round(downtime_minutes, 2)],
    }

    # Daily Bar + Reason
    daily_downtime = defaultdict(timedelta)
    daily_reasons = defaultdict(set)
    for e in events:
        key = e.down_time.date()
        daily_downtime[key] += e.duration()
        if e.reason:
            daily_reasons[key].add(e.reason)

    bar_labels, bar_data, bar_reasons = [], [], []
    for date in sorted(daily_downtime):
        bar_labels.append(date.strftime("%Y-%m-%d"))
        bar_data.append(round(daily_downtime[date].total_seconds() / 60, 2))
        bar_reasons.append(next(iter(daily_reasons[date]), "No Reason"))

    daily_bar = {
        "labels": bar_labels,
        "data": bar_data,
        "reasons": bar_reasons,
    }

    # Trend Line
    trend_counts = defaultdict(int)
    for e in events:
        trend_counts[e.down_time.date()] += 1

    trend_line = {
        "labels": [d.strftime("%Y-%m-%d") for d in sorted(trend_counts)],
        "data": [trend_counts[d] for d in sorted(trend_counts)],
    }

    return JsonResponse(
        {
            "uptime_pie": uptime_pie,
            "daily_bar": daily_bar,
            "trend_line": trend_line,
        }
    )


# In your views.py
def daily_event_trend_api(request):
    """
    Calculates the daily trend of network events based on selected filters.
    Counts all matching events per day.
    """
    # Get filtered queryset (already filtered by name/type/start/end date)
    queryset = get_query(request)

    # Aggregate per day using down_time
    trend_data = (
        queryset.annotate(event_date=TruncDate("down_time"))
        .values("event_date")
        .annotate(count=Count("id"))
        .order_by("event_date")
    )

    labels = [item["event_date"].strftime("%Y-%m-%d") for item in trend_data]
    data = [item["count"] for item in trend_data]

    return JsonResponse({"labels": labels, "data": data})


def sync_page_view(request):
    # This view is now only for processing, not for displaying a page
    if request.method != "POST":
        # If someone tries to access this URL via GET, just send them home.
        return redirect("index")  # Or whatever your main page is named

    try:
        summary = sync_network_events_from_google_sheet()

        if summary.get("message"):
            messages.info(request, summary["message"])
        else:
            summary_str = (
                f"Sync complete! Created: {summary['created']}, Updated: {summary['updated']}, "
                f"Duplicates: {summary['duplicates']}, Skipped: {summary['skipped']}."
            )
            messages.success(request, summary_str)

    except Exception as e:
        messages.error(request, f"An error occurred during the sync: {e}")

    # --- REDIRECT LOGIC ---
    # Redirect back to the page the user was on.
    # Fallback to the 'index' page if 'next' is not in the form.
    next_url = request.POST.get("next", reverse("index"))

    # Basic security check to prevent open redirect vulnerabilities
    # This is a simple check; for high-security apps, use django.utils.http.url_has_allowed_host_and_scheme
    if not next_url or not next_url.startswith("/"):
        next_url = reverse("index")

    return redirect(next_url)

def monthly_view(request):
    # Get selected month/day from URL params for initial page load state
    selected_month = request.GET.get('month')
    selected_day = request.GET.get('day')
    
    # Fetch ALL events
    all_events = get_query(request).order_by('down_time')   
    # Process events to extract clean day and month
    processed_events = []
    for event in all_events:
        # Default values in case parsing fails
        event_day = None
        event_month = None
        
        if event.date and ' ' in str(event.date):
            # Debug: Print the original date for first few events
            if len(processed_events) < 5:
                print(f"Processing date: '{event.date}'")
            
            # Splits "12th Ashoj" into ["12th", "Ashoj"]
            parts = str(event.date).strip().split(' ', 1)
            
            if len(parts) >= 2:
                # Use regex to extract only the numbers from the day part "12th" -> "12"
                day_match = re.match(r'(\d+)', parts[0])
                if day_match:
                    event_day = str(int(day_match.group(1)))  # Convert to string for consistency
                
                event_month = parts[1].strip()
                
                # Debug output for first few events
                if len(processed_events) < 5:
                    print(f"  Extracted - Day: '{event_day}', Month: '{event_month}'")
        
        # Add the processed data to the event object itself for easy template access
        event.data_day = event_day
        event.data_month = event_month
        processed_events.append(event)
    
    # Note: Fixed typo "Aasar" -> "Asar" to match your data
    months = ['Baisakh', 'Jestha', 'Aasar', 'Shrawan', 'Bhadra', 'Ashoj', 'Kartik', 'Mangsir', 'Poush', 'Magh', 'Falgun', 'Chaitra']
    
    nepali_month_days = {
        'Baisakh': 31, 'Jestha': 31, 'Aasar': 32, 'Shrawan': 31,
        'Bhadra': 31, 'Ashoj': 30, 'Kartik': 30, 'Mangsir': 30,
        'Poush': 29, 'Magh': 29, 'Falgun': 30, 'Chaitra': 30,
    }
    
    context = {
        'months': months,
        'events': processed_events,
        'selected_month_initial': selected_month,
        'selected_day_initial': selected_day,
        'nepali_month_days_json': json.dumps(nepali_month_days),
    }
    
    return render(request, 'base/monthwise.html', context)
