import socket, select, sys, random, signal

#Vérification des arguments au lancement du script
if len(sys.argv) != 2:
    print('Usage:', sys.argv[0], 'port')
    sys.exit(1)

HOST = '127.0.0.1'  
PORT = int(sys.argv[1])
ACCEPT_NEW_CONNEXIONS = True

clients = {} #Dictionnaire pour garder une trace des clients connectés (socket , pseudo)
disconnected_clients = [] #Liste des clients déconnecté mais qui pourraient se reconnecter
clients_cookies = {} #Dictionnaire pour les cookies (pseudo , cookie)
vivants = []
morts = []
crashed = []

#Diffuse un message à tous les clients sauf à l'expéditeur
def broadcast_message(message, sendersocket):
    if sendersocket in clients :
        senderpseudo = f"{clients[sendersocket]}: "
        message = f"{senderpseudo}{message.decode('utf-8')}"
        print(message)
    else : 
        message = f"Admin: {message.decode('utf-8')}"
    for clientsocket in clients:
        if clientsocket != sendersocket:
            clientsocket.send(message.encode('utf-8'))

#Reçoit un message du client, retourne False en cas d'échec
def receive_message(clientsocket):
    try:
        message = clientsocket.recv(1024)
        if not message:
            return False
        return message
    except:
        return False

#Envoie un message privé aux utilisateurs spécifiés par leur pseudo
def private_message(message, sendersocket):
    parts = message.split()
    dest = []
    actual_message = []
    RECHERCHE_PSEUDO = True

    for part in parts:
        if part[0] == '@' and RECHERCHE_PSEUDO:
            if part[1:].lower() == "admin":
                actual_message = parts[1:]  # Capture le reste du message après "@Admin"
                print(f"Message privé au modérateur: {' '.join(actual_message)}")
                return
            dest.append(part[1:])
        else:
            RECHERCHE_PSEUDO = False
            actual_message.append(part)

    actual_message = ' '.join(actual_message)
    senderpseudo = clients[sendersocket]

    for dest_pseudo in dest:
        dest_socket = None
        for sock, pseudo in clients.items():
            if pseudo == dest_pseudo:
                dest_socket = sock
                break
        if dest_socket:
            if senderpseudo == dest_pseudo:
                 dest_socket.send(f"Vous ne pouvez pas envoyer de message à vous même.".encode('utf-8'))               
            else :
                dest_socket.send(f"Message privé de {senderpseudo}: {actual_message}".encode('utf-8'))
                print(f"Message privé de {senderpseudo} à {dest_pseudo} : {actual_message}")
        else:
            sendersocket.send(f"Pas d'utilisateur connecté nommé {dest_pseudo}.".encode('utf-8'))
            print(f"{senderpseudo} a essayé d'envoyer un message à un utilisateur nommé {dest_pseudo}.")

    if not dest:
        print("Aucun pseudo valide pour ce message privé.")

#Envoie la liste des utilisateurs connectés au client demandeur (!list)
def send_clientlist(sock):
    if clients:
        clientlist = "Utilisateurs connectés : "
        for pseudo in morts:
            clientlist += pseudo + "(mort), "
        for pseudo in vivants:
            clientlist += pseudo + "(vivant), "
        for pseudo in crashed :
            clientlist += pseudo + "(crashed), "
        clientlist = clientlist.rstrip(", ")
    else:
        clientlist = "Pas d'autres utilisateurs connectés."
    
    if sock == serversocket :
        print(clientlist)
    else :
        sock.send(clientlist.encode('utf-8'))

#Interprète et exécute les commandes entrées par le serveur via l'entrée standard
def handle_command(commande):
    global ACCEPT_NEW_CONNEXIONS
    parts = commande.strip().split()
    cmd = parts[0]
    if not parts :
        return 
    if cmd == "!start":
        ACCEPT_NEW_CONNEXIONS = False
        broadcast_message("Le jeu commence maintenant! Aucune nouvelle connexion n'est autorisée.".encode('utf-8'), serversocket)
        print("Le jeu commence, plus aucune connexion n'est autorisée.")
    elif cmd == "!list":
        send_clientlist(serversocket)
    elif len(parts) >= 2 and cmd.startswith("@") :
        user = cmd[1:]  
        if parts[1] == "!ban":
            ban(user)
        elif parts[1] == "!suspend":
            suspend(user)
        elif parts[1] == "!forgive":
            forgive(user)
    else:
        commande = commande.encode("utf-8")
        broadcast_message(commande, serversocket)

#Bannit un utilisateur spécifié, ferme sa connexion et informe tous les autres clients (!ban)
def ban(username):
    FOUND = False
    for sock, pseudo in list(clients.items()):
        if pseudo == username:
            FOUND = True
            sock.send("!ban".encode('utf-8'))
            close_socket(sock)
            broadcast_message(f"{username} a été banni du serveur.".encode('utf-8'), serversocket)
            print(f"{username} a été banni du serveur.")
            morts.append(username)
            vivants.remove(username)
            break
    if not FOUND : 
        print("Pas d'utilisateur ayant ce pseudo.")

#Suspend temporairement les activités d'un utilisateur spécifié sur le serveur (!suspend)
def suspend(username):
    FOUND = False
    for sock, pseudo in list(clients.items()):
        if pseudo == username:
            sock.send("!suspend".encode('utf-8'))
            print(f"{username} à été suspendu.")
            FOUND = True
    if not FOUND : 
        print("Pas d'utilisateur ayant ce pseudo.")

#Rétablit les activités d'un utilisateur précédemment suspendu sur le serveur (!forgive)
def forgive(username):
    FOUND = False
    for sock, pseudo in list(clients.items()):
        if pseudo == username:
            sock.send("!forgive".encode('utf-8'))
            print(f"{username} n'est plus suspendu.")
            FOUND = True
    if not FOUND : 
        print("Pas d'utilisateur ayant ce pseudo.")

#Génère un cookie
def generate_cookie():
    cookie = str(random.randint(10000000, 99999999))
    return cookie

#Fonction pour valider le cookie reçu lors de la reconnexion
def validate_cookie(username, received_cookie, clients_cookies):
    c = clients_cookies.get(username)
    if c and received_cookie == c:
        return True
    return False

#Fonction qui gère les connexions
def connexion(clientsocket, addr, clients, clients_cookies):
    data = receive_message(clientsocket)
    if not data:
        print("Aucune donnée reçue lors de la tentative de connexion.")
        clientsocket.close()
        return
    data = data.decode('utf-8')
    username, received_cookie = data.split(":")[0], None
    print("Donnée reçue du client: "+data)
    if ':' in data:
        received_cookie = data.split(":")[1]
    if received_cookie and username in disconnected_clients:
        print("Tentative de reconnexion...")
        if validate_cookie(username, received_cookie, clients_cookies):
            print(f"Reconnexion réussie pour {username}")
            clients[clientsocket] = username
            clientsocket.send("RECONNECT_OK".encode('utf-8'))
            if username in morts :
                morts.remove(username)
            if username in crashed :
                crashed.remove(username)
            vivants.append(username)
            return True
        else:
            print(f"Echec de la reconnexion pour {username}")
            clientsocket.send("RECONNECT_FAILED".encode('utf-8'))
            clientsocket.close()
            return False
    else:
        if username in clients.values():
            if username not in disconnected_clients:
                clientsocket.send("Vous êtes déjà connecté.".encode('utf-8'))
                clientsocket.close()
                print(f"Tentative de reconnexion de {username} rejetée car il est déjà connecté.")
            else:
                clientsocket.send("Pseudo déjà utilisé. Veuillez choisir un autre pseudo.".encode('utf-8'))
                clientsocket.close()
            return False
        else:
            cookie = generate_cookie()
            clients[clientsocket] = username
            clients_cookies[username] = cookie
            clientsocket.send(f"SET_COOKIE:{cookie}".encode('utf-8'))
            print(f"Nouvelle connexion acceptée de {username}.")
            vivants.append(username)
            return True

#Handler pour SIGINT
def signal_handler(sig, ignore):
    print("Fermeture du serveur...")
    for client_socket in list(clients.keys()):
        client_socket.close()
    socketlist.clear()
    clients.clear()
    disconnected_clients.clear()
    clients_cookies.clear()
    serversocket.close()
    print("Le serveur a été fermé correctement.")
    sys.exit(0)

#Ferme proprement une socket client et met à jour les listes
def close_socket(sock):
    if sock in socketlist:
        socketlist.remove(sock) 
    if sock in clients:
        del clients[sock] 
    if sock in clients_cookies:
        del clients_cookies[sock] 
    sock.close() 

#Fonction pour gérer la déconnexion d'un client en l'enregistrant dans la liste des déconnectés
def disconnect_client(clientsocket):
    username = clients.pop(clientsocket, None)
    if username:
        disconnected_clients.append(username) 
        vivants.remove(username)
        crashed.append(username)
        close_socket(clientsocket)

# ╔════════════════════════════════════════════════════╗
# ║         CHAT KILLER – SERVEUR PRINCIPAL            ║
# ║     Lancement du serveur et gestion des clients    ║
# ╚════════════════════════════════════════════════════╝
if __name__ == "__main__":
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serversocket.bind((HOST, PORT))
    serversocket.listen()

    print(f"En attente de connexions sur {HOST}:{PORT}...")

    socketlist = [serversocket, sys.stdin]

    #Gestionnaire de signal pour SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while True:
        readable, _, _ = select.select(socketlist, [], [])

        for s in readable:
            #Serveur
            if s == serversocket:
                if ACCEPT_NEW_CONNEXIONS :
                    if s == serversocket:
                        clientsocket, addr = serversocket.accept()
                        if connexion(clientsocket, addr, clients, clients_cookies):
                            socketlist.append(clientsocket)
                            
                else : 
                    clientsocket, addr = serversocket.accept()
                    clientsocket.send("Vous ne pouvez pas vous connecter, le jeu a commencé.".encode('utf-8'))
                    close_socket(clientsocket)
                    print("Nouvelle connexion rejetée.")

            #Entrée standard
            elif s == sys.stdin:
                commande = sys.stdin.readline()
                handle_command(commande)

            else:
                #Client
                message = receive_message(s)

                if message is False:
                    print(f"Déconnexion de {clients[s]}.")
                    disconnect_client(s)
                    continue

                #Commande !list
                elif message.strip() == b"!list":
                    send_clientlist(s)

                #Envoie de messages privés
                elif message.startswith(b"@"):
                    private_message(message.decode('utf-8').strip(), s)

                #Envoie message à tout le monde
                else:
                    broadcast_message(message, s)