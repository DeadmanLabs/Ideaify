#!/usr/bin/env python3
"""
VOIP Library Implementation using pjsua2

Features:
- Event-driven architecture
- Concurrent call handling
- DTMF menu navigation
- Recording/playback controls
- Docker compatible
- Phone number formatting support
"""

import os
import re
import sys
import time
import threading
import logging
from typing import Dict, Callable, Optional
from dotenv import load_dotenv
from datetime import datetime
from pjsua2 import *

load_dotenv()

class CallSession:
    """Manages state and media for a single call"""
    def __init__(self, call, config: dict):
        self.call = call
        self.config = config
        self.recorder = None
        self.player = None
        self.audio_med = None
        self.dtmf_buffer = []
        self.recording_file = None
        self._init_recording()

    def _init_recording(self):
        if self.config.get('record', True):
            self.recording_file = f"recording_{int(time.time()*1000)}.wav"
            self.recorder = AudioMediaRecorder()
            self.recorder.createRecorder(self.recording_file)

    def play_audio(self, file_path: str):
        """Play audio file to the call"""
        if self.player:
            self.player.stopTransmit(self.audio_med)
        self.player = AudioMediaPlayer()
        self.player.createPlayer(file_path)
        self.player.startTransmit(self.audio_med)

    def start_recording(self):
        """Start recording call audio"""
        if self.recorder and self.audio_med:
            self.audio_med.startTransmit(self.recorder)

    def stop_recording(self):
        """Stop and save recording"""
        if self.recorder and self.audio_med:
            self.audio_med.stopTransmit(self.recorder)
            return self.recording_file
        return None

    def handle_dtmf(self, digit: str):
        """Process DTMF digit and navigate menu"""
        self.dtmf_buffer.append(digit)
        menu = self.config.get('dtmf_menu')
        if menu:
            current = menu
            for d in self.dtmf_buffer:
                current = current.get(d, {})
                if 'action' in current:
                    current['action'](self)
                    self.dtmf_buffer = []

class VoIPLibrary(Account):
    """Main VOIP library class with phone number support"""
    def __init__(self):
        super().__init__()
        self.ep = Endpoint()
        self.active_calls: Dict[str, CallSession] = {}
        self.event_handlers = {
            'incoming_call': None,
            'incoming_message': None,
            'call_connected': None,
            'call_ended': None,
            'dtmf_received': None
        }
        self._init_endpoint()

    def _init_endpoint(self):
        self.ep.libCreate()
        ep_cfg = EpConfig()
        ep_cfg.logConfig.level = 4
        ep_cfg.logConfig.consoleLevel = 0
        ep_cfg.logConfig.filename = f"{datetime.now()}-pjsua2-server.log"
        self.ep.libInit(ep_cfg)
        self.ep.audDevManager().setNullDev()

    def _format_phone_number(self, number: str) -> str:
        """Convert phone number to SIP URI using .env config"""
        # Clean the number
        cleaned = re.sub(r'(?!^\+)\D', '', number)
        
        # Get domain from SIP_REGISTRAR
        registrar = os.getenv("SIP_REGISTRAR", "sip:provider.example.com")
        domain = registrar.split("@")[-1].split(":")[0]
        
        return f"sip:{cleaned}@{domain}"

    def place_call(self, number: str, config: dict) -> CallSession:
        """Initiate outgoing call to phone number or SIP URI"""
        if not number.startswith("sip:"):
            number = self._format_phone_number(number)
            
        call = Call(self, CallOpParam())
        call_prm = CallOpParam(True)
        try:
            call.makeCall(number, call_prm)
            session = CallSession(call, config)
            self.active_calls[call.getId()] = session
            return session
        except Exception as e:
            logging.error(f"Call failed: {str(e)}")
            raise

    def send_message(self, number: str, text: str):
        """Send text message to phone number or SIP URI"""
        if not number.startswith("sip:"):
            number = self._format_phone_number(number)
            
        send_prm = SendInstantMessageParam()
        self.sendInstantMessage(number, text, send_prm)

    def start_service(self):
        """Start VOIP service with .env config"""
        # Configure transport
        trans_cfg = TransportConfig()
        trans_cfg.port = int(os.getenv("SIP_PORT", 5060))
        self.ep.transportCreate(PJSIP_TRANSPORT_UDP, trans_cfg)
        
        # Start library
        self.ep.libStart()
        
        # Register account
        acc_cfg = AccountConfig()
        acc_cfg.idUri = os.getenv("SIP_ID_URI")
        acc_cfg.regConfig.registrarUri = os.getenv("SIP_REGISTRAR")
        auth = AuthCredInfo(
            "digest",
            os.getenv("SIP_REALM", "*"),
            os.getenv("SIP_USERNAME"),
            0,
            os.getenv("SIP_PASSWORD")
        )
        acc_cfg.sipConfig.authCreds.append(auth)
        self.create(acc_cfg)
        
        # Start event loop
        self.running = True
        self.event_thread = threading.Thread(target=self._event_loop, daemon=True)
        self.event_thread.start()

    def _event_loop(self):
        """Handle library events"""
        # Register this thread with PJSUA
        try:
            self.ep.libRegisterThread("event_thread")
            while self.running:
                self.ep.libHandleEvents(10)
                time.sleep(0.01)
        except KeyboardInterrupt:
            self.stop_service()
        except Exception as e:
            logging.error(f"Event loop failed: {str(e)}")
            self.stop_service()

    def stop_service(self):
        """Shutdown VOIP service"""
        self.running = False
        for call_id, session in list(self.active_calls.items()):
            try:
                session.call.hangup(CallOpParam())
            except Exception as e:
                logging.error(f"Error hanging up call {call_id}: {str(e)}")

        try:
            self.setRegistration(False)
        except Exception as e:
            logging.error(f"Error unregistering account: {str(e)}")

        time.sleep(1)

        self.ep.libDestroy()
        if self.event_thread.is_alive():
            self.event_thread.join(timeout=1)

    def onIncomingCall(self, prm):
        """Handle incoming call event"""
        call = Call(self, prm.callId)
        session = CallSession(call, {})
        self.active_calls[call.getId()] = session
        
        if self.event_handlers['incoming_call']:
            self.event_handlers['incoming_call'](session)

    def onInstantMessage(self, prm):
        """Handle incoming text message"""
        if self.event_handlers['incoming_message']:
            self.event_handlers['incoming_message']({
                'from': prm.fromUri,
                'content': prm.msgBody
            })

    def onRegState(self, prm):
        """Handle registration state changes"""
        logging.info(f"Registration status: {prm.code} {prm.reason}")
        if prm.code == 200:
            print("Connected: Successfully registered with the SIP server.")
        else:
            print(f"Registration update: {prm.code} - {prm.reason}")

    def onIncomingSubscribe(self, prm):
        """Handle presence subscription requests"""
        return 202  # Automatically accept subscriptions

    class Call(Call):
        def onCallState(self, prm):
            """Handle call state changes"""
            session = self.account.active_calls.get(self.getId())
            if prm.e.body.type == PJSIP_EVENT_RX_MSG:
                if prm.e.body.rxMsg.method == "BYE" and session:
                    if self.account.event_handlers['call_ended']:
                        self.account.event_handlers['call_ended'](session)
                    del self.account.active_calls[self.getId()]
            elif self.getInfo().state == PJSIP_INV_STATE_CONFIRMED and session:
                if self.account.event_handlers['call_connected']:
                    self.account.event_handlers['call_connected'](session)

        def onCallDtmfDigit(self, prm):
            """Handle DTMF digit detection"""
            session = self.account.active_calls.get(self.getId())
            if session and self.account.event_handlers['dtmf_received']:
                session.handle_dtmf(prm.digit)
                self.account.event_handlers['dtmf_received'](prm.digit)

def main():
    """Example usage preserving original functionality"""
    lib = VoIPLibrary()
    
    # Setup event handlers
    lib.event_handlers['incoming_call'] = lambda session: (
        session.play_audio(os.getenv("GREETING_WAV", "greeting.wav")),
        session.start_recording()
    )
    
    lib.event_handlers['call_ended'] = lambda session: (
        print(f"Call ended, recording saved to {session.recording_file}")
    )
    
    lib.start_service()
    print("VOIP service running. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        lib.stop_service()

if __name__ == '__main__':
    main()
