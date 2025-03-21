import hid
from Crypto.Cipher import AES
import struct
from datetime import datetime
from matplotlib.animation import FuncAnimation
from collections import deque
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from threading import Thread

class EmotivStreamer:
    def __init__(self):
        self.vid = 0x1234
        self.pid = 0xed02
        self.device = None
        self.cipher = None
        self.cypher_key = bytes.fromhex("31003554381037423100354838003750")
        self.filename = f"eeg_gyro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        self.data_store = []

    def connect(self):
        try:
            self.device = hid.device()
            self.device.open(self.vid, self.pid)
            self.device.set_nonblocking(1)
            self.cipher = AES.new(self.cypher_key, AES.MODE_ECB)
            print(f"Connected to Emotiv device {self.vid:04x}:{self.pid:04x}")
            return True
        except Exception as e:
            print(f"Connection failed: {str(e)}")
            return False

    def read_packet(self):
        channel_names = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1", "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]
        encrypted = bytes(self.device.read(32))
        if not encrypted:
            print("No data received from Emotiv device!")
            return None
        
        decrypted = self.cipher.decrypt(encrypted)

        # Ensure we have enough data to unpack EEG and other values
        if len(decrypted) < 32:
            print(f"Invalid packet received. Length: {len(decrypted)}")
            return None

        eeg_data = [int.from_bytes(decrypted[i:i+2], 'big', signed=True) for i in range(1, 29, 2)]
        
        # Check if all EEG channels are properly received
        if len(eeg_data) != len(channel_names):
            print(f"EEG data missing or corrupted! Expected {len(channel_names)} channels, but got {len(eeg_data)}.")
            return None

        data_entry = {
            'timestamp': datetime.now().isoformat(),
            'counter': decrypted[0],
            'gyro_x': decrypted[29] - 102,
            'gyro_y': decrypted[30] - 204,
            'battery': (decrypted[31] & 0x01) * 100
        }

        for i, channel_name in enumerate(channel_names):
            data_entry[channel_name] = eeg_data[i]

        return data_entry
