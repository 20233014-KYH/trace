"""
git_watch.py — 감시 폴더 안의 git 저장소에서 커밋·푸시를 잡는다.

커밋은 그 자체가 "시각 + 해시 + 바뀐 파일·줄 수"를 가진 기록이라 체인과 성격이 같다.
증명서에서 커밋 해시와 체인 안 이벤트를 대조할 수 있다 (로드맵 결정 13).

  이벤트(두 모드 · 체인):  commit    {repo, hash, branch, files, added, removed}     내용 없음 — 메시지도 안 넣는다
                          git_push  {repo, remote_ref, hash}                        origin/main 이 새 커밋을 가리키게 됨
  맥락(Learn 만):          commit    커밋 메시지 (≤200자) · meta {repo, hash}

5초마다 `git rev-parse HEAD` · `git for-each-ref refs/remotes` 만 돌린다 (가볍다). git 이 없으면 조용히 꺼진다.
"""
import os
import shutil
import subprocess
import threading

POLL_SEC = 5.0
MAX_MSG = 200
_GIT = shutil.which("git")


def _git(repo: str, *args: str) -> str:
    try:
        r = subprocess.run([_GIT, "-C", repo, *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def find_repos(dirs: list[str], max_depth: int = 2) -> list[str]:
    """감시 폴더와 그 아래 2단계까지 .git 이 있는 폴더"""
    out = []
    for d in dirs:
        base_depth = d.rstrip(os.sep).count(os.sep)
        for root, subdirs, _ in os.walk(d):
            if ".git" in subdirs:
                out.append(root)
                subdirs[:] = []                       # 저장소 안은 더 안 들어감
                continue
            if root.count(os.sep) - base_depth >= max_depth:
                subdirs[:] = []
            subdirs[:] = [s for s in subdirs if s not in ("node_modules", ".venv", "__pycache__")]
    return out


class GitWatcher(threading.Thread):
    def __init__(self, dirs: list[str], emit_event, emit_context=None, note=print, poll_sec: float = POLL_SEC):
        super().__init__(daemon=True)
        self.emit_event, self.emit_context, self.note, self.poll = emit_event, emit_context, note, float(poll_sec)
        self.repos = find_repos(dirs) if _GIT else []
        self._head: dict[str, str] = {}               # repo → HEAD 해시
        self._remotes: dict[str, dict[str, str]] = {} # repo → {origin/main: 해시}
        self._stop = threading.Event()
        for r in self.repos:                          # 시작 상태 — 이후 바뀐 것만 이벤트
            self._head[r] = _git(r, "rev-parse", "HEAD")
            self._remotes[r] = self._remote_refs(r)

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            for r in self.repos:
                try:
                    self._tick(r)
                except Exception as e:                # git 이 잠깐 잠겨 있어도 감시는 계속
                    self.note(f"        · git 감시 오류 {os.path.basename(r)}: {e}")
            self._stop.wait(self.poll)

    def _remote_refs(self, repo: str) -> dict[str, str]:
        out = {}
        for line in _git(repo, "for-each-ref", "refs/remotes", "--format=%(refname:short) %(objectname)").splitlines():
            parts = line.split()
            if len(parts) == 2 and not parts[0].endswith("/HEAD"):
                out[parts[0]] = parts[1]
        return out

    def _tick(self, repo: str):
        name = os.path.basename(repo)
        head = _git(repo, "rev-parse", "HEAD")
        old = self._head.get(repo)
        if head and head != old:
            self._head[repo] = head
            # old..head 사이 새 커밋들. amend·rebase·checkout 이면 old 가 조상이 아니므로 head 하나만
            if old and self._is_ancestor(repo, old, head):
                hashes = _git(repo, "rev-list", "--reverse", f"{old}..{head}").splitlines() or [head]
            else:
                hashes = [head]
            branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
            for h in hashes[-20:]:                    # 한꺼번에 많이 와도 최근 20개까지만
                self._commit(repo, name, h, branch)
        remotes = self._remote_refs(repo)
        for ref, h in remotes.items():
            if self._remotes.get(repo, {}).get(ref) != h:
                self.emit_event({"type": "git_push", "repo": name, "remote_ref": ref, "hash": h[:12]})
        self._remotes[repo] = remotes

    def _is_ancestor(self, repo: str, a: str, b: str) -> bool:
        r = subprocess.run([_GIT, "-C", repo, "merge-base", "--is-ancestor", a, b], capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return r.returncode == 0

    def _commit(self, repo: str, name: str, h: str, branch: str):
        files = added = removed = 0
        for line in _git(repo, "show", "--numstat", "--format=", h).splitlines():
            p = line.split("\t")
            if len(p) >= 2:
                files += 1
                added += int(p[0]) if p[0].isdigit() else 0
                removed += int(p[1]) if p[1].isdigit() else 0
        self.emit_event({"type": "commit", "repo": name, "hash": h[:12], "branch": branch, "files": files, "added": added, "removed": removed})
        if self.emit_context:
            msg = _git(repo, "log", "-1", "--format=%s%n%b", h).strip()
            if msg:
                self.emit_context([_item("commit", msg[:MAX_MSG], {"repo": name, "hash": h[:12], "branch": branch})])


def _item(kind: str, text: str, meta: dict) -> dict:
    import uuid
    from datetime import datetime, timedelta, timezone
    return {"id": str(uuid.uuid4()), "ts": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"),
            "source": "git", "kind": kind, "text": text, "meta": meta}
