import urwid
import socket


class MyListBox(urwid.ListBox):
    def focus_next(self):
        try:
            self.body.set_focus(self.body.get_next(self.body.get_focus()[1])[1])
        except:
            pass

    def focus_previous(self):
        try:
            self.body.set_focus(self.body.get_orev(self.body.get_focus()[1])[1])
        except:
            pass


def add_line(text):
    global vary
    vary += 1
    if vary > 2:
        listbox_walker.prepend(urwid.Pile([urwid.AttrMap(urwid.Text(text), 'dark')]))
    elif vary > 0:
        listbox_walker.prepend(urwid.Pile([urwid.AttrMap(urwid.Text(text), 'light')]))
    if vary == 4:
        vary = 0


def reset_chat():
    chat_widget.original_widget.set_edit_text("")


def add_question():
    add_line(current_question)
    reset_chat()


def submit_question(question):
    current_question = question.upper()
    query_list = current_question.split(" ")
    query = query_list[0]
    match query:
        case "STATS":
            send("STATS")
        case "HELP":
            parse_response(b"HELP")
            return
        case "REVIEW":
            send("REVIEW " + question.split(" ", 1)[1])
        case "READ":
            review_id = query_list[1]
            send(f"CHALLENGE {review_id}")
            res = s.recv(2048)
            global challenge
            challenge = res.decode("utf-8").split(" ", 1)[1]
            send(f"DECRYPT {reviews[review_id]}:{challenge}")
            dec_chall = s.recv(2048).decode("utf-8").split(" ", 2)[1]
            send(f"GETREVIEW {review_id}:{dec_chall}")
        case "LIST":
            parse_response(b"LIST_OWN")
            return
        case "REVIEW_IDS":
            send("LIST " + question.split(" ", 1)[1])
        case _:
            send("MSG " + question)
    response = s.recv(2048)
    parse_response(response)


def send(msg):
    s.sendall(bytes(msg + "\n", 'utf-8'))


def parse_stats_response(response):
    output = ""
    response = response.split(" ")
    output += "Your Unique User ID: "
    output += response[1]
    output += "\n"
    output += "Questions asked: "
    output += response[2]
    output += "\n"
    output += "Clients connected: "
    output += response[3]
    output = output[:-1]
    return output


def parse_help_response(response):
    output = ""
    output += "Type HELP to call this menu.\n"
    output += "Type STATS to receive up-to-date statistics.\n"
    output += "Type REVIEW [message here] to leave confidential feedback for 8-Ball.\n"
    output += "Type READ [id here] to read the feedback you left.\n"
    output += "Type LIST to list all your submitted feedback.\n"
    output += "Type REVIEW_IDS [pagenumber here] to see all IDs of other reviews.\n"
    output += "Type anything else to send a message to the 8-Ball server.\n"
    output += "To scroll through the chat, left click on the message area and use the UP/DOWN Arrow keys.\n"
    output += "To resume chatting, left click in the chat window at the bottom of your terminal."
    return output


def parse_list_own_response(response):
    output = ""
    if len(reviews) == 0:
        output += "You have not left any feedback yet.\n"
        return output
    output += f"Your feedback IDs are: {list(reviews.keys())}"
    return output


def parse_list_response(response):
    output = ""
    output += f"Reviewer IDs on the requested page are: {response.split(' ')[1]}"
    return output


def parse_message_response(response):
    output = ""
    response = response[4:]
    output += response[:-1]
    return output


def parse_review_response(response):
    response = response.split(" ")[1].split(":")
    global review_id
    review_id = response[0]
    global priv_key
    priv_key = response[1]
    reviews[review_id] = priv_key.strip()
    return f"Review with ID {review_id} successfully submitted!"


def parse_read_response(response):
    output = ""
    output += f"Review #{review_id}:\n"
    output += response.split(" ", 1)[1]
    return output


def parse_response(response):
    response = response.decode("utf-8")
    output = ""
    response_type = response.split(" ")[0]
    match response_type:
        case "ERROR":
            output += "An error occurred."
        case "STATS":
            output += parse_stats_response(response)
        case "HELP":
            output += parse_help_response(response)
        case "MSG":
            output += parse_message_response(response)
        case "REVIEW":
            output += parse_review_response(response)
        case "GETREVIEW":
            output += parse_read_response(response)
        case "LIST_OWN":
            output += parse_list_own_response(response)
        case "LIST":
            output += parse_list_response(response)
        case _:
            output += "Unknown Response Type received."
    add_line(output)
    order()


def order():
    listbox_walker[0], listbox_walker[1] = listbox_walker[1], listbox_walker[0]


class ChatBox(urwid.Edit):
    def keypress(self, size: tuple[int], key: str):
        if key in useless:
            return None
        global current_question
        if key != "enter":
            current_question += key
            if key == "backspace":
                current_question = current_question.replace("backspace", "")[:-1]
            super().keypress(size, key)
            return None
        if current_question:
            add_question()
            submit_question(current_question)
        current_question = ""


class AdvancedListWalker(urwid.SimpleListWalker):
    def prepend(self, item: urwid.Pile):
        self.reverse()
        self.append(item)
        self.reverse()


reviews = {}
current_question = ""
vary = 0
useless = ["up", "down", "right", "left", "ctrl", "alt", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12", "esc", "tab",]
header_widget = urwid.AttrMap(urwid.Text("Welcome to the Interactive 8-Ball chat! CTRL+C to exit."), 'header')
output_widget = urwid.Pile([urwid.AttrMap(urwid.Text("Ask a question to get started!\nType STATS for statistics, HELP for help."), 'dark')])
chat_widget = urwid.AttrMap(ChatBox(""), 'chat')
listbox_content = [output_widget]
listbox_walker = AdvancedListWalker(listbox_content)
listbox = MyListBox(listbox_walker)
frame_widget = urwid.Frame(
    header=header_widget,
    body=listbox,
    footer=chat_widget,
    focus_part="footer"
)
palette = [
    ('chat', 'black', 'light gray'),
    ('header', 'white', 'dark blue'),
    ('light', 'black', 'white'),
    ('dark', 'white', 'black')
]
full = ChatBox()
loop = urwid.MainLoop(frame_widget, palette=palette)

HOST = 'localhost'
PORT = 17280
ADDRESS = (HOST, PORT)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(ADDRESS)


def run():
    loop.run()
