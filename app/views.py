# coding: utf-8
from django.views.generic import TemplateView, ListView, View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from app.models import *
from app.forms import *
import requests
import os, json, re
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
from bs4 import BeautifulSoup
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
            threads = []
            for t in r.json()['threads']:
                thread_snippet = cache.get('thread_{}'.format(t['id']), False)
                nt = t
                if not thread_snippet:
                    rr = requests.get('https://www.googleapis.com/gmail/v1/users/me/threads/{}'.format(t['id']),
                                    params=params)
                    if rr.status_code == 200:
                        ans = rr.json()
                        thread_snippet = ans['messages'][0]['snippet']
                        cache.set('thread_{}'.format(t['id']), thread_snippet)
                        nt['snippet'] = thread_snippet
                else:
                    t['snippet'] = thread_snippet
                threads.append(nt)
            return HttpResponse(json.dumps(threads), content_type='application/json')
        else:
            return HttpResponse(r.text, content_type='application/json', status=r.status_code)

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
            ans = r.json()
            msgs = []
            for m in r.json()['messages']:
                mr  = requests.get('https://www.googleapis.com/gmail/v1/users/me/messages/{}'.format(m['id']),
                params={'access_token': request.GET.get('access_token'), 'format': request.GET.get('format')})
                if mr.status_code == 200:
                    msg = {
                        'id': m['id'],
                        'opened': True if cache.get(m['id']) else False,
                        'snippet': mr.json()['snippet']
                    }
                    if request.GET.get('format'):
                        msg_raw = str(mr.json()['raw'])
                        if request.GET.get('decode'):
                            msg = email.message_from_string(base64.urlsafe_b64decode(msg_raw))
                            if msg.is_multipart():
                                msg['raw'] = ''
                                for payload in msg.get_payload():
                                    msg['raw'] += payload.get_payload()
                            else:
                                msg['raw'] = msg.get_payload()
                        else:
                            msg['raw'] = msg_raw
                    else:
                        # msg['data'] = mr.json()
                        if 'parts' in mr.json()['payload']:
                            self.parse_parts(msg, mr.json()['payload']['parts'])
                        else:
                            self.parse_parts(msg, [mr.json()['payload'],])
                    msgs.append(msg)
            ans['messages'] = msgs
            return HttpResponse(json.dumps(ans), content_type='application/json')
        else:
            return HttpResponse(r.text, content_type='application/json', status=r.status_code)

    def parse_parts(self, msg, parts):
        for part in parts:
            if part['mimeType'] == 'text/plain':
                msg['data'] = base64.urlsafe_b64decode(str(part['body']['data'])).decode('utf-8')
                msg['original_data'] = msg['data']
                if u'\r\n>' in msg['data']:
                    msg['data'] = msg['data'].split(u'\r\n>')[0]
                msg['data'] = re.split(r'\r\n[-]+\r\n', msg['data'])[0]
                msg['data'] = re.split(r'\r\n[-]{2,}', msg['data'])[0]
                msg['data'] = re.split(r'\r\n[-]{2,}\s{2,}', msg['data'])[0]
                msg['data'] = re.split('\d{2} (?u)[\w]+ \d{4} (?u)\w{1}., \d{2}:\d{2}', msg['data'], re.U)[0]
                msg['data'] = re.split('\d{2} (?u)[\w]+ \d{4} (?u)\w{1}. \d{2}:\d{2}', msg['data'], re.U)[0]
                msg['data'] = re.split(r'\r\n\d{4}-\d{2}-\d{2}', msg['data'])[0]
                msg['data'] = re.split(r'On \d{2}.\d{2}.\d{2}, \d{2}:\d{2}', msg['data'])[0]
                msg['data'] = re.split(r'\r\n\d{2}.\d{2}.\d{2}, (?u)[\w]+', msg['data'])[0]
                msg['data'] = re.split(r'On \d{2} [\w]+ \d{4} \d{2}:\d{2}', msg['data'])[0]
                msg['data'] = re.split(r'\r\nOn [\w]+, [\w]+ \d{2}, \d{4} at \d{2}:\d{2}', msg['data'])[0]
                msg['data'] = re.split(r'\r\n\d{2}.\d{2}.\d{4}, \d{2}:\d{2},', msg['data'])[0]
                msg['data'] = re.split(r'\d{2}.\d{2}.\d{4}, \d{2}:\d{2}, \\', msg['data'])[0]
                msg['data'] = re.split(r'\r\n\s+From: \w+', msg['data'])[0]
                if u'—\r\nSent from Mailbox' in msg['data']:
                    msg['data'] = msg['data'].split(u'—\r\nSent from Mailbox')[0]
                if u'View this email\r\nin your browser' in msg['data']:
                    msg['data'] = msg['data'].split(u'View this email\r\nin your browser')[0]
                if u'\r\nBest regards' in msg['data']:
                    msg['data'] = msg['data'].split(u'\r\nBest regards')[0]
                if u'\r\nОтправлено из мобильной Почты Mail.Ru\r\n' in msg['data']:
                    msg['data'] = msg['data'].split(u'\r\nОтправлено из мобильной Почты Mail.Ru\r\n')[0]
                msg['data'] = re.split(r'[\r\n]+$', msg['data'])[0]
                return
            if part['mimeType'] == 'text/html':
                msg['type'] = 'html'
                msg['data'] = base64.urlsafe_b64decode(str(part['body']['data']))
                soup = BeautifulSoup(msg['data'])
                msg['data'] = u''.join(soup.findAll(text=True))
                msg['data'] = re.split(r'View this conversation on GetMailDone', msg['data'])[0]
                msg['data'] = re.split(r'\d{2}.\d{2}.\d{4}, \d{2}:\d{2},', msg['data'])[0]
            if 'parts' in part:
                self.parse_parts(msg, part['parts'])


import email
import base64
import simplejson
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
import hashlib
from django.core.cache import cache

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
        new_key = cache.get('max_value', 1)
        cache.set('max_value', new_key+1)

        msg = base64.b64decode(simplejson.loads(request.body.replace('\n', ''))['raw'])
        msg = email.message_from_string(msg)
        if msg.get_default_type() == 'text/plain':
            n_msg = MIMEMultipart('alternative')
            n_msg['To'] = msg['To']
            n_msg['From'] = msg['From']
            n_msg['Subject'] = msg['Subject']
            n = msg.get_payload() + '<img width="1" height="1" src="http://lab.mailburn.com/track.gif?m=mail-{}" />'.format(new_key)
            n_text = MIMEText(n, 'html')
            n_text.set_charset('utf-8')
            n_msg.attach(n_text)
        else:
            n_msg = msg
#        raise KeyError(n_msg.as_string())
#        msg.set_default_type('text/html')

        d = {'raw': base64.b64encode(n_msg.as_string())}
        d['raw'] = d['raw'].replace('+', '-')
        d = simplejson.dumps(d)
        r = requests.post('https://www.googleapis.com/gmail/v1/users/me/messages/send',
                        params=p, data=d, headers={
                'Authorization': request.META['HTTP_AUTHORIZATION'],
                'Content-Type': 'application/json'
            })
        if r.status_code == 200:
            cache.set('mail-{}'.format(new_key), r.json()['id'])
            return HttpResponse(json.dumps(r.json()), content_type='application/json')
        else:
            return HttpResponse(r.text, content_type='application/json', status=r.status_code)

class TrackView(View):
    def get(self, request, *args, **kwargs):
        if request.GET.get('m'):
            if cache.get(request.GET.get('m')):
                cache.set(cache.get(request.GET.get('m')), 'Opened')
        r = HttpResponse('')
        r['Cache-Control'] = 'no-cache'
        r['Content-Length'] = 0
        return r