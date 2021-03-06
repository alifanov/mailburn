from django.conf.urls import patterns, include, url

from app.views import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', HomeView.as_view(), name='home'),
    url(r'^decode/$', Decode64View.as_view(), name='decode'),
    url(r'^track.gif$', TrackView.as_view(), name='track'),
    url(r'^api/threads/$', ThreadsList.as_view(), name='api-threads-list'),
    url(r'^api/threads/(?P<threadId>\w+)/$', ThreadsGet.as_view(), name='api-threads-get'),
    url(r'^api/messages/send/$', MessageSend.as_view(), name='api-message-send'),
    # url(r'^oauth2callback$', auth_return, name='google-oauth2-return'),
    # url(r'^blog/', include('blog.urls')),
    url('', include('social.apps.django_app.urls', namespace='social')),

    url(r'^admin/', include(admin.site.urls)),
)
