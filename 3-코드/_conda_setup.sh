# conda 를 찾아 trace 환경을 켠다. 맥용 .command 파일들이 공통으로 쓴다.
# ★ 변수 이름이 전부 영어인 이유 — 배시·zsh 는 한글 변수명을 못 쓴다.
find_conda() {
  for c in "$HOME/anaconda3" "$HOME/miniconda3" "$HOME/opt/anaconda3" \
           "$HOME/miniforge3" "/opt/homebrew/anaconda3" "/opt/anaconda3"; do
    [ -f "$c/etc/profile.d/conda.sh" ] && echo "$c" && return 0
  done
  command -v conda >/dev/null 2>&1 && conda info --base 2>/dev/null && return 0
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
  echo "  'trace' 환경이 없습니다. 처음 한 번만:"
  echo ""
  echo "      conda create -n trace python=3.11 -y"
  echo "      conda activate trace"
  echo "      pip install -r requirements.txt"
  echo ""
  read -n 1 -s -r -p "  아무 키나 누르면 닫힙니다..."; exit 1
fi
