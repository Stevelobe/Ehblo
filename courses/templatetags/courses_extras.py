# courses/templatetags/courses_extras.py

from django import template
import os

register = template.Library()

@register.filter
def lower_class_name(obj):
    if obj:
        return obj.__class__.__name__.lower()
    return ''

@register.filter
def split_filename(filepath):
    """
    Returns just the filename from a full file path.
    Useful for displaying user-friendly file names.
    """
    if filepath:
        return os.path.basename(filepath)
    return ''