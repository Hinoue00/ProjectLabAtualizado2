from django import template
import os

register = template.Library()

@register.filter
def endswith(value, arg):
    """Check if the string ends with the given argument"""
    if not value:
        return False
    return str(value).lower().endswith(arg.lower())

@register.filter
def lower(value):
    """Convert a string to lowercase"""
    if not value:
        return ""
    return str(value).lower()