from django import template

register = template.Library()

@register.filter
def split(value, delimiter=None):
    if not value:
        return []
    if delimiter == r'\n':
        return value.split('\n')
    return value.split(delimiter or ",")