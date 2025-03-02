#!/usr/bin/env python3
import os, sys, time, threading, queue
from time import sleep
from dotenv import load_dotenv
from pjsua2 import *

sys.path.insert(0, '/opt/pjproject/pjsip-apps/src/python')
sys.path.insert(0, '/usr/local/lib/python3.8/dist-packages')
print("Current sys.path:", sys.path)
load_dotenv()

"""
VOIP Server Implementation using pjsua2 with .env configuration.
Handles both incoming text messages and voice calls.
- Incoming texts are directly forwarded to idea_summarizer.py.
- For voice calls:
    • A greeting message is played.
    • The call is recorded until it ends.
    • The recorded audio is converted to a 16kHz WAV file.
    • whisper.cpp (assumed to be available as an executable) transcribes the audio.
    • The transcription text is forwarded to idea_summarizer.py.
"""

recording_queue = queue.Queue()

def generate_unique_filename(prefix="recording", ext="wav"):
    return f"{prefix}_{int(time.time() * 1000)}.{ext}"

def transcription_worker():
    while True:
        recording_file = recording_queue.get()
        if recording_file is None:
            break
        try:
            print(f"[Transcription] Transcribing file: {recording_file}")
            cmd_whisper = ["whisper.exe", recording_file]
            result = subprocess.run(cmd_whisper, capture_output=True, text=True, check=True)
            transcription = result.stdout.strip()
            print(f"[Transcription] Result for {recording_file}: {len(transcription.split(' '))} words")
            #Idea Summarize
        except Exception as e:
            print(f"[Transcription] Error processing {recording_file}: {e}")
        finally:
            recording_queue.task_done()

# Define the Account callback to handle incoming calls and messages
class MyAccount(Account):
    def __init__(self):
        super().__init__()
        self.calls = []

    def onRegState(self, prm):
        print(f"Registration state: {prm.code} ({prm.reason})")

    def onIncomingCall(self, prm):
        print("Incoming call...")
        call = MyCall(self, prm.callId)
        self.calls.append(call)
        call_prm = CallOpParam()
        call_prm.statusCode = 180  # 180 Ringing
        call.answer(call_prm)
        call_prm.statusCode = 200
        call.answer(call_prm)
        print("Incoming call answered.")

    def onInstantMessage(self, prm):
        # Handle incoming text messages
        text = prm.content
        print("Received text message:", text)
        forward_text_to_idea_summarizer(text)

# Define the Call callback to manage call media and state
class MyCall(Call):
    def __init__(self, acc, call_id=PJSUA_INVALID_ID):
        super().__init__(acc, call_id)
        self.record_file = generate_unique_filename()
        self.player = None
        self.recorder = None
        self.audio_med = None

    def onCallState(self, prm):
        ci = self.getInfo()
        print(f"[Call] State: {ci.stateText}")
        print(f"[Call] Incoming call from: {ci.remoteUri}")
        if ci.state == PJSIP_INV_STATE_DISCONNECTED:
            if self.recorder:
                time.sleep(1)
                print(f"[Call] Call disconnected. Pushing {self.record_file} to transcription queue.")
                recording_queue.put(self.record_file)
            self.cleanup()

    def onCallMediaState(self, prm):
        ci = self.getInfo()
        for mi in ci.media:
            if mi.type == PJMEDIA_TYPE_AUDIO and \
               (mi.status == PJSUA_CALL_MEDIA_ACTIVE or 
                mi.status == PJSUA_CALL_MEDIA_REMOTE_HOLD):
                try:
                    self.audio_med = self.getAudioMedia(mi.index)
                    self.start_audio(self.audio_med)
                except Exception as e:
                    print("[Call] Error getting audio media:", e)

    def start_audio(self, audio_med):
        try:
            greeting_file = os.getenv("GREETING_WAV", "greeting.wav")
            if os.path.exists(greeting_file):
                self.player = AudioMediaPlayer()
                self.player.createPlayer(greeting_file)
                self.player.startTransmit(audio_med)
                print("[Call] Playing greeting audio.")
            else:
                print("[Call] Greeting file not found, skipping playback.")
            self.recorder = AudioMediaRecorder()
            self.recorder.createRecorder(self.record_file)
            audio_med.startTransmit(self.recorder)
            print(f"[Call] Recording call audio to {self.record_file}.")
        except Exception as e:
            print("[Call] Error in start_audio:", e)

    def cleanup(self):
        try:
            if self.audio_med:
                if self.player:
                    self.audio_med.stopTransmit(self.player)
                    self.player = None
                if self.recorder:
                    self.audio_med.stopTransmit(self.recorder)
                    self.recorder = None
            # Ensure the call is properly hung up.
            self.hangup(CallOpParam())
        except Exception as e:
            print("[Call] Error during cleanup:", e)

def place_call(account, dest_uri):
    call = MyCall(account)
    call_prm = CallOpParam(True)
    try:
        call.makeCall(dest_uri, call_prm)
        print("[Outgoing] Placing call to {dest_uri}.")
    except Exception as e:
        print("[Outgoing] Error placing call:", e)

def forward_text_to_idea_summarizer(text):
    """
    Forwards the given text to idea_summarizer.py.
    The idea_summarizer.py script is expected to read the text argument and process it.
    """
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "idea_summarizer.py"), text]
    #subprocess.run(cmd, check=True)
    print("Text forwarded to idea_summarizer.py.")

def main():
    ep = Endpoint()
    ep.libCreate()
    ep_cfg = EpConfig()
    ep_cfg.logConfig.level = 4
    ep_cfg.logConfig.consoleLevel = 4
    ep.libInit(ep_cfg)

    ep.audDevManager().setNullDev()

    trans_cfg = TransportConfig()
    trans_cfg.port = int(os.getenv("SIP_PORT", "5060"))
    ep.transportCreate(PJSIP_TRANSPORT_UDP, trans_cfg)
    ep.libStart()
    print("pjsua2 library started.")

    acc_cfg = AccountConfig()
    acc_cfg.idUri = os.getenv("SIP_ID_URI")
    acc_cfg.regConfig.registrarUri = os.getenv("SIP_REGISTRAR")
    user = os.getenv("SIP_USERNAME")
    password = os.getenv("SIP_PASSWORD")
    auth_cred = AuthCredInfo("digest", "*", user, 0, password)
    acc_cfg.sipConfig.authCreds.append(auth_cred)

    my_acc = MyAccount()
    my_acc.create(acc_cfg)
    print("SIP account created and registered.")

    print("VOIP server is running. Press Ctrl+C to exit.")
    shutdown_event = threading.Event()
    try:
        while not shutdown_event.is_set():
            ep.libHandleEvents(50)
            shutdown_event.wait(0.05)
    except KeyboardInterrupt:
        print("KeyboardIntrrupt received, shutting down VOIP server...")
    finally:
        ep.libDestroy()
        print("pjsua2 library destroyed.")

if __name__ == '__main__':
    main()
