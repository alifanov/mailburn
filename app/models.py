from django.db import models
from mailer import Mailer, Message
from django.core.mail import EmailMessage

# Create your models here.

STATUS_CHOICES = (
    ('S', u'Send'),
    ('R', u'Readed')
)

class Mail(models.Model):
    subject = models.CharField(max_length=256, verbose_name=u'Subject')
    text = models.TextField(verbose_name=u'Body')
    to = models.CharField(max_length=256, verbose_name=u'To')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, verbose_name=u'Status', default='S')

    def send(self):
        t = self.text + '<img width="1" height="1" src="http://lab.mailburn.com/track.jpg?m={}" />'.format(self.pk)
        msg = EmailMessage(
            self.subject,
            t,
            'info@mailburn.com',
            to=[self.to,]
        )
        msg.content_subtype = 'html'
        msg.send()

    def __unicode__(self):
        return u'{}: {}'.format(self.to, self.subject)

    class Meta:
        verbose_name = u'Mail message'
        verbose_name_plural = u'Mail messages'
