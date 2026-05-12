"""Custom template tags for CodeArena."""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key in templates."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def get_field(form, field_name):
    """Get a form field by name dynamically."""
    try:
        return form[field_name]
    except KeyError:
        return None
