#!/usr/bin/env python3
"""Source-driven bitmap fixtures, not native HOI4 screenshots or an engine emulator."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess

from PIL import Image

spec = importlib.util.spec_from_file_location("archive_preview", Path(__file__).with_name("Preview-BarradArchive.py"))
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
P = "HSM_BAR_service_gui_"
nodes = A.parse_files([A.MOD / "interface/HSM_BAR_service_gui.gui"])[0]
containers = {A.prop(n["value"], "name"): n["value"] for n in A.prop(nodes, "guiTypes")}
catalogue = json.loads(subprocess.run(
    ["node", "-e", "const b=require('./tools/Build-BarradServiceGui.cjs');process.stdout.write(JSON.stringify({actions:b.actions,cases:b.cases}));"],
    cwd=A.REPO, capture_output=True, text=True, encoding="utf-8", check=True).stdout)


def expand(text, loc, remaining=75):
    for _ in range(24):
        new = loc.get(text, text)
        new = re.sub(r"\$(\w+)\$", lambda m: loc.get(m[1], m[0]), new)
        if new == text:
            break
        text = new
    text = re.sub(r"\[\?days_mission_timeout@HSM_BAR_service_gui_\w+\|0\]", str(remaining), text)
    A.require(not re.search(r"\$HSM_BAR_|\bHSM_BAR_\w+\b", re.sub(r"£[^£]+£", "", text)), "Unresolved text: " + text)
    return text


def locale(language):
    result = {}
    for path in sorted((A.MOD / "localisation" / language).glob("HSM_BAR*.yml")):
        for key, value in re.findall(r'^\s*(\w+):\d*\s+"(.*)"\s*$', A.read(path), re.M):
            result[key] = value.replace(r"\n", "\n").replace(r'\"', '"')
    return result


def dimensions(body, default=(1000, 700)):
    size = A.prop(body, "size", [])
    return int(A.prop(size, "width", A.prop(size, "x", default[0]))), int(A.prop(size, "height", A.prop(size, "y", default[1])))


def render(language, subject, region):
    assets, loc = A.Assets(language), locale(language)
    selected = [a for a in catalogue["actions"] if a["subject"] == subject][:3]
    subjects = [0] + [i + 1 for i, case in enumerate(catalogue["cases"]) if case in ("rock", "titan", "entity", "amulet", "reactor", "echo", "compass", "plants")]
    if region != 1:
        subjects = [0, subject]
    subject_id = catalogue["cases"][subject - 1]
    getters = {
        "GetHSMBARServiceSubjectTitle": "HSM_BAR_archive_" + subject_id + "_title",
        "GetHSMBARServiceSubjectBody": "HSM_BAR_archive_" + subject_id + "_intake",
    }
    checks = []

    def label(value, values):
        if value.startswith("["):
            value = values[value.strip("[]")]
        return expand(value, loc, values.get("remaining", 75))

    def field(body, values):
        width, height = int(A.prop(body, "maxWidth")), int(A.prop(body, "maxHeight"))
        text = label(A.prop(body, "text"), values)
        image, used = A.text_image(text, assets.font(A.prop(body, "font")), assets, width, height)
        A.require(used <= height, f"{language} overflow {A.prop(body, 'name')}: {used}>{height}: {text}")
        checks.append((A.prop(body, "name"), used, height))
        return image

    def render_container(body, values):
        canvas = Image.new("RGBA", dimensions(body), (0, 0, 0, 0))
        for node in body:
            kind, child = node["key"], node["value"]
            if not isinstance(child, list):
                continue
            name = A.prop(child, "name", "")
            position = A.prop(child, "position", [])
            x, y = int(A.prop(position, "x", 0)), int(A.prop(position, "y", 0))
            if kind == "containerWindowType":
                image = render_container(child, values)
            elif kind == "gridboxType":
                image = Image.new("RGBA", dimensions(child), (0, 0, 0, 0))
                row_name = P + ("subject_row" if name == P + "subject_list" else "action_row")
                entries = subjects if name == P + "subject_list" else selected
                step = int(A.prop(A.prop(child, "slotsize"), "height"))
                for index, entry in enumerate(entries):
                    row_values = dict(values)
                    if isinstance(entry, int):
                        row_values["GetHSMBARServiceSubjectEntry"] = ("HSM_BAR_archive_" + catalogue["cases"][entry - 1] + "_title") if entry else P + "office"
                        row_values["selected"] = entry == subject
                    else:
                        row_values.update(GetHSMBARServiceActionName=entry["id"], GetHSMBARServiceActionPrice=entry["key"] + "_price", GetHSMBARServiceActionState=entry["key"] + "_remaining" if index == 0 and entry["days"] else P + "ready")
                        if entry.get("investigation"):
                            row_values.update(GetHSMBARServiceActionPrice=P + "protocol_price", GetHSMBARServiceActionState="HSM_BAR_investigation_row_pending")
                        row_values["running"] = index == 0 and not entry.get("investigation")
                        row_values["remaining"] = max(1, entry["days"] - 7)
                    image.alpha_composite(render_container(containers[row_name], row_values), (0, index * step))
            elif kind in ("background", "buttonType"):
                if name == P + "investigate" and subject_id not in ("rock", "titan", "entity", "amulet", "plants", "echo", "compass"):
                    continue
                if name in (P + "input_floor", P + "input_shield", P + "empty"):
                    continue
                if name == P + "cancel" and not values.get("running"):
                    continue
                sprite = A.prop(child, "quadTextureSprite")
                if name == P + "subject_button" and values.get("selected"):
                    sprite = "GFX_HSM_BAR_archive_index_selected"
                if name == P + "region_" + str(region):
                    sprite = "GFX_HSM_BAR_archive_tab_selected"
                image = assets.sprite(sprite, disabled=name == P + "start" and values.get("running", False)).copy()
                key = A.prop(child, "buttonText")
                if key:
                    text = label(key, values)
                    layer, used = A.text_image(text, assets.font(A.prop(child, "buttonFont")), assets, image.width - 14, image.height - 6, "center")
                    A.require(used <= image.height - 6, f"{language} button overflow {name}: {text}")
                    image.alpha_composite(layer, (7, max(3, (image.height - used) // 2)))
            elif kind == "instantTextboxType":
                if name == P + "empty":
                    continue
                image = field(child, values)
            else:
                continue
            canvas.alpha_composite(image, (x, y))
        return canvas

    canvas = render_container(containers[P + "window"], getters)
    # Validate every authored action, not just rows present in the screenshot fixture.
    row = containers[P + "action_row"]
    for action in catalogue["actions"]:
        values = dict(GetHSMBARServiceActionName=action["id"], GetHSMBARServiceActionPrice=action["key"] + "_price", GetHSMBARServiceActionState=action["key"] + "_remaining" if action["days"] else P + "ready")
        for node in row:
            if node["key"] == "instantTextboxType":
                field(node["value"], values)
    for case in catalogue["cases"]:
        text = expand("HSM_BAR_archive_" + case + "_title", loc)
        _, used = A.text_image(text, assets.font("HSM_BAR_archive_ink"), assets, 247, 28, "center")
        A.require(used <= 28, f"{language} dossier-button overflow: {text}")
        checks.append((case, used, 28))
    target = A.REPO / "art/previews" / f"HSM_BAR_service_gui_{language}_{subject_id}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(target)
    print(f"PASS: {language} / {subject_id}: {len(checks)} native-font text-fit checks; {target}")


if __name__ == "__main__":
    render("russian", 1, 1)
    render("english", 13, 2)
