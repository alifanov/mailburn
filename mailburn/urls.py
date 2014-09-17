from django.conf.urls import patterns, include, url

from app.views import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', HomeView.as_view(), name='home'),
    url(r'^track.gif$', TrackView.as_view(), name='track'),
    url(r'^oauth2callback$', auth_return.as_view(), name='google-oauth2-return'),
    # url(r'^blog/', include('blog.urls')),
    # url('', include('social.apps.django_app.urls', namespace='social')),

    url(r'^admin/', include(admin.site.urls)),
)
