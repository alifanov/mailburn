from django.db import models

# Create your models here.

STATUS_CHOICES = (
    ('S', u'Send'),
    ('R', u'Readed')
)

class Mail(models.Model):
    subject = models.CharField(max_length=256, verbose_name=u'Subject')
    text = models.TextField(verbose_name=u'Body')
    to = models.TextField(verbose_name=u'To')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, verbose_name=u'Status')

    def __unicode__(self):
        return u'{}: {}'.format(self.to, self.subject)

    class Meta:
        verbose_name = u'Mail message'
        verbose_name_plural = u'Mail messages'
