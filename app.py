"""AI Imposter Arena: a streaming Gradio front-end for the existing game engine.

Run: python app.py
Live mode uses the existing main.py phases. Demo mode never calls an API.
"""

from __future__ import annotations

import html
import os
from pathlib import Path
from queue import Queue
from threading import Thread
from time import sleep

import gradio as gr

from game_logic import add_clue, add_vote, resolve_game
from input_and_validation import user_input
from players import setup_players

ROOT = Path(__file__).resolve().parent
NAMES = ("ChatGPT", "Claude", "Gemini", "Groq")
INITIAL_ORDER = list(NAMES)
PRESETS = {
    "Animals · Penguin": ("Animals", "Penguin"),
    "Food · Burger": ("Food", "Burger"),
    "Cars · Ferrari": ("Cars", "Ferrari"),
    "Nature · Volcano": ("Nature", "Volcano"),
    "Sports · Tennis": ("Sports", "Tennis"),
}
TAGS = {"ChatGPT": "OPENAI", "Claude": "ANTHROPIC", "Gemini": "GOOGLE", "Groq": "GROQ"}
INITIALS = {"ChatGPT": "G", "Claude": "C", "Gemini": "✦", "Groq": "⚡"}


def esc(text: object) -> str:
    """Escape untrusted model/user text before embedding in our HTML."""
    return html.escape(str(text), quote=True)


def avatar(name: str) -> str:
    cls = {"ChatGPT": "openai", "Claude": "claude", "Gemini": "gemini", "Groq": "groq"}.get(name, "unknown")
    return f'<span class="bot-icon {cls}">{esc(INITIALS.get(name, "?"))}</span>'


def header() -> str:
    return """
    <section class="hero">
      <div class="hero-copy">
        <div class="eyebrow"><span class="live-orb"></span> THE SOCIAL DEDUCTION LAB <span class="eyebrow-sep">/</span> AI VS AI</div>
        <h1>FOUR MINDS.<br><em>ONE IMPOSTOR.</em></h1>
        <p>Four AI models. One secret word. A single liar in the room.<br>Watch them drop clues, cast suspicion, and turn on each other.</p>
        <div class="hero-tags"><span>● 4 CONTENDERS</span><span>◇ 1 HIDDEN IMPOSTOR</span><span>↗ LIVE AI REASONING</span></div>
      </div>
      <div class="hero-art" aria-hidden="true">
        <div class="orbit orbit-one"></div><div class="orbit orbit-two"></div>
        <div class="hero-core">?</div>
        <div class="orbit-avatar ava-one">G</div><div class="orbit-avatar ava-two">C</div>
        <div class="orbit-avatar ava-three">✦</div><div class="orbit-avatar ava-four">⚡</div>
        <span class="hero-art-label">IDENTITY UNKNOWN</span>
      </div>
    </section>
    """


def phase_panel(phase: str, n_clues: int = 0, n_votes: int = 0, mode: str = "LIVE", category: str = "", error: str = "") -> str:
    definitions = [("01", "CLUE ROUND"), ("02", "SECRET BALLOT"), ("03", "THE REVEAL")]
    stage = {"idle": 0, "clues": 1, "voting": 2, "complete": 3, "error": -1}.get(phase, 0)
    progress = {"idle": 0, "clues": 6 + n_clues * 12, "voting": 54 + n_votes * 10, "complete": 100, "error": 0}[phase]
    status = {"idle": "READY FOR YOUR NEXT MATCH", "clues": "PLAYERS ARE DROPPING CLUES", "voting": "BALLOTS ARE BEING CAST", "complete": "MATCH COMPLETE", "error": "MATCH INTERRUPTED"}[phase]
    badge = '<span class="pill pill-demo">DEMO / NO API</span>' if mode == "DEMO" else '<span class="pill pill-live">LIVE MODE</span>'
    steps = []
    for index, (number, label) in enumerate(definitions, 1):
        state = "completed" if stage > index else "active" if stage == index else "future"
        steps.append(f'<div class="step {state}"><span class="step-number">{number}</span><span class="step-name">{label}</span></div>')
    message = f'<div class="status-error">{esc(error)}</div>' if error else ""
    return f"""
    <section class="phase-card panel">
      <div class="phase-heading"><div><div class="micro-label">MATCH STATUS</div><div class="phase-title">{esc(status)}</div></div>{badge}</div>
      <div class="progress-track"><div class="progress-fill" style="width:{progress}%"></div></div>
      <div class="phase-bottom"><span>{'A new round is one click away' if phase == 'idle' else esc(category) if category else 'AI imposter game'}</span><span>{n_clues}/4 CLUES · {n_votes}/4 VOTES</span></div>
      <div class="steps">{''.join(steps)}</div>{message}
    </section>"""


def clue_panel(order: list[str], clues: list[dict], revealed: bool = False, imposter: str | None = None) -> str:
    known = {item["name"]: item["clue"] for item in clues}
    tiles = []
    for index, name in enumerate(order, 1):
        clue = known.get(name)
        cls = "ready" if clue else "pending"
        role = '<span class="role-chip impostor">IMPOSTOR</span>' if revealed and name == imposter else '<span class="role-chip innocent">INNOCENT</span>' if revealed else ''
        show_clue = f'<strong class="clue-text">{esc(clue)}</strong>' if clue else '<span class="waiting-word"><i></i><i></i><i></i></span>'
        state = 'CLUE SUBMITTED' if clue else 'AWAITING TURN'
        tiles.append(f"""
          <article class="player-card {cls} {'exposed' if revealed and name == imposter else ''}">
           <div class="player-top"><span class="player-index">PLAYER {index:02d}</span><span class="card-state">{'●' if clue else '○'} {state}</span></div>
           <div class="player-identity">{avatar(name)}<div class="player-name-box"><b>{esc(name)}</b><small>{esc(TAGS.get(name, 'AI MODEL'))}</small></div></div>
           <div class="clue-field"><span class="clue-label">ONE-WORD CLUE</span>{show_clue}</div>
           {role}
          </article>""")
    return f'<section class="board"><div class="section-heading"><div><div class="micro-label">ROUND 01 / THE EVIDENCE</div><h2>THE CLUE BOARD</h2></div><span class="section-counter">{len(known):02d} / 04 REVEALED</span></div><div class="player-grid">{"".join(tiles)}</div></section>'


def voting_panel(order: list[str], votes: list[dict], revealed: bool = False) -> str:
    known = {entry["name"]: entry for entry in votes}
    tiles = []
    for index, name in enumerate(order, 1):
        vote = known.get(name)
        if revealed and vote:
            middle = (f'<div class="ballot-accuse">VOTES FOR <b>{esc(vote["vote"])}</b></div>'
                      f'<p class="ballot-reason">“{esc(vote["reason"])}”</p>')
            chip = '<span class="ballot-badge revealed">REVEALED</span>'
        elif vote:
            middle = '<div class="ballot-seal">◈<span>BALLOT LOCKED</span></div>'
            chip = '<span class="ballot-badge">SEALED</span>'
        else:
            middle = '<div class="ballot-seal faded">◇<span>AWAITING VOTE</span></div>'
            chip = '<span class="ballot-badge muted">PENDING</span>'
        tiles.append(f'<article class="ballot-card"><div class="ballot-header">{avatar(name)}<b>{esc(name)}</b>{chip}</div>{middle}</article>')
    footer = 'Votes are secret until all four AIs have submitted.' if not revealed else 'All ballots are in. Every accusation is now public.'
    return (f'<section class="board"><div class="section-heading"><div><div class="micro-label">ROUND 02 / THE ACCUSATIONS</div>'
            f'<h2>THE VOTING ROOM</h2></div><span class="section-counter">{len(known):02d} / 04 BALLOTS CAST</span></div>'
            f'<div class="ballot-grid">{"".join(tiles)}</div><div class="section-note">◇ {esc(footer)}</div></section>')


def result_panel(result: dict | None = None, imposter: str = "", word: str = "", err: str = "") -> str:
    if err:
        return '<section class="results-card panel"><div class="micro-label">FINAL VERDICT</div><div class="result-placeholder">The match was interrupted. Review the status message above and try again.</div></section>'
    if result is None:
        return '<section class="results-card panel"><div class="micro-label">FINAL VERDICT</div><div class="result-placeholder"><span class="placeholder-glyph">◎</span><b>THE VERDICT IS SEALED</b><span>The winner, secret word and impostor will be revealed here after voting.</span></div></section>'
    imposter_wins = result["winner"] == "Imposter"
    title = "THE IMPOSTOR ESCAPES" if imposter_wins else "THE IMPOSTOR IS CAUGHT"
    desc = result["final_statement"]
    status_cls = "villain" if imposter_wins else "heroes"
    summary = '<span class="result-kicker">✦ IMPOSTOR VICTORY</span>' if imposter_wins else '<span class="result-kicker">✦ INNOCENTS VICTORY</span>'
    bar_rows = []
    for name, score in sorted(result["scores"].items(), key=lambda item: item[1], reverse=True):
        pct = max(0, min(100, score / 4 * 100))
        is_suspect = name in result["suspects"]
        bar_rows.append(f'<div class="score-entry"><div class="score-header"><span>{esc(name)}{" <em>TOP SUSPECT</em>" if is_suspect else ""}</span><b>{score} <small>VOTES</small></b></div><div class="score-track"><div class="score-bar" style="width:{pct}%"></div></div></div>')
    return f"""
    <section class="results-card panel resolved {status_cls}">
     <div class="micro-label">ROUND 03 / THE FINAL VERDICT</div>
     <div class="verdict-layout"><div class="verdict-copy">{summary}<h2>{title}</h2><p>{esc(desc)}</p>
     <div class="reveal-pills"><span>IMPOSTOR <b>{esc(imposter)}</b></span><span>SECRET WORD <b>{esc(word)}</b></span>
     <span>{'TIE / NO ELIMINATION' if result['is_tie'] else 'ELIMINATED: ' + esc(result['suspects'][0])}</span></div></div>
     <div class="tally"><div class="micro-label">FINAL VOTE TALLY</div>{''.join(bar_rows)}</div></div>
    </section>"""


def activity_panel(events: list[tuple[str, str]] | None = None) -> str:
    events = events or [("idle", "Set the category and secret word, then launch a match."), ("idle", "Or try the built-in demo without API keys.")]
    rows = []
    for index, (kind, line) in enumerate(reversed(events[-8:])):
        marker = "✓" if kind == "success" else "!" if kind == "error" else "◌" if kind == "idle" else "→"
        rows.append(f'<li class="activity-row {esc(kind)}"><span class="activity-marker">{marker}</span><span>{esc(line)}</span></li>')
    return '<section class="activity panel"><div class="micro-label">MATCH ACTIVITY</div><ul>' + ''.join(rows) + '</ul></section>'


def _render(phase, order, clues, votes, result, imposter, word, cat, events, mode, error=""):
    completed = phase == "complete"
    running = phase in ("clues", "voting")
    return (
        phase_panel(phase, len(clues), len(votes), mode, cat, error),
        clue_panel(order, clues, completed, imposter if completed else None),
        voting_panel(order, votes, completed),
        result_panel(result if completed else None, imposter if completed else "", word if completed else "", error),
        activity_panel(events),
        gr.update(interactive=not running),
        gr.update(interactive=not running),
        gr.update(interactive=not running),
    )


def _live_worker(category: str, secret_word: str, output: Queue):
    """Keep live game rules and retry handling in main.py; emit public events only."""
    try:
        from main import run_clue_phase, run_voting_phase
        category, secret_word = user_input(category, secret_word)
        players, imposter = setup_players(secret_word, category)
        public_order = [player["name"] for player in players]
        output.put(("started", (category, public_order)))
        clues = run_clue_phase(players, secret_word, on_clue=lambda clue: output.put(("clue", clue)))
        output.put(("voting_started", None))
        votes = run_voting_phase(players, clues, secret_word, on_vote=lambda vote: output.put(("vote", vote)))
        outcome = resolve_game(players, votes, imposter)
        output.put(("complete", (outcome, imposter, secret_word)))
    except Exception as exc:
        output.put(("error", exc))


def _demo_worker(output: Queue):
    """A self-contained, clearly labeled sample. No API calls, tokens, or credentials."""
    try:
        category, secret_word, imposter = "Animals", "Penguin", "ChatGPT"
        order = ["Groq", "Claude", "Gemini", "ChatGPT"]
        players = [{"name": name, "category": category,
                    "secret_word": "Imposter" if name == imposter else secret_word} for name in order]
        output.put(("started", (category, order)))
        sample_clues = [("Groq", "tuxedo"), ("Claude", "Antarctica"), ("Gemini", "swim"), ("ChatGPT", "bird")]
        clues = []
        for name, clue in sample_clues:
            sleep(0.28)
            add_clue(clues, name, clue, secret_word)
            output.put(("clue", clues[-1].copy()))
        output.put(("voting_started", None))
        sample_votes = [
            ("Groq", "Gemini", "The clue swim could fit almost any animal."),
            ("Claude", "Gemini", "Swim is a broad action compared with the distinctive clues."),
            ("Gemini", "ChatGPT", "Bird seems unusually broad and adds little information."),
            ("ChatGPT", "Claude", "Antarctica feels like a location rather than an animal characteristic."),
        ]
        votes = []
        for name, vote, reason in sample_votes:
            sleep(0.28)
            candidates = [player["name"] for player in players if player["name"] != name]
            add_vote(votes, name, {"vote": vote, "reason": reason}, candidates, secret_word)
            output.put(("vote", votes[-1].copy()))
        output.put(("complete", (resolve_game(players, votes, imposter), imposter, secret_word)))
    except Exception as exc:
        output.put(("error", exc))


def play_match(category: str, secret_word: str, demo: bool = False):
    """Gradio generator. Each public clue/ballot triggers one live UI update."""
    order = INITIAL_ORDER.copy()
    clues: list[dict] = []
    votes: list[dict] = []
    events: list[tuple[str, str]] = []
    phase = "clues"
    result = None
    imposter, final_word = "", ""
    mode = "DEMO" if demo else "LIVE"
    current_category = "DEMO ROUND" if demo else (category or "UNNAMED CATEGORY").strip()

    # Validate before starting a thread, without exposing the secret word in UI errors.
    if not demo:
        try:
            current_category, _ = user_input(category, secret_word)
        except (ValueError, TypeError) as exc:
            events.append(("error", "Invalid game setup. Check category and secret word."))
            yield _render("error", order, clues, votes, result, imposter, final_word, current_category, events, mode, str(exc))
            return

    events.append(("info", "Starting a preview game with sample AI responses." if demo else "Connecting the four AI providers."))
    yield _render("clues", order, clues, votes, result, imposter, final_word, current_category, events, mode)

    inbox: Queue = Queue()
    worker = Thread(target=_demo_worker if demo else _live_worker,
                    args=(inbox,) if demo else (category, secret_word, inbox), daemon=True)
    worker.start()

    while True:
        kind, payload = inbox.get()
        if kind == "started":
            current_category, order = payload
            events.append(("info", "Match initialized. The secret roles have been assigned."))
        elif kind == "clue":
            clues.append(payload)
            events.append(("success", f'{payload["name"]} submitted a clue.'))
        elif kind == "voting_started":
            phase = "voting"
            events.append(("info", "All clues are in. Voting is now open to the AI players."))
        elif kind == "vote":
            votes.append(payload)
            events.append(("success", f'{payload["name"]} has sealed a ballot.'))
        elif kind == "complete":
            result, imposter, final_word = payload
            phase = "complete"
            events.append(("success", f'Final verdict: {result["winner"]} win.'))
            yield _render(phase, order, clues, votes, result, imposter, final_word, current_category, events, mode)
            break
        elif kind == "error":
            phase = "error"
            # Detailed provider errors stay server-side. Avoid leaking credentials or raw prompts to the browser.
            print(f"[AI Imposter] Match error ({mode}): {type(payload).__name__}: {payload}")
            msg = "The AI provider could not complete this match. Check the terminal for details, your API keys, and remaining quota."
            if isinstance(payload, (ValueError, TypeError)):
                msg = "The match encountered invalid game data. Check the terminal for details."
            events.append(("error", "Round stopped before a final verdict was reached."))
            yield _render(phase, order, clues, votes, None, "", "", current_category, events, mode, msg)
            break
        yield _render(phase, order, clues, votes, result, imposter, final_word, current_category, events, mode)


def play_live(category: str, secret_word: str):
    yield from play_match(category, secret_word, demo=False)


def play_demo():
    yield from play_match("", "", demo=True)


def reset_view():
    return _render("idle", INITIAL_ORDER, [], [], None, "", "", "", [], "LIVE")


def fill_preset(selection: str):
    if selection in PRESETS:
        return PRESETS[selection]
    return "", ""


def make_app() -> gr.Blocks:
    with gr.Blocks(title="AI Imposter Arena", fill_width=True, analytics_enabled=False) as demo:
        with gr.Column(elem_id="arena-shell"):
            gr.HTML(header(), elem_id="hero")
            with gr.Row(equal_height=False, elem_id="setup-row"):
                with gr.Column(scale=5, min_width=320):
                    with gr.Group(elem_classes="setup-panel"):
                        gr.HTML('<div class="micro-label">YOUR NEXT MATCH</div><div class="setup-headline">SET THE SCENE<span>.</span></div><p class="setup-descr">Choose a category and a secret word. Three models get the answer; one is kept in the dark.</p>')
                        with gr.Row():
                            category = gr.Textbox(label="CATEGORY", placeholder="e.g. Animals", value="Animals", elem_id="category-field")
                            secret_word = gr.Textbox(label="SECRET WORD", placeholder="e.g. Penguin", value="Penguin", type="password", elem_id="word-field")
                        preset = gr.Dropdown(choices=["Custom"] + list(PRESETS), label="QUICK SCENARIOS", value="Custom", elem_id="preset-select")
                        with gr.Row(elem_id="control-row"):
                            live = gr.Button("⚡  LAUNCH LIVE MATCH", variant="primary", elem_id="live-button", scale=3)
                            trial = gr.Button("▷  TRY DEMO", variant="secondary", elem_id="demo-button", scale=2)
                        gr.HTML('<div class="setup-foot"><span><b>LIVE</b> requires your four provider API keys</span><span><b>DEMO</b> uses a sample match · no credits</span></div>')
                with gr.Column(scale=4, min_width=310):
                    status = gr.HTML(phase_panel("idle"), elem_id="status-component")
            clues = gr.HTML(clue_panel(INITIAL_ORDER, []), elem_id="clues-component")
            votes = gr.HTML(voting_panel(INITIAL_ORDER, []), elem_id="votes-component")
            with gr.Row(equal_height=False, elem_id="bottom-row"):
                with gr.Column(scale=6, min_width=345):
                    results = gr.HTML(result_panel(), elem_id="results-component")
                with gr.Column(scale=4, min_width=280):
                    activity = gr.HTML(activity_panel(), elem_id="activity-component")
                    reset_button = gr.Button("↺  RESET ARENA", elem_id="reset-button", size="md")
            gr.HTML('<div class="arena-footer"><span>AI IMPOSTER ARENA <i>©</i> BUILT WITH PYTHON + GRADIO</span><span>4 MODELS · 1 SECRET · ZERO TRUST</span></div>')

        fields = [status, clues, votes, results, activity, live, trial, reset_button]
        preset.change(fill_preset, inputs=preset, outputs=[category, secret_word], show_progress="hidden")
        live.click(play_live,
                   inputs=[category, secret_word], outputs=fields, concurrency_limit=1, show_progress="minimal")
        trial.click(play_demo,
                    inputs=[], outputs=fields, concurrency_limit=1, show_progress="minimal")
        reset_button.click(reset_view, inputs=[], outputs=fields, show_progress="hidden")
    return demo


if __name__ == "__main__":
    app = make_app()
    app.queue(default_concurrency_limit=2)
    app.launch(server_name=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
               server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")),
               share=False, inbrowser=True, show_error=True,
               css_paths=str(ROOT / "style.css"), theme=gr.themes.Base())
