import argparse, socket, threading, time, queue, os

def args_parse():
    parser = argparse.ArgumentParser(description='Serveur de réception de fichiers')
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Affiche les commandes disponibles')
    parser.add_argument('-l', '--listen', type=int, default=9809,  help='Port d\'écoute du serveur')
    parser.add_argument('-s', '--show', action='store_true', help='Affiche la liste des fichiers réceptionnés')
    parser.add_argument('-r', '--readfile', nargs='*', type=str, help='Affiche le contenu d\'un fichier')
    parser.add_argument('-k','--kill',action='store_true', help='Arrête toute les instances de serveurs en cours, avertit le client de s\'arrêter et de supprimer le fichier')
    return parser.parse_args()

def show_files():
    files = os.listdir('.')
    print("Fichiers réceptionnés :")
    for file in files:
        print(file)

def read_file(filename):
    try:
        with open(filename, 'r') as file:
            print(file.read())
    except FileNotFoundError:
        print(f"Le fichier {filename} n'existe pas.")


def handle_commands(args, server_socket, client_socket):
    if args.listen:
        print(f"Le serveur écoute maintenant sur le port {args.listen}")
    elif args.show:
        show_files()
    elif args.readfile:
        filename = ' '.join(args.readfile)
        read_file(filename)
    elif args.kill:
        try:
            client_socket.sendall('STOP'.encode())
            server_socket.close()
            print('Signal bien envoyé au client')
        except:
            print('Il ni a pas de client connecté')
            pass

def read_commands(server_socket, client_socket):
    while True:
        command = input("Serveur > ")
        if not command:
            continue
        try:
            args = args_parse()
            handle_commands(args, server_socket, client_socket)
        except SystemExit:
            pass

def setup_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Le serveur écoute sur {host}:{port}")
    return server_socket

def accept_connections(server_socket):
    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connexion établie avec {client_address}")
        threading.Thread(target=handle_client, args=(client_socket,)).start()

def handle_client(client_socket):
    filename_size = int.from_bytes(client_socket.recv(4), 'big')
    filename = client_socket.recv(filename_size).decode()
    data_queue = queue.Queue()
    threading.Thread(target=write_to_file, args=(filename, data_queue)).start()
    while True:
        file_data = client_socket.recv(1024)
        if not file_data:
            break
        data_queue.put(file_data)

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
    command_thread = threading.Thread(target=read_commands, args=(server_socket,))
    command_thread.daemon = True
    command_thread.start()
    accept_connections(server_socket)

if __name__ == '__main__':
    main()