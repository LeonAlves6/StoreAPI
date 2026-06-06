from rest_framework import serializers
from .models import ContactMessage
from .validators import validate_message_length, validate_subject_length

class ContactSerializer(serializers.ModelSerializer):
    message = serializers.CharField(validators=[validate_message_length])
    subject = serializers.CharField(validators=[validate_subject_length])

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']

    def validate_email(self, value):
        return value.lower()
