#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/pjproject/pjsip-apps/src/python')
sys.path.insert(0, '/usr/local/lib/python3.8/dist-packages')
print("Current sys.path:", sys.path)

import os
import subprocess
from time import sleep
from dotenv import load_dotenv
from pjsua2 import *

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

# Define the Account callback to handle incoming calls and messages
class MyAccount(Account):
    def onIncomingCall(self, prm):
        call = MyCall(self, prm.callId)
        call_prm = CallOpParam()
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
        self.recorder = None
        self.record_file = "recording.wav"
        self.rec_16k_file = "recording_16khz.wav"

    def onCallState(self, prm):
        ci = self.getInfo()
        print(f"Call with id {ci.id} is now in state: {ci.stateText}")
        # When call is disconnected, process the recorded audio if any
        if ci.state == pjsip_inv_state.PJSIP_INV_STATE_DISCONNECTED:
            if self.recorder:
                sleep(1)
                print("Call ended. Processing recording...")
                try:
                    cmd_convert = ["ffmpeg", "-i", self.record_file, "-ar", "16000", self.rec_16k_file]
                    subprocess.run(cmd_convert, check=True)
                    print("Audio converted to 16kHz WAV.")
                except Exception as e:
                    print("Error converting audio:", e)
                    return
                try:
                    cmd_whisper = ["whisper.exe", self.rec_16k_file]
                    result = subprocess.run(cmd_whisper, capture_output=True, text=True, check=True)
                    transcription = result.stdout.strip()
                    print("Transcription result:", transcription)
                except Exception as e:
                    print("Error during transcription:", e)
                    transcription = ""
                if transcription:
                    forward_text_to_idea_summarizer(transcription)

    def onCallMediaState(self, prm):
        ci = self.getInfo()
        for mi in ci.media:
            if mi.type == pjmedia_type.PJMEDIA_TYPE_AUDIO:
                audio_med = AudioMedia()
                try:
                    self.getAudioMedia(mi.index, audio_med)
                except Exception as e:
                    print("Error getting audio media:", e)
                    continue

                greeting_file = os.getenv("GREETING_WAV", "greeting.wav")
                if os.path.exists(greeting_file):
                    try:
                        player = AudioMediaPlayer()
                        player.createPlayer(greeting_file)
                        player.startTransmit(audio_med)
                        print("Playing greeting message.")
                    except Exception as e:
                        print("Error playing greeting:", e)
                else:
                    print("Greeting file not found. Skipping greeting playback.")
                
                try:
                    recorder = AudioMediaRecorder()
                    recorder.createRecorder(self.record_file)
                    audio_med.startTransmit(recorder)
                    self.recorder = recorder
                    print("Started recording the call.")
                except Exception as e:
                    print("Error starting recorder:", e)

def forward_text_to_idea_summarizer(text):
    """
    Forwards the given text to idea_summarizer.py.
    The idea_summarizer.py script is expected to read the text argument and process it.
    """
    cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "idea_summarizer.py"), text]
    subprocess.run(cmd, check=True)
    print("Text forwarded to idea_summarizer.py.")

def main():
    ep = Endpoint()
    ep.libCreate()
    ep_cfg = EpConfig()
    ep.libInit(ep_cfg)

    trans_cfg = TransportConfig()
    trans_cfg.port = int(os.getenv("SIP_PORT", "5060"))
    ep.transportCreate(PJSIP_TRANSPORT_UDP, trans_cfg)
    ep.libStart()
    print("pjsua2 library started.")

    acc_cfg = AccountConfig()
    acc_cfg.idUri = os.getenv("SIP_ID")
    acc_cfg.regConfig.registrarUri = os.getenv("SIP_REGISTRAR")
    user = os.getenv("SIP_USER")
    password = os.getenv("SIP_PASS")
    auth_cred = AuthCredInfo("digest", "*", user, 0, password)
    acc_cfg.sipConfig.authCreds.append(auth_cred)

    my_acc = MyAccount()
    my_acc.create(acc_cfg)
    print("SIP account created and registered.")

    print("VOIP server is running. Press Ctrl+C to exit.")
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        print("Shutting down VOIP server...")
    finally:
        ep.libDestroy()
        print("pjsua2 library destroyed.")

if __name__ == '__main__':
    main()
