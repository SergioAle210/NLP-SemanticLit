"""Tema "Puesto de Control": CSS y tema de Gradio generados desde `tokens.json` (el mismo del sistema de diseño).

`tokens.json` y `puesto.css` son copias del sistema de diseño publicado; los cambios de diseño se hacen allí y se
copian aquí. El CSS define los dos turnos como variables: el turno de día en `:root` y el de noche bajo `.dark`
(la clase que Gradio pone en la página para su modo oscuro), así que el modo oscuro de Gradio es el turno de noche.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
TOKENS = json.loads((HERE / "tokens.json").read_text(encoding="utf-8"))
FIRST, SECOND = (t["id"] for t in TOKENS["color"]["themes"])  # dia, noche

FONTS_HEAD = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700'
    '&family=Pixelify+Sans:wght@400;500;700&family=VT323&display=swap">'
)


def _value(token: dict, theme: str) -> str:
    v = token["value"]
    return v if isinstance(v, str) else v.get(theme, v[FIRST])


def _themed(theme: str) -> str:
    colors = "".join(f"--{t['name']}:{_value(t, theme)};" for t in TOKENS["color"]["tokens"])
    shadows = "".join(f"--{t['name']}:{_value(t, theme)};" for t in TOKENS["shadow"]["tokens"])
    return colors + shadows


def _shared() -> str:
    out = []
    for family in ("spacing", "radius", "border"):
        out += [f"--{t['name']}:{t['value']};" for t in TOKENS[family]["tokens"]]
    out += [f"--font-{k}:{v};" for k, v in TOKENS["type"]["families"].items()]
    return "".join(out)


def tokens_css() -> str:
    return f":root{{{_themed(FIRST)}{_shared()}}}\n.dark{{{_themed(SECOND)}}}\n"


# Ajustes sobre los controles propios de Gradio (pestañas, campos, botones, listas) para que usen los tokens.
OVERRIDES = """
html,body,.gradio-container,.app{background:var(--desk)!important;color:var(--on-desk)!important;font-family:var(--font-body)}
.gradio-container{max-width:1180px!important;margin:0 auto}
.gradio-container footer{display:none!important}
.pc-app .block,.pc-app .form,.pc-app .panel{background:transparent!important;border:0!important;box-shadow:none!important}
.pc-app .prose,.pc-app .prose *{font-family:var(--font-body)}
.pc-app label>span,.pc-app .block-label,.pc-app [data-testid=block-info]{font-family:var(--font-display)!important;font-weight:500!important;font-size:.875rem!important;letter-spacing:.06em;text-transform:uppercase;color:var(--on-desk-muted)!important;background:transparent!important}
.pc-app textarea,.pc-app input[type=text],.pc-app input[role=listbox]{font-family:var(--font-body)!important;font-size:1rem!important;line-height:1.5rem!important;background:var(--sheet)!important;color:var(--ink)!important;border:0!important;border-bottom:var(--border-doc) solid var(--ink)!important;border-radius:0!important;box-shadow:none!important;min-height:44px}
.pc-app .wrap-inner,.pc-app .secondary-wrap{background:var(--sheet)!important;border-radius:0!important}
.pc-app ul.options,.pc-app ul[role=listbox]{background:var(--paper)!important;color:var(--ink)!important;border:var(--border-doc) solid var(--ink)!important;border-radius:0!important}
.pc-app ul.options li{color:var(--ink)!important;font-family:var(--font-body)}
.pc-app ul.options li.selected,.pc-app ul.options li:hover{background:var(--hl)!important}
.pc-app button.pc-btn{border-radius:0!important;font-family:var(--font-display)!important;font-weight:700!important;font-size:1rem!important;letter-spacing:.06em;text-transform:uppercase;background:var(--sheet)!important;color:var(--ink)!important;border:var(--border-doc) solid var(--ink)!important;box-shadow:var(--shadow-press)!important;min-height:44px}
.pc-app button.pc-btn--primary{background:var(--stamp-review)!important;color:var(--on-stamp)!important}
.pc-app button.pc-btn:hover{top:-1px}
.pc-app button.pc-btn:active{transform:translateY(3px);box-shadow:0 1px 0 0 var(--ink)!important}
.pc-app .tab-container,.pc-app .tab-wrapper{border-color:var(--desk-edge)!important}
.pc-app button[role=tab]{font-family:var(--font-display)!important;font-weight:700!important;font-size:.9375rem!important;letter-spacing:.06em;text-transform:uppercase;min-height:44px;border-radius:0!important;background:var(--desk)!important;color:var(--on-desk-muted)!important;border:var(--border-doc) solid var(--desk-edge)!important;border-bottom:0!important}
.pc-app button[role=tab][aria-selected=true]{background:var(--paper)!important;color:var(--ink)!important;border-color:var(--ink)!important}
.pc-app button[role=tab]:focus-visible,.pc-app button.pc-btn:focus-visible,.pc-app textarea:focus-visible,.pc-app input:focus-visible{outline:3px solid var(--focus)!important;outline-offset:2px;box-shadow:0 0 0 6px var(--focus-halo)!important}
.pc-app details.pc-refd summary{list-style:none;display:inline-block}
.pc-app details.pc-refd summary::-webkit-details-marker{display:none}
.pc-app details.pc-refd[open] .pc-excerpt{margin-top:var(--space-2)}
.pc-app .pc-booth-head{display:flex;justify-content:space-between;align-items:center;gap:var(--space-4);padding-bottom:var(--space-3);border-bottom:var(--border-doc) solid var(--desk-edge)}
"""


def css() -> str:
    return tokens_css() + (HERE / "puesto.css").read_text(encoding="utf-8") + OVERRIDES


def gradio_theme():
    """Tema base de Gradio con los dos turnos (claro = día, oscuro = noche) para los controles que aún pinta Gradio."""
    import gradio as gr

    c = {t["name"]: t["value"] for t in TOKENS["color"]["tokens"]}
    d, n = FIRST, SECOND
    return gr.themes.Base(font=[gr.themes.Font("Courier Prime"), gr.themes.Font("Courier New"), gr.themes.Font("monospace")]).set(
        body_background_fill=c["desk"][d], body_background_fill_dark=c["desk"][n],
        body_text_color=c["on-desk"][d], body_text_color_dark=c["on-desk"][n],
        block_background_fill="transparent", block_background_fill_dark="transparent",
        block_border_width="0px", block_shadow="none", block_radius="0px",
        input_background_fill=c["sheet"][d], input_background_fill_dark=c["sheet"][n],
        input_border_color=c["ink"][d], input_border_color_dark=c["ink"][n],
        input_radius="0px", button_large_radius="0px", button_small_radius="0px",
        button_primary_background_fill=c["stamp-review"][d], button_primary_background_fill_dark=c["stamp-review"][n],
        button_primary_text_color=c["on-stamp"][d], button_primary_text_color_dark=c["on-stamp"][n],
        button_secondary_background_fill=c["sheet"][d], button_secondary_background_fill_dark=c["sheet"][n],
        button_secondary_text_color=c["ink"][d], button_secondary_text_color_dark=c["ink"][n],
        color_accent=c["stamp-review"][d],
    )
