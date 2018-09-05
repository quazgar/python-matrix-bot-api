import traceback
import re
from matrix_client.client import MatrixClient
from matrix_client.room import Room
from matrix_client.api import MatrixRequestError


class MatrixBotAPI:

    # username - Matrix username
    # password - Matrix password
    # server   - Matrix server url : port
    # rooms    - List of rooms ids to operate in, or None to accept all rooms
    def __init__(self, username, password, server,
                 rooms=None, exclusive_rooms=True):
        self.username = username

        # Authenticate with given credentials
        self.client = MatrixClient(server)
        try:
            self.client.login_with_password(username, password)
        except MatrixRequestError as e:
            print(e)
            if e.code == 403:
                print("Bad username/password")
        except Exception as e:
            print("Invalid server URL")
            traceback.print_exc()

        # Store empty list of handlers
        self.handlers = []

        # If rooms is None, we should listen for invites and automatically accept them
        if rooms is None:
            self.client.add_invite_listener(self.handle_invite)
        else:
            old_rooms = self.client.get_rooms()
            new_rooms = []
            # Add the message callback for all specified rooms
            for room in rooms:
                if isinstance(room, str):
                    room = Room(self.client, room)
                new_rooms.append(room)
            # Remove existing rooms which were not specified explicitly
            new_ids = [r.room_id for r in new_rooms]
            if exclusive_rooms:
                rooms_to_leave = []
                for room_id, room in old_rooms.items():
                    if not room_id in new_ids:
                        rooms_to_leave.append(room)
                for room in rooms_to_leave:
                    room.leave()

        # Store clean list of allowed rooms
        self.rooms = []
        # Add all rooms we're currently in to self.rooms and add their callbacks
        for room_id, room in self.client.get_rooms().items():
            room.add_listener(self.handle_message)
            self.rooms.append(room_id)

    def add_handler(self, handler):
        self.handlers.append(handler)

    def handle_message(self, room, event):
        # Make sure we didn't send this message
        if re.match("@" + self.username, event['sender']):
            return

        # Loop through all installed handlers and see if they need to be called
        for handler in self.handlers:
            if handler.test_callback(room, event):
                # This handler needs to be called
                try:
                    handler.handle_callback(room, event)
                except:
                    traceback.print_exc()

    def handle_invite(self, room_id, state):
        print("Got invite to room: " + str(room_id))
        print("Joining...")
        room = self.client.join_room(room_id)

        # Add message callback for this room
        room.add_listener(self.handle_message)

        # Add room to list
        self.rooms.append(room)

    def start_polling(self):
        # Starts polling for messages
        self.client.start_listener_thread()
        return self.client.sync_thread
