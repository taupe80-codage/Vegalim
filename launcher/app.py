"""ALIM - Panneau de controle.

Interface graphique unique pour lancer les scripts de creation et de
controle du projet sans taper de commandes dans PowerShell. Regroupe par
categorie (voir registry.py), avec un journal de sortie en direct pour les
scripts "captures" et une fenetre de console dediee pour les pipelines
interactifs (menus, saisies au clavier).
"""
from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from registry import ACTIONS, categories, find_python, find_root


class LauncherApp:
    def __init__(self) -> None:
        self.root_dir = find_root()
        self.python_exe = find_python(self.root_dir)

        self.proc: subprocess.Popen | None = None
        self.out_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.dry_run_vars: dict[str, tk.BooleanVar] = {}
        self.run_buttons: list[tk.Button] = []

        self.win = tk.Tk()
        self.win.title("ALIM — Panneau de controle")
        self.win.geometry("1000x760")
        self.win.minsize(760, 560)

        self._build_ui()
        self._append_log(f"Racine du projet : {self.root_dir}\n")
        self._append_log(f"Interpreteur Python : {self.python_exe}\n\n")
        self._poll_queue()

    # ── UI ───────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        header = tk.Frame(self.win, bg="#1f2430")
        header.pack(fill="x")
        tk.Label(
            header, text="ALIM — Panneau de controle", bg="#1f2430", fg="white",
            font=("Segoe UI", 14, "bold"), padx=14, pady=10, anchor="w",
        ).pack(fill="x")

        self.notebook = ttk.Notebook(self.win)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(10, 6))

        for cat in categories():
            tab = self._build_category_tab(cat)
            self.notebook.add(tab, text=cat)

        log_frame = tk.Frame(self.win)
        log_frame.pack(fill="both", expand=False, padx=10, pady=(0, 10))

        toolbar = tk.Frame(log_frame)
        toolbar.pack(fill="x")
        self.status_var = tk.StringVar(value="Pret.")
        tk.Label(
            toolbar, textvariable=self.status_var, anchor="w", font=("Segoe UI", 9, "bold")
        ).pack(side="left")
        self.stop_btn = tk.Button(
            toolbar, text="Arreter", command=self._stop_current, state="disabled", width=10
        )
        self.stop_btn.pack(side="right")
        tk.Button(
            toolbar, text="Effacer le journal", command=self._clear_log, width=16
        ).pack(side="right", padx=(0, 6))

        self.log = scrolledtext.ScrolledText(
            log_frame, height=16, bg="#111318", fg="#d8dee4",
            insertbackground="white", font=("Consolas", 9),
        )
        self.log.pack(fill="both", expand=True, pady=(4, 0))
        self.log.configure(state="disabled")

    def _build_category_tab(self, category: str) -> tk.Widget:
        outer = tk.Frame(self.notebook)

        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_enter(_event: object) -> None:
            canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        def _on_leave(_event: object) -> None:
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _on_enter)
        canvas.bind("<Leave>", _on_leave)

        for action in (a for a in ACTIONS if a.category == category):
            self._build_card(inner, action)

        return outer

    def _build_card(self, parent: tk.Widget, action) -> None:  # noqa: ANN001
        card = tk.Frame(parent, relief="groove", bd=1, padx=12, pady=10, bg="#fafafa")
        card.pack(fill="x", padx=8, pady=6)

        tk.Label(
            card, text=action.title, font=("Segoe UI", 10, "bold"),
            anchor="w", justify="left", bg="#fafafa",
        ).pack(fill="x")

        tk.Label(
            card, text=action.description, wraplength=860, justify="left",
            fg="#3a3a3a", anchor="w", bg="#fafafa",
        ).pack(fill="x", pady=(3, 8))

        row = tk.Frame(card, bg="#fafafa")
        row.pack(fill="x")

        if action.dry_run:
            var = tk.BooleanVar(value=True)
            self.dry_run_vars[action.key] = var
            tk.Checkbutton(
                row, text="Dry-run (apercu, aucune ecriture)", variable=var, bg="#fafafa",
            ).pack(side="left")

        if action.kind == "console":
            btn_text = "Ouvrir la console"
        else:
            btn_text = "Lancer"
        btn = tk.Button(row, text=btn_text, width=18, command=lambda a=action: self._launch(a))
        btn.pack(side="right")
        self.run_buttons.append(btn)

    # ── Execution ────────────────────────────────────────────────────────
    def _launch(self, action) -> None:  # noqa: ANN001
        if action.kind == "console":
            self._open_console(action)
            return

        if self.proc is not None:
            messagebox.showinfo(
                "Deja en cours",
                "Un script est deja en cours d'execution. Attends qu'il se "
                "termine ou clique sur «Arreter».",
            )
            return

        dry_run = action.dry_run and self.dry_run_vars.get(action.key, tk.BooleanVar(value=False)).get()
        cmds = []
        for step in action.steps:
            cmd = [self.python_exe if tok == "{python}" else tok for tok in step]
            if dry_run:
                cmd.append("--dry-run")
            cmds.append(cmd)

        self._set_running(action.title)
        threading.Thread(target=self._run_steps, args=(cmds,), daemon=True).start()

    def _run_steps(self, cmds: list[list[str]]) -> None:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        ok = True
        for cmd in cmds:
            self.out_queue.put(("line", "$ " + " ".join(cmd) + "\n"))
            try:
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                self.proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.root_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env,
                    creationflags=creationflags,
                )
            except FileNotFoundError as exc:
                self.out_queue.put(("line", f"[ERREUR] Introuvable : {exc}\n"))
                ok = False
                break

            assert self.proc.stdout is not None
            for line in self.proc.stdout:
                self.out_queue.put(("line", line))
            code = self.proc.wait()
            self.proc = None
            if code != 0:
                self.out_queue.put(("line", f"[ECHEC] code retour {code}\n"))
                ok = False
                break

        self.out_queue.put(("done", ok))

    def _open_console(self, action) -> None:  # noqa: ANN001
        bat_path = self.root_dir / action.bat
        if not bat_path.exists():
            messagebox.showerror("Introuvable", f"Fichier introuvable : {bat_path}")
            return
        self._append_log(f"Fenetre de console ouverte pour {action.bat}\n")
        subprocess.Popen(
            ["cmd", "/c", "start", action.title, "cmd", "/k", str(bat_path)],
            cwd=str(self.root_dir),
        )

    def _stop_current(self) -> None:
        if self.proc is not None:
            self.proc.terminate()
            self._append_log("[ARRETE par l'utilisateur]\n")

    # ── Etat / journal ───────────────────────────────────────────────────
    def _set_running(self, label: str) -> None:
        self.status_var.set(f"En cours : {label}")
        self.stop_btn.config(state="normal")
        for b in self.run_buttons:
            b.config(state="disabled")

    def _set_idle(self, ok: bool) -> None:
        self.status_var.set("Termine." if ok else "Termine avec erreurs.")
        self.stop_btn.config(state="disabled")
        for b in self.run_buttons:
            b.config(state="normal")

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.out_queue.get_nowait()
                if kind == "line":
                    self._append_log(str(payload))
                elif kind == "done":
                    self._set_idle(ok=bool(payload))
        except queue.Empty:
            pass
        self.win.after(80, self._poll_queue)

    def run(self) -> None:
        self.win.mainloop()


if __name__ == "__main__":
    LauncherApp().run()
