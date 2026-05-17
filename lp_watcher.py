"""
LP 폴더 자동 감시 프로그램
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
구글 드라이브 동기화 폴더를 감시하다가
새 사진이 생기면 자동으로 처리합니다.

실행: python3 lp_watcher.py
종료: Ctrl+C
"""

import os
import sys
import time
import json
import base64
import io
import pickle
import subprocess
import threading
from pathlib import Path
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from anthropic import Anthropic
from notion_client import Client
from PIL import Image
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

CONFIG_FILE    = "lp_config.json"
PROCESSED_FILE = "lp_processed.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"}
GDRIVE_SCOPES    = ["https://www.googleapis.com/auth/drive.file"]


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def notify_mac(title: str, message: str):
    try:
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"'
        ], check=False)
    except Exception:
        pass


def load_processed() -> set:
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()


def save_processed(processed: set):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(list(processed), f)


def get_gdrive_service(cred_file: str):
    creds = None
    token_path = "token.pickle"
    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_file, GDRIVE_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)
    return build("drive", "v3", credentials=creds)


def process_one(image_path: Path, cfg: dict, gdrive, anthropic_client, notion_client, seq: int) -> bool:
    log(f"📀 처리 시작: {image_path.name}")

    # 파일 크기 체크 (100KB 미만이면 iCloud 동기화 미완료로 판단)
    if image_path.stat().st_size < 100 * 1024:
        log(f'  ⚠️  파일이 너무 작습니다 ({image_path.stat().st_size//1024}KB) — 나중에 재시도합니다.')
        return "RETRY"

    try:
        original = Image.open(image_path)
        # EXIF 방향 자동 보정
        try:
            from PIL import ImageOps
            original = ImageOps.exif_transpose(original)
           
        except:
            pass
        original = original.convert("RGB")
    except Exception as e:
        log(f"  ❌ 이미지 열기 실패: {e}")
        return False

    w, h = original.size

    # 5MB 이하로 리사이즈
    buf_orig = io.BytesIO()
    original.save(buf_orig, format="JPEG", quality=85)
    while buf_orig.tell() > 3 * 1024 * 1024:
        new_w = int(original.width * 0.9)
        new_h = int(original.height * 0.9)
        original = original.resize((new_w, new_h), Image.LANCZOS)
        w, h = original.size
        buf_orig = io.BytesIO()
        original.save(buf_orig, format="JPEG", quality=85)
        log(f"  🔄 리사이즈: {new_w}x{new_h} ({buf_orig.tell()//1024}KB)")

    b64 = base64.standard_b64encode(buf_orig.getvalue()).decode()
    mt  = "image/jpeg"

    # 크롭 없이 원본 사용
    cropped = original
    log("  📸 원본 이미지 사용")

    log("  ☁️  Google Drive 업로드 중...")
    buf = io.BytesIO()
    cropped.save(buf, format="JPEG", quality=90)
    fname = f"LP_CROP_{image_path.stem}.jpg"
    meta  = {"name": fname, "parents": [cfg["gdrive_folder"]]}

    # 최대 3번 재시도
    img_url = None
    for attempt in range(3):
        try:
            mu = MediaIoBaseUpload(io.BytesIO(buf.getvalue()), mimetype="image/jpeg")
            up = gdrive.files().create(body=meta, media_body=mu, fields="id").execute()
            fid = up.get("id")
            gdrive.permissions().create(fileId=fid, body={"type": "anyone", "role": "reader"}).execute()
            img_url = f"https://drive.google.com/thumbnail?id={fid}&sz=w800"
            log("  ✅ 업로드 완료")
            break
        except Exception as e:
            if attempt < 2:
                log(f"  ⚠️  업로드 실패, 재시도 중... ({attempt+1}/3)")
                time.sleep(3)
            else:
                raise e
    # ── STEP 3: 앨범 정보 분석
    log("  🔍 앨범 정보 분석 중...")
    info_resp = anthropic_client.messages.create(
        model="claude-sonnet-4-6", max_tokens=600,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}},
            {"type": "text", "text":
             'LP 재킷 이미지를 분석해서 아래 JSON 형식으로만 반환해주세요. '
             '알 수 없는 항목은 빈 문자열로 두세요.\n'
             '{"title":"앨범타이틀","composer":"작곡자","performer":"연주자(솔리스트)",'
             '"orchestra":"연주단체(오케스트라/앙상블)","conductor":"지휘자",'
             '"label":"레이블(레코드사)","serial":"시리얼번호","year":"발매년도(숫자만)",'
             '"genre":"장르(Classical/Jazz/Pop/Rock/Blues 등)","memo":"기타특이사항"}'}
        ]}]
    )
    raw2 = info_resp.content[0].text.strip()
    if "```" in raw2:
        raw2 = raw2.split("```")[1]
        if raw2.startswith("json"): raw2 = raw2[4:]
    try:
        lp = json.loads(raw2.strip())
    except Exception:
        lp = {"title": image_path.stem, "composer": "", "performer": "",
              "orchestra": "", "conductor": "", "label": "", "serial": "",
              "year": "", "genre": "", "memo": "자동 인식 실패"}

    # ── STEP 4: Notion 저장
    catalog = f"LP-{seq:04d}"
    year_num = None
    try:
        year_num = int(str(lp.get("year", ""))[:4])
    except Exception:
        pass

    props = {
        "타이틀":   {"title":     [{"text": {"content": lp.get("title", "") or image_path.stem}}]},
        "분류번호": {"rich_text": [{"text": {"content": catalog}}]},
        "장르":     {"rich_text": [{"text": {"content": lp.get("genre", "")}}]},
        "작곡자":   {"rich_text": [{"text": {"content": lp.get("composer", "")}}]},
        "연주자":   {"rich_text": [{"text": {"content": lp.get("performer", "")}}]},
        "연주단체": {"rich_text": [{"text": {"content": lp.get("orchestra", "")}}]},
        "지휘자":   {"rich_text": [{"text": {"content": lp.get("conductor", "")}}]},
        "레이블":   {"rich_text": [{"text": {"content": lp.get("label", "")}}]},
        "시리얼번호": {"rich_text": [{"text": {"content": lp.get("serial", "")}}]},
        "랙위치":   {"select": None},
        "메모":     {"rich_text": [{"text": {"content": lp.get("memo", "")}}]},
    }
    if year_num:
        props["발매년도"] = {"number": year_num}

    page = notion_client.pages.create(
        parent={"database_id": cfg["notion_db"]},
        properties=props,
        cover={"type": "external", "external": {"url": img_url}},
    )
    notion_client.blocks.children.append(
        block_id=page["id"],
        children=[{"object": "block", "type": "image",
                   "image": {"type": "external", "external": {"url": img_url}}}]
    )

    log(f"  ✅ [{catalog}] {lp.get('title', '-')} / {lp.get('composer', '-')} 저장 완료!")
    notify_mac("LP 등록 완료 🎵", f"{catalog} {lp.get('title', image_path.name)}")
    return True


class LPFolderHandler(FileSystemEventHandler):
    def __init__(self, cfg, gdrive, anthropic_client, notion_client, processed, seq_ref):
        self.cfg              = cfg
        self.gdrive           = gdrive
        self.anthropic_client = anthropic_client
        self.notion_client    = notion_client
        self.processed        = processed
        self.seq_ref          = seq_ref
        self._lock            = threading.Lock()
        self._pending         = {}

    def on_created(self, event):
        if not event.is_directory:
            p = Path(event.src_path)
            if p.suffix.lower() in IMAGE_EXTENSIONS and not p.name.startswith("LP_CROP_"):
                self._pending[str(p)] = time.time()

    def on_modified(self, event):
        self.on_created(event)

    def flush_pending(self):
        now = time.time()
        to_process = [p for p, t in list(self._pending.items()) if now - t >= 2.0]
        for p in to_process:
            del self._pending[p]
            path = Path(p)
            if str(path) in self.processed or not path.exists():
                continue
            with self._lock:
                try:
                    self.seq_ref[0] += 1
                    success = process_one(
                        path, self.cfg, self.gdrive,
                        self.anthropic_client, self.notion_client,
                        self.seq_ref[0]
                    )
                    if success == "RETRY":
                        log(f"  🔄 동기화 대기 중, 5분 후 재시도: {path.name}")
                        self._pending[str(path)] = time.time() + 300
                        self.seq_ref[0] -= 1
                    elif success:
                        self.processed.add(str(path))
                        save_processed(self.processed)
                    else:
                        self.seq_ref[0] -= 1
                except Exception as e:
                    log(f"  ❌ 처리 오류: {e}")
                    self.seq_ref[0] -= 1
                time.sleep(1)


def main():
    if not os.path.exists(CONFIG_FILE):
        print("❌ 설정 파일이 없습니다. 먼저 lp_setup.py 를 실행해 설정을 저장해 주세요.")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        cfg = json.load(f)

    watch_folder = cfg.get("watch_folder", "")
    if not watch_folder or not Path(watch_folder).exists():
        print("❌ 감시 폴더가 설정되지 않았습니다.")
        print("   lp_setup.py 를 먼저 실행해 주세요.")
        sys.exit(1)

    print("=" * 52)
    print("  🎵  LP to Notion  —  자동 감시 모드")
    print("=" * 52)
    log(f"감시 폴더: {watch_folder}")
    log("Google Drive 인증 중...")

    gdrive           = get_gdrive_service(cfg["cred_file"])
    anthropic_client = Anthropic(api_key=cfg["anthropic_key"])
    notion_client    = Client(auth=cfg["notion_key"])

    log("✅ 연결 완료!")

    processed = load_processed()
    total = 0
    cursor = None
    while True:
        if cursor:
            existing = notion_client.databases.query(database_id=cfg["notion_db"], start_cursor=cursor)
        else:
            existing = notion_client.databases.query(database_id=cfg["notion_db"])
        total += len(existing.get("results", []))
        if not existing.get("has_more"):
            break
        cursor = existing.get("next_cursor")
    seq_ref = [total]
    log(f"현재 Notion DB: {seq_ref[0]}장 등록됨. 다음 번호: LP-{seq_ref[0]+1:04d}")

    # 폴더에 이미 있는 미처리 파일 먼저 처리
    existing_images = sorted([
        f for f in Path(watch_folder).iterdir()
        if f.suffix.lower() in IMAGE_EXTENSIONS and str(f) not in processed and not f.name.startswith("LP_CROP_")
    ])
    if existing_images:
        log(f"📂 미처리 사진 {len(existing_images)}장 발견 — 처리 시작!\n")
        for img in existing_images:
            try:
                seq_ref[0] += 1
                success = process_one(img, cfg, gdrive, anthropic_client, notion_client, seq_ref[0])
                if success:
                    processed.add(str(img))
                    save_processed(processed)
                else:
                    seq_ref[0] -= 1
            except Exception as e:
                log(f"  ❌ 오류: {e}")
                seq_ref[0] -= 1
            time.sleep(1)

    log("📂 새 사진을 기다리는 중... (종료: Ctrl+C)\n")
    notify_mac("LP Watcher 시작 🎵", f"감시 폴더: {Path(watch_folder).name}")

    handler  = LPFolderHandler(cfg, gdrive, anthropic_client, notion_client, processed, seq_ref)
    observer = Observer()
    observer.schedule(handler, watch_folder, recursive=False)
    observer.start()

    try:
        while True:
            handler.flush_pending()
            time.sleep(0.5)
    except KeyboardInterrupt:
        log("감시 종료.")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
