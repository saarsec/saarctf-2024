import sys
import random
from pathlib import Path

from gamelib import *

# See the "SampleServiceInterface" from gamelib for a bigger example
# See https://gitlab.saarsec.rocks/saarctf/gamelib/-/blob/master/docs/howto_checkers.md for documentation.

class API:
    def __init__(self, base_url, session=None):
        self.session = session or Session()
        self.base_url = base_url.rstrip('/')
    
    def login(self, username: str, password: str) -> bool:
        assert_requests_response(self.session.post(f"{self.base_url}/api/login", json={"username":username, "password":password}), "application/json")

    def info(self) -> dict[str,object]:
        r = assert_requests_response(self.session.get(f"{self.base_url}/api/info"), "application/json")
        return r.json()
    
    def reverse_text(self, text: str) -> int:
        r = assert_requests_response(self.session.post(f"{self.base_url}/api/text/new", headers={'Content-Type': 'text/plain;charset=UTF-8'}, data=text), "application/json")
        r_id = r.json().get('id', None)
        assert r_id is not None
        return r_id
    
    def reverse_array(self, array: list[int]) -> int:
        r = assert_requests_response(self.session.post(f"{self.base_url}/api/array/new", headers={'Content-Type': 'application/octet-stream', 'Content-Transfer-Encoding': 'base64'}, data=base64.b64encode(bytes(array))), "application/json")
        r_id = r.json().get('id', None)
        assert r_id is not None
        return r_id
    
    def reverse_audio(self, audiodata: bytes) -> int:
        r = assert_requests_response(self.session.post(f"{self.base_url}/api/audio/new", headers={'Content-Type': 'application/octet-stream'}, data=audiodata), "application/json")
        r_id = r.json().get('id', None)
        assert r_id is not None
        return r_id
    
    def get_text(self, r_id:int) -> str:
        r = assert_requests_response(self.session.get(f"{self.base_url}/api/text/{r_id}"), "application/octet-stream")
        return r.text
    
    def get_array(self, r_id:int) -> list[int]:
        r = assert_requests_response(self.session.get(f"{self.base_url}/api/array/{r_id}"), "application/octet-stream")
        return list(base64.b64decode(r.text))
    
    def get_audio(self, r_id:int) -> bytes:
        r = assert_requests_response(self.session.get(f"{self.base_url}/api/audio/{r_id}"), "application/octet-stream")
        return r.content

def gen_random_sample(debug=False):
    if debug: # generate simple audio files for debugging
        SAMPLE_LEN = 0x27 #adjust to taste
        sample = bytes.fromhex('524946463400000057415645666D7420100000000100010044AC000044AC00000100080064617461') + SAMPLE_LEN.to_bytes(4, 'little') + bytes(i&0xff for i in range(SAMPLE_LEN))
    else:
        with open(random.choice(list(Path(__file__).parent.glob('*.wav'))),'rb') as f:
            sample = f.read()
    
    
    data_start = sample.find(b'data')
    if data_start < 0:
        raise ValueError("Cannot find data chunk of sample")
    data_start += 8 # adjust for tag and length
    
    sample_len = min(random.randint(8*1024, 255*1024), len(sample)-data_start)
    sample_offset = random.randint(0, len(sample) - (data_start+sample_len))
    # find start of DATA chunk
    subsample = sample[8:data_start-4] + sample_len.to_bytes(4, 'little') + sample[data_start+sample_offset:data_start+sample_offset+sample_len]
    return b'RIFF' + len(subsample).to_bytes(4, 'little') + subsample

class ReversaarInterface(ServiceInterface):
    name = 'Reversaar'
    flag_id_types = ['username', 'username', 'username']

    EVERY_N_TEXT = 5    # simple flag, but only every 5th tick
    EVERY_N_ARRAY = 2   # medium flag, every 2nd tick
    EVERY_N_AUDIO = 1   # hard flag, every tick

    def check_integrity(self, team: Team, tick: int):
        session = Session()
        response = assert_requests_response(session.get(f'http://{team.ip}:7331/'), 'text/html')
        self.check_integrity_text(team)
        self.check_integrity_array(team)
        self.check_integrity_audio(team)
    
    def check_integrity_text(self, team):
        username = usernames.generate_username()
        password = usernames.generate_password()
        print(f"Testing text reversing functionality with user {username} (pw: {password})")
        api = API(f'http://{team.ip}:7331/')
        api.login(username, password)
        test_text = usernames.generate_name(words=random.randint(8, 64), alphanum=False, sep=' ')
        if random.randint(0,1) == 0:
            test_text = test_text[::-1]
        r_id = api.reverse_text(test_text)
        assert api.get_text(r_id) == test_text[::-1], "Failed to reverse text"
    
    def check_integrity_array(self, team):
        username = usernames.generate_username()
        password = usernames.generate_password()
        print(f"Testing array reversing functionality with user {username} (pw: {password})")
        api = API(f'http://{team.ip}:7331/')
        api.login(username, password)
        test_array = random.randbytes(random.randint(8, 256))
        if random.randint(0,1) == 0:
            test_array = test_array[::-1]
        r_id = api.reverse_array(list(test_array))
        assert bytes(api.get_array(r_id)) == test_array[::-1], "Failed to reverse array"
    
    def check_integrity_audio(self, team):
        username = usernames.generate_username()
        password = usernames.generate_password()
        print(f"Testing audio reversing functionality with user {username} (pw: {password})")
        api = API(f'http://{team.ip}:7331/')
        api.login(username, password)
        test_audio = bytearray(gen_random_sample())
        data_start = test_audio.find(b'data')
        if data_start < 0:
            raise ValueError("Cannot find data chunk of sample")
        data_start += 8 # adjust for tag and length
        if random.randint(0,1) == 0:
            test_audio[data_start:] = test_audio[data_start:][::-1]
        r_id = api.reverse_audio(test_audio)
        return_audio = api.get_audio(r_id)
        assert len(return_audio) == len(test_audio), "Failed to reverse audio (truncated)"
        assert return_audio[:data_start] == test_audio[:data_start], "Failed to reverse audio (header modified)"                    
        assert return_audio[data_start:] == test_audio[data_start:][::-1], "Failed to reverse audio (data incorrect)"

    def store_flags(self, team: Team, tick: int):
        if (tick + team.id) % self.EVERY_N_TEXT == 0:
            self.store_flag_text(team, tick)
        if (tick + team.id) % self.EVERY_N_ARRAY == 0:
            self.store_flag_array(team, tick)
        if (tick + team.id) % self.EVERY_N_AUDIO == 0:
            self.store_flag_audio(team, tick)
    
    def store_flag_text(self, team: Team, tick: int):
        try:
            username, password, r_id = self.load(team, tick, 'credentials_text')
            return #already done
        except TypeError:
            pass
        flag = self.get_flag(team, tick, 0)
        username = self.get_flag_id(team, tick, 0)
        password = usernames.generate_password()
        
        api = API(f'http://{team.ip}:7331/')
        print(f"Storing text flag for user {username} (pw: {password}): {flag}...")
        api.login(username, password)
        r_id = api.reverse_text(flag + flag[::-1])
        if r_id is not None:
            print(f"success!")
            self.store(team, tick, 'credentials_text', [username, password, r_id])
        else:
            print(f"failed :(")
        

    def store_flag_array(self, team: Team, tick: int):
        try:
            username, password, r_id = self.load(team, tick, 'credentials_array')
            return #already done
        except TypeError:
            pass
        flag = self.get_flag(team, tick, 1)
        username = self.get_flag_id(team, tick, 1)
        password = usernames.generate_password()
        
        api = API(f'http://{team.ip}:7331/')
        print(f"Storing array flag for user {username} (pw: {password}): {flag}...")
        api.login(username, password)
        r_id = api.reverse_array(list(flag.encode('ascii')))
        if r_id is not None:
            print(f"success!")
            self.store(team, tick, 'credentials_array', [username, password, r_id])
        else:
            print(f"failed :(")
        

    def store_flag_audio(self, team: Team, tick: int):
        try:
            username, password, r_id = self.load(team, tick, 'credentials_audio')
            return #already done
        except TypeError:
            pass
        
        flag = self.get_flag(team, tick, 2)
        flag_encoded = flag.encode('ascii')
        username = self.get_flag_id(team, tick, 2)
        password = usernames.generate_password()
        
        api = API(f'http://{team.ip}:7331/')
        print(f"Storing audio flag for user {username} (pw: {password}): {flag}...")
        api.login(username, password)
        
        sample = bytearray(gen_random_sample())
        data_start = sample.find(b'data')
        if data_start < 0:
            raise ValueError("Cannot find data chunk of sample")
        data_start += 8 # adjust for tag and length
        
        flag_pos = random.randint(data_start, len(sample) - len(flag_encoded))
        sample[flag_pos:flag_pos+len(flag_encoded)] = flag_encoded
        
        r_id = api.reverse_audio(sample)
        if r_id is not None:
            print(f"success!")
            self.store(team, tick, 'credentials_audio', [username, password, r_id])
        else:
            print(f"failed :(")


    def retrieve_flags(self, team: Team, tick: int):
        if (tick + team.id) % self.EVERY_N_TEXT == 0:
            self.retrieve_flag_text(team, tick)
        if (tick + team.id) % self.EVERY_N_ARRAY == 0:
            self.retrieve_flag_array(team, tick)
        if (tick + team.id) % self.EVERY_N_AUDIO == 0:
            self.retrieve_flag_audio(team, tick)
        
    
    def retrieve_flag_text(self, team: Team, tick: int):
        try:
            username, password, r_id = self.load(team, tick, 'credentials_text')
        except TypeError:
            raise FlagMissingException('Flag not stored')  # self.store didn't run last tick
        print(f"Retrieving text flag for user {username} (pw: {password}), idx {r_id}...")

        api = API(f'http://{team.ip}:7331/')
        api.login(username, password)
        text = api.get_text(r_id)
        print(f"Got text: {text}")

        flag = self.get_flag(team, tick, 0)
        if flag not in text and flag not in text[::-1]:
            raise FlagMissingException('Flag not found')

    def retrieve_flag_array(self, team: Team, tick: int):
        try:
            username, password, r_id = self.load(team, tick, 'credentials_array')
        except TypeError:
            raise FlagMissingException('Flag not stored')  # self.store didn't run last tick
        print(f"Retrieving array flag for user {username} (pw: {password}), idx {r_id}...")

        api = API(f'http://{team.ip}:7331/')
        api.login(username, password)
        array_bytes = bytes(api.get_array(r_id))
        print(f"Got array: {array_bytes}")

        flag_encoded = self.get_flag(team, tick, 1).encode('ascii')
        
        if flag_encoded not in array_bytes and flag_encoded not in array_bytes[::-1]:
            raise FlagMissingException('Flag not found')
        
    def retrieve_flag_audio(self, team: Team, tick: int):
        try:
            username, password, r_id = self.load(team, tick, 'credentials_audio')
        except TypeError:
            raise FlagMissingException('Flag not stored')  # self.store didn't run last tick
        print(f"Retrieving audio flag for user {username} (pw: {password}), idx {r_id}...")

        api = API(f'http://{team.ip}:7331/')
        api.login(username, password)
        audio = api.get_audio(r_id)
        print(f"Got audio (first 64 bytes:) {audio[:64]}")

        flag_encoded = self.get_flag(team, tick, 2).encode('ascii')
        if flag_encoded not in audio and flag_encoded not in audio[::-1]:
            raise FlagMissingException('Flag not found')


if __name__ == '__main__':
    # USAGE: python3 interface.py                      # test against localhost
    # USAGE: python3 interface.py 1.2.3.4              # test against IP
    # USAGE: python3 interface.py 1.2.3.4 retrieve     # retrieve last 10 ticks (for exploits relying on checker interaction)
    # USAGE: python3 interface.py 1.2.3.4 store        # store a few ticks (for exploits relying on checker interaction)
    # (or use gamelib/run-checkers to test against docker container)
    team = Team(1, 'TestTeam', sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1')
    service = ReversaarInterface(1)

    if len(sys.argv) > 2 and sys.argv[2] == 'retrieve':
        for tick in range(1, 10):
            try:
                service.retrieve_flags(team, tick)
            except:
                pass
        sys.exit(0)
    elif len(sys.argv) > 2 and sys.argv[2] == 'store':
        for tick in range(50, 55):
            try:
                service.store_flags(team, tick)
            except:
                pass
        sys.exit(0)

    for tick in range(1, 4):
        print(f'\n\n=== TICK {tick} ===')
        service.check_integrity(team, tick)
        service.store_flags(team, tick)
        service.retrieve_flags(team, tick)
