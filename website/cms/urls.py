from django.urls import path

from .views import (
    PublicWebsiteAssetView,
    PublicWebsiteIndexView,
    PublicWebsitePageView,
    WebsiteCalculatorView,
    WebsiteContentView,
    WebsiteLeadCreateView,
    WebsitePageDetailView,
)


urlpatterns = [
    path('api/v1/website/content/', WebsiteContentView.as_view(), name='website-content'),
    path('api/v1/website/pages/<slug:slug>/', WebsitePageDetailView.as_view(), name='website-page-detail'),
    path('api/v1/website/leads/', WebsiteLeadCreateView.as_view(), name='website-leads'),
    path('api/v1/website/calculator/', WebsiteCalculatorView.as_view(), name='website-calculator'),
    path('styles.css', PublicWebsiteAssetView.as_view(), {'filename': 'styles.css'}, name='website-styles'),
    path('script.js', PublicWebsiteAssetView.as_view(), {'filename': 'script.js'}, name='website-script'),
    path('about/', PublicWebsitePageView.as_view(), {'slug': 'about'}, name='website-about'),
    path('eligibility/', PublicWebsitePageView.as_view(), {'slug': 'eligibility'}, name='website-eligibility'),
    path('civil-servants/', PublicWebsitePageView.as_view(), {'slug': 'civil-servants'}, name='website-civil-servants'),
    path('calculator/', PublicWebsitePageView.as_view(), {'slug': 'calculator'}, name='website-calculator-page'),
    path('contact/', PublicWebsitePageView.as_view(), {'slug': 'contact'}, name='website-contact'),
    path('privacy/', PublicWebsitePageView.as_view(), {'slug': 'privacy'}, name='website-privacy'),
    path('terms/', PublicWebsitePageView.as_view(), {'slug': 'terms'}, name='website-terms'),
    path('', PublicWebsiteIndexView.as_view(), name='website-home'),
]
