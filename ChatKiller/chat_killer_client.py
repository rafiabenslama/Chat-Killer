import socket, select, sys, os, signal

FERMETURE = False #Variable globale utilisée dans le handler de SIGCHLD pour que les terminaux ne se réouvrent pas à l'appel de sigterm et sigint

#Gestionnaire SIGINT pour arrêter le programme mais permettre une éventuelle reconnexion
def sigint_handler(sig, ignore):
    global FERMETURE
    FERMETURE = True
    if pids :
        for pid in pids:  
            os.kill(pid, signal.SIGKILL)
    print("Déconnecté du serveur de chat.")
    sys.exit(0) 

#Gestionnaire pour SIGCHLD appelé à la terminaison d'un processus enfant
def sigchld_handler(sig, ignore):
    global FERMETURE 
    if FERMETURE:
        return #Ne relance pas les terminaux enfants si le serveur a fermé ou si le client est banni
    try:
        while True:
            pid, status = os.waitpid(-1, os.WNOHANG)  #Non bloquant
            if pid == 0:
                break  
            elif pid in pids:
                index = pids.index(pid)
                relaunch_process(index, pids) 
    except ChildProcessError:
        pass

#Gestionnaire SIGTERM pour arrêter proprement le programme 
def sigterm_handler(sig, ignore):
    global FERMETURE
    FERMETURE = True 
    clean(TUBE, log_file, pids)
    print("Déconnecté du serveur de chat.")
    sys.exit(0)  

#Fonction pour nettoyer les ressources lors de la fermeture
def clean(tube, log, pids):
    delete_cookie(pseudo)
    os.unlink(tube)
    log.close()  
    for pid in pids:  
        os.kill(pid, signal.SIGKILL)

#Relance un processus enfant spécifié qui a terminé 
def relaunch_process(index, pids):
    if index == 0:
        new_pid = os.fork()
        if new_pid == 0:
            os.execvp("xterm", ["xterm", "-e", f"cat > {TUBE}"])
            sys.exit(0)
        else:
            pids[0] = new_pid
    elif index == 1:
        new_pid = os.fork()
        if new_pid == 0:
            os.execvp("xterm", ["xterm", "-e", f"tail -f {LOG}"])
            sys.exit(0)
        else:
           pids[1] = new_pid

#Enregistre le cookie dans un fichier 
def save_cookie(pseudo, cookie):
    path = f"/var/tmp/{pseudo}"
    if not os.path.exists(path):
        os.makedirs(path)
    with open(os.path.join(path, 'cookie'), 'w') as file:
        file.write(cookie)

#Lit le cookie (utilisé pour la reconnexion)
def read_cookie(pseudo):
    path = f"/var/tmp/{pseudo}/cookie"
    if os.path.exists(path):
        with open(path, 'r') as file:
            return file.read().strip()
    else:
        return None
    
#Supprime le fichier ou est stocké le cookie
def delete_cookie(pseudo):
    path = f"/var/tmp/{pseudo}/cookie"
    if os.path.exists(path):
        os.remove(path)

#Fonction pour envoyer un message en détectant les échecs d'envoi
def send_message(socket, message):
    try:
        socket.send(message)
    except (socket.error, BrokenPipeError) as e:
        print(f"Erreur d'envoi : {e}. La connexion avec le serveur semble interrompue.")
        return False
    return True

# ╔════════════════════════════════════════════════════╗
# ║         CHAT KILLER – CLIENT PRINCIPAL             ║
# ║    Superviseur : gestion des terminaux et socket   ║
# ╚════════════════════════════════════════════════════╝
if __name__ == "__main__":
    #Vérification des arguments
    if len(sys.argv) != 3:
        print('Usage:', sys.argv[0], 'host port')
        sys.exit(1)

    HOST = sys.argv[1]
    PORT = int(sys.argv[2])
    pid = os.getpid()
    pids = []

    #Gestionnaires de signal
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGCHLD, sigchld_handler)
    
    #Connexion au serveur 
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        connected = False
        while not connected:
            pseudo = input("Entrez votre pseudo: ")
            cookie = read_cookie(pseudo)
            if cookie:
                print("Tentative de reconnexion...")
                send_message(s, f"{pseudo}:{cookie}".encode('utf-8'))
            else:
                send_message(s, pseudo.encode('utf-8'))
                print("Tentative de connexion...")
            
            response = s.recv(1024).decode('utf-8')
            if "Pseudo déjà utilisé" in response:
                print("Pseudo déjà utilisé. Veuillez choisir un autre pseudo.")
            elif "Vous ne pouvez pas vous connecter" in response:
                print(response)
                sys.exit(0)
            elif "RECONNECT_FAILED" in response:
                print("Echec de la reconnexion. Veuillez retentez.")
                sys.exit(0)
            elif "Vous êtes déjà connecté" in response:
                print(response)
                sys.exit(0)
            else:
                connected = True 
                if "SET_COOKIE:" in response:
                    first_connexion = True 
                    cookie = response.split(":")[1]
                    save_cookie(pseudo, cookie)
                    print(f"Connexion réussie ! Cookie reçu et enregistré: {cookie}.")
                elif "RECONNECT_OK" in response:
                    first_connexion = False
                    print("Reconnexion réussie !")
        
        #Une fois la connexion acceptée ouverture des terminaux
        TUBE = f"/var/tmp/killer_{pseudo}.fifo"
        LOG = f"/var/tmp/killer_{pseudo}.log"

        #Création du tube nommé et du log si nécessaire
        if first_connexion :
            os.mkfifo(TUBE)
            with open(LOG, 'w', encoding='utf-8') as log_file:
                log_file.write("Démarrage du client de chat...\n")

        #Création des terminaux pour l'entrée et la sortie

        pid1 = os.fork()
        if pid1 == 0:
            os.execvp("xterm", ["xterm", "-e", f"cat > {TUBE}"])
            sys.exit(0)
        pids.append(pid1)

        pid2 = os.fork()
        if pid2 == 0:
            os.execvp("xterm", ["xterm", "-e", f"tail -f {LOG}"])
            sys.exit(0)
        pids.append(pid2)
    
        with open(TUBE, 'r') as fifo, open(LOG, 'a', encoding='utf-8') as log_file, s:
            while True:
                
                socketlist = [fifo, s]
                readable, _, _ = select.select(socketlist, [], [])

                for sock in readable:
                    if sock == fifo:
                        message = fifo.readline()
                        if message:
                            send_message(s, message.encode('utf-8'))
                            if not message.startswith("!"):
                                log_file.write(f"Moi: {message} \n")
                                log_file.flush()
                    else:
                        message = s.recv(1024)
                        if not message:
                            print("Fermeture du serveur de chat...")
                            FERMETURE = True
                            clean(TUBE, log_file, pids)
                            sys.exit(0)
                        else:
                            received_message = message.decode('utf-8')
                            if received_message == "!suspend":
                                os.kill(pid1, signal.SIGSTOP)
                                log_file.write("Vous avez été suspendu par le modérateur.\n")
                                log_file.flush()
                            elif received_message == "!forgive":
                                os.kill(pid1, signal.SIGCONT)
                                log_file.write("Vous n'êtes plus suspendu.\n")
                                log_file.flush()
                            elif received_message == "!ban":
                                print("Le modérateur vous a banni.")
                                os.kill(pid, signal.SIGTERM)
                            else:
                                log_file.write(f"{received_message}\n")
                                log_file.flush()
    
    except ConnectionResetError :
        print("Impossible de se connecter au serveur.")
        if pseudo:
            delete_cookie(pseudo)

    except ConnectionRefusedError :
            print("Impossible de se connecter au serveur.")
