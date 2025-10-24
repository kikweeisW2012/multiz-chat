#!/usr/bin/env python3
import socket
import threading
import sys
import random

class Colors:
    RED = '\033[91m'
    PURPLE = '\033[35m'
    TEAL = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    
    @staticmethod
    def colorize(message, is_error=False, is_join_leave=False, is_server=False):
        if is_error or is_join_leave:
            return f"{Colors.RED}{message}{Colors.RESET}"
        elif is_server:
            return f"{Colors.WHITE}{message}{Colors.RESET}"
        elif ': ' in message:
            parts = message.split(': ', 1)
            if len(parts) == 2:
                username, content = parts
                if username == '[SERVER]':
                    return f"{Colors.WHITE}{message}{Colors.RESET}"
                return f"{Colors.PURPLE}{username}{Colors.RESET}: {Colors.TEAL}{content}{Colors.RESET}"
        return f"{Colors.TEAL}{message}{Colors.RESET}"

class ChatServer:
    def __init__(self, port):
        self.port = port
        self.clients = []
        self.nicknames = []
        self.client_addresses = []
        self.banned_ips = set()
        
    def broadcast(self, message, exclude_client=None):
        for client in self.clients:
            if client != exclude_client:
                try:
                    client.send(message)
                except:
                    self.remove_client(client)
    
    def remove_client(self, client):
        if client in self.clients:
            index = self.clients.index(client)
            self.clients.remove(client)
            nickname = self.nicknames.pop(index)
            self.client_addresses.pop(index)
            leave_message = f'{nickname} left the chat!'
            print(Colors.colorize(leave_message, is_join_leave=True))
            self.broadcast(leave_message.encode('utf-8'))
            client.close()
    
    def ban_user(self, username, reason="No reason provided"):
        if username in self.nicknames:
            index = self.nicknames.index(username)
            client = self.clients[index]
            client_ip = self.client_addresses[index]
            self.banned_ips.add(client_ip)
            
            try:
                client.send(f"You have been banned from this server. Reason: {reason}".encode('utf-8'))
            except:
                pass
            
            self.remove_client(client)
            ban_message = f"{username} has been banned for the reason of: {reason}"
            print(Colors.colorize(ban_message, is_error=True))
            self.broadcast(ban_message.encode('utf-8'))
            return True
        return False
    
    def handle_client(self, client):
        while True:
            try:
                message = client.recv(1024)
                if message:
                    decoded_message = message.decode('utf-8')
                    print(Colors.colorize(decoded_message))
                    self.broadcast(message, exclude_client=client)
                else:
                    self.remove_client(client)
                    break
            except:
                self.remove_client(client)
                break
    
    def server_input_handler(self):
        while True:
            try:
                server_message = input()
                if server_message.strip():
                    if server_message.startswith('/ban '):
                        ban_args = server_message[5:].strip()
                        if '-' in ban_args:
                            username, reason = ban_args.split('-', 1)
                            username = username.strip()
                            reason = reason.strip()
                            if username:
                                self.ban_user(username, reason)
                            else:
                                print(Colors.colorize("Usage: /ban username-reason", is_error=True))
                        else:
                            print(Colors.colorize("Usage: /ban username-reason", is_error=True))
                    elif server_message.startswith('/help'):
                        print(Colors.colorize("Server commands:", is_server=True))
                        print(Colors.colorize("/ban username-reason - Ban a user with reason", is_server=True))
                        print(Colors.colorize("/help - Show this help message", is_server=True))
                    else:
                        formatted_message = f'[SERVER]: {server_message}'
                        print(Colors.colorize(formatted_message, is_server=True))
                        self.broadcast(formatted_message.encode('utf-8'))
            except KeyboardInterrupt:
                break
            except:
                break
    
    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('0.0.0.0', self.port))
        server.listen()
        
        print(f"Server hosted on port {self.port}")
        print("Waiting for connections...")
        
        input_thread = threading.Thread(target=self.server_input_handler)
        input_thread.daemon = True
        input_thread.start()
        
        while True:
            try:
                client, address = server.accept()
                client_ip = address[0]
                
                if client_ip in self.banned_ips:
                    try:
                        client.send("BANNED".encode('utf-8'))
                        client.close()
                        print(Colors.colorize(f"Blocked banned IP: {client_ip}", is_error=True))
                        continue
                    except:
                        client.close()
                        continue
                
                client.send('NICK'.encode('utf-8'))
                nickname = client.recv(1024).decode('utf-8')
                
                self.nicknames.append(nickname)
                self.clients.append(client)
                self.client_addresses.append(client_ip)
                join_message = f'{nickname} joined the chat!'
                print(Colors.colorize(join_message, is_join_leave=True))
                self.broadcast(join_message.encode('utf-8'))
                client.send('Connected to server!'.encode('utf-8'))
                
                thread = threading.Thread(target=self.handle_client, args=(client,))
                thread.start()
            except KeyboardInterrupt:
                print("\nServer shutting down...")
                server.close()
                break

class ChatClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.nickname = input("Choose a nickname: ")
        
    def receive_messages(self, client):
        while True:
            try:
                message = client.recv(1024).decode('utf-8')
                if message == 'NICK':
                    client.send(self.nickname.encode('utf-8'))
                elif message == 'BANNED':
                    print(Colors.colorize("You have been banned from this server.", is_error=True))
                    client.close()
                    break
                else:
                    if 'has been banned for the reason of:' in message:
                        print(Colors.colorize(message, is_error=True))
                    elif 'joined the chat!' in message or 'left the chat!' in message:
                        print(Colors.colorize(message, is_join_leave=True))
                    else:
                        print(Colors.colorize(message))
            except:
                print(Colors.colorize("An error occurred!", is_error=True))
                client.close()
                break
    
    def send_messages(self, client):
        while True:
            try:
                user_input = input("")
                if user_input.strip():
                    message = f'{self.nickname}: {user_input}'
                    client.send(message.encode('utf-8'))
            except:
                break
    
    def start_client(self):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((self.host, self.port))
            
            receive_thread = threading.Thread(target=self.receive_messages, args=(client,))
            receive_thread.start()
            
            send_thread = threading.Thread(target=self.send_messages, args=(client,))
            send_thread.start()
            
        except ConnectionRefusedError:
            print(Colors.colorize("Could not connect to server. Make sure the host is running and the room code is correct.", is_error=True))
        except Exception as e:
            print(Colors.colorize(f"An error occurred: {e}", is_error=True))

def parse_room_code(room_code):
    if ':' in room_code:
        parts = room_code.split(':')
        if len(parts) == 2:
            try:
                return parts[0], int(parts[1])
            except ValueError:
                return None, None
    else:
        try:
            return "127.0.0.1", int(room_code)
        except ValueError:
            return None, None
    return None, None

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def find_available_port():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        return port
    except:
        return random.randint(10000, 65535)

def main():
    print("===Multiz chat===")
    print("-----------------")
    
    choice = input("(h)ost or (j)oin (h or j): ").lower().strip()
    
    if choice == 'h' or choice == 'host':
        try:
            port = find_available_port()
            local_ip = get_local_ip()
            
            if local_ip != "127.0.0.1":
                print(f"Room code: {local_ip}:{port}")
            else:
                print(f"Room code: {port}")
            
            server = ChatServer(port)
            server.start_server()
            
        except PermissionError:
            print(Colors.colorize("Permission denied. Unable to bind to port.", is_error=True))
        except KeyboardInterrupt:
            print("\nShutting down server...")
        except Exception as e:
            print(Colors.colorize(f"Error starting server: {e}", is_error=True))
    
    elif choice == 'j' or choice == 'join':
        room_code = input("Room code: ")
        ip, port = parse_room_code(room_code)
        
        if ip is None or port is None:
            print(Colors.colorize("Invalid room code format.", is_error=True))
            return
            
        if port < 1024 or port > 65535:
            print(Colors.colorize("Port must be between 1024 and 65535", is_error=True))
            return
        
        try:
            client = ChatClient(ip, port)
            client.start_client()
        except ValueError:
            print(Colors.colorize("Invalid room code", is_error=True))
    
    else:
        print(Colors.colorize("Invalid choice. Please enter 'h' for host or 'j' for join.", is_error=True))

if __name__ == "__main__":
    main()