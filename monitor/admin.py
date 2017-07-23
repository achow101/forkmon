from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(ForkState)
admin.site.register(Block)
admin.site.register(Node)
admin.site.register(BIP9Fork)
admin.site.register(MTFork)