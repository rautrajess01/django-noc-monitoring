from django.urls import path

from . import views

urlpatterns = [
    path("", views.display, name="index"),
    path('host/<str:pk>/', views.per_host_details, name='host-details'),
    path('api/aggregate-uptime/', views.aggregate_uptime_api, name='api-aggregate-uptime'),
    path("api/host/<str:pk>/charts/", views.host_all_charts_api, name="host-charts"),
    path("daily_event_trend_api/", views.daily_event_trend_api, name="daily_event_trend_api"),
    path('sync-events/', views.sync_page_view, name='sync_page'),
    path('monthview/', views.monthly_view, name='monthview'),
   
]
