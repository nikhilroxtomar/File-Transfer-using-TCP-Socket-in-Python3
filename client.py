import socket
from base64 import b64encode, b64decode
from json import loads, dumps

# FORMAT = 'utf-8'


class ClientHandler:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None
        self.email = None
        self.password = None
        self.connect()
        self.isconnected = False

    def run(self):
        print('[CLIENT] This is run()')
        while True:
            response = input('[SIGN IN]: 1\n[SIGN UP]: 2\n> ')
            self.send_text(response)
            if self.recv_text() == '-1':
                print('<WRONG INPUT>')
                continue
            elif response == '1':
                # [SIGN IN]
                while True:
                    # input username
                    username = input('username: ')
                    self.send_text(username, True)
                    if self.recv_text() == '-1':
                        print('<INEXISTENT USERNAME>')
                        continue
                    break
                while True:
                    # input password
                    password = input('password: ')
                    self.send_text(password, True)
                    if self.recv_text() == '-1':
                        print('<WRONG PASSWORD>')
                        continue
                    break
                self.send_text()
                cln_info = self.recv_data(1024, True)
                print(cln_info)         ###############
                self.set_cln_info(cln_info)
            elif response == '2':
                # [SIGN UP]
                while True:
                    # input username
                    username = input('username: ')
                    self.send_text(username, True)
                    if self.recv_text() == '-1':
                        print('<USERNAME IS UNAVAILABLE>')
                        continue
                    self.set_username(username)
                    break
                while True:
                    # input email
                    email = input('email:    ')
                    self.send_text(email, True)
                    if self.recv_text() == '-1':
                        print('<THIS EMAIL IS ALREADY USED>')
                        continue
                    self.set_email(email)
                    break
                while True:
                    # input password
                    password = input('password: ')
                    if password != input('confirm:  '):
                        print('<PASSWORD DID NOT MATCHED>')
                        continue
                    self.send_text(password, True)
                    self.set_password(password)
                    break
            self.isconnected = True
            self.recv_text()
            break

        while True:
            response = self.recv_()
            if response == 'help':
                msg = '[list]:   list all the files from the server.\n' \
                      '[upload]: upload a file to the server.\n' \
                      '[delete]: delete a file from the server.\n' \
                      '[logout]: disconnect from the server.\n' \
                      '[help]:   list all the commands'
                self.send_text(msg)
                continue
            elif response == 'logout':
                self.conn.close()
                self.send_text('Connection is closed!')
            elif response == 'list':
                files = os.listdir(self.client.client_path)
                self.send_text(str(files))
            elif response == 'delete':
                self.send_text()
                while True:
                    filename = self.recv_()
                    filepath = os.path.join(self.client.client_path, filename)
                    if os.path.exists(filepath):
                        os.system(f'rm {filepath}')
                        self.send_text()
                        break
                    self.send_text('-1')
            elif response == 'upload':
                self.send_text()
                self.recv()
                self.send_text()

    def prepare_text(self, text=' ', encode=False):
        if encode:
            return b64encode(text.encode()).decode()
        else:
            return text

    def prepare_file(self, filepath, encode):
        with open(filepath, 'wb') as f:
            file_data = f.read()
            if encode:
                file_data = b64encode(file_data)
            return file_data

    def send(self, data_type=None, text=None, filepath=None, isfolder=False, folder_path=None, encode=False,
             to_client=False, client_username=''):
        sendable_data = dict()
        send_info = {'data_type': data_type,
                     'isfolder': str(isfolder),
                     'folder_name': os.path.split(folder_path),
                     'to_client': str(to_client),
                     'client_username': client_username,
                     'encoded': str(encode)}
        self.send_dict(send_info)
        self.conn.recv(1)
        if data_type == 'text':
            sendable_data['data'] = self.prepare_text(text, encode)
        elif data_type == 'file':
            sendable_data['filename'] = os.path.split(filepath)[-1]
            sendable_data['data'] = self.prepare_file(filepath, encode)
        # elif data_type == 'data_sheet':
        #     sendable_data['filename'] = os.path.split(filepath)[-1]
        elif isfolder:
            if os.path.exists(folder_path):
                for item in os.listdir(folder_path):
                    item_path = os.path.join(folder_path, item)
                    self.send(data_type=data_type, filepath=item_path, encode=encode, to_client=to_client)
                self.send_dict({'finished': 'True'})
                return
        self.send_dict(sendable_data)
        self.recv_(1)

    def send_data(self, data):
        self.conn.sendall(dumps(data, indent=4).encode() + b':EOF')

    # [recv]
    def recv(self, buffer=None):
        recv_info = loads(self.conn.recv(1024)[:-4].decode())
        self.conn.send(b' ')
        decode = bool()
        if recv_info.get('encoded') == ' True':
            decode = True
        if recv_info.get('data_type') == 'text':
            if buffer is None:
                buffer = 1024
            return self.recv_(buffer, decode)
        elif recv_info.get('data_type') == 'file':
            if buffer is None:
                buffer = 81920  # 80 KB
            self.recv_file(buffer, decode)
        elif recv_info.get('data+type') == 'folder':
            if buffer is None:
                buffer = 81920  # 80 KB
            while self.recv_file(buffer, decode):
                pass

    def recv_text(self, buffer, decode):
        data = loads(self.conn.recv(buffer)[:-4].decode())['data']
        if decode:
            b64decode(data.encode()).decode()
        return data

    def recv_file(self, buffer, decode):
        data = b''
        while True:
            data_chunk = self.conn.recv(buffer)
            if data_chunk[-4:] == b':EOF':
                data += data_chunk[:-4]
                break
            data += data_chunk
        data = loads(data.decode())
        if data.get('finished') == 'True':
            return False
        filename = data['filename']
        if decode:
            data = b64decode(data['data'].encode())
        with open(filename, 'wb') as f:
            f.write(data)
            f.close()
        return True

    def recv_(self, buffer=1024, decode=False):
        msg = self.conn.recv(buffer)
        if decode:
            msg = b64decode(msg.decode())
        return msg.decode()

    def recv_dict(self, buffer=1024, decode=False):
        data = b''
        while True:
            data_chunk = self.conn.recv(buffer)
            if data_chunk[-4:] == b':EOF':
                data += data_chunk[:-4]
                break
            data += data_chunk
        data = loads(data.decode())
        if decode:
            for key in data.keys():
                data[key] = b64decode(data[key].encode()).decode()
        return data

    def send_text(self, msg=' ', encode=False):
        if encode:
            self.conn.send(b64encode(msg.encode()))
        else:
            self.conn.send(msg.encode())

    def send_dict(self, data, encode=False):
        if encode:
            for key in data.keys():
                data[key] = b64encode(data[key].encode()).decode()
        self.conn.sendall(dumps(data, indent=4).encode() + b':EOF')

    def connect(self):
        self.conn.connect(self.get_addr())

    def get_addr(self):
        return self.get_ip(), self.get_port()

    def get_ip(self):
        return self.ip

    def get_port(self):
        return self.port

    def get_username(self):
        return self.username

    def set_username(self, username):
        self.username = username

    def get_email(self):
        return self.email

    def set_email(self, email):
        self.email = email

    def get_password(self):
        return self.password

    def set_password(self, password):
        self.password = password

    def get_cln_info(self):
        return {'username': self.get_username(),
                'email': self.get_email(),
                'password': self.get_password()}

    def set_cln_info(self, info):
        self.set_username(info['username'])
        self.set_email(info['email'])
        self.set_password(info['password'])


def client_main():
    IP = 'localhost'
    PORT = 5050
    client = ClientHandler(IP, PORT)
    client.run()
    # client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # client.connect((IP, PORT))


if __name__ == '__main__':
    client_main()
