import json

# 1. Read the dataset from a JSON file.
file_path = "C:/data/PhD/paper4/cwes_ds/dataset/enriched_cwe_dataset_v6.json"
with open(file_path, "r", encoding="utf-8") as f:
    cwe_data = json.load(f)

# 2. Build dictionaries for fast lookups.
category_map = {}
tags_map = {}

for item in cwe_data:
    cat = item["category"]
    if cat not in category_map:
        category_map[cat] = []
    category_map[cat].append(item)

    for tag in item["Additional_tags"]:
        # If tag is a dictionary, convert it into a string or extract a field.
        if isinstance(tag, dict):
            tag_value = str(tag)
        else:
            tag_value = tag

        if tag_value not in tags_map:
            tags_map[tag_value] = []
        tags_map[tag_value].append(item)

# 3. Define helper functions to retrieve data.

def get_records_by_category(category_name):
    """
    Returns all CWE records that match the specified category.
    """
    return category_map.get(category_name, [])

def get_records_by_tag(tag_value):
    """
    Returns all CWE records that have the specified tag in their Additional_tags list.
    """
    return tags_map.get(tag_value, [])

# Example usage:
def get_related_cwe_list(tags_string, target_languages: list[str] | None = None) -> str:
    # Convert the JSON-formatted string into a Python list
    # if not tags_string:
    cleaned = (
        tags_string
        .replace("TextBlock(citations=None, text=\'```json\\n", "")
        .replace("\\n```', type='text'", "")
        .replace("```json", "")
        .replace("\\n", "")
        .replace("```", "")
        .replace("', type='text')", "")
        .replace("TextBlock(text='", "")
        .replace("citations=None,", "")
        .replace(")", "")
        .replace("text='", "")
        .replace("TextBlock( ", "")
    )
    import re
    print(cleaned)
    tags_list = json.loads(cleaned)
    tags_list+=["Language Basics"]
    web_dev_records=[]
    # Iterate over each item in the list and print it
    for tag in tags_list:
        print(tag)
        web_dev_records += get_records_by_category(tag)
        web_dev_records += get_records_by_tag(tag)

# Deduplicate while preserving order
    seen = set()
    unique_records = []
    for rec in web_dev_records:
        sig = signature(rec)
        if sig not in seen:
            seen.add(sig)
            unique_records.append(rec)

    web_dev_records = unique_records

    mitigration_list=""
    # Iterate over each record and print desired fields
    counter = 0  # Initialize the counter

    # for record in web_dev_records:
    #     counter += 1  # Increment for each record
    #     mitigation:str = record["mitigation"]
    #     mitigration_list += f"[\"Rules#{counter}: {mitigation}\"],\n"

    for record in web_dev_records:
        counter += 1  # Increment for each record

        mitigations = record.get("mitigations", {})
        general_rules = mitigations.get("general_rules", [])
        lang_specific = mitigations.get("language_specific", {})
        code_review = record.get("code_review_checklist", [])
        finetune_examples = record.get("finetune_examples", [])

        # 1) General Mitigation
        if general_rules:
            mitigration_list += "## General Mitigation\n"
            for rule in general_rules:
                mitigration_list += f"[\"Rules#{counter}: {rule.strip()}\"]\n"
                counter += 1
            mitigration_list += "\n"

        # 2) Language-Specific Mitigation
        # Determine which languages to include
        if target_languages:
            selected_langs = [
                k for k in lang_specific.keys()
                if k.lower() in [t.lower() for t in target_languages]
            ]
        else:
            selected_langs = list(lang_specific.keys())


        for lang in selected_langs:
            lang_data = lang_specific.get(lang, {})
            guidance = lang_data.get("guidance", [])
            checklist = lang_data.get("checklist", [])

            mitigration_list += f"## {lang.upper()} Specific Mitigation\n"
            if guidance:
                mitigration_list += "### Guidance\n"
                for g in guidance:
                    mitigration_list += f"- {g.strip()}\n"
            if checklist:
                mitigration_list += "\n### Checklist\n"
                for c in checklist:
                    mitigration_list += f"- {c.strip()}\n"
            mitigration_list += "\n"

        # 3) Code Review Checklist
        if code_review:
            mitigration_list += "## Code Review Checklist\n"
            for item in code_review:
                mitigration_list += f"- {item.strip()}\n"
            mitigration_list += "\n"

        # 4) Finetune Examples
        if finetune_examples:
            # Normalize target languages for comparison
            if target_languages:
                target_set = set(lang.lower() for lang in target_languages)
            else:
                target_set = set()  # empty means include all

            # Filter examples
            if target_set:
                filtered_examples = [
                    ex for ex in finetune_examples
                    if (ex.get("language") or "").strip().lower() in target_set
                ]
            else:
                filtered_examples = finetune_examples  # include all if no filter

            # Only add section if examples exist after filtering
            if filtered_examples:
                mitigration_list += "## Finetune Examples\n"
                for i, ex in enumerate(filtered_examples, start=1):
                    ex_lang = (ex.get("language") or "generic").strip()
                    mitigration_list += f"### Example {i} ({ex_lang})\n"

                    instruction = (ex.get("instruction") or "").strip()
                    input_code = (ex.get("input") or "").strip()
                    output_code = (ex.get("output") or "").strip()

                    if instruction:
                        mitigration_list += f"Instruction: {instruction}\n"
                    if input_code:
                        mitigration_list += f"Input:\n```\n{input_code}\n```\n"
                    if output_code:
                        mitigration_list += f"Ideal Output:\n```\n{output_code}\n```\n"

                mitigration_list += "\n"



    return mitigration_list

def signature(obj):
    """Create a stable, hashable signature for any JSON-like object."""
    try:
        # Fast path: canonical JSON with sorted keys
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=repr)
    except TypeError:
        # Fallback: recursive freeze for odd types
        return _freeze(obj)

def _freeze(obj):
    if isinstance(obj, dict):
        return tuple((k, _freeze(v)) for k, v in sorted(obj.items()))
    if isinstance(obj, list) or isinstance(obj, tuple):
        return tuple(_freeze(x) for x in obj)
    if isinstance(obj, set):
        return tuple(sorted(_freeze(x) for x in obj))
    # Last resort: use repr for anything else
    return obj if isinstance(obj, (str, int, float, bool, type(None))) else repr(obj)

if __name__ == "__main__":
    # Choose one or more languages to include
    selected_languages = ["java","C"]
    tag_list_response = "[\"Language Basics\",\"Data safety and security\",\"Web Development, API & Web Services\"]"

    # Generate mitigation text for the selected languages only
    mitigation_text = get_related_cwe_list(tag_list_response, target_languages=selected_languages)

    print(f"\n{mitigation_text}")
