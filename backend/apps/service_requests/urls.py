from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, DashboardSummaryView, RequestViewSet

router = SimpleRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("requests", RequestViewSet, basename="request")

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    *router.urls,
]
