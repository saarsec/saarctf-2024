import sys
import random

from gamelib import *

# See the "SampleServiceInterface" from gamelib for a bigger example
# See https://gitlab.saarsec.rocks/saarctf/gamelib/-/blob/master/docs/howto_checkers.md for documentation.

from pwn import *
import re


## Parsing chars

def set_palette(pal):
    return bytes([0x9b, 0x30 + pal, 0x40])

def set_fg_color_simple(c):
    return bytes([0x80 + c]) 

def set_bg_color_simple(c):
    return bytes([0x90 + c]) 

def set_fg_color(c):
    return set_palette(c >> 3) + set_fg_color_simple(c & 7)

def set_bg_color(c):
    return set_palette(c >> 3) + set_bg_color_simple(c & 7)

def show_cursor():
    return b'\x11'

def set_cursor(y, x):
    return bytes([0x1f, 0x40 + y, 0x40 + x])

def end_of_page():
    return b'\x1f\x58\x41\x11\x1a'

## Interaction chars

# this is the f2 button
def terminator():
    return b'\x1c'

# this is the f1 button
def initiator():
    return b'\x13'

debug=True
def debug_print(s):
    if debug:
        dbg = ""
        for c in s:
            dbg += hex(c)[2:]
        print(f"{dbg}")


fingerprints = {
    # "login":[(2, 1), (18, 8), (18, 25), (18, 36), (20, 8)],
    "login":[(24, 1), (24, 1), (24, 19), (2, 1), (18, 8), (20, 8), (20, 26), (22, 8), (24, 1), (24, 1), (24, 19), (24, 1), (18, 26), (20, 27), (22, 26), (18, 26)],
    "home": [(24, 1), (24, 1), (24, 19), (19, 1), (24, 1), (24, 1), (24, 19), (24, 1), (24, 1), (24, 1)],
    "create_user": [(24, 1), (24, 1), (24, 1), (24, 1), (24, 19), (2, 1), (7, 25), (12, 31), (24, 1), (24, 1), (24, 19), (24, 1), (6, 19), (8, 13), (9, 12), (10, 13), (11, 9), (12, 6), (12, 17), (12, 37), (15, 11), (6, 19)], 
    "blog": [(24, 1), (24, 1), (24, 1), (24, 2), (24, 1), (24, 1), (24, 19), (2, 1), (7, 1), (11, 1), (24, 1), (24, 1), (24, 19), (24, 1), (8, 1), (12, 1), (8, 1)],
    "blog_overview": [(24, 1), (24, 1), (24, 1), (24, 1), (24, 19), (2, 1), (24, 1), (24, 1), (24, 19), (24, 1), (24, 1), (24, 1)],
}
# pages seem to always end with this ending if it is this weird hint
# without hint, it is probably sequence_end_of_page
page_ends = {
    "login": set_fg_color(3) + set_bg_color(12) + show_cursor(),
    "logout": set_cursor(24,1) + show_cursor(),
    "home": set_cursor(24,1) + show_cursor(),
    "create_user": set_fg_color(3) + set_bg_color(12) + show_cursor(),
    "blog": set_fg_color(3) + set_bg_color(4) + show_cursor(),
    "blog_overview": set_cursor(24,1) + set_cursor(24,1) + show_cursor(),
}


def sublist(subset, complete):
   ls = [element for element in subset if element in complete]
   return len(ls) == len(subset)

def get_cursors(data):
    r = re.findall(b"\x1f..",data)
    cursor_list = []
    for m in r:
        ctrl, y, x = m
        if (y<0x40) or (x<0x40):
            continue
        assert ctrl == 0x1f 
        cursor_list.append((y-0x40,x-0x40))
    print(cursor_list)
    return cursor_list
    
def verify_page(data,name):
    ctrl = fingerprints[name]
    return sublist(ctrl,data)

def login(conn, participant_number=b"", password=b""):
    data = conn.recvuntil(page_ends["login"])
    assert verify_page(get_cursors(data),"login"), "Could not access login page"
    conn.send(participant_number + terminator())
    data = conn.recvuntil(page_ends["login"])
    assert b"Enter extension" in data, "Login process broken"
    conn.send(terminator())
    data = conn.recvuntil(page_ends["login"])
    assert b"leave empty for guest" in data, "Login process broken"
    conn.send(password + terminator())
    data = conn.recvuntil(page_ends["home"])
    assert b"Input is being processed" in data, "Login process broken"
    assert b"Bildschirmtext" in data, "Login process broken"
    assert b"German Federal Postal Service" in data, "Login process broken"
    assert verify_page(get_cursors(data),"home"), "Could not access home page"


def register(conn, participant_number, salutation, ln, fn, street, zip_nr, city, password):
    login(conn)
    conn.send(b"7")
    data = conn.recvuntil(page_ends["create_user"])
    debug_print(data)
    get_cursors(data)
    try:
        assert verify_page(get_cursors(data),"create_user"), "Could not access user creation page"
        # participant number
        conn.send(participant_number + terminator())
        # There are 2 options here: either we're already registered (then we
        # get an error message and end_of_page()), or we are not (then we see
        # page_ends["create_user"] and can continue inserting data).
        data = conn.recvuntil([end_of_page(), page_ends["create_user"]])
        if b"Participant no. already assigned" in data:
            # If we are already registered, log out and go back to login
            print("User exists, skipping registration")
            # logout
            conn.send(terminator() + initiator() + b"8" + terminator())
            # receive logout page
            conn.recvuntil(page_ends["logout"])
            conn.recvuntil(page_ends["logout"])
            # go to login page
            conn.send(terminator())
            return
        # salutation
        conn.send(salutation + terminator())
        data = conn.recvuntil(page_ends["create_user"])
        # last name
        conn.send(ln + terminator())
        data = conn.recvuntil(page_ends["create_user"])
        # first name
        conn.send(fn + terminator())
        data = conn.recvuntil(page_ends["create_user"])
        # street
        conn.send(street + terminator())
        data = conn.recvuntil(page_ends["create_user"])
        # zip
        conn.send(zip_nr + terminator())
        data = conn.recvuntil(page_ends["create_user"])
        # shitty
        conn.send(city + terminator())
        data = conn.recvuntil(page_ends["create_user"])
        # country code
        conn.send(terminator())
        # password
        conn.send(password + terminator())
        data = conn.recvuntil(page_ends["create_user"])
        conn.send(terminator())
    except Exception:
        assert 0, "Register page broken"


def create_blog(conn, title, content, notes):
    conn.send(initiator() + b"31" + terminator())
    data = conn.recvuntil(page_ends["blog"])
    assert verify_page(get_cursors(data),"blog"), "Could not access blog creation page"
    assert b"Blogging Service" in data, "Could not access blog creation page"
    # title + f2
    conn.send(title + terminator())
    data = conn.recvuntil(page_ends["blog"])
    # Public? + f2
    conn.send(b"false" + terminator())
    data = conn.recvuntil(page_ends["blog"])
    # Private Notes + f2
    conn.send(notes + terminator())
    data = conn.recvuntil(page_ends["blog"])
    # content + f2
    conn.send(content + terminator())
    data = conn.recvuntil(end_of_page())
    assert b"Publish?" in data, "Blog create broken"
    # 19 + f2
    conn.send(b"19" + terminator())
    data = conn.recvuntil(page_ends["blog_overview"])
    assert verify_page(get_cursors(data),"blog_overview"),"Redirect after blog creation broken"


def retrieve_blog(conn, uid, title, content, notes, idx):
    conn.send(initiator() + b"33" + terminator())
    data = conn.recvuntil(end_of_page())
    # data = conn.recvall(timeout=1)

    assert b"Enter user id:" in data, "blog listing broken 1"
    conn.send(uid + terminator())
    data = conn.recvuntil(page_ends["blog_overview"])
    assert b"Blogs of" in data, "blog listing broken 2"
    assert title in data, "blog listing broken 3"
    conn.send(idx)
    data = conn.recvuntil(page_ends["blog_overview"])
    assert title in data, "unable to receive correct blog"
    if content not in data:
        # verbose error logging is always a good idea
        print('GOT:', data)
        # flag not found? Raise FlagMissingException
        if b"SAAR" in content:
            raise FlagMissingException('Flag not found')
        else: 
            raise MumbleException("unable to receive correct blog content")
    if notes not in data:
        # verbose error logging is always a good idea
        print('GOT:', data)
        # flag not found? Raise FlagMissingException
        if b"SAAR" in notes:
            raise FlagMissingException('Flag not found')
        else: 
            raise MumbleException("unable to receive correct blog content")
    debug_print(data)

def retrieve_blog_error(conn, uid, idx):
    conn.send(initiator() + b"33" + terminator())
    data = conn.recvuntil(end_of_page())
    assert b"Enter user id:" in data, "blog listing broken 1"
    conn.send(uid + terminator())
    data = conn.recvuntil(page_ends["blog_overview"])
    assert b"Blog Error" in data, "unable to retrieve blog error page"

def logout(conn):
    conn.send(initiator() + b"8" + terminator())
    conn.close()


class BTXServiceInterface(ServiceInterface):
    name = 'BTX'
    flag_id_types = ['choose_k_from:9:0123456789']

    def check_integrity(self, team: Team, tick: int):
        # a unique user id
        uid = str(random.randint(10,10**10))
        pw = usernames.generate_password(max_length=8)
        title = usernames.generate_name()
        content = usernames.generate_name()
        notes = usernames.generate_name()
        
        with remote_connection(team.ip, 1983) as conn:    
            register(conn,
                participant_number=uid.encode(),
                salutation=usernames.generate_random_string()[:3].encode(),
                ln=usernames.generate_name(words=1)[:18].encode(),
                fn=usernames.generate_name(words=1)[:18].encode(),
                street=(usernames.generate_name(words=1) + "str")[:15].encode(),
                zip_nr=str(random.randint(1,99999)).rjust(5,"0").encode(),
                city=(usernames.generate_name(words=1)+"stadt")[:12].encode(),
                password=pw.encode()
            )
            login(conn, uid.encode(), pw.encode())
            retrieve_blog_error(conn, uid.encode(), str(random.randint(1,9)).encode())
            logout(conn)

        with remote_connection(team.ip, 1983) as conn:
            login(conn, uid.encode(), pw.encode())
            create_blog(conn, title.encode(), content.encode(), notes.encode())
            retrieve_blog(conn, uid.encode(), title.encode(), content.encode(), notes.encode(), b"1")
            logout(conn)


    def store_flags(self, team: Team, tick: int):
        with remote_connection(team.ip, 1983) as conn:
            flag_id = self.get_flag_id(team, tick, 0)
            title = self.get_flag(team, tick, 0)
            notes = self.get_flag(team, tick, 1)

            # did we register this user already?
            # if so, re-use data. otherwise, register.
            user_info = self.load(team, tick, "user_info")
            if user_info:
                uid, pw, content = user_info
            else: 
                uid = str(flag_id)
                pw = usernames.generate_password(max_length=8)
                content = usernames.generate_name()
                self.store(team, tick, "user_info", [uid, pw, content])
                register(conn,
                    participant_number=uid.encode(),
                    salutation=usernames.generate_random_string()[:3].encode(),
                    ln=usernames.generate_name(words=1)[:18].encode(),
                    fn=usernames.generate_name(words=1)[:18].encode(),
                    street=(usernames.generate_name(words=1) + "str")[:15].encode(),
                    zip_nr=str(random.randint(1,99999)).rjust(5,"0").encode(),
                    city=(usernames.generate_name(words=1)+"stadt")[:12].encode(),
                    password=pw.encode()
                )

            login(conn, uid.encode(), pw.encode())
            create_blog(conn, title.encode(), content.encode(), notes.encode())
            logout(conn)


    def retrieve_flags(self, team: Team, tick: int):
        flag1 = self.get_flag(team, tick, 0)
        flag2 = self.get_flag(team, tick, 1)
        with remote_connection(team.ip, 1983) as conn:
            user_info = self.load(team, tick, "user_info")
            if not user_info:
                raise FlagMissingException("Flag not found (likely not stored last time).")
            uid, pw, content = user_info
            login(conn, uid.encode(), pw.encode())
            retrieve_blog(conn, uid.encode(), flag1.encode(), content.encode(), flag2.encode(), b"1")
            logout(conn)


if __name__ == '__main__':
    # USAGE: python3 interface.py                      # test against localhost
    # USAGE: python3 interface.py 1.2.3.4              # test against IP
    # USAGE: python3 interface.py 1.2.3.4 retrieve     # retrieve last 10 ticks (for exploits relying on checker interaction)
    # USAGE: python3 interface.py 1.2.3.4 store        # store a few ticks (for exploits relying on checker interaction)
    # (or use gamelib/run-checkers to test against docker container)
    team = Team(1, 'TestTeam', sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1')
    service = BTXServiceInterface(1)

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
