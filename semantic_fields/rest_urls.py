from rest_framework import routers

from . import views

router = routers.SimpleRouter()
router.register(r'semanticfield', views.SemanticFieldViewSet,
                base_name="semantic_fields_semanticfield")

urlpatterns = router.urls
