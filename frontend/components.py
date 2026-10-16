"""Builders for each tab of the UI. Each one wires widgets to the orchestrator."""

from __future__ import annotations

from pathlib import Path

import gradio as gr

from backend.interfaces import ChatTurn
from backend.orchestrator import Orchestrator, QuizSession
from frontend import formatting as fmt


def documents_tab(orch: Orchestrator) -> None:
    with gr.Tab("📄 Documents"):
        gr.Markdown("Upload lecture slides, readings or briefing documents (PDF or PPTX).")
        files = gr.File(file_count="multiple", file_types=[".pdf", ".pptx"],
                        label="Course materials")
        ingest_btn = gr.Button("Ingest", variant="primary")
        status = gr.Markdown()
        table = gr.Dataframe(headers=["File", "Chunks"], value=fmt.documents_rows(orch.documents()),
                             interactive=False, label="Ingested documents")

        def ingest(paths):
            if not paths:
                return "Choose at least one file first.", fmt.documents_rows(orch.documents())
            result = orch.upload([Path(p) for p in paths])
            icon = "✅" if result.ok else "⚠️"
            return f"{icon} {result.message}", fmt.documents_rows(result.documents)

        ingest_btn.click(ingest, inputs=files, outputs=[status, table])


def ask_tab(orch: Orchestrator) -> None:
    with gr.Tab("💬 Ask"):
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(type="messages", height=460, label="Study Buddy")
                with gr.Row():
                    question = gr.Textbox(placeholder="Ask about your course materials…",
                                          show_label=False, scale=5, autofocus=True,
                                          elem_classes="no-scrollbar")
                    send = gr.Button("Send", variant="primary", scale=1)
                clear = gr.Button("Clear chat", size="sm")
                with gr.Accordion("Sources for the last answer", open=True):
                    sources = gr.Markdown("_Ask a question to see its sources._")
            with gr.Column(scale=2):
                gr.Markdown("### Compare: Ctrl+F baseline\n"
                            "<sub>Exact keyword search over the raw text: the non-AI way.</sub>")
                keyword = gr.Textbox(label="Keyword", placeholder="e.g. checkpoint",
                                     elem_classes="no-scrollbar")
                search = gr.Button("Search", size="sm")
                hits = gr.Markdown()

        def respond(message, history):
            turns = [ChatTurn(m["role"], m["content"]) for m in history
                     if isinstance(m.get("content"), str)]
            answer = orch.ask(message, turns)
            history = history + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": fmt.answer_markdown(answer)},
            ]
            # Run the baseline on the same question so the contrast is visible.
            baseline = fmt.hits_markdown(message, orch.ctrl_f(message))
            return "", history, fmt.sources_markdown(answer.citations), message, baseline

        outputs = [question, chatbot, sources, keyword, hits]
        send.click(respond, inputs=[question, chatbot], outputs=outputs)
        question.submit(respond, inputs=[question, chatbot], outputs=outputs)
        clear.click(lambda: ([], "_Ask a question to see its sources._"),
                    outputs=[chatbot, sources])

        def run_search(kw):
            return fmt.hits_markdown(kw, orch.ctrl_f(kw))

        search.click(run_search, inputs=keyword, outputs=hits)
        keyword.submit(run_search, inputs=keyword, outputs=hits)


def quiz_tab(orch: Orchestrator) -> None:
    with gr.Tab("📝 Quiz"):
        session = gr.State(None)
        with gr.Row():
            topic = gr.Textbox(label="Topic", placeholder="e.g. evaluation metrics", scale=3,
                               elem_classes="no-scrollbar")
            count = gr.Slider(3, 10, value=5, step=1, label="Questions", scale=2)
        generate = gr.Button("Generate quiz", variant="primary")
        status = gr.Markdown()

        with gr.Group(visible=False) as quiz_box:
            progress = gr.Markdown()
            question = gr.Markdown()
            answer = gr.Textbox(label="Your answer", elem_classes="no-scrollbar")
            submit = gr.Button("Submit", variant="primary")
            feedback = gr.Markdown()
            next_btn = gr.Button("Next question", visible=False)
        summary = gr.Markdown()

        def show_question(s: QuizSession):
            q = s.current
            return (fmt.quiz_progress(s), fmt.quiz_question(q),
                    gr.update(value="", interactive=True), gr.update(interactive=True),
                    "", gr.update(visible=False))

        question_outputs = [progress, question, answer, submit, feedback, next_btn]

        def on_generate(t, n):
            s, msg = orch.start_quiz(t, int(n))
            if s is None:
                return (None, f"⚠️ {msg}", gr.update(visible=False), "",
                        *[gr.update()] * len(question_outputs))
            return (s, msg, gr.update(visible=True), "", *show_question(s))

        generate.click(on_generate, inputs=[topic, count],
                       outputs=[session, status, quiz_box, summary, *question_outputs])

        def on_submit(s: QuizSession, user_answer):
            if s is None or s.finished:
                return gr.update(), gr.update(), gr.update(), gr.update()
            q = s.current
            grade = orch.submit_answer(s, user_answer)
            label = "See results" if s.finished else "Next question"
            return (fmt.quiz_feedback(grade, q), gr.update(interactive=False),
                    gr.update(interactive=False), gr.update(visible=True, value=label))

        submit.click(on_submit, inputs=[session, answer],
                     outputs=[feedback, answer, submit, next_btn])
        answer.submit(on_submit, inputs=[session, answer],
                      outputs=[feedback, answer, submit, next_btn])

        def on_next(s: QuizSession):
            if s.finished:
                return (gr.update(visible=False), fmt.quiz_summary(orch.quiz_summary(s)),
                        *[gr.update()] * len(question_outputs))
            return (gr.update(visible=True), "", *show_question(s))

        next_btn.click(on_next, inputs=session,
                       outputs=[quiz_box, summary, *question_outputs])


def log_tab(orch: Orchestrator) -> None:
    with gr.Tab("🧾 AI Log"):
        gr.Markdown("Every AI interaction is recorded for transparency and evaluation "
                    f"(`{orch.log.path.name}`). Most recent last.")
        refresh = gr.Button("Refresh", size="sm")

        def load():
            rows = []
            for e in orch.log.tail(50):
                text = e.get("question") or e.get("topic") or ""
                rows.append([e["timestamp"], e["mode"], text, e["backend"].get("model", "")])
            return rows

        # A callable value is re-evaluated on every page load.
        table = gr.Dataframe(value=load, headers=["Time (UTC)", "Mode", "Input", "Model"],
                             interactive=False, wrap=True)
        refresh.click(load, outputs=table)
