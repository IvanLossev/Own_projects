from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .config import settings
from .ghl_converter import split_prompt_by_fields


def generate_prompt(business) -> dict:
    template_dir = settings.TEMPLATE_PATH.parent
    template_name = settings.TEMPLATE_PATH.name

    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template(template_name)

    context = {
        "name": business.name,
        "type": business.type,
        "address": business.address,
        "hours": business.hours,
        "services": business.services,
        "prices": business.prices,
        "faq": business.faq,
        "usp": business.usp,
        "doctors": business.doctors,
        "contact_phone": business.contact_phone,
    }

    prompt_text = template.render(**context)

    fields = split_prompt_by_fields(prompt_text)

    return {
        "prompt_text": prompt_text,
        "ghl_field_1": fields["ghl_field_1"],
        "ghl_field_2": fields["ghl_field_2"],
        "ghl_field_3": fields["ghl_field_3"],
    }