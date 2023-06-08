from django import template

register = template.Library()


@register.filter
def is_dict(value):
    return isinstance(value, dict)
