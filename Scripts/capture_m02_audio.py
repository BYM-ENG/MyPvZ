"""GUI editor-only check: render the imported sample through the real mixer.

Launch with -ExecutePythonScript=<this file>, without -nullrhi/-nosound.
The editor remains open after recording, for visual inspection and normal exit.
"""
import array
import json
import math
from pathlib import Path
import time
import wave

import unreal

unreal.EditorPythonScripting.set_keep_python_script_alive(True)
root = Path(unreal.Paths.project_dir()).resolve()
output = root / "Saved" / "Diagnostics" / "M02"
output.mkdir(parents=True, exist_ok=True)
recording = output / "M02_Mixer.wav"
request = output / "start_audio_capture.flag"
if recording.exists():
    raise RuntimeError("Remove or archive the previous M02_Mixer.wav before a new capture")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.CameraActor):
    unreal.log("M02 CAMERA DIAGNOSTIC: " + str(actor.get_actor_rotation()) + " forward=" + str(actor.get_actor_forward_vector()))
sound = unreal.load_asset("/Game/M02/Audio/SW_SeedTrial")
if sound is None:
    raise RuntimeError("Import M02 before recording")

started = time.monotonic()
phase = 0
component = None
handle = None


def tick(delta_seconds):
    global phase, started, component, handle
    elapsed = time.monotonic() - started
    try:
        if phase == 0 and request.exists():
            unreal.AudioMixerLibrary.start_recording_output(world, 3.0)
            phase = 1
            started = time.monotonic()
        elif phase == 1 and elapsed >= 0.25:
            component = unreal.GameplayStatics.spawn_sound2d(
                world, sound, volume_multiplier=1.0, pitch_multiplier=1.0,
                auto_destroy=False)
            if component is None:
                raise RuntimeError("Audio component was not created")
            phase = 2
            started = time.monotonic()
        elif phase == 2 and elapsed >= 1.1:
            component.stop()
            phase = 3
            started = time.monotonic()
        elif phase == 3 and elapsed >= 0.5:
            unreal.AudioMixerLibrary.stop_recording_output(
                world, unreal.AudioRecordingExportType.WAV_FILE,
                "M02_Mixer", str(output))
            phase = 4
            started = time.monotonic()
        elif phase == 4 and recording.exists() and elapsed >= 1.0:
            with wave.open(str(recording), "rb") as wav:
                assert wav.getsampwidth() == 2, "Expected PCM16 mixer export"
                samples = array.array("h", wav.readframes(wav.getnframes()))
                result = {
                    "channels": wav.getnchannels(), "sample_rate": wav.getframerate(),
                    "duration_seconds": wav.getnframes() / wav.getframerate(),
                    "peak": max(abs(x) for x in samples) / 32768,
                    "rms": math.sqrt(sum(x*x for x in samples) / len(samples)) / 32768,
                    "nonzero_samples": sum(x != 0 for x in samples),
                }
            assert result["peak"] > 0.01 and result["rms"] > 0.001, result
            assert result["nonzero_samples"] > 1000, result
            (output / "mixer_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            unreal.log("M02 MIXER CAPTURE PASSED: " + json.dumps(result))
            unreal.unregister_slate_post_tick_callback(handle)
            phase = 5
        elif elapsed > (180.0 if phase == 0 else 20.0):
            raise RuntimeError("Timed out waiting for audio capture phase " + str(phase))
    except Exception:
        if component is not None:
            component.stop()
        unreal.unregister_slate_post_tick_callback(handle)
        raise


handle = unreal.register_slate_post_tick_callback(tick)
unreal.log("M02 mixer capture ready: activate editor, then create Saved/Diagnostics/M02/start_audio_capture.flag")
