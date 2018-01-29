import hashlib
import random
import sys


def random_password() -> str:
    return hashlib.md5(str(random.randint(0, sys.maxsize)).encode('UTF-8')).hexdigest()
