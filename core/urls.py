
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("check-code/", views.check_bet_code, name="check_bet_code"),
    path("fixtures/", views.fixtures_centre, name="fixtures_centre"),
]
