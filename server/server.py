import argparse, socket, threading, time, queue, os
SCREENSHOT_DIR = 'screenshots/{ip}/{date}'

# Function to parse the arguments
def args_parse():
    parser = argparse.ArgumentParser(description='Server of file receiver')
    parser.add_argument('-l', '--listen', type=int, default=9809, help='Port to listen on')
    parser.add_argument('-s', '--show', action='store_true', help='Display the list of files received')
    parser.add_argument('-r', '--readfile', nargs='*', type=str, help='Read the content of a file')
    parser.add_argument('-k', '--kill', action='store_true', help='Kill the server and delete client files')
    return parser.parse_args()

# Function to display the list of files received
def show_files():
    files = os.listdir('.')
    print("Files received:")
    for file in files:
        print(file)

# Function to read the content of a file
def read_file(filename):
    try:
        with open(filename, 'r') as file:
            print(file.read())
    except FileNotFoundError:
        print(f"File {filename} not found")

# Function to handle the commands
def handle_commands(args, server_socket, client_socket):
    if args.listen:
        print(f"Server listening now on port {args.listen}")
    elif args.show:
        show_files()
    elif args.readfile:
        filename = ' '.join(args.readfile)
        read_file(filename)
    elif args.kill:
        try:
            client_socket.sendall('STOP'.encode())
            server_socket.close()
            print('Server killed')
        except:
            print('There is no client connected')
            pass

# Function to read the commands
def read_commands(server_socket, client_socket):
    while True:
        command = input("Server > ")
        if command:
            args = args_parse()
            handle_commands(args, server_socket, client_socket)

# Function to setup the server
def setup_server(host, port):
    global SCREENSHOT_DIR
    ip = socket.gethostbyname(socket.gethostname())
    date = time.strftime('%d-%m-%Y')
    SCREENSHOT_DIR = SCREENSHOT_DIR.format(ip=ip, date=date)
    if not os.path.exists(SCREENSHOT_DIR):
        os.makedirs(SCREENSHOT_DIR)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Server listening on {host}:{port}")
    return server_socket

# Function to accept the connections
def accept_connections(server_socket):
    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection from {client_address}")
        threading.Thread(target=handle_client, args=(client_socket,)).start()

# Function to handle the client
def handle_client(client_socket):
    filename_size = int.from_bytes(client_socket.recv(4), 'big')
    filename = client_socket.recv(filename_size).decode()
    _, file_extension = os.path.splitext(filename)
    if file_extension.lower() in '.png':
        filename = os.path.join(SCREENSHOT_DIR, filename)
    data_queue = queue.Queue()
    threading.Thread(target=write_to_file, args=(filename, data_queue)).start()
    while True:
        file_data = client_socket.recv(1024)
        if not file_data:
            break
        data_queue.put(file_data)

# Function to write to the file
def write_to_file(filename, data_queue):
    while True:
        with open(filename, 'ab') as file:
            while not data_queue.empty():
                file_data = data_queue.get()
                file.write(file_data)
        time.sleep(10)

def main():
    args = args_parse()
    host = 'localhost'
    port = args.listen
    server_socket = setup_server(host, port)
    command_thread = threading.Thread(target=read_commands, args=(server_socket,None))
    command_thread.daemon = True
    command_thread.start()
    accept_connections(server_socket)

if __name__ == '__main__':
    main()