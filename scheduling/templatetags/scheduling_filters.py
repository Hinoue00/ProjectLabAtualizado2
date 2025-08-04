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

@register.filter
def basename(value):
    """Extract the basename (filename) from a file path"""
    if not value:
        return ""
    return os.path.basename(str(value))

@register.filter
def department_codes(laboratory):
    """Get department codes for a laboratory"""
    try:
        if hasattr(laboratory, 'get_departments_codes'):
            codes = laboratory.get_departments_codes()
            return codes if codes else []
        elif hasattr(laboratory, 'department') and laboratory.department:
            # Fallback para campo antigo
            return [laboratory.department]
        return []
    except Exception as e:
        # Em caso de erro, retorna lista vazia
        return []