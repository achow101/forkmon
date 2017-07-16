from django.shortcuts import render
from .models import *

# Create your views here.
def index(request):
    if request.method == 'GET':
        # chainsplit bool
        chain_split = ForkState.objects.all()[0].has_forked

        # node info
        nodes = Node.objects.all()

        context = {'chain_split':chain_split, 'nodes':nodes}
        return render(request, 'index.html', context)