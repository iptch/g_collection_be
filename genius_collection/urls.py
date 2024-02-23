from django.urls import include, path
from django.contrib import admin
from rest_framework import routers, permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from genius_collection.core import views
from django.views.decorators.csrf import csrf_exempt


router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'cards', views.CardViewSet)

schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version='v1',
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('overview/', views.OverviewViewSet.as_view()),
    path('distribute/', views.DistributeViewSet.as_view()),
    path('upload-picture/', csrf_exempt(views.upload_picture))
]
