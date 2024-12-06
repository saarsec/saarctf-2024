import random
import sys
import time
import traceback
from base64 import b64encode, b64decode
from binascii import hexlify

import websocket
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption

from gamelib import *

try:
    from .api import Api, Sth, TreeLeaf, TreeLeafProof, assert_signature, sign_data, SOT
except ImportError:
    from api import Api, Sth, TreeLeaf, TreeLeafProof, assert_signature, sign_data, SOT


class CertifiedTransparencyInterface(ServiceInterface):
    name = 'CertifiedTransparency'

    def __init__(self, service_id: int) -> None:
        super().__init__(service_id)
        self._pubkey: bytes | None = None

    def finalize_team(self, team: Team) -> None:
        super().finalize_team(team)
        self._pubkey = None

    def check_integrity(self, team: Team, tick: int):
        api = Api(team.ip)
        self._pubkey = api.get_pubkey()
        assert len(self._pubkey) == 32, 'invalid public key'
        binary_sth = api.get_sth()
        sth = Sth.from_binary(binary_sth)
        assert_signature(self._pubkey, sth.signature, sth.hash, 'invalid sth signature')

    def store_flags(self, team: Team, tick: int):
        flag1 = self.get_flag(team, tick, 0)
        flag2 = self.get_flag(team, tick, 1)
        chash: bytes = os.urandom(32)
        self.store(team, tick, 'chash', b64encode(chash).decode())

        api = Api(team.ip)
        if self._pubkey is None:
            self._pubkey = api.get_pubkey()
            assert len(self._pubkey) == 32, 'invalid public key'

        # Step 1: get a SOT
        sot = api.sign_entry({
            'content_hash': chash,
            'name': usernames.generate_username(),
        })
        self.store(team, tick, 'sot', b64encode(sot).decode())
        decoded_sot = SOT.from_binary(sot)
        assert_signature(self._pubkey, decoded_sot.signature, decoded_sot.checksum(), 'invalid sot signature')
        assert decoded_sot.hash == chash, 'sot for wrong hash'

        try:
            with api.watch() as ws:
                ws.ping('')
                time.sleep(random.randint(500, 1500) / 1000.0)

                # Step 2: get a public entry
                claim_private_key = ed25519.Ed25519PrivateKey.generate()
                claim_index = api.add_entry({
                    'content_hash': chash,
                    'name': usernames.generate_username(),
                    'pubkey': claim_private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
                    'data_private': '',
                    'data_public': ''
                })
                if claim_index < 2:
                    # some extra entries so that attacks work
                    api.add_entry({
                        'content_hash': chash,
                        'name': usernames.generate_username(),
                        'pubkey': claim_private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw),
                        'data_private': '',
                        'data_public': ''
                    })
                time.sleep(random.randint(500, 1500) / 1000.0)

                # Step 3: store the actual flag
                flag_public_key = ed25519.Ed25519PrivateKey.generate().public_key()
                flag_index = api.add_entry({
                    'content_hash': chash,
                    'name': 'SaarFlag Corporation International',
                    'pubkey': flag_public_key.public_bytes(Encoding.Raw, PublicFormat.Raw),
                    'data_private': flag1,
                    'data_public': flag2
                })
                self.store(team, tick, 'indices', (claim_index, flag_index))
                self.store(team, tick, 'privatekey', b64encode(
                    claim_private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
                ).decode())

                self._wait_for_ws_message(ws, flag_index, chash)
        except ConnectionRefusedError:
            raise OfflineException('Websocket unavailable')
        except websocket.WebSocketException:
            traceback.print_exc()
            raise MumbleException('Websocket connection failed')

    def retrieve_flags(self, team: Team, tick: int):
        try:
            chash: bytes = b64decode(self.load(team, tick, 'chash'))
            sot: bytes = b64decode(self.load(team, tick, 'sot'))
            claim_index, flag_index = self.load(team, tick, 'indices')
            private_key: bytes = b64decode(self.load(team, tick, 'privatekey'))
        except TypeError:
            raise FlagMissingException('flag not stored')

        api = Api(team.ip)
        if self._pubkey is None:
            self._pubkey = api.get_pubkey()
            assert len(self._pubkey) == 32, 'invalid public key'

        flag_proof = api.get_entry_proof(flag_index)
        self._check_proof(self._pubkey, chash, flag_proof)
        flag1 = api.claim_private(sot, flag_proof)
        if flag1 != self.get_flag(team, tick, 0):
            raise FlagMissingException('Could not claim flag with private proof')

        claiming_proof = api.get_entry_proof(claim_index)
        self._check_proof(self._pubkey, chash, claiming_proof)
        signature = sign_data(private_key, TreeLeafProof.from_binary(claiming_proof).leaf)
        flag2 = api.claim_public(claiming_proof, flag_proof, signature)
        if flag2 != self.get_flag(team, tick, 1):
            raise FlagMissingException('Could not claim flag with public proof')

    def _check_proof(self, pubkey: bytes, chash: bytes, binary_proof: bytes) -> None:
        proof = TreeLeafProof.from_binary(binary_proof)
        assert_signature(pubkey, proof.head.signature, proof.head.hash, 'invalid sth signature')
        assert proof.validate(), 'invalid proof hash chain'
        leaf = TreeLeaf.from_binary(proof.leaf)
        assert leaf.contenthash == chash, 'proof for wrong hash'

    def _wait_for_ws_message(self, ws: websocket.WebSocket, flag_index: int, chash: bytes):
        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            message = ws.recv()
            print(f'< [websocket] {message}')
            try:
                parsed = json.loads(message)
                index, leaf = parsed['index'], TreeLeaf.from_binary(b64decode(parsed['leaf']))
                if index == flag_index and leaf.contenthash == chash:
                    return
                else:
                    print(f'  ws received: {index} {hexlify(leaf.contenthash)} {leaf.name}')
            except:
                traceback.print_exc()
        raise MumbleException('/watch did not report new entries')


if __name__ == '__main__':
    # USAGE: python3 interface.py                      # test against localhost
    # USAGE: python3 interface.py 1.2.3.4              # test against IP
    # USAGE: python3 interface.py 1.2.3.4 retrieve     # retrieve last 10 ticks (for exploits relying on checker interaction)
    # (or use gamelib/run-checkers to test against docker container)
    team = Team(1, 'TestTeam', sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1')
    service = CertifiedTransparencyInterface(1)

    if len(sys.argv) > 2 and sys.argv[2] == 'store':
        for tick in range(1, 5):
            try:
                # exploit requires us to store some flags
                service.store_flags(team, tick)
            except:
                pass
        sys.exit(0)

    for tick in range(1, 4):
        print(f'\n\n=== TICK {tick} ===')
        service.check_integrity(team, tick)
        service.store_flags(team, tick)
        service.retrieve_flags(team, tick)
