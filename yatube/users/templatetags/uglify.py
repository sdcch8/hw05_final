from django import template

register = template.Library()


@register.filter
def uglify(text):
    ugly_text = ''
    for char_index in range(len(text)):
        if char_index % 2 == 0:
            ugly_text += text[char_index].lower()
        else:
            ugly_text += text[char_index].upper()
    return ugly_text
