#!/bin/bash
# Installs the interview recorder into ~/interviews. Safe to run again to update.
# Run with:  bash -c "$(curl -fsSL https://raw.githubusercontent.com/EngoyD/interview-recorder/main/install.sh)"
set -euo pipefail

RAW="https://raw.githubusercontent.com/EngoyD/interview-recorder/main"
DIR="$HOME/interviews"
MODELS=(
  "ggml-large-v3-turbo.bin|https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin|1fc70f774d38eb169993ac391eea357ef47c88757ef72ee5943879b7e8e2bc69"
  "ggml-silero-v6.2.0.bin|https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin|2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987"
)

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
die() { printf '\n\033[31mError: %s\033[0m\n' "$1" >&2; exit 1; }

[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || die "This needs a Mac with Apple Silicon (M1 or newer)."

step "Homebrew"
if [[ -x /opt/homebrew/bin/brew ]]; then
  echo "Already installed."
else
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # shellcheck disable=SC2016  # written literally so brew loads in every new Terminal window
  grep -qs 'brew shellenv' "$HOME/.zprofile" || echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
fi
eval "$(/opt/homebrew/bin/brew shellenv)"

step "ffmpeg and whisper.cpp"
brew install ffmpeg whisper-cpp

step "BlackHole (macOS will ask for your password)"
brew install --cask blackhole-2ch

step "Recorder"
mkdir -p "$DIR/models"
curl -fsSL "$RAW/interview.py" -o "$DIR/interview.py.new"
if [[ -f "$DIR/interview.py" ]] && ! cmp -s "$DIR/interview.py" "$DIR/interview.py.new"; then
  cp "$DIR/interview.py" "$DIR/interview.py.bak"
  echo "Saved your previous version as interview.py.bak"
fi
mv "$DIR/interview.py.new" "$DIR/interview.py"
chmod +x "$DIR/interview.py"
ln -sf "$DIR/interview.py" /opt/homebrew/bin/interview

step "Debrief skill for Claude"
mkdir -p "$DIR/interview-debrief"
curl -fsSL "$RAW/skill/interview-debrief/SKILL.md" -o "$DIR/interview-debrief/SKILL.md"
rm -f "$DIR/interview-debrief.zip"
(cd "$DIR" && zip -qr interview-debrief.zip interview-debrief)
echo "Saved $DIR/interview-debrief.zip"

step "Speech models (about 1.6 GB, the first time only)"
for entry in "${MODELS[@]}"; do
  IFS='|' read -r name url sha <<< "$entry"
  dest="$DIR/models/$name"
  if [[ -f "$dest" ]] && [[ "$(shasum -a 256 "$dest" | cut -d' ' -f1)" == "$sha" ]]; then
    echo "$name already downloaded."
    continue
  fi
  curl -fL --retry 3 -C - "$url" -o "$dest.part"
  [[ "$(shasum -a 256 "$dest.part" | cut -d' ' -f1)" == "$sha" ]] || { rm -f "$dest.part"; die "$name didn't download correctly. Run the installer again."; }
  mv "$dest.part" "$dest"
done

step "Done"
cat <<'EOF'
Two things left, both in the README:
  1. Audio MIDI Setup: create a Multi-Output Device with your headphones and BlackHole 2ch.
  2. Optional: a keyboard shortcut to start and stop recording.

Then open a NEW Terminal window, and before a call run:  interview acme
(press q when the call ends)

README: https://github.com/EngoyD/interview-recorder#readme
EOF
