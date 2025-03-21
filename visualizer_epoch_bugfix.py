from threading import Thread, Event
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from gyro2D_visualizer import RealtimeEEGVisualizer
from kalman_filter import KalmanFilter
from emotive_streamer import EmotivStreamer
import numpy as np

# Flag to signal the end of data collection and saving
stop_saving_thread = Event()

def save_data_continuously(data_store):
    while True:
        if data_store:
            filename = f"eeg_gyro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            try:
                df = pd.DataFrame(data_store)
                df.to_excel(filename, index=False)
                print(f"Data saved to {filename}")
                data_store.clear()  # Clear after saving to avoid duplication
            except Exception as e:
                print(f"Error saving data to Excel: {str(e)}")



if __name__ == "__main__":
    emotiv = EmotivStreamer()
    visualizer = RealtimeEEGVisualizer()
    kalman_x, kalman_y = KalmanFilter(), KalmanFilter()

    def data_generator():
        channel_names = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1", "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]

        while True:
            packet = emotiv.read_packet()

            if packet is None:
                print("Warning: No data received from Emotiv!")
                continue  # Skip iteration
            
            print(f"Received Packet: {packet}")  # Debugging

            if 'eeg' not in packet:
                print("Error: EEG data missing from packet!")
                continue  # Skip iteration

            # Apply Kalman filter
            filtered_gyro_x = kalman_x.update(packet['gyro_x'])
            filtered_gyro_y = kalman_y.update(packet['gyro_y'])

            visualizer.gyro_x_buffer.append(filtered_gyro_x)
            visualizer.gyro_y_buffer.append(filtered_gyro_y)

            # Save data
            data_entry = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "gyro_x": filtered_gyro_x,
                "gyro_y": filtered_gyro_y,
            }

            eeg_channels = packet['eeg']  # This line caused the KeyError
            for i, channel_name in enumerate(channel_names):
                data_entry[channel_name] = eeg_channels[i]

            emotiv.data_store.append(data_entry)
            yield None  # Ensure generator continues


    if emotiv.connect():
        try:
            # Start the data-saving thread
            save_thread = Thread(target=save_data_continuously, args=(emotiv.data_store,))
            save_thread.start()

            # Set up the animation
            ani = FuncAnimation(
                visualizer.fig,
                visualizer.update,
                frames=data_generator,
                interval=500,  # Stream data every half a second
                cache_frame_data=False
            )
            plt.show()
        except KeyboardInterrupt:
            print("Session terminated.")

            # Stop the saving thread
            stop_saving_thread.set()

            # Ensure data is saved once more before closing
            save_thread.join()

            # Close the Emotiv device
            emotiv.device.close()
            print("Connection closed.")
