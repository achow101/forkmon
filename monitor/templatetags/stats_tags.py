from django import template

register = template.Library()

@register.filter
def subtract(value, arg):
    return value - arg

@register.filter
def getpercent(value, arg):
    return "{0:.02f}%".format(float(value)/arg * 100)
