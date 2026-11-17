"""Syntakt MAX custom installer v2: choose the OS and your mods, see each mod's status and the CPU estimate, build
the .syx locally. v2.5: presets, each mod's notes (latest progress, what to check on the unit), the progress log,
and your own test notes per mod, kept in Documents (they survive new installer versions)."""
from __future__ import annotations
import datetime, json, queue, threading, tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import max_custom as M

BAR_W, BAR_H = 360, 22
BADGE = {"STABLE": ("#2e7d32", "STABLE"), "BETA": ("#ef8f00", "BETA"), "EXPERIMENTAL": ("#c62828", "EXPERIMENTAL")}


RESULTS = ("not tried", "works", "problem")
MARK = {"not tried": "", "works": "✓ works on my unit", "problem": "⚠ problem noted"}


def notes_path() -> Path:
    docs = Path.home() / "Documents"
    return (docs if docs.is_dir() else Path(__file__).resolve().parent) / "SyntaktJOG_builder_notes.json"


def load_notes() -> dict:
    try:
        d = json.loads(notes_path().read_text(encoding="utf-8"))
        return {"groups": dict(d.get("groups", {})), "general": str(d.get("general", ""))}
    except (OSError, ValueError):
        return {"groups": {}, "general": ""}


def save_notes(d: dict) -> None:
    try:
        notes_path().write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        messagebox.showerror("Syntakt Performance Mods", f"Couldn't save your notes to {notes_path()}:\n{e}")


def badge(parent, status):
    colour, text = BADGE[status]
    return tk.Label(parent, text=f" {text} ", bg=colour, fg="white", font=("Segoe UI", 8, "bold"))


class App(ttk.Frame):
    def __init__(self, root):
        super().__init__(root, padding=14)
        self.grid(sticky="nsew")
        root.title("Syntakt Performance Mods builder v1.1")
        root.minsize(980, 640)
        self.cat = M.catalog()
        self.groups = {g["id"]: g for g in self.cat["groups"]}
        self.var, self.rows, self.marks = {}, {}, {}
        self.my = load_notes()
        self.osv = tk.StringVar(value="1.42")
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text="Syntakt Performance Mods builder", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(self, text="Builds locally from your official OS file; it never sends anything to the Syntakt. "
                             "Private: don't share the .syx files you build.").grid(row=1, column=0, columnspan=2,
                                                                                     sticky="w")
        # OS + legend
        top = ttk.Frame(self)
        top.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 8))
        ttk.Label(top, text="OS:").grid(row=0, column=0, sticky="w")
        for i, (v, o) in enumerate(self.cat["oses"].items()):
            ttk.Radiobutton(top, text=f"{v} (base {o['base']})", value=v, variable=self.osv,
                            command=self.os_changed).grid(row=0, column=1 + 2 * i, sticky="w", padx=(6, 2))
            badge(top, o["status"]).grid(row=0, column=2 + 2 * i, sticky="w", padx=(0, 12))
        ttk.Button(top, text="Progress & notes…", command=self.show_progress).grid(row=0, column=9, sticky="w",
                                                                                  padx=(12, 0))
        pre = ttk.Frame(top)
        pre.grid(row=2, column=0, columnspan=10, sticky="w", pady=(6, 0))
        ttk.Label(pre, text="Preset:").grid(row=0, column=0, sticky="w")
        self.preset = tk.StringVar()
        names = [p["name"] for p in self.cat.get("presets", [])]
        ttk.Combobox(pre, textvariable=self.preset, values=names, state="readonly", width=48).grid(
            row=0, column=1, sticky="w", padx=6)
        ttk.Button(pre, text="Apply", command=self.apply_preset).grid(row=0, column=2, sticky="w")
        ttk.Label(pre, text="(then tick or untick any mod to test it on its own)", foreground="#555").grid(
            row=0, column=3, sticky="w", padx=6)
        leg = ttk.Frame(top)
        leg.grid(row=1, column=0, columnspan=8, sticky="w", pady=(6, 0))
        for i, s in enumerate(BADGE):
            badge(leg, s).grid(row=i, column=0, sticky="w", pady=1)
            ttk.Label(leg, text=self.cat["status"][s], foreground="#555", wraplength=820).grid(
                row=i, column=1, sticky="w", padx=6)
        # mods
        frame = ttk.LabelFrame(self, text="Mods", padding=6)
        frame.grid(row=3, column=0, sticky="nsew", padx=(0, 12))
        self.rowconfigure(3, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        canvas = tk.Canvas(frame, highlightthickness=0, width=540)
        sb = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        box = ttk.Frame(canvas, padding=4)
        canvas.create_window((0, 0), window=box, anchor="nw")
        box.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        for i, g in enumerate(self.cat["groups"]):
            v = tk.BooleanVar(value=bool(g.get("locked") or g.get("default")))
            self.var[g["id"]] = v
            head = ttk.Frame(box)
            head.grid(row=2 * i, column=0, sticky="w")
            cb = ttk.Checkbutton(head, text=g["label"], variable=v, command=lambda gid=g["id"]: self.toggle(gid))
            cb.grid(row=0, column=0, sticky="w")
            badge(head, g["status"]).grid(row=0, column=1, sticky="w", padx=6)
            ttk.Button(head, text="Notes…", width=8, command=lambda gid=g["id"]: self.show_notes(gid)).grid(
                row=0, column=2, sticky="w")
            mk = tk.StringVar()
            self.marks[g["id"]] = mk
            ttk.Label(head, textvariable=mk, foreground="#2e7d32").grid(row=0, column=3, sticky="w", padx=6)
            cost = "screen only" if not (g["idle"] or g["busy"]) else \
                f"idle {g['idle']} / engaged {g['busy']} instr. per block ({g['busy_what']})"
            req = g.get("requires")
            extra = f"  Needs: {', '.join(self.groups[r]['label'] for r in req)}." if req else ""
            ttk.Label(box, text=f"{g['info']}{extra}\nStatus: {g['why']}\nCPU: {cost}", foreground="#555",
                      wraplength=520, justify="left").grid(row=2 * i + 1, column=0, sticky="w", padx=(24, 0),
                                                           pady=(0, 8))
            self.rows[g["id"]] = cb
        # meter
        side = ttk.LabelFrame(self, text="CPU estimate", padding=10)
        side.grid(row=3, column=1, sticky="nsew")
        self.meter = tk.Canvas(side, width=BAR_W, height=150, highlightthickness=0)
        self.meter.grid(row=0, column=0, sticky="w")
        self.cpu_txt = tk.StringVar()
        ttk.Label(side, textvariable=self.cpu_txt, wraplength=BAR_W, justify="left").grid(row=1, column=0,
                                                                                         sticky="w")
        self.overall = tk.StringVar()
        ttk.Label(side, textvariable=self.overall, wraplength=BAR_W, justify="left",
                  font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Label(side, text="Estimates from the emulator, scaled to the device (stock's audio interrupt put at "
                             "≈ 89 % of the CPU, an estimate never timed on a unit). 'Engaged' = every selected "
                             "effect working at once. The UI (screen, knobs, keys) gets what is left: less "
                             "headroom = more lag.",
                  foreground="#555", wraplength=BAR_W, justify="left").grid(row=3, column=0, sticky="w",
                                                                           pady=(8, 0))
        # build
        bottom = ttk.Frame(self)
        bottom.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        bottom.columnconfigure(1, weight=1)
        self.src = tk.StringVar()
        self.src_label = tk.StringVar()
        ttk.Label(bottom, textvariable=self.src_label).grid(row=0, column=0, sticky="w")
        ttk.Entry(bottom, textvariable=self.src).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(bottom, text="Choose…", command=self.choose).grid(row=0, column=2)
        self.go = ttk.Button(bottom, text="Build and Save", command=self.start)
        self.go.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.status = tk.StringVar(value="Pick the OS and your mods, choose that OS's official .syx, then Build and Save.")
        ttk.Label(bottom, textvariable=self.status, wraplength=900).grid(row=2, column=0, columnspan=3,
                                                                        sticky="w", pady=(8, 0))
        self.q = queue.Queue()
        self.after(120, self.poll)
        self.update_marks()
        self.os_changed()

    # ---- notes, progress, presets
    def update_marks(self):
        for gid, mk in self.marks.items():
            r = self.my["groups"].get(gid, {}).get("result", "not tried")
            mk.set(MARK.get(r, ""))

    def show_notes(self, gid):
        g = self.groups[gid]
        n = g.get("notes", {})
        mine = self.my["groups"].get(gid, {})
        w = tk.Toplevel(self)
        w.title(f"Notes: {g['label']}")
        w.minsize(560, 480)
        f = ttk.Frame(w, padding=12)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=g["label"], font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(f, text=f"Status: {g['status']}. {g['why']}", wraplength=520, justify="left").pack(anchor="w",
                                                                                                      pady=(4, 0))
        ttk.Label(f, text="Latest: " + n.get("latest", "–"), wraplength=520, justify="left").pack(anchor="w",
                                                                                                  pady=(6, 0))
        if n.get("check"):
            ttk.Label(f, text="What to check on your unit:", font=("Segoe UI", 9, "bold")).pack(anchor="w",
                                                                                                pady=(8, 0))
            ttk.Label(f, text="\n".join(f"• {c}" for c in n["check"]), wraplength=520, justify="left").pack(
                anchor="w")
        ttk.Label(f, text="Your result:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 0))
        res = tk.StringVar(value=mine.get("result", "not tried"))
        rb = ttk.Frame(f)
        rb.pack(anchor="w")
        for i, r in enumerate(RESULTS):
            ttk.Radiobutton(rb, text=r, value=r, variable=res).grid(row=0, column=i, padx=(0, 10))
        ttk.Label(f, text="Your notes (which build, what you heard, what went wrong):",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 0))
        t = tk.Text(f, height=8, wrap="word")
        t.pack(fill="both", expand=True)
        t.insert("1.0", mine.get("text", ""))
        if mine.get("updated"):
            ttk.Label(f, text=f"Last saved {mine['updated']}", foreground="#555").pack(anchor="w")

        def save():
            self.my["groups"][gid] = {"result": res.get(), "text": t.get("1.0", "end").strip(),
                                      "updated": datetime.date.today().isoformat()}
            save_notes(self.my)
            self.update_marks()
            w.destroy()
        b = ttk.Frame(f)
        b.pack(anchor="e", pady=(8, 0))
        ttk.Button(b, text="Save", command=save).grid(row=0, column=0, padx=4)
        ttk.Button(b, text="Close", command=w.destroy).grid(row=0, column=1)

    def show_progress(self):
        w = tk.Toplevel(self)
        w.title("Progress & notes")
        w.minsize(640, 560)
        f = ttk.Frame(w, padding=12)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text="Where we are", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        log = "\n".join(f"• {p['build']} (OS {p['os']}): {p['what']}  On your unit: {p['on_unit']}."
                        for p in self.cat.get("progress", []))
        ttk.Label(f, text=log, wraplength=600, justify="left").pack(anchor="w", pady=(4, 0))
        if self.cat.get("next"):
            ttk.Label(f, text="Next:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 0))
            ttk.Label(f, text="\n".join(f"• {x}" for x in self.cat["next"]), wraplength=600,
                      justify="left").pack(anchor="w")
        tried = [(self.groups[g]["label"], d) for g, d in self.my["groups"].items() if g in self.groups and
                 (d.get("result", "not tried") != "not tried" or d.get("text"))]
        if tried:
            ttk.Label(f, text="Your results so far:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 0))
            ttk.Label(f, text="\n".join(f"• {lab}: {d.get('result')} ({d.get('updated', '')})"
                                        + (f" – {d['text'][:120]}" if d.get("text") else "") for lab, d in tried),
                      wraplength=600, justify="left").pack(anchor="w")
        ttk.Label(f, text="Your general notes:", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 0))
        t = tk.Text(f, height=8, wrap="word")
        t.pack(fill="both", expand=True)
        t.insert("1.0", self.my.get("general", ""))
        ttk.Label(f, text=f"Saved in {notes_path()}", foreground="#555").pack(anchor="w")

        def save():
            self.my["general"] = t.get("1.0", "end").strip()
            save_notes(self.my)
            w.destroy()
        b = ttk.Frame(f)
        b.pack(anchor="e", pady=(8, 0))
        ttk.Button(b, text="Save", command=save).grid(row=0, column=0, padx=4)
        ttk.Button(b, text="Close", command=w.destroy).grid(row=0, column=1)

    def apply_preset(self):
        p = next((p for p in self.cat.get("presets", []) if p["name"] == self.preset.get()), None)
        if not p:
            return
        if p["os"] in self.cat["oses"] and p["os"] != self.osv.get():
            self.osv.set(p["os"])
            self.os_changed()
        avail = self.available()
        want = (set(avail) if p["groups"] == "all" else set(p["groups"])) - set(p["except"])
        for a, b in M.clashes(self.cat, want):                       # "all": keep the default one of a pair
            want.discard(b if self.groups[a].get("default") else a)
        want |= {gid for gid in avail if self.groups[gid].get("locked")}
        want = M.resolve(self.cat, want & avail, self.osv.get())
        for gid, v in self.var.items():
            v.set(gid in want)
        self.refresh()
        self.status.set(f"Preset applied: {p['name']}. Tick or untick mods to change it.")

    # ---- state
    def available(self) -> set[str]:
        return {g["id"] for g in M.groups_for(self.cat, self.osv.get())}

    def chosen(self) -> set[str]:
        return {gid for gid, v in self.var.items() if v.get()} & self.available()

    def os_changed(self):
        avail = self.available()
        for gid, cb in self.rows.items():
            if gid not in avail:
                self.var[gid].set(False)
                cb.state(["disabled"])
            elif not self.groups[gid].get("locked"):
                cb.state(["!disabled"])
        self.src_label.set(f"Official OS {self.osv.get()} .syx")
        self.refresh()

    def toggle(self, gid):
        g = self.groups[gid]
        if self.var[gid].get():
            if g["status"] == "EXPERIMENTAL" and not messagebox.askyesno(
                    "Syntakt Performance Mods", f"“{g['label']}” is EXPERIMENTAL.\n\n{g['why']}\n\n"
                                   f"{self.cat['status']['EXPERIMENTAL']}\n\nAdd it?"):
                self.var[gid].set(False)
                return
            for r in M.rivals(self.cat, gid):                        # e.g. the JOG page with / without LINK
                if r in self.var and self.var[r].get():
                    self.var[r].set(False)
                    self.status.set(f"“{self.groups[r]['label']}” unticked: it can't be in one build with "
                                    f"“{g['label']}”.")
            for r in M.resolve(self.cat, {gid}, self.osv.get()) - self.chosen():
                self.var[r].set(True)
        else:
            dep = [d for d in M.dependents(self.cat, gid) if self.var[d].get()]
            if dep:
                names = "\n".join("• " + self.groups[d]["label"] for d in dep)
                if messagebox.askyesno("Syntakt Performance Mods", f"Removing “{g['label']}” also removes:\n\n{names}\n\n"
                                                      "Continue?"):
                    for d in dep:
                        self.var[d].set(False)
                else:
                    self.var[gid].set(True)
        self.refresh()

    def refresh(self):
        sel = M.resolve(self.cat, self.chosen(), self.osv.get())
        c = M.cpu(self.cat, sel)
        cv = self.meter
        cv.delete("all")
        lo = 80.0                                                    # bars show 80..100 %

        def bar(y, label, pct, colour):
            cv.create_text(0, y, text=label, anchor="w")
            x0, y0 = 0, y + 10
            cv.create_rectangle(x0, y0, x0 + BAR_W, y0 + BAR_H, outline="#999", fill="#eee")
            w = max(0.0, min(1.0, (pct - lo) / (100 - lo))) * BAR_W
            cv.create_rectangle(x0, y0, x0 + w, y0 + BAR_H, outline="", fill=colour)
            sx = (c["stock_pct"] - lo) / (100 - lo) * BAR_W
            cv.create_line(sx, y0 - 3, sx, y0 + BAR_H + 3, fill="#000", dash=(3, 2))
            cv.create_text(x0 + BAR_W - 4, y0 + BAR_H / 2, text=f"{pct:.1f} %", anchor="e")

        def colour(ui):
            return "#4caf50" if ui >= 9 else "#ffb300" if ui >= 6 else "#e53935"
        bar(8, "Idle (nothing engaged)", c["idle_pct"], colour(c["idle_ui"]))
        bar(70, "Engaged (worst case)", c["busy_pct"], colour(c["busy_ui"]))
        cv.create_text(0, 140, text="scale 80–100 %   ┆ dashed line = stock OS", anchor="w", fill="#555")
        self.cpu_txt.set(f"UI headroom idle: {c['idle_ui']:.1f} %   engaged: {c['busy_ui']:.1f} %   "
                         f"(stock OS: {c['stock_ui']:.1f} %)")
        osv = self.osv.get()
        notes = M.variant_notes(self.cat, sel, osv)
        why = "".join(f"\n• {n}: {w}" for n, w in {(n, w) for n, _, w in notes}) if notes else ""
        self.overall.set(f"This build: {M.worst_status(self.cat, sel, osv)} (the least proven part sets it)" +
                         (f"\nRebuilt parts:{why}" if why else ""))

    # ---- build
    def choose(self):
        p = filedialog.askopenfilename(filetypes=[("Syntakt firmware", "*.syx"), ("All files", "*.*")])
        if p:
            self.src.set(p)
            v = M.os_of(self.cat, p)
            if v:
                if v != self.osv.get():
                    self.osv.set(v)
                    self.os_changed()
                self.status.set(f"Official OS {v} file recognised; OS {v} selected.")
            else:
                self.status.set("This is NOT an official Syntakt OS " + " / ".join(self.cat["oses"]) +
                                " file (SHA-256 differs).")

    def start(self):
        if not self.src.get():
            return messagebox.showerror("Syntakt Performance Mods", f"Choose your OS {self.osv.get()} .syx file first.")
        v = M.os_of(self.cat, self.src.get())
        if v != self.osv.get():
            return messagebox.showerror("Syntakt Performance Mods", f"That file is not the official OS {self.osv.get()} file.")
        sel = M.resolve(self.cat, self.chosen(), v)
        worst = M.worst_status(self.cat, sel, v)
        if worst == "EXPERIMENTAL" and not messagebox.askyesno(
                "Syntakt Performance Mods", "This build has EXPERIMENTAL parts. Back up your projects and samples first, and "
                               "keep a known-good .syx ready for recovery mode.\n\nBuild it?"):
            return
        name = f"Syntakt_JOG_{'full' if sel == self.available() else 'custom'}_OS{v}.syx"
        out = filedialog.asksaveasfilename(defaultextension=".syx", initialfile=name,
                                           filetypes=[("SysEx firmware", "*.syx")])
        if not out:
            return
        self.go.state(["disabled"])
        self.status.set("Starting local build…")
        threading.Thread(target=self.worker, args=(self.src.get(), out, sel), daemon=True).start()

    def worker(self, src, out, sel):
        try:
            r = M.build(src, out, sel, lambda s: self.q.put(("progress", s)))
            with open(r["output"] + ".txt", "w", encoding="utf-8") as f:
                f.write(f"OS {r['os']}\nstatus {r['status']}\nSHA-256 {r['sha256']}\nboot margin {r['boot_margin']}\n"
                        f"same as {r['known'] or 'no earlier test build (a new combination)'}\n"
                        f"groups {', '.join(r['groups'])}\nmods {', '.join(r['mods'])}\n")
                f.write("\nWHAT TO CHECK (the mods in this build that aren't STABLE)\n")
                for gid in r["groups"]:
                    g = self.groups.get(gid)
                    if not g or g["status"] == "STABLE":
                        continue
                    n, mine = g.get("notes", {}), self.my["groups"].get(gid, {})
                    f.write(f"\n{g['label']} [{g['status']}]\n  {n.get('latest', '')}\n")
                    for c in n.get("check", []):
                        f.write(f"  [ ] {c}\n")
                    if mine.get("text") or mine.get("result", "not tried") != "not tried":
                        f.write(f"  Your notes ({mine.get('result')}, {mine.get('updated', '')}): "
                                f"{mine.get('text', '')}\n")
            self.q.put(("ok", r))
        except Exception as e:                                       # noqa: BLE001 (shown to the user)
            self.q.put(("error", str(e)))

    def poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "progress":
                    self.status.set(val)
                elif kind == "ok":
                    same = f"Identical to {val['known']}." if val["known"] else \
                        "A new combination: each mod is labelled, but this exact build hasn't run on your unit."
                    self.status.set(f"Saved {val['output']}  ({val['status']})  SHA-256 {val['sha256']}")
                    messagebox.showinfo("Syntakt Performance Mods", f"Build verified and saved.\n\nOS {val['os']}, "
                                                       f"{val['status']}\n{same}\n\nSHA-256: {val['sha256']}\n"
                                                       f"Boot margin: {val['boot_margin']}\nMods: {len(val['mods'])}")
                else:
                    self.status.set("No output was saved.")
                    messagebox.showerror("Syntakt Performance Mods", "Build failed. No output was saved.\n\n" + val)
                if kind in ("ok", "error"):
                    self.go.state(["!disabled"])
        except queue.Empty:
            pass
        self.after(120, self.poll)


if __name__ == "__main__":
    root = tk.Tk()
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    App(root)
    root.mainloop()
