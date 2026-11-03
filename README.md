# Interview recorder

Records your side and the interviewer's side of a video call on separate tracks, then writes a transcript labeled by speaker. Transcription runs on your Mac with Whisper, so the audio never leaves your computer. A Claude skill is included that grades your answers afterward.

Works with Google Meet, Zoom, Teams, or anything else that plays audio through your Mac.

**You need:** a Mac with Apple Silicon (M1 or newer) that you're an administrator on, about 5 GB of free space, and headphones. Without headphones your mic picks up the interviewer, and their words show up as yours in the transcript.

**Ask before you record.** Some states, California included, require everyone on the call to agree. The easy way to handle it is to ask at the start: "Mind if I record this so I can take notes later?"

## 1. Install

Open Terminal, paste this, and press Return:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/EngoyD/interview-recorder/main/install.sh)"
```

Plan on 15 to 20 minutes. It may ask you to press Return and to type your Mac password, possibly more than once. Nothing shows on screen while you type the password; that's normal. Part of the install can sit with no visible progress for several minutes, and the speech model is a 1.6 GB download. One of the things it installs is BlackHole, a free virtual audio device that lets the recorder hear the call. If BlackHole doesn't show up in step 2, restart your Mac.

When it finishes, close Terminal and open a new window before using the `interview` command.

Running the same command later updates you to the newest version.

## 2. Route the call audio (one time, 2 minutes)

The recorder hears the interviewer through BlackHole. This step sends call audio to your headphones and to BlackHole at the same time. Connect your headphones first.

1. Press ⌘Space, type **Audio MIDI Setup**, and open it.
2. Click **+** at the bottom left and choose **Create Multi-Output Device**.
3. On the right, tick your headphones and **BlackHole 2ch**. Set **Primary Device** to your headphones, and tick **Drift Correction** on the BlackHole 2ch row.
4. Double-click the new device's name in the left list and rename it, for example **AirPods + BlackHole**.
5. Click your headphones in the left list and note the sample rate under **Format**. Click **BlackHole 2ch** and set it to the same rate. A mismatch makes audio sound choppy.

Then in your call app, set the **speaker** to the device you just made. In Google Meet that's ⚙ Settings → Audio → Speakers. Leave the microphone alone.

If you use more than one pair of headphones, make a Multi-Output Device for each.

The recorder records your voice from the Mac's current input (System Settings → Sound → Input). Keep that set to the same mic your call app uses.

## 3. Record

Before the call, in Terminal:

```bash
interview acme
```

Swap `acme` for the company name and leave the window open. When the call ends, click the Terminal window and press **q**. Transcribing takes a few minutes, longer for long calls. When Terminal prints `Done:`, the transcript is in `~/interviews/<date>_acme/transcript.md`. In Finder, that's Go → Home → interviews.

The first time, macOS asks whether Terminal can use the microphone. Click Allow. Then do a test: set System Settings → Sound → Output to your Multi-Output Device, play a YouTube video, run `interview test`, talk for at least 20 seconds, and press q. Check that the transcript has both "Me" and "Interviewer" lines. The first recording after allowing the mic may be silent, so test twice if needed. Switch the Mac's output back to your headphones afterward if you like.

Recordings take about 0.7 GB per hour of call. Once a transcript looks right, you can delete the `.wav` files in its folder.

### Optional: a keyboard shortcut instead of Terminal

1. Open **Shortcuts**, go to **Shortcuts → Settings → Advanced**, and turn on **Allow Running Scripts**.
2. Click **+** to make a new shortcut and name it **Interview Recorder**.
3. In the right sidebar, search for **Run Shell Script** and double-click it.
4. Leave the shell set to zsh and replace the script text with:
   ```
   /usr/bin/python3 ~/interviews/interview.py toggle
   ```
5. Click **ⓘ** in the right sidebar, choose **Add Keyboard Shortcut**, and press ⌃⌥⌘R.

Press ⌃⌥⌘R to start and again to stop. Notifications tell you when it starts, stops, and when the transcript is ready. Allow the microphone prompt the first time, then test once more. Shortcut recordings go in folders ending in `_call`.

## 4. Debrief with Claude

The installer saved `~/interviews/interview-debrief.zip`. In Claude, go to **Customize → Skills**, click **+**, choose **Create skill → Upload a skill**, and pick that zip. Skills need **Code execution and file creation** turned on in Settings → Capabilities.

After an interview, start a chat, attach the `transcript.md`, and say "debrief this." Attach the job description or your resume too and the feedback gets more specific. You get a grade for each answer, rewrites of the weak ones, and a list of habits to work on.

## Troubleshooting

**"No speech on the Interviewer side."** The call app's speaker wasn't set to your Multi-Output Device, or your headphones weren't ticked in it. Check step 2. If you plugged in different headphones mid-call, the call app may have switched to them directly.

**"No speech on the Me side."** Open System Settings → Privacy & Security → Microphone and turn on Terminal, Shortcuts, and ffmpeg if they're listed. Also check System Settings → Sound → Input.

**Choppy audio while recording.** A sample-rate mismatch. In Audio MIDI Setup, set your headphones, BlackHole 2ch, and the Multi-Output Device to the same rate.

**The shortcut does nothing.** Open the shortcut in Shortcuts and click ▶ at the top. Any error shows on screen there. Usually it's the microphone permission above. Each recording folder also has a `log.txt`.

**No notifications from the shortcut.** Focus and Do Not Disturb hide them. Also check System Settings → Notifications, where they may be listed under Script Editor. Without notifications you can't tell whether a shortcut recording started, so use Terminal until they show up.

**"Recording stopped on its own."** One of the audio devices dropped out partway through the call, for example headphones disconnecting. The transcript covers the part before that. Start a new recording to capture the rest.

**Volume keys don't work.** macOS often won't change the volume of a Multi-Output Device. Set the volume in the call app or on your headphones.

**Using a specific mic.** By default the recorder uses whatever input macOS has selected. To always use one mic, list the names with `ffmpeg -f avfoundation -list_devices true -i ""`, then save the one you want, for example:
```bash
echo "MacBook Air Microphone" > ~/interviews/mic.txt
```
Delete `mic.txt` to go back to the default.

## Uninstall

```bash
rm /opt/homebrew/bin/interview
brew uninstall ffmpeg whisper-cpp
brew uninstall --cask blackhole-2ch
```

Then delete `~/interviews` in Finder. That folder also holds your recordings, so move anything you want to keep first.
