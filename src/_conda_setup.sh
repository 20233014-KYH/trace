# conda 를 찾아 trace 환경을 켠다. (맥용 .command 파일들이 공통으로 쓴다)
#
# ★ 변수 이름이 전부 영어인 이유 ★
#   파이썬은 한글 이름을 써도 되지만 배시(터미널 언어)는 안 된다.
#   한글로 썼다가 "not a valid identifier" 로 스크립트가 통째로 깨졌다.

find_conda() {
  for candidate in "$HOME/anaconda3" "$HOME/miniconda3" "$HOME/opt/anaconda3" \
                   "$HOME/miniforge3" "/opt/homebrew/anaconda3" "/opt/anaconda3"; do
    if [ -f "$candidate/etc/profile.d/conda.sh" ]; then echo "$candidate"; return 0; fi
  done
  if command -v conda >/dev/null 2>&1; then conda info --base 2>/dev/null; return 0; fi
  return 1
}

CONDA_HOME="$(find_conda)"
if [ -z "$CONDA_HOME" ] || [ ! -f "$CONDA_HOME/etc/profile.d/conda.sh" ]; then
  echo ""; echo "  conda 를 찾지 못했습니다. Anaconda 가 설치되어 있나요?"; echo ""
  read -n 1 -s -r -p "  아무 키나 누르면 닫힙니다..."; exit 1
fi

. "$CONDA_HOME/etc/profile.d/conda.sh"

if ! conda activate trace 2>/dev/null; then
  echo ""
  echo "  'trace' 환경이 없습니다. 처음 한 번만 아래를 터미널에 치세요:"
  echo ""
  echo "      conda create -n trace python=3.11 -y"
  echo "      conda activate trace"
  echo "      pip install -r requirements.txt"
  echo ""
  read -n 1 -s -r -p "  아무 키나 누르면 닫힙니다..."; exit 1
fi
