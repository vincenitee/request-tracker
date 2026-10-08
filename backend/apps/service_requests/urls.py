from rest_framework.routers import SimpleRouter

from .views import CategoryViewSet, RequestViewSet

router = SimpleRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("requests", RequestViewSet, basename="request")

urlpatterns = router.urls
