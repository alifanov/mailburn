from django.views.generic import TemplateView, ListView, View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from app.models import *
from app.forms import *
import requests
import os, json
import httplib2

from apiclient.discovery import build
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.conf import settings
from oauth2client import xsrfutil
from oauth2client.client import flow_from_clientsecrets
from oauth2client.django_orm import Storage
# Create your views here.
CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), '..', 'client_secrets.json')

FLOW = flow_from_clientsecrets(
    CLIENT_SECRETS,
    scope=[
        'https://www.googleapis.com/auth/plus.me',
        'https://mail.google.com/',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify',
    ],
    redirect_uri='http://lab.mailburn.com/oauth2callback')

class HomeView(ListView):
    template_name = 'home.html'
    model = Mail
    queryset = Mail.objects.order_by('-pk')
    context_object_name = 'mails'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(HomeView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = MailForm(request.POST)
        if form.is_valid():
            m = form.save()
            m.send()
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(HomeView, self).get_context_data(**kwargs)
        ctx['form'] = MailForm()
        if self.request.user.social_auth.filter(provider='google-oauth2').exists():
            ctx['token'] = self.request.user.social_auth.filter(provider='google-oauth2')[0].extra_data['access_token']
#        if r.status_code == 200:
#            raise KeyError
#            ctx['threads'] = r.json()
        return ctx

@login_required
def auth_return(request):
    if not xsrfutil.validate_token(settings.SECRET_KEY, request.REQUEST['state'],
                                 request.user):
        return  HttpResponseBadRequest()
    credential = FLOW.step2_exchange(request.REQUEST)
    storage = Storage(CredentialsModel, 'id', request.user, 'credential')
    storage.put(credential)
    return HttpResponseRedirect("/")

class ThreadsList(View):
    def get(self, request, *args, **kwargs):
        params = {
            'access_token': request.GET.get('access_token')
        }
        if request.GET.get('maxResults'):
            params['maxResults'] = request.GET.get('maxResults')
        if request.GET.get('pageToken'):
            params['pageToken'] = request.GET.get('pageToken')
        if request.GET.get('q'):
            params['q'] = request.GET.get('q')
        r = requests.get('https://www.googleapis.com/gmail/v1/users/me/threads/',
                        params=params)
        if r.status_code == 200:
            return HttpResponse(json.dumps(r.json()['threads']), content_type='application/json')
        else:
            return HttpResponse(r.text, content_type='application/json', status=r.status_code)
        return HttpResponse('')

class ThreadsGet(View):
    def get(self, request, *args, **kwargs):
        params = {
            'access_token': request.GET.get('access_token')
        }
        if request.GET.get('maxResults'):
            params['maxResults'] = request.GET.get('maxResults')
        if request.GET.get('pageToken'):
            params['pageToken'] = request.GET.get('pageToken')
        if request.GET.get('q'):
            params['q'] = request.GET.get('q')
        r = requests.get('https://www.googleapis.com/gmail/v1/users/me/threads/{}'.format(kwargs.get('threadId')),
                        params=params)
        if r.status_code == 200:
            msgs = []
            for m in r.json()['messages']:
                mr  = requests.get('https://www.googleapis.com/gmail/v1/users/me/messages/{}'.format(m['id']),
                params={'access_token': request.GET.get('access_token')})
                if request.GET.get('format'):
                    params['format'] = request.GET.get('format')
                if mr.status_code == 200:
                    msgs.append({
                        'id': m['id'],
                        'opened': False,
                        'snippet': m['snippet'],
                        'raw': mr.json()
                    })
            return HttpResponse(json.dumps(r.json()['messages']), content_type='application/json')
        else:
            return HttpResponse(r.text, content_type='application/json', status=r.status_code)
        return HttpResponse('')

class MessageSend(View):

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(MessageSend, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        p = {'access_token': request.GET.get('access_token')}
        if request.GET.get('threadId'):
            p['threadId'] = request.GET.get('threadId')
        if request.GET.get('key'):
            p['key'] = request.GET.get('key')
        r = requests.post('https://www.googleapis.com/gmail/v1/users/me/messages/send',
                        params=p, data=request.body, headers={
                'Authorization': request.META['HTTP_AUTHORIZATION'],
                'Content-Type': 'application/json'
            })
        if r.status_code == 200: return HttpResponse(json.dumps(r.json()), content_type='application/json')
        else:
            return HttpResponse(r.text, content_type='application/json', status=r.status_code)

class TrackView(View):
    def get(self, request, *args, **kwargs):
        if request.GET.get('m'):
            m = Mail.objects.get(pk=request.GET.get('m'))
            m.status = 'R'
            m.save()
        r = HttpResponse('')
        r['Cache-Control'] = 'no-cache'
        r['Content-Length'] = 0
        return r