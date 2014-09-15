from django.views.generic import TemplateView, ListView, View
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from app.models import *
from app.forms import *
# Create your views here.

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
        return ctx

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