import re


def split_prompt_by_fields(prompt_text: str) -> dict:
    fields = {"ghl_field_1": "", "ghl_field_2": "", "ghl_field_3": ""}

    pattern = re.compile(r"^#\s*FIELD\s*(\d)", re.MULTILINE)
    matches = list(pattern.finditer(prompt_text))

    if not matches:
        fields["ghl_field_1"] = prompt_text.strip()
        return fields

    for i, match in enumerate(matches):
        field_num = int(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(prompt_text)
        content = prompt_text[start:end].strip()

        key = f"ghl_field_{field_num}"
        if key in fields:
            fields[key] = content

    return fields