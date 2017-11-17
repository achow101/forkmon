from django.shortcuts import render
from .models import *

# Create your views here.
def index(request):
    if request.method == 'GET':
        # chainsplit bool
        is_forked = ForkState.objects.all()[0].is_currently_forked
        has_forked = ForkState.objects.all()[0].has_forked

        # node info
        nodes = Node.objects.all()

        # soft fork stats
        forks = BIP9Fork.objects.all()

        # mtp forks
        mtpforks = MTFork.objects.all()

        # height forks
        heightforks = HeightFork.objects.all()

        context = {'is_forked':is_forked, 'has_forked':has_forked, 'nodes':nodes, 'forks':forks, 'mtpforks':mtpforks, 'heightforks':heightforks}
        return render(request, 'index.html', context)