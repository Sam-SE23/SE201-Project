"""AI Study Buddy: Gradio entry point.

Run from the repo root:  python -m frontend.app
"""

from __future__ import annotations

import logging

import gradio as gr

from backend.orchestrator import Orchestrator
from frontend import components
from frontend import formatting as fmt

DISCLOSURE = ("⚠️ **AI-generated content.** Answers and quiz questions are produced by AI "
              "from your uploaded materials and may contain mistakes. "
              "Always check the cited sources.")

# Injected into <head> verbatim. css= would be scoped to .gradio-container,
# and the Settings modal may sit outside it.
CUSTOM_HEAD = """<style>
/* Gradio has no options to remove these built-in Settings sections, so hide
   everything after the theme switch (Language, PWA, Screen Studio). */
.banner-wrap:has(.theme-buttons) ~ .banner-wrap { display: none !important; }

/* Gradio textareas force overflow-y: scroll. Hide the scrollbar but keep
   wheel scrolling. */
.no-scrollbar textarea { scrollbar-width: none; }
.no-scrollbar textarea::-webkit-scrollbar { display: none; }

#status-line, #status-line * { overflow: visible !important; }
</style>"""


def build_app(orch: Orchestrator) -> gr.Blocks:
    with gr.Blocks(title="AI Study Buddy", head=CUSTOM_HEAD) as app:
        gr.Markdown("# 📚 AI Study Buddy\nAsk questions about your course materials "
                    "and test yourself, with every answer cited back to the source.")
        gr.Markdown(DISCLOSURE)
        gr.Markdown(fmt.status_line(orch.status, orch.warnings),
                    elem_id="status-line", container=False)
        components.documents_tab(orch)
        components.ask_tab(orch)
        components.quiz_tab(orch)
        components.log_tab(orch)
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    build_app(Orchestrator()).launch()


if __name__ == "__main__":
    main()
