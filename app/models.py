from django.db import models
from mailer import Mailer, Message

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
        msg = Message(
            From='info@mailburn.com',
            To=self.to
        )
        msg.Subject = self.subject
        msg.Html = self.text + '<img src="http://lab.mailburn.com/track.jpg?m={}" />'.format(self.pk)

        sender = Mailer('localhost')
        sender.send(msg)

    def __unicode__(self):
        return u'{}: {}'.format(self.to, self.subject)

    class Meta:
        verbose_name = u'Mail message'
        verbose_name_plural = u'Mail messages'
