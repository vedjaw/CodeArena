"""Custom template tags for CodeArena."""
import re
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import linebreaks, escape

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


@register.filter
def render_text(value):
    """Render text that may be HTML or plain text.
    If it contains HTML tags, render as-is. Otherwise apply linebreaks."""
    if not value:
        return ''
    if re.search(r'<[a-zA-Z][^>]*>', str(value)):
        return mark_safe(value)
    return mark_safe(linebreaks(escape(value)))
