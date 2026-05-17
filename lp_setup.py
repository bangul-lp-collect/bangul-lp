"""
LP to Notion 설정 도우미
실행: python3 lp_setup.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import threading
from pathlib import Path

CONFIG_FILE = "lp_config.json"


def save_config(data: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


class LPApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 LP to Notion 설정")
        self.root.geometry("680x700")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")
        self.cfg = load_config()
        self._build_ui()

    def _build_ui(self):
        # 타이틀
        tk.Label(self.root, text="🎵  LP to Notion  설정 도우미",
                 font=("Helvetica", 18, "bold"),
                 bg="#1a1a2e", fg="#ffffff").pack(pady=(24, 4))
        tk.Label(self.root, text="아래 항목을 모두 입력하고 저장하세요",
                 font=("Helvetica", 10), bg="#1a1a2e", fg="#888888").pack(pady=(0, 16))

        frame = tk.Frame(self.root, bg="#16213e")
        frame.pack(fill="both", expand=True, padx=24, pady=4)

        def section(text):
            f = tk.Frame(frame, bg="#16213e")
            f.pack(fill="x", padx=20, pady=(12, 2))
            tk.Label(f, text=text, font=("Helvetica", 10, "bold"),
                     bg="#16213e", fg="#e94560").pack(anchor="w")
            tk.Frame(f, bg="#e94560", height=1).pack(fill="x")

        def field(label, key, show=False, hint=""):
            f = tk.Frame(frame, bg="#16213e")
            f.pack(fill="x", padx=20, pady=3)
            tk.Label(f, text=label, width=20, anchor="w",
                     font=("Helvetica", 10), bg="#16213e", fg="#cccccc").pack(side="left")
            var = tk.StringVar(value=self.cfg.get(key, ""))
            e = tk.Entry(f, textvariable=var, show="•" if show else "",
                         font=("Helvetica", 10), bg="#0f3460", fg="#ffffff",
                         insertbackground="#ffffff", relief="flat",
                         highlightthickness=1, highlightcolor="#e94560",
                         highlightbackground="#333355")
            e.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 6))
            if hint:
                tk.Label(f, text=hint, font=("Helvetica", 8),
                         bg="#16213e", fg="#666688").pack(side="left")
            return var

        # Anthropic
        section("1.  Anthropic API 키  (console.anthropic.com)")
        self.v_ant = field("API 키", "anthropic_key", show=True, hint="sk-ant-...")

        # Notion
        section("2.  Notion 설정")
        self.v_nkey = field("Integration 토큰", "notion_key", show=True, hint="ntn_...")
        self.v_ndb  = field("Database ID", "notion_db", hint="32자리")

        # Google Drive
        section("3.  Google Drive")
        # credentials.json 파일 선택
        cf = tk.Frame(frame, bg="#16213e")
        cf.pack(fill="x", padx=20, pady=3)
        tk.Label(cf, text="credentials.json", width=20, anchor="w",
                 font=("Helvetica", 10), bg="#16213e", fg="#cccccc").pack(side="left")
        self.v_cred = tk.StringVar(value=self.cfg.get("cred_file", ""))
        tk.Entry(cf, textvariable=self.v_cred,
                 font=("Helvetica", 10), bg="#0f3460", fg="#ffffff",
                 insertbackground="#ffffff", relief="flat",
                 highlightthickness=1, highlightcolor="#e94560",
                 highlightbackground="#333355").pack(side="left", fill="x",
                                                     expand=True, ipady=5, padx=(0, 6))
        tk.Button(cf, text="찾기", command=self._pick_cred,
                  bg="#e94560", fg="white", relief="flat",
                  font=("Helvetica", 9), padx=8).pack(side="left")

        self.v_gfolder = field("Drive 폴더 ID", "gdrive_folder", hint="folders/ 뒤 ID")

        # 감시 폴더
        section("4.  자동 감시 폴더  (구글 드라이브 동기화 로컬 폴더)")
        wf = tk.Frame(frame, bg="#16213e")
        wf.pack(fill="x", padx=20, pady=3)
        tk.Label(wf, text="감시 폴더 경로", width=20, anchor="w",
                 font=("Helvetica", 10), bg="#16213e", fg="#cccccc").pack(side="left")
        self.v_watch = tk.StringVar(value=self.cfg.get("watch_folder", ""))
        tk.Entry(wf, textvariable=self.v_watch,
                 font=("Helvetica", 10), bg="#0f3460", fg="#ffffff",
                 insertbackground="#ffffff", relief="flat",
                 highlightthickness=1, highlightcolor="#e94560",
                 highlightbackground="#333355").pack(side="left", fill="x",
                                                     expand=True, ipady=5, padx=(0, 6))
        tk.Button(wf, text="찾기", command=self._pick_watch,
                  bg="#e94560", fg="white", relief="flat",
                  font=("Helvetica", 9), padx=8).pack(side="left")

        # 저장 버튼
        tk.Frame(frame, bg="#16213e", height=10).pack()
        tk.Button(frame, text="  💾  설정 저장  ",
                  command=self._save,
                  bg="#e94560", fg="white", relief="flat",
                  font=("Helvetica", 13, "bold"), pady=10).pack(padx=20, fill="x")

        self.lbl_status = tk.Label(frame, text="",
                                   font=("Helvetica", 10),
                                   bg="#16213e", fg="#44cc88")
        self.lbl_status.pack(pady=6)

        # 로그
        tk.Label(frame, text="로그", font=("Helvetica", 9, "bold"),
                 bg="#16213e", fg="#666688").pack(anchor="w", padx=20, pady=(8, 2))
        self.log_box = scrolledtext.ScrolledText(
            frame, height=5, font=("Courier", 9),
            bg="#0a0a1a", fg="#00ff88", relief="flat", state="disabled")
        self.log_box.pack(fill="x", padx=20, pady=(0, 16))

    def _pick_cred(self):
        p = filedialog.askopenfilename(
            title="credentials.json 선택",
            filetypes=[("JSON", "*.json")])
        if p:
            self.v_cred.set(p)

    def _pick_watch(self):
        p = filedialog.askdirectory(title="구글 드라이브 동기화 폴더 선택")
        if p:
            self.v_watch.set(p)

    def _log(self, msg):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _save(self):
        cfg = {
            "anthropic_key": self.v_ant.get().strip(),
            "notion_key":    self.v_nkey.get().strip(),
            "notion_db":     self.v_ndb.get().strip(),
            "cred_file":     self.v_cred.get().strip(),
            "gdrive_folder": self.v_gfolder.get().strip(),
            "watch_folder":  self.v_watch.get().strip(),
        }
        if not all(cfg.values()):
            messagebox.showwarning("입력 확인", "모든 항목을 입력해 주세요.")
            return
        save_config(cfg)
        self.cfg = cfg
        self.lbl_status.config(text="✅  설정이 저장되었습니다! 이제 lp_watcher.py 를 실행하세요.")
        self._log("✅ 설정 저장 완료!")
        self._log("터미널에서: python3 lp_watcher.py")


if __name__ == "__main__":
    root = tk.Tk()
    app = LPApp(root)
    root.mainloop()
