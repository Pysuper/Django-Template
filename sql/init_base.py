import os

import django
from faker import Faker

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()


faker = Faker()
