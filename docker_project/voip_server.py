#!/usr/bin/env python3
"""
VOIP Server using pjsua2 for Idea Summarization
------------------------------------------------
This script utilizes pjsua2 (Python bindings for pjsip) to handle VOIP events.
It processes incoming calls and instant messages:
  - For calls: when a call ends, it will record the call audio (assumed to be saved as a file)
    and then transcribe and summarize the audio using the Idea Summarizer.
  - For instant messages: it processes the text directly.
Note: Proper SIP account credentials and network configuration must be provided in the environment.
"""

import os
import time
import threading
from idea_summarizer import load_config, IdeaSummarizer
import pjsua2
from dotenv import load_dotenv
load_dotenv()

# Load the Idea Summarizer configuration
config = load_config()
summarizer = IdeaSummarizer(config)

# Custom call class to handle call events
class MyCall(pjsua2.Call):
    def onCallState(self, prm):
        ci = self.getInfo()
        print("Call with", ci.remoteUri, "is", ci.stateText)
        # When call is disconnected, assume the call audio has been recorded to 'recorded_audio.wav'
        if ci.state == pjsua2.PJSIP_INV_STATE_DISCONNECTED:
            print("Call disconnected. Processing recorded audio...")
            # In a real implementation, audio recording handling is required.
            recorded_audio = "recorded_audio.wav"
            if os.path.exists(recorded_audio):
                try:
                    idea = summarizer.process_input("audio_file", file_path=recorded_audio)
                    if idea:
                        print("Call Summary:")
                        print("Title:", idea.title)
                        print("Summary:", idea.summary)
                except Exception as e:
                    print("Error processing call audio:", e)
            else:
                print("No recorded audio found.")

    def onCallMediaState(self, prm):
        # In a full implementation, set up media and recording here.
        print("Call media state changed.")

# Custom account class to handle registration and instant messages
class MyAccount(pjsua2.Account):
    def onRegState(self, prm):
        print("Registration status:", prm.code, prm.reason)

    def onInstantMessage(self, prm):
        print("Received IM from", prm.fromUri, ":", prm.msgBody)
        try:
            idea = summarizer.process_input("direct_text", text=prm.msgBody)
            if idea:
                print("IM Summary:")
                print("Title:", idea.title)
                print("Summary:", idea.summary)
        except Exception as e:
            print("Error processing IM text:", e)

def main():
    # Create and initialize the endpoint
    ep = pjsua2.Endpoint()
    ep.libCreate()
    ep_cfg = pjsua2.EpConfig()
    ep.libInit(ep_cfg)
    
    # Create a UDP transport on port 5060
    tcfg = pjsua2.TransportConfig()
    tcfg.port = 5060
    ep.transportCreate(pjsua2.PJSIP_TRANSPORT_UDP, tcfg)
    ep.libStart()
    print("pjsua2 endpoint started.")

    # Set up SIP account configuration; these values should be set in the environment
    acc_cfg = pjsua2.AccountConfig()
    acc_cfg.idUri = os.environ.get("SIP_ID_URI", "sip:username@sip_provider")
    acc_cfg.regConfig.registrarUri = os.environ.get("SIP_REGISTRAR", "sip:sip_provider")
    # Set SIP authentication credentials
    auth_cred = pjsua2.AuthCredInfo("digest", "*", os.environ.get("SIP_USERNAME", "username"), 0, os.environ.get("SIP_PASSWORD", "password"))
    acc_cfg.sipConfig.authCreds.append(auth_cred)
    
    # Create account and register
    acc = MyAccount()
    acc.create(acc_cfg)
    print("SIP account created and registration initiated.")

    # Main event loop
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting VOIP server...")

    ep.libDestroy()

if __name__ == "__main__":
    main()
