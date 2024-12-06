## Service overview:
The service is a socket based java application that uses a simple plaintext protocol ontop.

The basics of the service are that people can interact with a oracle that can answer yes/no questions in a style similar to an "8 Ball". The service provides also a client writting in python.

### Protocol Structure:

`<command> <params>`

### List of commands
- `MSG <msg>` | Used for questions and answers
- `STATS` | Used to check connections / bot stats
- `REVIEW <review_text>` | Used to create reviews
- `GETREVIEW <id>:<decrypted_challenge>` | Used to read reviews
- `CHALLENGE <review_id>` | Used internally by client/server for "security"
- `DECRYPT <private_key>:<challenge>` | Used internally by client/server for "security"
- `LIST <page_number>` | List (max 25) reviews (starts at 0)
- `ERROR <error message>` | Used when the server wants to return an error 

#### A sample message would like like this:

client -> server: `MSG Is saarsec the best CTF team?`

server -> client: `MSG I'm not just an 8-ball; I'm a 'no' ball.`

### How the review system works internally

The service is using a sqlite database as the backend and for encryption asymmetric crypto. When a user submits a review they get back a pair of values `(id:private_key)`. If a user wants to retreive a review all they need is this pair. First they need to ask the server for a challenge with `CHALLENGE <id>` where `<id>`is the id of the review they want a challenge for. Then they need to decrypt the challenge with the respective private key they have for that id with `DECRYPT <private_key>:<challenge>`. The user should get back a value that they can use to retrieve a specific review with `GETREVIEW <id>:<decrypted_challenge>`. Now the user should see the review again. All of this is wrapped inside the client.

## Exploit overview:
### Breaking LFSR in Java:
Java uses linear congruential generator (LCG) for it's randomness. The problem with LCG's is that they are prone to `state reversing ` attacks. This is due to the fact that LCG's aren't truly random but act similar to finite state automate. Where they are in one state then move to another state and so one. The key here is that these states are finite and that they are circular. Meaning that somepoint they "random" numbers will repeat. Now if we have enough information on the numbers the LCG produces we can infer in which state we are in and thus predict future value of the random number generator. Applying this to the service we see that the challenge is created by these LCG's and we can use the `STATS` command to retreive values to reversing the state of the LCG. Then after reversing the state we reroll the challenge by supplying a wrong challenge. After this the reversed state and the server random state are the same. Now we can supply our predicted value and thus break the challenge based review system. 