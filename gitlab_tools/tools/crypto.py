import hashlib
import socket
import paramiko
import random
import time
import sys
import string

import Crypto.PublicKey.RSA as RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256


def sign_data(data: bytes, private_key: RSA):
    """
    Signs message
    :param data: message to sign 
    :param private_key: private key to use
    :return: 
    """
    signer = PKCS1_v1_5.new(private_key)
    digest = SHA256.new()
    digest.update(data)
    return signer.sign(digest)


def verify_data(data: bytes, signature: bytes, public_key: RSA) -> bool:
    """
    Verifies message 
    :param data: Message to verify
    :param signature: signature of message to verify
    :param public_key: public key to use
    :return: 
    """
    signer = PKCS1_v1_5.new(public_key)
    digest = SHA256.new()
    digest.update(data)
    return signer.verify(digest, signature)


def import_key(key_path: str) -> RSA:
    with open(key_path, 'r') as f:
        return RSA.importKey(f.read())


def random_password() -> str:
    """
    Generates random password with fixed len of 64 characters
    :return: 64 len string
    """
    return hashlib.sha256('{}_{}_{}'.format(
        random.randint(0, sys.maxsize),
        round(time.time() * 1000),
        ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(20))
    ).encode('UTF-8')).hexdigest()


def get_remote_server_key(ip: str, port: int=22) -> paramiko.pkey.PKey:
    """
    Returns PKey for given server
    :param ip: IP or Hostname
    :param port: Port
    :return: Returns PKey
    """

    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.connect((ip, port))

    my_transport = paramiko.Transport(my_socket)
    my_transport.start_client()
    ssh_key = my_transport.get_remote_server_key()
    my_transport.close()
    my_socket.close()
    return ssh_key


def calculate_fingerprint(pkey: paramiko.pkey.PKey, algorithm: str='md5') -> bytes:
    """
    Calculates fingerprint for PKey
    :param pkey: pkey
    :param algorithm: algoright to use 
    :return: fingerprint
    """

    h = hashlib.new(algorithm)
    h.update(pkey.asbytes())
    return h.digest()
