from django.core.management.base import BaseCommand, CommandError
from monitor.node_updates import update_nodes

class Command(BaseCommand):
    help = 'Updates the database with information from nodes'

    def handle(self, *args, **options):
        update_nodes()