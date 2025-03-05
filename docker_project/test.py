#!/usr/bin/env python3
"""Test script for VOIP library functionality"""

import os
import re
from voip_server import VoIPLibrary
from dotenv import load_dotenv

load_dotenv()

class VoIPTestConsole:
    """Console interface for testing VOIP functionality"""
    
    def __init__(self):
        self.lib = VoIPLibrary()
        self.running = True
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Configure event handlers"""
        # Incoming call handler
        self.lib.event_handlers['incoming_call'] = lambda session: (
            print(f"\n[Incoming call] Session ID: {session.call.getId()}"),
            session.play_audio(os.getenv("GREETING_WAV", "greeting.wav")),
            session.start_recording()
        )

        # Call ended handler
        self.lib.event_handlers['call_ended'] = lambda session: (
            print(f"\n[Call ended] Recording saved to: {session.recording_file}")
        )

        # Incoming message handler
        self.lib.event_handlers['incoming_message'] = lambda msg: (
            print(f"\n[New message] {msg}")
        )

        # DTMF handler
        self.lib.event_handlers['dtmf_received'] = lambda session, digit: (
            print(f"\n[DTMF received] Digit: {digit}")
        )

    def _format_phone_number(self, number: str) -> str:
        """Convert phone number to SIP URI format"""
        cleaned = re.sub(r'(?!^\+)\D', '', number)
        registrar = os.getenv("SIP_REGISTRAR", "sip:provider.example.com")
        domain = registrar.split("@")[-1]
        return f"sip:{cleaned}@{domain}"

    def place_call(self, number: str):
        """Place outgoing call to formatted SIP URI"""
        sip_uri = self._format_phone_number(number)
        print(f"\n[STDOUT] Placing call to: {sip_uri}")
        try:
            self.lib.place_call(sip_uri, {
                'record': True,
                'initial_audio': os.getenv("GREETING_WAV", "greeting.wav")
            })
        except Exception as e:
            print(f"\n[STDOUT] Call failed: {str(e)}")

    def send_message(self, number: str, text: str):
        """Send text message to phone number"""
        sip_uri = self._format_phone_number(number)
        print(f"\n[STDOUT] Sending message to: {sip_uri}")
        try:
            self.lib.send_message(sip_uri, text)
        except Exception as e:
            print(f"\n[STDOUT] Message failed: {str(e)}")

    def run(self):
        """Main console interface"""
        self.lib.start_service()
        print("\nVOIP Test Console\n")
        print("Commands:")
        print("  call [number]       - Place outgoing call")
        print("  msg [number] [text] - Send text message")
        print("  quit                - Exit program\n")

        while self.running:
            try:
                cmd = input("> ").split()
                if not cmd:
                    continue

                if cmd[0] == "call" and len(cmd) > 1:
                    self.place_call(cmd[1])
                elif cmd[0] == "msg" and len(cmd) > 2:
                    self.send_message(cmd[1], " ".join(cmd[2:]))
                elif cmd[0] == "quit":
                    self.running = False
                else:
                    print("Invalid command")

            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"Error: {str(e)}")

        self.lib.stop_service()
        print("\nVOIP service stopped")

if __name__ == '__main__':
    console = VoIPTestConsole()
    console.run()
