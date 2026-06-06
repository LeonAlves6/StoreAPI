from django.db import models

# Create your models here.
class ContactMessage(models.Model):
    name = models.CharField(max_length=255, verbose_name='Nome')
    email = models.EmailField(verbose_name='Email')
    subject = models.CharField(max_length=255, verbose_name='Assunto')
    message = models.TextField(verbose_name='Mensagem')
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} - {self.subject}'
    
    class Meta:
        db_table = 'contact_messages'
        ordering = ['-sent_at']
        verbose_name = 'Mensagem de Contato'
        verbose_name_plural = 'Mensagens de Contato'