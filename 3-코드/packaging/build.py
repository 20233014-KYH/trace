"""
build.py — 설치판 만들기 (v0.1 · 10/13)

  python 3-코드/packaging/build.py             # 이 OS 용으로 묶고 → 자체 시험 → (윈도우) 설치 파일
  python 3-코드/packaging/build.py --no-installer

결과 (packaging/dist/):
  Trace/                       묶인 앱 폴더 (Trace.exe + _internal)
  Trace-Setup-<버전>.exe        윈도우 설치 파일 (Inno Setup · 관리자 권한 없이 내 계정에 설치)
  Trace-<버전>-extension.zip    크롬 확장 (압축 풀어 "압축해제된 확장 프로그램 로드")

GitHub 에서는 .github/workflows/release.yml 이 태그(v0.1.0)를 올릴 때 윈도우에서 이걸 부르고 릴리스에 올린다.
버전은 core/version.py 하나 — 태그와 다르면 멈춘다.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                         # 3-코드
DIST, WORK = os.path.join(HERE, "dist"), os.path.join(HERE, "build")
sys.path.insert(0, ROOT)
from core.version import VERSION                    # noqa: E402
from core import settings                           # noqa: E402

WIN = sys.platform == "win32"


def 단계(t):
    print(f"\n━━ {t}", flush=True)


def 버전_확인():
    tag = os.environ.get("GITHUB_REF_NAME", "") if os.environ.get("GITHUB_REF_TYPE") == "tag" else ""
    if tag and tag.lstrip("vV") != VERSION:
        sys.exit(f"태그 {tag} 와 core/version.py ({VERSION}) 가 다릅니다 — version.py 를 고치고 다시 태그를 다세요")
    print(f"버전 {VERSION}" + (f" · 태그 {tag}" if tag else ""))


def 아이콘():
    """앱 아이콘 = app/trace.ico (기록 창 작업 표시줄과 같은 것 · 10/13 박상진 — 점 흐림을 반투명 대신 색을 섞어 그림)"""
    os.makedirs(WORK, exist_ok=True)
    shutil.copyfile(os.path.join(ROOT, "app", "trace.ico"), os.path.join(WORK, "trace.ico"))

def 버전_정보():
    """윈도우 파일 속성의 버전 (탐색기 · 작업 관리자에 보이는 이름)"""
    n = tuple(int(x) for x in re.findall(r"\d+", VERSION)[:3]) + (0,)
    n = (n + (0, 0, 0, 0))[:4]
    os.makedirs(WORK, exist_ok=True)
    with open(os.path.join(WORK, "version_info.txt"), "w", encoding="utf-8") as f:
        f.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={n}, prodvers={n}),
  kids=[StringFileInfo([StringTable('041204B0', [
    StringStruct('CompanyName', 'Trace'),
    StringStruct('FileDescription', 'Trace — AI 활용 기록'),
    StringStruct('FileVersion', '{VERSION}'),
    StringStruct('ProductName', 'Trace'),
    StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [0x0412, 1200])])]
)
""")


def 묶기():
    shutil.rmtree(os.path.join(DIST, "Trace"), ignore_errors=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", os.path.join(HERE, "trace.spec"), "--noconfirm",
                    "--distpath", DIST, "--workpath", os.path.join(WORK, "work")], check=True)


def 자체_시험():
    exe = os.path.join(DIST, "Trace", "Trace.exe" if WIN else "Trace")
    결과 = os.path.join(settings.app_data(), "selftest.txt")
    if os.path.exists(결과):
        os.remove(결과)
    r = subprocess.run([exe, "--selftest"], timeout=300)
    글 = open(결과, encoding="utf-8").read() if os.path.exists(결과) else "(결과 파일 없음 — 로그를 보세요)"
    print(글)
    if r.returncode != 0:
        로그 = os.path.join(settings.app_data(), "logs", "selftest.log")
        if os.path.exists(로그):
            print(open(로그, encoding="utf-8").read()[-6000:])
        sys.exit(f"자체 시험 실패 (exit {r.returncode})")


def iscc():
    for p in (shutil.which("iscc"), r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe", r"C:\Program Files\Inno Setup 6\ISCC.exe"):
        if p and os.path.exists(p):
            return p
    return None


def 설치_파일():
    exe = iscc()
    if not exe:
        sys.exit("Inno Setup 이 없습니다 — choco install innosetup  (또는 --no-installer)")
    인자 = [exe, f"/DAppVersion={VERSION}", f"/DSourceDir={os.path.join(DIST, 'Trace')}", f"/DOutDir={DIST}"]
    if os.path.exists(os.path.join(os.path.dirname(exe), "Languages", "Korean.isl")):
        인자.append("/DKorean")
    if os.path.exists(os.path.join(WORK, "trace.ico")):
        인자.append(f"/DIconFile={os.path.join(WORK, 'trace.ico')}")
    subprocess.run(인자 + [os.path.join(HERE, "trace.iss")], check=True)


def 확장_zip():
    src = os.path.join(ROOT, "extension")
    out = os.path.join(DIST, f"Trace-{VERSION}-extension.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for d, dirs, files in os.walk(src):
            dirs[:] = [x for x in dirs if x not in ("test", "__pycache__")]
            for f in files:
                p = os.path.join(d, f)
                z.write(p, os.path.join("trace-extension", os.path.relpath(p, src)))
    print(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-installer", action="store_true")
    a = ap.parse_args()
    단계("버전"); 버전_확인()
    단계("아이콘 · 버전 정보"); 아이콘(); 버전_정보()
    단계("PyInstaller"); 묶기()
    단계("자체 시험"); 자체_시험()
    if WIN and not a.no_installer:
        단계("설치 파일 (Inno Setup)"); 설치_파일()
    단계("크롬 확장 zip"); 확장_zip()
    단계("끝")
    for n in sorted(os.listdir(DIST)):
        p = os.path.join(DIST, n)
        if os.path.isfile(p):
            print(f"  {n}  {os.path.getsize(p) // 1048576}MB")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    main()
