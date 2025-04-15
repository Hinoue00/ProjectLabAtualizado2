# scheduling/templatetags/scheduling_tags.py
from django import template

register = template.Library()

@register.filter
def split_materials(value):
    """
    Split materials string safely, stripping whitespace
    
    Args:
        value (str): String of materials separated by commas
    
    Returns:
        list: List of stripped materials
    """
    if not value:
        return []
    
    return [material.strip() for material in value.split(',') if material.strip()]