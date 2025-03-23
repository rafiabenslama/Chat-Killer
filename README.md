# Chat Killer 

Jeu multijoueur en ligne de commande – Projet Système (2024).
Développé dans le cadre du cours de Système 2 (L2 Informatique).

---

## 🚀 Fonctionnalités

- 💬 Messagerie publique et privée entre joueurs
- 🔐 Connexion sécurisée avec pseudo unique
- 👀 Superviseur côté client, détaché du terminal
- 🖥️ Ouverture automatique de deux terminaux (affichage + saisie)
- 🔁 Relance automatique des terminaux en cas de crash
- 💡 Commandes disponibles : `!list`, `!ban`, `!suspend`, `!forgive`, `!reconnect`, etc.
- 🔄 Reconnexion d’un joueur après crash du client

---

## 🛠️ Technologies utilisées

- Python 3
- Sockets TCP

---

## ▶️ Lancer le projet

1. **Cloner le dépôt**
2. **Lancer le serveur** : python3 chat_killer_server.py 42042
3. **Lancer un ou plusieurs** clients (dans différents terminaux) : python3 chat_killer_client.py 127.0.0.1 42042

---

## 📂 Fichiers principaux

- chat_killer_server.py : Serveur TCP multiclient, gère les messages, commandes et modération.
- chat_killer_client.py : Processus superviseur côté client : il lance deux terminaux (affichage et saisie), gère la communication avec le serveur et les interactions utilisateur.

---

## 🧩 Contributeurs 

- Rafia Ben Slama (moi)
