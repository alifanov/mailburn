from django.views.generic import TemplateView, ListView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required, permission_required
from app.models import *
# Create your views here.

class HomeView(ListView):
    template_name = 'home.html'
    model = Mail
    queryset = Mail.objects.all()
    context_object_name = 'mails'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(HomeView, self).dispatch(*args, **kwargs)
