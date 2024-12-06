import random
import traceback

from gamelib import *
import sys

# See the "SampleServiceInterface" from gamelib for a bigger example
# See https://gitlab.saarsec.rocks/saarctf/gamelib/-/blob/master/docs/howto_checkers.md for documentation.

class ExampleServiceInterface(ServiceInterface):
    name = '8-bit-oracle'
    PORT = 17280

    def check_integrity(self, team: Team, tick: int):
        print("[Starting Checker]")
        HOST = team.ip
        with remote_connection(HOST, self.PORT) as s:
            try:
                print("[Sending faulty Message]")
                s.send(b'Hello World\n')
                data = s.recvline()
                # check for conditions - if an assert fails the service status is MUMBLE
                assert 'ERROR' in data.decode(), "Didn't get an Error Return on faulty message"

                print("[Sending MSG]")
                msg = "MSG " + get_question() + "\n"
                s.send(bytes(msg, "utf-8"))
                data = s.recvline()
                print(f'< {data}')
                assert 'MSG' in data.decode(), "Didn't get a Message Return"

                print("[Sending STATS]")
                s.send(b'STATS\n')
                data = s.recvline()
                print(f'< {data}')
                assert 'STATS' in data.decode(), "Didn't get a Stats Return"
                assert re.match(r'STATS [0-9a-fA-F]{7,8} \d+ \d+', data.decode()), "Missing Stats Parameters"

                print("[Sending REVIEW]")
                i_review = get_review()
                print(f"[Using Review {i_review}]")
                msg = "REVIEW " + i_review + "\n"
                s.send(bytes(msg, "utf-8"))
                data = s.recvline()
                print(f'< {data}')
                assert 'REVIEW' in data.decode(), "Didn't get a Review Return"
                assert re.match(r'REVIEW \d+:(?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$', data.decode()), "Missing Review Parameters"
                try:
                    id, key = data.decode().split(" ")[1].split(":")
                    key = key.strip()
                except:
                    print(f'Data: {data!r}')
                    assert False, "?"

                print("[Sending CHALLENGE]")
                msg = "CHALLENGE " + id + "\n"
                s.send(bytes(msg, "utf-8"))
                challenge = s.recvline().decode("utf-8").split(" ", 1)[1]
                print(f'< {challenge}')
                assert re.match(r'(?:[A-Za-z0-9+\/]{4})*(?:[A-Za-z0-9+\/]{4}|[A-Za-z0-9+\/]{3}=|[A-Za-z0-9+\/]{2}={2})$', challenge), "Invalid Challenge Format"

                print("[Sending DECRYPT]")
                msg = f"DECRYPT {key}:{challenge}\n"
                s.send(bytes(msg, "utf-8"))
                dec_chall = s.recvline().decode("utf-8").split(" ", 2)[1]
                print(f'< {dec_chall}')
                assert re.match(r'[0-9a-fA-F]+', dec_chall), "Invalid Decrypted Challenge Format"

                print("[Sending GETREVIEW]")
                msg = f"GETREVIEW {id}:{dec_chall}\n"
                s.send(bytes(msg, "utf-8"))
                review = s.recvline().decode().split(" ", 1)[1].strip()
                print(f'< {review}')
                print(f"[Receiving Review {review}]")
                assert review == i_review, "Returned incorrect review"
            except (KeyError, UnicodeError) as e:
                # service sends invalid exceptions (split()[] or decode() failed)
                traceback.print_exc()
                raise MumbleException("invalid response") from e

        print("[Finished Checker]")

    def store_flags(self, team: Team, tick: int):
        flag = self.get_flag(team, tick)
        with remote_connection(team.ip, self.PORT) as s:
            try:
                print("[Storing Flag]")
                msg = "REVIEW " + flag + "\n"
                s.send(bytes(msg, "utf-8"))
                print("[Sent Message]", msg)
                data = s.recvline()
                print(f'< {data}')
                id, key = data.decode().split(" ")[1].split(":")
                self.store(team, tick, "creds", [id, key])
                print("[Received And Stored Data]", data)
            except (KeyError, UnicodeError) as e:
                # service sends invalid exceptions (split()[] or decode() failed)
                traceback.print_exc()
                raise MumbleException("invalid response") from e

    def retrieve_flags(self, team: Team, tick: int):
        flag = self.get_flag(team, tick)
        with remote_connection(team.ip, self.PORT) as s:
            print("[Retrieving Flag]")
            try:
                data = self.load(team, tick, "creds")
                id, key = data
                key = key.strip()
            except TypeError:
                raise FlagMissingException('Not Stored')
            print("[Retrieved ID]", id)
            print("[Retrieved Key]", key)
            try:
                msg = "CHALLENGE " + id + "\n"
                s.send(bytes(msg, "utf-8"))
                print("[Sent Challenge Request]", msg)
                challenge = s.recvline().decode("utf-8").split(" ", 1)[1].strip()
                print("[Received Challenge]", challenge)
                msg = f"DECRYPT {key}:{challenge}\n"
                s.send(bytes(msg, "utf-8"))
                print("[Sent Decrypt]", msg)
                dec_chall = s.recvline().decode("utf-8").split(" ", 2)[1].strip()
                print("[Received Decrypted Challenge]", dec_chall)
                msg = f"GETREVIEW {id}:{dec_chall}\n"
                s.send(bytes(msg, "utf-8"))
                print("[Sent GetReview]", msg)
                review = s.recvline().decode().split(" ", 1)[1]
                if flag != review.strip():
                    # verbose error logging is always a good idea
                    print('GOT:', review)
                    # flag not found? Raise FlagMissingException
                    raise FlagMissingException('Flag not found')
            except (KeyError, UnicodeError) as e:
                # service sends invalid exceptions (split()[] or decode() failed)
                traceback.print_exc()
                raise MumbleException("invalid response") from e

def get_question():
    funny_questions = [
        "If you were a vegetable, would you be a cute-cumber or a dill-ightful pickle?",
        "Do you believe in love at first swipe?",
        "If life gives you lemons, do you make lemonade or squirt them in someone's eye?",
        "Would you rather fight one horse-sized duck or a hundred duck-sized horses?",
        "If you could only eat one food for the rest of your life, would it be pizza or tacos?",
        "If you could be any mythical creature, would you be a unicorn or a dragon?",
        "Do you think aliens have social media profiles and just haven't added us yet?",
        "If animals could talk, which would be the rudest?",
        "Would you rather sneeze confetti or burp glitter?",
        "If you could only listen to one song for the rest of your life, would it be 'Never Gonna Give You Up' by Rick Astley or 'What Does The Fox Say?' by Ylvis?",
        "Do you think plants gossip about us when we're not around?",
        "Would you rather have a rewind button for your life or a pause button?",
        "If you could swap lives with any fictional character, who would it be?",
        "Do you believe in Bigfoot, or do you think he's just really good at hide and seek?",
        "Would you rather fight 100 chicken-sized zombies or 10 zombie-sized chickens?",
        "If you could only speak in emojis for a day, how would you communicate?",
        "Do you think that cereal is soup?",
        "Would you rather have a flying carpet or a teleportation device?",
        "If you could have any superpower, but it had to be completely useless, what would it be?",
        "Do you believe in karma, or do you think it's just a way for people to feel better about being mean?",
        "Would you rather have a rewind button for your life or a pause button?",
        "Do you think dogs have their own version of the internet where they share pictures of their owners?",
        "If you could only wear one color for the rest of your life, what would it be?",
        "Would you rather fight a hundred duck-sized horses or one horse-sized duck?",
        "If you could only eat one cuisine for the rest of your life, what would it be?",
        "Do you think that aliens have ever visited Earth disguised as humans?",
        "If you could have dinner with any fictional character, who would it be?",
        "Would you rather have fingers for toes or toes for fingers?",
        "Do you believe in ghosts, or do you think it's just your mind playing tricks on you?",
        "If you could have any celebrity be your personal assistant for a day, who would it be?",
        "Would you rather have a rewind button for your life or a pause button?",
        "Do you think that aliens have ever visited Earth disguised as humans?",
        "If you could have dinner with any fictional character, who would it be?",
        "Would you rather have fingers for toes or toes for fingers?",
        "Do you believe in ghosts, or do you think it's just your mind playing tricks on you?",
        "If you could have any celebrity be your personal assistant for a day, who would it be?",
        "Would you rather have a rewind button for your life or a pause button?",
        "Do you believe in ghosts, or do you think it's just your mind playing tricks on you?",
        "If you could have dinner with any fictional character, who would it be?",
        "Would you rather have fingers for toes or toes for fingers?",
        "Do you believe in ghosts, or do you think it's just your mind playing tricks on you?",
        "If you could have any celebrity be your personal assistant for a day, who would it be?",
        "Would you rather have a rewind button for your life or a pause button?",
        "Do you think that aliens have ever visited Earth disguised as humans?",
        "If you could have dinner with any fictional character, who would it be?",
        "Would you rather have fingers for toes or toes for fingers?",
        "Do you believe in ghosts, or do you think it's just your mind playing tricks on you?",
        "If you could have any celebrity be your personal assistant for a day, who would it be?",
        "Would you rather have a rewind button for your life or a pause button?",
        "Do you think that aliens have ever visited Earth disguised as humans?",
        "If you could have dinner with any fictional character, who would it be?",
        "Would you rather have fingers for toes or toes for fingers?",
        "Do you believe in ghosts, or do you think it's just your mind playing tricks on you?",
        "If you could have any celebrity be your personal assistant for a day, who would it be?",
        "Would you rather have a rewind button for your life or a pause button?",
        "Do you think that aliens have ever visited Earth disguised as humans?",
        "If you could have dinner with any fictional character, who would it be?",
        "Would you rather have fingers for toes or toes for fingers?",
        "Do you believe in ghosts, or do you think it's just your mind playing tricks on you?",
        "If you could have any celebrity be your personal assistant for a day, who would it be?",
        "Would you rather have a rewind button for your life or a pause button?",
        "Do you think that aliens have ever visited Earth disguised as humans?",
        "If you could have dinner with any fictional character, who would it be?",
        "Would you rather have fingers for toes or toes for fingers?",
        "Do you believe in ghosts, or do you think it's just your mind playing tricks on you?",
        "If you could have any celebrity be your personal assistant for a day, who would it be?",
        "Would you rather have a rewind button for your life or a pause button?",
        "Do you think that aliens have ever visited Earth disguised as humans?",
        "If you could have dinner with any fictional character, who would it be?",
        "Would you rather have fingers for toes or toes for fingers?",
        "Do you believe in ghosts, or do you think it's just your mind playing tricks on you?",
        "If you could have any celebrity be your personal assistant for a day, who would it be?",
        "Would you rather have a rewind button for your life or a pause button?",
        "Do you think that aliens have ever visited Earth disguised as humans?",
        "If you could have dinner with any fictional character, who would it be?",
        "Would you rather have fingers for toes or toes for fingers?",
        "Do you believe in ghosts, or do you think it's just your mind playing tricks on you?",
        "If you could have any celebrity be your personal assistant for a day, who would it be?",
        "Would you rather have a rewind button for your life or a pause button?",
        "Do you think that aliens have ever visited Earth disguised as humans?",
        "If you could have dinner with any fictional character, who would it be?",
        "Would you rather have fingers for toes or toes for fingers?",
    ]
    return random.choice(funny_questions)

def get_review():
    funny_reviews = [
        "I asked the 8-bit oracle if I should wear socks today. It said '01101100 01101111 01101100', so I'm going sockless!",
        "I consulted the 8-bit oracle about whether I should order pizza or sushi for dinner. It replied with '01010000 01101001 01111010 01111010 01100001'. Pizza it is!",
        "I asked the 8-bit oracle if I should go to the gym. It answered with '01011001 01100101 01110011'. I'll take that as a yes... or a maybe.",
        "The 8-bit oracle said '01001001 00100000 01100100 01101111 01101110 00100111 01110100 00100000 01101011 01101110 01101111 01110111 00101110'. I'm not sure what that means, but I'm taking it as a sign to stay home.",
        "I consulted the 8-bit oracle about whether I should buy that expensive gadget. It said '01001110 01101111'. Looks like I'm saving some money today!",
        "The 8-bit oracle replied '01001001 01110100 00100000 01101001 01110011 00100000 01100111 01100101 01101101 01110011' when I asked if I should watch another episode. I guess I'm binge-watching tonight!",
        "I asked the 8-bit oracle if I should tell my crush how I feel. It said '01001110 01101111'. Looks like I'm keeping my feelings to myself for now.",
        "The 8-bit oracle said '01001000 01100001 01110110 01100101 00100000 01100001 01101110 00100000 01100101 01111000 01110100 01110010 01100001 00100001' when I asked if I should try skydiving. I'm taking that as a yes!",
        "I consulted the 8-bit oracle about whether I should adopt a cat. It replied with '01011001 01100101 01110011'. Looks like I'm becoming a cat parent!",
        "The 8-bit oracle answered '01001001 01110100 00100000 01101001 01110011 00100000 01100001 01110011 01101011 01101001 01101110 01100111 00101110' when I asked if I should eat the last slice of cake. Looks like it's mine!",
    ]
    return random.choice(funny_reviews)

if __name__ == '__main__':
    # USAGE: python3 interface.py                      # test against localhost
    # USAGE: python3 interface.py 1.2.3.4              # test against IP
    # USAGE: python3 interface.py 1.2.3.4 retrieve     # retrieve last 10 ticks (for exploits relying on checker interaction)
    # (or use gamelib/run-checkers to test against docker container)
    team = Team(1, 'TestTeam', sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1')
    service = ExampleServiceInterface(1)

    if len(sys.argv) > 2 and sys.argv[2] == 'retrieve':
        for tick in range(1, 10):
            try:
                service.retrieve_flags(team, tick)
            except:
                pass
        sys.exit(0)

    for tick in range(1, 4):
        print(f'\n\n=== TICK {tick} ===')
        service.check_integrity(team, tick)
        service.store_flags(team, tick)
        service.retrieve_flags(team, tick)
