from django.urls import include, path
from django.contrib import admin
from rest_framework import routers
from genius_collection.core import views

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'cards', views.CardViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
