import traceback
from base64 import b64encode, b64decode
from contextlib import contextmanager
from functools import wraps
from hashlib import sha3_256

import websocket
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from dataclasses import dataclass

from gamelib import *


def assert_signature(pubkey: bytes, signature: bytes, data: bytes, error_message: str) -> None:
    pk = ed25519.Ed25519PublicKey.from_public_bytes(pubkey)
    try:
        pk.verify(signature, data)
    except InvalidSignature:
        raise MumbleException(error_message)


def sign_data(privkey: bytes, data: bytes) -> bytes:
    key = ed25519.Ed25519PrivateKey.from_private_bytes(privkey)
    return key.sign(sha3_256(data).digest())


def byte_slice(b: bytes) -> bytes:
    return struct.pack('>H', len(b)) + b


def read_byte_slice(b: bytes) -> tuple[bytes, bytes]:
    l, = struct.unpack('>H', b[:2])
    return b[2:2 + l], b[2 + l:]


def read_string(b: bytes) -> bytes:
    l = b[0]
    return b[1:1 + l]


def write_string(b: bytes) -> bytes:
    return bytes([len(b)]) + b


def deserialization_errors(what):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except (KeyError, ValueError, IndexError, struct.error) as e:
                traceback.print_exc()
                raise MumbleException(f'deserialization error ({what})')

        return wrapper

    return decorator


@dataclass
class Sth:
    size: int
    timestamp: bytes
    hash: bytes
    signature: bytes

    @classmethod
    @deserialization_errors('STH')
    def from_binary(cls, b: bytes) -> 'Sth':
        return Sth(
            int.from_bytes(b[:8], byteorder='big'),
            b[8:8 + 15],
            b[8 + 15:8 + 15 + 32],
            b[8 + 15 + 32:]
        )

    def to_binary(self) -> bytes:
        return struct.pack('>Q', self.size) + \
            self.timestamp + \
            self.hash + \
            self.signature


@dataclass
class SOT:
    timestamp: bytes
    hash: bytes
    name: bytes
    signature: bytes

    @classmethod
    @deserialization_errors('STH')
    def from_binary(cls, data: bytes) -> 'SOT':
        owner = data[15:-64]
        return SOT(
            data[:15],
            owner[:32],
            read_string(owner[32:]),
            data[-64:]
        )

    def checksum(self) -> bytes:
        return sha3_256(b'ownership' + self.timestamp + self.hash + write_string(self.name)).digest()


@dataclass
class TreeLeaf:
    created: bytes
    contenthash: bytes
    name: bytes
    pubkey: bytes
    data_for_private_claims: bytes
    data_for_public_claims: bytes

    def to_binary(self) -> bytes:
        assert len(self.created) == 15
        assert len(self.contenthash) == 32
        return self.created + byte_slice(
            self.contenthash + struct.pack('>B', len(self.name)) + self.name
        ) + byte_slice(self.pubkey) + byte_slice(self.data_for_private_claims) + byte_slice(self.data_for_public_claims)

    @classmethod
    @deserialization_errors('TreeLeaf')
    def from_binary(cls, data: bytes) -> 'TreeLeaf':
        ts = data[:15]
        owner, data = read_byte_slice(data[15:])
        pubkey, data = read_byte_slice(data)
        data_private, data = read_byte_slice(data)
        data_public, data = read_byte_slice(data)
        return TreeLeaf(
            ts,
            owner[:32],
            read_string(owner[32:]),
            pubkey,
            data_private,
            data_public
        )


@dataclass
class TreeLeafProof:
    head: Sth
    index: int
    leaf: bytes
    hashes: list[bytes]

    def to_binary(self) -> bytes:
        return byte_slice(self.head.to_binary()) + \
            struct.pack('>Q', self.index) + \
            byte_slice(self.leaf) + \
            struct.pack('>H', len(self.hashes)) + b''.join(self.hashes)

    @classmethod
    @deserialization_errors('TreeLeafProof')
    def from_binary(self, data: bytes) -> 'TreeLeafProof':
        head, data = read_byte_slice(data)
        index, = struct.unpack('>Q', data[:8])
        leaf, data = read_byte_slice(data[8:])
        hash_len, = struct.unpack('>H', data[:2])
        hashes = [data[2 + i * 32:2 + i * 32 + 32] for i in range(hash_len)]
        return TreeLeafProof(Sth.from_binary(head), index, leaf, hashes)

    def validate(self) -> bool:
        hash1 = sha3_256(self.leaf).digest()
        pos: TreeIntermediatePos = TreeIntermediatePos(self.index, self.index + 1)
        for hash2 in self.hashes:
            if pos.is_root(self.head.size):
                return False
            if pos.is_left_child():
                hash1 = sha3_256(hash1 + hash2).digest()
            else:
                hash1 = sha3_256(hash2 + hash1).digest()
            pos = pos.parent()

        return pos.is_root(self.index) and hash1 == self.head.hash


@dataclass
class TreeIntermediatePos:
    left: int
    right: int

    def is_root(self, size: int) -> bool:
        return self.left == 0 and self.right >= size

    def is_left_child(self) -> bool:
        return self.left & (self.right - self.left) == 0

    def parent(self) -> 'TreeIntermediatePos':
        if self.is_left_child():
            return TreeIntermediatePos(
                self.left,
                self.right + self.right - self.left,
            )
        else:
            return TreeIntermediatePos(
                self.left - (self.right - self.left),
                self.right,
            )


def json_encode(data: Any) -> bytes:
    for k, v in list(data.items()):
        if isinstance(v, bytes):
            data[k] = b64encode(v).decode()
    return json.dumps(data).encode()


class Api:
    def __init__(self, ip: str) -> None:
        self.ip = ip
        self.session = Session()

    def get_entries(self, start: int, end: int) -> list[bytes]:
        response = self.session.get(f'http://{self.ip}:3000/api/v1/get-entries?start={start}&end={end}')
        assert_requests_response(response)
        print(f'< {response}')
        assert 'leaves' in response.json(), 'Invalid response from get-entries'
        try:
            return [b64decode(leaf) for leaf in response.json()['leaves']]
        except Exception as e:
            raise MumbleException('Invalid base64 encoding in get-entries')

    def get_entry_proof(self, index: int) -> bytes:
        response = self.session.get(f'http://{self.ip}:3000/api/v1/get-entry-and-proof?leaf_index={index}')
        assert_requests_response(response)
        print(f'< {response}')
        assert 'proof' in response.json(), 'Invalid response from get-entry-and-proof'
        try:
            return b64decode(response.json()['proof'])
        except Exception as e:
            raise MumbleException('Invalid base64 encoding in get-entry-and-proof')

    def add_entry(self, entry: Any) -> int:
        response = self.session.post(f'http://{self.ip}:3000/api/v1/add-entry', data=json_encode(entry))
        assert_requests_response(response)
        print(f'< {response.text}')
        assert 'index' in response.json(), 'Invalid response from add-entry'
        index = response.json()['index']
        assert isinstance(index, int), 'Invalid response from add-entry'
        return index

    def sign_entry(self, entry: Any) -> bytes:
        response = self.session.post(f'http://{self.ip}:3000/api/v1/sign-entry', data=json_encode(entry))
        assert_requests_response(response)
        print(f'< {response.text}')
        assert 'sot' in response.json(), 'Invalid response from sign-entry'
        try:
            return b64decode(response.json()['sot'])
        except Exception as e:
            raise MumbleException('Invalid base64 encoding in sign-entry')

    def get_sth(self) -> bytes:
        response = self.session.get(f'http://{self.ip}:3000/api/v1/get-sth')
        assert_requests_response(response)
        print(f'< {response.text}')
        assert 'sth' in response.json(), 'Invalid response from get-sth'
        try:
            return b64decode(response.json()['sth'])
        except Exception as e:
            raise MumbleException('Invalid base64 encoding in get-sth')

    def get_pubkey(self, from_monitor: bool = False) -> bytes:
        response = self.session.get(f'http://{self.ip}:{3001 if from_monitor else 3000}/api/v1/get-pubkey')
        assert_requests_response(response)
        print(f'< {response.text}')
        assert 'pubkey' in response.json(), 'Invalid response from get-pubkey'
        try:
            return b64decode(response.json()['pubkey'])
        except Exception as e:
            raise MumbleException('Invalid base64 encoding in get-pubkey')

    def claim_private(self, sot: bytes, claimed_leaf: bytes) -> str:
        response = self.session.post(f'http://{self.ip}:3001/api/v1/claim-private', data=json_encode({
            'sot': sot,
            'claimed_leaf': claimed_leaf
        }))
        assert_requests_response(response)
        print(f'< {response.text}')
        return self._parse_claim_response(response)

    def claim_public(self, claiming_leaf: bytes, claimed_leaf: bytes, signature: bytes) -> str:
        response = self.session.post(f'http://{self.ip}:3001/api/v1/claim-public', data=json_encode({
            'claiming_leaf': claiming_leaf,
            'claimed_leaf': claimed_leaf,
            'claiming_leaf_signature': signature,
        }))
        assert_requests_response(response)
        print(f'< {response.text}')
        return self._parse_claim_response(response)

    def _parse_claim_response(self, response: requests.Response) -> str:
        d = response.json()
        assert 'granted' in d and 'data' in d, 'invalid claim response'
        assert d['granted'] is True, 'claim not granted'
        assert isinstance(d['data'], str), 'invalid claim response'
        return d['data']

    @contextmanager
    def watch(self, timeout: float = TIMEOUT):
        print('> /api/v1/watch')
        ws = websocket.create_connection(f"ws://{self.ip}:3001/api/v1/watch", timeout=timeout)
        try:
            print('< websocket open')
            yield ws
        finally:
            ws.close()
